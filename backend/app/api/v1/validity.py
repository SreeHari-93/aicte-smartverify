from datetime import datetime, date, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.document_validity import DocumentValidityRecord
from backend.app.schemas.stage3 import (
    LeaseUpdatePayload,
    RenewalDecisionRequest,
    ValidityRecordResponse,
)
from backend.app.api.deps import get_current_user, require_role
from backend.app.services.validity_service import ValidityService

STAFF_ROLES = [
    UserRole.ADMIN,
    UserRole.REGIONAL_OFFICER,
    UserRole.BUREAU_OFFICER,
    UserRole.REVIEWER,
]
require_staff_role = require_role(STAFF_ROLES)


router = APIRouter(tags=["Document Validity & Lease Governance"])


def serialize_validity(r: DocumentValidityRecord) -> Dict[str, Any]:
    inst = r.institute
    app = r.application
    return {
        "id": r.id,
        "document_id": r.document_id,
        "institute_id": r.institute_id,
        "institute_name": inst.name if inst else "Registered Institution",
        "institute_state": inst.state if inst else "Unknown",
        "application_id": r.application_id,
        "application_code": app.application_id if app else None,
        "document_type_code": r.document_type_code,
        "document_name": r.document_name,
        "certificate_number": r.certificate_number,
        "issuing_authority": r.issuing_authority,
        "issue_date": str(r.issue_date) if r.issue_date else None,
        "expiry_date": str(r.expiry_date) if r.expiry_date else None,
        "status": r.status,
        "days_left": r.days_left,
        "expiring_soon_window_days": r.expiring_soon_window_days,
        "renewal_document_id": r.renewal_document_id,
        "renewal_status": r.renewal_status,
        "renewal_submitted_at": r.renewal_submitted_at,
        "renewal_decision_reason": r.renewal_decision_reason,
        "is_lease": r.is_lease,
        "lessor": r.lessor,
        "lessee": r.lessee,
        "lease_start": str(r.lease_start) if r.lease_start else None,
        "lease_end": str(r.lease_end) if r.lease_end else None,
        "property_address": r.property_address,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


@router.get("")
@router.get("/")
def list_validity_records(
    region: Optional[str] = Query(None),
    institute_id: Optional[int] = Query(None),
    document_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_lease: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List monitored validity records.
    Institutes are isolated to their own records; staff can filter across region, institute, type, and status.
    Committee members are restricted.
    """
    if current_user.role == UserRole.COMMITTEE_MEMBER:
        raise HTTPException(
            status_code=403,
            detail="Committee members do not have access to document validity management.",
        )
    records = ValidityService.list_records(
        db=db,
        user=current_user,
        region=region,
        institute_id=institute_id,
        document_type=document_type,
        status=status,
        is_lease=is_lease,
        search=search,
    )
    return [serialize_validity(r) for r in records]


@router.post("/{record_id}/renew")
def renew_document(
    record_id: int,
    request: Request,
    renewal_file: UploadFile = File(...),
    new_issue_date: str = Form(...),
    new_expiry_date: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit renewed document certificate linked to an existing monitored document record.
    """
    try:
        issue_d = datetime.strptime(new_issue_date.strip()[:10], "%Y-%m-%d").date()
        expiry_d = datetime.strptime(new_expiry_date.strip()[:10], "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    rec = ValidityService.submit_renewal(
        db=db,
        record_id=record_id,
        renewal_file=renewal_file,
        new_issue_date=issue_d,
        new_expiry_date=expiry_d,
        user=current_user,
        request=request,
    )
    return serialize_validity(rec)


@router.post("/{record_id}/decide-renewal")
def decide_renewal(
    record_id: int,
    payload: RenewalDecisionRequest,
    request: Request,
    current_user: User = Depends(require_staff_role),
    db: Session = Depends(get_db),
):
    """
    Accept or reject submitted document renewal with mandatory statutory reason.
    """
    rec = ValidityService.decide_renewal(
        db=db,
        record_id=record_id,
        action=payload.action,
        reason=payload.reason,
        new_expiry_date=payload.new_expiry_date,
        user=current_user,
        request=request,
    )
    return serialize_validity(rec)


@router.patch("/{record_id}/lease")
def update_lease_details(
    record_id: int,
    payload: LeaseUpdatePayload,
    request: Request,
    current_user: User = Depends(require_staff_role),
    db: Session = Depends(get_db),
):
    """
    Update editable lease deed registration metadata.
    """
    rec = ValidityService.update_lease_fields(
        db=db,
        record_id=record_id,
        lessor=payload.lessor,
        lessee=payload.lessee,
        lease_start=payload.lease_start,
        lease_end=payload.lease_end,
        property_address=payload.property_address,
        user=current_user,
        request=request,
    )
    return serialize_validity(rec)
