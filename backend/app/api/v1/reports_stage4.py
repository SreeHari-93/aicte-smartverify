import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.application import Application
from backend.app.models.workflow import ApplicationWorkflow
from backend.app.models.institute import Institute
from backend.app.api.deps import get_current_user
from backend.app.services.consolidated_report_service import (
    ConsolidatedReportService,
    REPORT_TYPES,
    normalize_region,
    CANONICAL_REGIONS,
)
from backend.app.services.audit_service import AuditService

logger = logging.getLogger("aicte.reports_api")
router = APIRouter(prefix="/reports", tags=["Consolidated Reports"])


@router.get("/consolidated/list")
def list_consolidated_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available consolidated statutory reports."""
    return ConsolidatedReportService.list_report_types()


@router.get("/applications")
def list_report_applications(
    region: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List applications for the application summary report dropdown.
    - Admin & Bureau Officer see all applications (or filter by chosen region).
    - Regional Officer only sees applications in their assigned region (locked).
    - Committee member sees only assigned applications.
    - Ordered by newest first.
    - Option label format: 'APP-2026-S01 · Institute name · Stage'.
    """
    if current_user.role == UserRole.INSTITUTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institutes cannot access this administrative application list."
        )

    user_canonical_region = normalize_region(current_user.region) if current_user.region else None
    req_canonical_region = normalize_region(region)

    if current_user.role == UserRole.REGIONAL_OFFICER:
        if req_canonical_region and user_canonical_region and req_canonical_region != user_canonical_region:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regional officers may only access applications in their assigned region."
            )
        effective_region = user_canonical_region
    elif current_user.role in (UserRole.ADMIN, UserRole.BUREAU_OFFICER, UserRole.REVIEWER):
        effective_region = req_canonical_region
    else:
        effective_region = None

    query = (
        db.query(Application, ApplicationWorkflow, Institute)
        .outerjoin(ApplicationWorkflow, Application.id == ApplicationWorkflow.application_id)
        .outerjoin(Institute, Application.institute_id == Institute.id)
    )

    if current_user.role == UserRole.COMMITTEE_MEMBER:
        query = query.filter(ApplicationWorkflow.assigned_officer_id == current_user.id)

    # Order newest first
    query = query.order_by(desc(Application.id))
    results_raw = query.all()

    items: List[Dict[str, Any]] = []
    for app, wf, inst in results_raw:
        app_region = normalize_region(wf.region) if (wf and wf.region) else (normalize_region(inst.state) if (inst and inst.state) else "Southern")
        if effective_region and app_region != effective_region:
            continue

        stage_name = wf.current_stage_name if wf else "Stage 1: AI Scrutiny"
        inst_name = inst.name if inst else "Unknown Institute"

        items.append({
            "id": app.id,
            "application_id": app.application_id,
            "institute_id": app.institute_id,
            "institute_name": inst_name,
            "stage": stage_name,
            "region": app_region or "Southern",
            "category": app.category or "General",
            "status": app.status or "SUBMITTED",
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "label": f"{app.application_id} · {inst_name} · {stage_name}",
        })

    return items


@router.get("/consolidated/export")
def export_consolidated_report(
    report_type: str = Query(..., description="Report type identifier"),
    format: str = Query("PDF", pattern="^(PDF|CSV)$"),
    region: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export consolidated report as PDF or CSV.
    Enforces regional jurisdiction guards for Regional Officers.
    """
    if current_user.role == UserRole.INSTITUTE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institutes cannot download administrative consolidated reports."
        )

    if report_type not in REPORT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report type '{report_type}'."
        )

    user_canonical_region = normalize_region(current_user.region) if current_user.region else None
    req_canonical_region = normalize_region(region)

    if current_user.role == UserRole.REGIONAL_OFFICER:
        if req_canonical_region and user_canonical_region and req_canonical_region != user_canonical_region:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regional officers may only access reports for their assigned region."
            )
        effective_region = user_canonical_region
    else:
        effective_region = req_canonical_region

    # Parse dates if provided
    start_date_obj: Optional[date] = None
    end_date_obj: Optional[date] = None
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date.strip()[:10], "%Y-%m-%d").date()
        except Exception:
            pass
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date.strip()[:10], "%Y-%m-%d").date()
        except Exception:
            pass

    AuditService.log(
        db=db,
        action="CONSOLIDATED_REPORT_EXPORTED",
        user_id=current_user.id,
        role=current_user.role,
        details={
            "report_type": report_type,
            "format": format,
            "region": effective_region,
            "start_date": start_date,
            "end_date": end_date,
        },
        reason=f"Official {format} report '{report_type}' exported by {current_user.email}"
    )

    filename_prefix = f"AICTE_{report_type.upper()}_{(effective_region or 'NATIONAL').upper()}"

    if format == "CSV":
        csv_data = ConsolidatedReportService.generate_csv(
            db,
            report_type,
            region=effective_region,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename_prefix}.csv"'}
        )
    else:
        pdf_bytes = ConsolidatedReportService.generate_pdf(
            db,
            report_type,
            region=effective_region,
            start_date=start_date_obj,
            end_date=end_date_obj,
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename_prefix}.pdf"'}
        )
