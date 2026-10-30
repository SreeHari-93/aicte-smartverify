import hashlib
import os
import uuid
from datetime import datetime, timezone, date
from typing import Optional, List, Any, Dict, Union
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Response, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.certificate import Certificate, CertificateRenewal
from backend.app.models.course import Course
from backend.app.models.accreditation import Accreditation
from backend.app.models.rule import Rule, RuleSet
from backend.app.models.document import Document
from backend.app.models.document_page import DocumentPage
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.document_classification import DocumentClassification
from backend.app.models.document_type import DocumentType
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.complaint import Complaint, ComplaintEvent
from backend.app.models.notification import Notification
from backend.app.models.report import Report
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.services.audit_service import AuditService
from backend.app.services.report_service import ReportService
from backend.app.services.document_pipeline.ocr import OCRService
from backend.app.services.document_pipeline.readiness import ReadinessService
from backend.app.services.validation.runner import ValidationRunner
from backend.app.services.explainer.root_cause import RootCauseAnalyzer
from backend.app.services.explainer.narrator import ExplainerNarrator
from backend.app.services.verification import (
    VerificationService,
    VerificationResponseOut,
)
from backend.app.services.anomaly import (
    AnomalyService,
    InstituteAnomalyFlagOut,
    EvidenceGraphBuilder,
    EvidenceGraphResponse,
)
from backend.app.api.deps import get_current_user

from backend.app.schemas.institute import (
    InstituteDashboardResponse,
    StatCount,
    CertificateListResponse,
    CertificateItem,
    CertificateStats,
    UpcomingExpiryItem,
    CertificateRenewRequest,
    ApplicationListResponse,
    ApplicationItem,
    ApplicationStats,
    CreateApplicationDraft,
    RuleGroup,
    RuleItem,
    RuleSummary,
    RulesResponse,
    DocumentItem,
    DocumentPageOut,
    DocumentOCRResponse,
    DocumentReprocessResponse,
    CandidateOut,
    ClassificationOut,
    ExtractedFieldOut,
    DocumentExtractionResponse,
    FieldCorrectionRequest,
    FieldCorrectionResponse,
    ApplicationReadinessResponse,
    InstituteChecklistItem,
    InstituteChecklistResponse,
    ValidationResponse,
    ValidationCheckItem,
    ValidationFindingOut,
    ValidationRunDiffOut,
    ValidationRunResponse,
    ValidationRunSummaryOut,
    WhyFailedResponse,
    RootCauseOut,
    HowToFixItem,
    WhyFailedReasonOut,
    ComplaintItem,
    CreateComplaintRequest,
    InstituteComplaintReplyRequest,
    ReportItem,
    GenerateReportRequest,
    NotificationItem,
)

router = APIRouter(prefix="/institute", tags=["Institute Portal"])

DOCUMENT_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../storage/documents"))
os.makedirs(DOCUMENT_STORAGE_DIR, exist_ok=True)


def get_current_institute_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency ensuring user is an INSTITUTE user with an assigned institute_id"""
    if current_user.role != UserRole.INSTITUTE or not current_user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: This resource is restricted to authorized Institute accounts only.",
        )
    return current_user


# ==============================================================================
# 1. DASHBOARD ENDPOINT
# ==============================================================================
@router.get("/dashboard", response_model=InstituteDashboardResponse)
def get_dashboard(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    institute = db.query(Institute).filter(Institute.id == user.institute_id).first()
    if not institute:
        raise HTTPException(status_code=404, detail="Institute record not found.")

    # Calculate Application stats
    apps = db.query(Application).filter(Application.institute_id == user.institute_id).all()
    filed_count = len(apps)
    approved_count = sum(1 for a in apps if a.status == "APPROVED")
    pending_count = sum(1 for a in apps if a.status in ["DRAFT", "SUBMITTED", "UNDER_REVIEW"])
    rejected_count = sum(1 for a in apps if a.status == "REJECTED")

    # Accreditation
    accreditation = db.query(Accreditation).filter(Accreditation.institute_id == user.institute_id).first()

    # Courses
    courses = db.query(Course).filter(Course.institute_id == user.institute_id).all()

    return InstituteDashboardResponse(
        institute_id=institute.id,
        aicte_institute_id=institute.aicte_institute_id,
        name=institute.name,
        state=institute.state,
        stats=StatCount(
            filed=filed_count,
            approved=approved_count,
            pending=pending_count,
            rejected=rejected_count,
        ),
        accreditation=accreditation,
        courses=courses,
    )


# ==============================================================================
# 2. CERTIFICATE EXPIRY ENDPOINTS
# ==============================================================================
@router.get("/certificates", response_model=CertificateListResponse)
def get_certificates(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    query = db.query(Certificate).filter(Certificate.institute_id == user.institute_id)
    all_certs = query.all()

    today = date.today()
    # Compute stats across all certificates for this institute
    total_count = len(all_certs)
    expiring_soon_count = 0
    expired_count = 0
    renewed_or_valid_count = 0

    computed_list = []
    for c in all_certs:
        st, days = c.compute_status(today)
        if st == "Expiring Soon":
            expiring_soon_count += 1
        elif st == "Expired":
            expired_count += 1
        else:
            renewed_or_valid_count += 1

        computed_item = CertificateItem(
            id=c.id,
            application_id=c.application_id,
            name=c.name,
            certificate_id=c.certificate_id,
            issue_date=c.issue_date,
            expiry_date=c.expiry_date,
            document_id=c.document_id,
            status=st,
            days_until_expiry=days,
        )

        # Apply filtering
        matches_search = True
        if search:
            s = search.lower()
            matches_search = (
                s in c.name.lower()
                or s in c.certificate_id.lower()
                or (c.application_id and s in c.application_id.lower())
            )

        matches_status = True
        if status_filter and status_filter.lower() != "all":
            matches_status = st.lower() == status_filter.lower()

        if matches_search and matches_status:
            computed_list.append(computed_item)

    # Sort soonest expiring first
    computed_list.sort(key=lambda x: x.days_until_expiry)

    # Paginate
    total_filtered = len(computed_list)
    start = (page - 1) * page_size
    paged_items = computed_list[start : start + page_size]

    return CertificateListResponse(
        items=paged_items,
        total=total_filtered,
        page=page,
        page_size=page_size,
        stats=CertificateStats(
            total=total_count,
            expiring_soon=expiring_soon_count,
            expired=expired_count,
            renewed=renewed_or_valid_count,
        ),
    )


@router.get("/certificates/upcoming", response_model=List[UpcomingExpiryItem])
def get_upcoming_expiries(
    limit: int = Query(6, ge=1, le=20),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    certs = db.query(Certificate).filter(Certificate.institute_id == user.institute_id).all()

    # Filter for future/upcoming expiries and sort soonest first
    upcoming = []
    for c in certs:
        st, days = c.compute_status(today)
        if days >= 0:
            upcoming.append(
                UpcomingExpiryItem(
                    id=c.id,
                    name=c.name,
                    certificate_id=c.certificate_id,
                    expiry_date=c.expiry_date,
                    days_until_expiry=days,
                    day=c.expiry_date.day,
                    month_name=c.expiry_date.strftime("%b"),
                    year=c.expiry_date.year,
                )
            )

    upcoming.sort(key=lambda x: x.days_until_expiry)
    return upcoming[:limit]


@router.post("/certificates/{certificate_id}/renew", status_code=status.HTTP_201_CREATED)
def renew_certificate(
    certificate_id: int,
    req: CertificateRenewRequest,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    cert = (
        db.query(Certificate)
        .filter(Certificate.id == certificate_id, Certificate.institute_id == user.institute_id)
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found or not owned by your institute.")

    if req.new_expiry_date <= req.new_issue_date:
        raise HTTPException(status_code=400, detail="New expiry date must be strictly after the issue date.")

    renewal = CertificateRenewal(
        certificate_id=cert.id,
        institute_id=user.institute_id,
        new_issue_date=req.new_issue_date,
        new_expiry_date=req.new_expiry_date,
        document_id=req.document_id,
        status="PENDING_VERIFICATION",
    )
    db.add(renewal)

    # Update certificate dates
    cert.issue_date = req.new_issue_date
    cert.expiry_date = req.new_expiry_date
    if req.document_id:
        cert.document_id = req.document_id

    db.commit()

    AuditService.log_event(
        db=db,
        action="CERTIFICATE_RENEWAL_REQUEST",
        user_id=user.id,
        role=user.role,
        reason=f"Submitted renewal for certificate {cert.certificate_id} ({cert.name})",
    )

    return {"message": "Certificate renewal request submitted successfully.", "renewal_id": renewal.id}


# ==============================================================================
# 3. APPLICATIONS ENDPOINTS
# ==============================================================================
@router.get("/applications", response_model=ApplicationListResponse)
def get_applications(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    apps = (
        db.query(Application)
        .filter(Application.institute_id == user.institute_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    stats = ApplicationStats(
        draft=sum(1 for a in apps if a.status == "DRAFT"),
        submitted=sum(1 for a in apps if a.status == "SUBMITTED"),
        under_review=sum(1 for a in apps if a.status == "UNDER_REVIEW"),
        approved=sum(1 for a in apps if a.status == "APPROVED"),
        rejected=sum(1 for a in apps if a.status == "REJECTED"),
        total=len(apps),
    )

    return ApplicationListResponse(items=apps, stats=stats)


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application_draft(
    payload: CreateApplicationDraft,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app_ref = f"APP-2026-{uuid.uuid4().hex[:5].upper()}"

    new_app = Application(
        institute_id=user.institute_id,
        application_id=app_ref,
        category=payload.category,
        academic_year=payload.academic_year,
        programme=payload.programme,
        status="DRAFT",
        filed_on=None,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    AuditService.log_event(
        db=db,
        action="APPLICATION_DRAFT_CREATED",
        user_id=user.id,
        role=user.role,
        reason=f"Draft application created: {app_ref} ({payload.category})",
    )

    return {"message": "Application draft created successfully.", "application": new_app}


@router.get("/applications/{application_id}/readiness", response_model=ApplicationReadinessResponse)
def get_institute_application_readiness(
    application_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app_record = (
        db.query(Application)
        .filter(
            Application.id == application_id,
            Application.institute_id == user.institute_id,
        )
        .first()
    )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied.",
        )

    readiness = ReadinessService.evaluate_application(db=db, application=app_record)
    return readiness


def _resolve_application_record(app_id_or_number: Any, institute_id: int, db: Session) -> Application:
    app_record = None
    app_str = str(app_id_or_number).strip()
    if app_str.isdigit():
        app_record = (
            db.query(Application)
            .filter(
                Application.id == int(app_str),
                Application.institute_id == institute_id,
            )
            .first()
        )
    if not app_record:
        app_record = (
            db.query(Application)
            .filter(
                Application.application_id == app_str,
                Application.institute_id == institute_id,
            )
            .first()
        )
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or access denied.",
        )
    return app_record


@router.post("/applications/{application_id}/validate", response_model=ValidationRunResponse)
def validate_institute_application(
    application_id: str,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app_record = _resolve_application_record(application_id, user.institute_id, db)

    val_run = ValidationRunner.run_validation(
        db=db,
        application_id=app_record.id,
        triggered_by=user.id,
    )

    findings_out = [
        ValidationFindingOut(
            id=f.id,
            rule_code=f.rule_code,
            rule_version=f.rule_version,
            rule_title=f.rule_title,
            severity=f.severity,
            status=f.status,
            reason=f.reason,
            evidence_json=f.evidence_json or [],
            suggested_action=f.suggested_action,
            created_at=f.created_at,
        )
        for f in val_run.findings
    ]

    diff_out = None
    if val_run.diff_json:
        diff_out = ValidationRunDiffOut(**val_run.diff_json)

    return ValidationRunResponse(
        id=val_run.id,
        application_id=val_run.application_id,
        application_number=app_record.application_id,
        ruleset_id=val_run.ruleset_id,
        ruleset_version=val_run.ruleset_version,
        status=val_run.status,
        overall_status=val_run.overall_status,
        score=val_run.score,
        blocker_count=val_run.blocker_count,
        major_count=val_run.major_count,
        minor_count=val_run.minor_count,
        advisory_count=val_run.advisory_count,
        started_at=val_run.started_at,
        finished_at=val_run.finished_at,
        findings=findings_out,
        diff=diff_out,
    )


@router.get("/applications/{application_id}/validation/latest", response_model=ValidationRunResponse)
def get_latest_application_validation(
    application_id: str,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app_record = _resolve_application_record(application_id, user.institute_id, db)

    val_run = (
        db.query(ValidationRun)
        .filter(ValidationRun.application_id == app_record.id)
        .order_by(ValidationRun.id.desc())
        .first()
    )

    if not val_run:
        val_run = ValidationRunner.run_validation(
            db=db,
            application_id=app_record.id,
            triggered_by=user.id,
        )

    findings_out = [
        ValidationFindingOut(
            id=f.id,
            rule_code=f.rule_code,
            rule_version=f.rule_version,
            rule_title=f.rule_title,
            severity=f.severity,
            status=f.status,
            reason=f.reason,
            evidence_json=f.evidence_json or [],
            suggested_action=f.suggested_action,
            created_at=f.created_at,
        )
        for f in val_run.findings
    ]

    diff_out = None
    if val_run.diff_json:
        diff_out = ValidationRunDiffOut(**val_run.diff_json)

    return ValidationRunResponse(
        id=val_run.id,
        application_id=val_run.application_id,
        application_number=app_record.application_id,
        ruleset_id=val_run.ruleset_id,
        ruleset_version=val_run.ruleset_version,
        status=val_run.status,
        overall_status=val_run.overall_status,
        score=val_run.score,
        blocker_count=val_run.blocker_count,
        major_count=val_run.major_count,
        minor_count=val_run.minor_count,
        advisory_count=val_run.advisory_count,
        started_at=val_run.started_at,
        finished_at=val_run.finished_at,
        findings=findings_out,
        diff=diff_out,
    )


@router.get("/applications/{application_id}/validation/history", response_model=List[ValidationRunSummaryOut])
def get_application_validation_history(
    application_id: str,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app_record = _resolve_application_record(application_id, user.institute_id, db)

    runs = (
        db.query(ValidationRun)
        .filter(ValidationRun.application_id == app_record.id)
        .order_by(ValidationRun.id.desc())
        .all()
    )

    return [
        ValidationRunSummaryOut(
            id=r.id,
            application_id=r.application_id,
            application_number=app_record.application_id,
            overall_status=r.overall_status,
            score=r.score,
            blocker_count=r.blocker_count,
            major_count=r.major_count,
            minor_count=r.minor_count,
            advisory_count=r.advisory_count,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/applications/{application_id}/why-failed", response_model=WhyFailedResponse)
def get_institute_application_why_failed(
    application_id: str,
    lang: str = Query("en", pattern="^(en|hi)$"),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Returns only the blocking and failing root causes, with evidence,
    steps to fix, and the rule reference for the institute.
    """
    app_record = _resolve_application_record(application_id, user.institute_id, db)

    val_run = (
        db.query(ValidationRun)
        .filter(ValidationRun.application_id == app_record.id)
        .order_by(ValidationRun.id.desc())
        .first()
    )

    if not val_run:
        val_run = ValidationRunner.run_validation(
            db=db,
            application_id=app_record.id,
            triggered_by=user.id,
        )

    institute = db.query(Institute).filter(Institute.id == app_record.institute_id).first()
    institute_name = institute.name if institute else "Institute"

    # Pre-fetch rules for metadata lookup
    rules = db.query(Rule).all()
    rules_by_code = {r.rule_code: r for r in rules}

    # Deterministic Root Cause Analysis (merges cascades, groups by cause)
    root_causes = RootCauseAnalyzer.analyze_findings(
        findings=val_run.findings,
        rules_by_code=rules_by_code,
    )

    # Generate explanation via Narrator (TEMPLATE default or grounded LLM)
    explanation = ExplainerNarrator.explain(
        root_causes=root_causes,
        application_id=app_record.application_id,
        institute_name=institute_name,
        lang=lang,
        run_id=val_run.id,
        db=db,
    )

    root_causes_out = [
        RootCauseOut(
            cause_code=rc.cause_code,
            headline=rc.headline,
            affected_rule_codes=rc.affected_rule_codes,
            severity=rc.severity,
            evidence=rc.evidence,
            fixable_by_institute=rc.fixable_by_institute,
            ordered_suggested_actions=rc.ordered_suggested_actions,
            needs_official_review=rc.needs_official_review,
            finding_ids=rc.finding_ids,
        )
        for rc in root_causes
    ]

    reasons_out = [
        WhyFailedReasonOut(
            cause_code=r.get("cause_code", ""),
            explanation=r.get("explanation", ""),
            finding_codes=r.get("finding_codes", []),
        )
        for r in explanation.get("reasons", [])
    ]

    how_to_fix_out = [
        HowToFixItem(
            step=h.get("step", ""),
            effort=h.get("effort", "Low"),
        )
        for h in explanation.get("how_to_fix", [])
    ]

    return WhyFailedResponse(
        headline=explanation.get("headline", ""),
        plain_summary=explanation.get("plain_summary", ""),
        root_causes=root_causes_out,
        how_to_fix=how_to_fix_out,
        reasons=reasons_out,
        what_officials_will_review=explanation.get("what_officials_will_review"),
        disclaimer=explanation.get("disclaimer", ""),
        lang=lang,
    )





# ==============================================================================
# 4. RULES ENDPOINT
# ==============================================================================
@router.get("/rules", response_model=RulesResponse)
def get_rules(
    q: Optional[str] = Query(None, description="Search term for rule code, title, description, or handbook reference"),
    search: Optional[str] = Query(None, description="Legacy search parameter"),
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by rule type: ALL | MANDATORY | ADVISORY"),
    sort: Optional[str] = Query("rule_code", description="Sort order: rule_code | recent"),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    # 1. Global counts for Summary Strip and Category Chips
    all_db_rules = db.query(Rule).all()
    total_count = len(all_db_rules)
    mandatory_total = sum(1 for r in all_db_rules if (r.rule_type == "MANDATORY" or r.is_mandatory))
    advisory_total = sum(1 for r in all_db_rules if r.rule_type == "ADVISORY")
    
    category_counts = {}
    for r in all_db_rules:
        category_counts[r.category] = category_counts.get(r.category, 0) + 1

    summary = RuleSummary(
        total=total_count,
        mandatory=mandatory_total,
        advisory=advisory_total,
        categories_count=len(category_counts),
        category_counts=category_counts,
    )

    # 2. Filtered Query
    query = db.query(Rule)
    term = q if q is not None else search
    if term and term.strip():
        s = f"%{term.strip()}%"
        query = query.filter(
            (Rule.rule_code.ilike(s))
            | (Rule.title.ilike(s))
            | (Rule.description.ilike(s))
            | (Rule.handbook_reference.ilike(s))
        )

    if category and category.strip() and category.strip().lower() != "all":
        query = query.filter(Rule.category == category.strip())

    if type and type.strip() and type.strip().upper() in ["MANDATORY", "ADVISORY"]:
        query = query.filter(Rule.rule_type == type.strip().upper())

    # Sort
    if sort in ["recent", "updated_at"]:
        query = query.order_by(Rule.category, Rule.updated_at.desc(), Rule.rule_code.asc())
    else:
        query = query.order_by(Rule.category, Rule.rule_code.asc())

    filtered_rules = query.all()

    # 3. Group by Category
    groups_dict = {}
    for r in filtered_rules:
        if r.category not in groups_dict:
            groups_dict[r.category] = []
        groups_dict[r.category].append(r)

    result_groups = []
    for cat, rules in groups_dict.items():
        mand_count = sum(1 for r in rules if (r.rule_type == "MANDATORY" or r.is_mandatory))
        adv_count = sum(1 for r in rules if r.rule_type == "ADVISORY")
        result_groups.append(
            RuleGroup(
                category=cat,
                total_count=len(rules),
                mandatory_count=mand_count,
                advisory_count=adv_count,
                rules=rules,
            )
        )

    return RulesResponse(summary=summary, groups=result_groups)


# ==============================================================================
# 5. UPLOAD & DOCUMENT MANAGEMENT ENDPOINTS
# ==============================================================================
MAGIC_BYTES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
}


@router.post("/documents", response_model=DocumentItem, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    application_id: Optional[int] = Form(None),
    document_type_code: Optional[str] = Form(None),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    # Max file size limit from DocumentType if available
    content = await file.read()
    file_size = len(content)

    doc_type_code_clean = document_type_code.strip().upper() if document_type_code else None
    max_limit_mb = 10
    dt_id = None
    if doc_type_code_clean:
        dt = db.query(DocumentType).filter(DocumentType.code == doc_type_code_clean).first()
        if dt:
            dt_id = dt.id
            if dt.max_size_mb:
                max_limit_mb = dt.max_size_mb

    if file_size > max_limit_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {max_limit_mb} MB limit.",
        )

    # MIME Type and Magic Bytes validation
    mime = file.content_type or ""
    is_valid_magic = False
    for expected_mime, magic in MAGIC_BYTES.items():
        if mime == expected_mime and content.startswith(magic):
            is_valid_magic = True
            break
        # Also handle image/jpeg variants (image/jpg)
        if mime in ["image/jpeg", "image/jpg"] and content.startswith(b"\xff\xd8\xff"):
            is_valid_magic = True
            mime = "image/jpeg"
            break

    if not is_valid_magic:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Invalid file format or corrupted header. Only authentic PDF, JPG, and PNG files are accepted.",
        )

    # Compute SHA-256 hash
    sha256 = hashlib.sha256(content).hexdigest()

    # Store outside web root with randomized UUID name
    ext = os.path.splitext(file.filename)[1].lower() or ".bin"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(DOCUMENT_STORAGE_DIR, stored_name)

    with open(saved_path, "wb") as f:
        f.write(content)

    doc = Document(
        institute_id=user.institute_id,
        application_id=application_id,
        document_type_id=dt_id,
        document_type_code=doc_type_code_clean,
        original_filename=file.filename,
        stored_filename=stored_name,
        file_path=saved_path,
        file_size=file_size,
        mime_type=mime,
        sha256_hash=sha256,
        status="Uploaded",
        ocr_status="PENDING",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    AuditService.log_event(
        db=db,
        action="DOCUMENT_UPLOADED",
        user_id=user.id,
        role=user.role,
        reason=f"Uploaded file: {file.filename} ({file_size} bytes, SHA256: {sha256[:12]}..., type: {doc_type_code_clean or 'unspecified'})",
        details={"document_id": doc.id, "ocr_status": "PENDING"},
    )

    # Launch asynchronous OCR processing
    background_tasks.add_task(OCRService.run_document_ocr_task, doc.id)

    return doc


@router.get("/documents/{document_id}/ocr", response_model=DocumentOCRResponse)
def get_document_ocr(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.institute_id == user.institute_id,
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    pages = (
        db.query(DocumentPage)
        .filter(DocumentPage.document_id == doc.id)
        .order_by(DocumentPage.page_no.asc())
        .all()
    )

    page_outs = [
        DocumentPageOut(
            page_no=p.page_no,
            text=p.text,
            width=p.width,
            height=p.height,
            words_count=len(p.words_json or []),
            words=p.words_json,
        )
        for p in pages
    ]

    return DocumentOCRResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        ocr_status=doc.ocr_status,
        ocr_engine=doc.ocr_engine,
        ocr_confidence=doc.ocr_confidence,
        page_count=doc.page_count or len(page_outs),
        language=doc.language or "en",
        processed_at=doc.processed_at,
        error_message=doc.error_message,
        pages=page_outs,
    )


@router.post("/documents/{document_id}/retry", response_model=DocumentReprocessResponse)
@router.post("/documents/{document_id}/reprocess", response_model=DocumentReprocessResponse)
def reprocess_document_ocr(
    document_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.institute_id == user.institute_id,
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    doc.ocr_status = "PENDING"
    doc.status = "Processing"
    doc.error_message = None
    db.commit()

    AuditService.log_event(
        db=db,
        action="DOCUMENT_REPROCESS_REQUESTED",
        user_id=user.id,
        role=user.role,
        reason=f"Reprocess OCR requested for document {doc.id} ({doc.original_filename})",
        details={"document_id": doc.id},
    )

    background_tasks.add_task(OCRService.run_document_ocr_task, doc.id)

    return DocumentReprocessResponse(
        message="Document re-processing queued successfully.",
        document_id=doc.id,
        ocr_status="PENDING",
    )


@router.get("/documents/{document_id}/extraction", response_model=DocumentExtractionResponse)
def get_document_extraction(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.institute_id == user.institute_id,
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    # 1. Classification details
    classification_out = None
    classification = db.query(DocumentClassification).filter(DocumentClassification.document_id == doc.id).first()
    if classification:
        candidates_out = [
            CandidateOut(
                code=c.get("code", ""),
                name=c.get("name", ""),
                score=c.get("score", 0.0),
                matched_keywords=c.get("matched_keywords", []),
            )
            for c in (classification.candidates_json or [])
        ]
        classification_out = ClassificationOut(
            predicted_type=classification.predicted_type,
            score=classification.score,
            candidates=candidates_out,
            mismatch_flag=classification.mismatch_flag,
            warning_message=classification.warning_message,
        )

    # 2. Extracted fields
    raw_fields = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == doc.id)
        .order_by(ExtractedField.id.asc())
        .all()
    )

    field_outs = [
        ExtractedFieldOut(
            id=f.id,
            key=f.key,
            value=f.value,
            normalized_value=f.normalized_value,
            confidence=f.confidence,
            page_no=f.page_no,
            bbox=f.bbox_json,
            source=f.source,
            needs_review=f.needs_review,
            verified_by_user=f.verified_by_user,
            corrected_value=f.corrected_value,
            effective_value=f.corrected_value if f.corrected_value is not None else f.value,
        )
        for f in raw_fields
    ]

    ext_data = doc.extracted_data or {}
    expiry_date = ext_data.get("expiry_date")
    issue_date = ext_data.get("issue_date")
    is_expired = ext_data.get("is_expired")
    days_remaining = ext_data.get("days_remaining")

    # Resilient fallback from fields
    if not expiry_date:
        for f in raw_fields:
            if f.key.lower() in {"valid_upto", "expiry_date", "valid_until", "maturity_date"}:
                val = f.corrected_value or f.normalized_value or f.value
                if val:
                    try:
                        d = date.fromisoformat(val)
                        expiry_date = d.isoformat()
                        today = date.today()
                        days_remaining = (d - today).days
                        is_expired = days_remaining < 0
                        break
                    except ValueError:
                        pass

    # 3. Statutory verification payload
    ver_payload = None
    ver_res = VerificationService.get_latest_verification(db=db, document_id=doc.id)
    if ver_res:
        details = ver_res.details_json or {}
        is_sim = (
            "simulated" in str(ver_res.source_name).lower()
            or "mock" in str(ver_res.source_name).lower()
            or bool(details.get("disclaimer"))
        )
        ver_payload = {
            "id": ver_res.id,
            "status": ver_res.status,
            "source_name": ver_res.source_name,
            "source_ref": ver_res.source_ref,
            "checked_at": ver_res.checked_at.isoformat() if ver_res.checked_at else None,
            "is_simulated": is_sim,
            "disclaimer": details.get("disclaimer"),
            "matched_fields": details.get("matched_fields", []),
            "mismatched_fields": details.get("mismatched_fields", []),
            "all_comparisons": details.get("all_comparisons", []),
            "message": details.get("message"),
            "manual_decision": ver_res.manual_decision,
            "manual_reason": ver_res.manual_reason,
        }

    return DocumentExtractionResponse(
        document_id=doc.id,
        filename=doc.original_filename,
        document_type_code=doc.document_type_code,
        ocr_status=doc.ocr_status,
        classification=classification_out,
        fields=field_outs,
        expiry_date=expiry_date,
        issue_date=issue_date,
        is_expired=is_expired,
        days_remaining=days_remaining,
        verification=ver_payload,
    )


@router.patch("/documents/{document_id}/fields/{key}", response_model=FieldCorrectionResponse)
def correct_extracted_field(
    document_id: int,
    key: str,
    payload: FieldCorrectionRequest,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.institute_id == user.institute_id,
    ).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied.",
        )

    field = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.document_id == doc.id,
            ExtractedField.key == key,
        )
        .first()
    )

    old_val = field.value if field else None
    if not field:
        # Create a new verified field if it was missing from original extraction
        field = ExtractedField(
            document_id=doc.id,
            key=key,
            value="",
            normalized_value=payload.corrected_value,
            confidence=1.0,
            page_no=1,
            source="manual",
            needs_review=False,
            verified_by_user=True,
            corrected_value=payload.corrected_value,
            corrected_by=user.id,
        )
        db.add(field)
    else:
        field.corrected_value = payload.corrected_value
        field.verified_by_user = True
        field.corrected_by = user.id
        field.needs_review = False

    db.commit()
    db.refresh(field)

    # Write audit log for correction
    AuditService.log_event(
        db=db,
        action="DOCUMENT_FIELD_CORRECTED",
        user_id=user.id,
        role=user.role,
        reason=f"Field '{key}' corrected for document ID {doc.id}",
        details={
            "document_id": doc.id,
            "field_key": key,
            "original_value": old_val,
            "corrected_value": payload.corrected_value,
            "corrected_by_user_id": user.id,
        },
    )

    field_out = ExtractedFieldOut(
        id=field.id,
        key=field.key,
        value=field.value,
        normalized_value=field.normalized_value,
        confidence=field.confidence,
        page_no=field.page_no,
        bbox=field.bbox_json,
        source=field.source,
        needs_review=field.needs_review,
        verified_by_user=field.verified_by_user,
        corrected_value=field.corrected_value,
        effective_value=field.corrected_value if field.corrected_value is not None else field.value,
    )

    return FieldCorrectionResponse(
        message=f"Field '{key}' corrected and verified successfully.",
        field=field_out,
    )


@router.post("/documents/{document_id}/verify", response_model=VerificationResponseOut)
def verify_institute_document(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Trigger or re-trigger statutory verification for an institute document.
    Enforces institute isolation.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    if doc.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Document does not belong to your institute.",
        )

    ver_res = VerificationService.verify_document(
        db=db,
        document_id=doc.id,
        triggered_by=user.id,
        force_reverify=True,
    )

    details = ver_res.details_json or {}
    return VerificationResponseOut(
        id=ver_res.id,
        document_id=ver_res.document_id,
        status=ver_res.status,
        source_name=ver_res.source_name,
        source_ref=ver_res.source_ref,
        checked_at=ver_res.checked_at,
        matched_fields=details.get("matched_fields", []),
        mismatched_fields=details.get("mismatched_fields", []),
        raw_response_hash=ver_res.response_hash,
        message=details.get("message"),
        details=details,
        manual_decision=ver_res.manual_decision,
        manual_reason=ver_res.manual_reason,
        manual_reviewed_by=ver_res.manual_reviewed_by,
        manual_reviewed_at=ver_res.manual_reviewed_at,
    )


@router.get("/documents/{document_id}/verification", response_model=VerificationResponseOut)
def get_institute_document_verification(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Fetch the latest statutory verification record for an institute document.
    Enforces institute isolation.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    if doc.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Document does not belong to your institute.",
        )

    ver_res = VerificationService.get_latest_verification(db=db, document_id=doc.id)
    if not ver_res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verification record found for this document. Verification may be pending.",
        )

    details = ver_res.details_json or {}
    return VerificationResponseOut(
        id=ver_res.id,
        document_id=ver_res.document_id,
        status=ver_res.status,
        source_name=ver_res.source_name,
        source_ref=ver_res.source_ref,
        checked_at=ver_res.checked_at,
        matched_fields=details.get("matched_fields", []),
        mismatched_fields=details.get("mismatched_fields", []),
        raw_response_hash=ver_res.response_hash,
        message=details.get("message"),
        details=details,
        manual_decision=ver_res.manual_decision,
        manual_reason=ver_res.manual_reason,
        manual_reviewed_by=ver_res.manual_reviewed_by,
        manual_reviewed_at=ver_res.manual_reviewed_at,
    )


@router.get("/checklist", response_model=InstituteChecklistResponse)
def get_institute_checklist(
    category: str = Query("EOA"),
    application_id: Optional[int] = Query(None),
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == category.upper()).first()
    if not cat:
        cat = db.query(ApplicationCategory).first()
        if not cat:
            return InstituteChecklistResponse(
                category_code=category.upper(),
                category_name=category.upper(),
                total_required=0,
                uploaded_count=0,
                missing_count=0,
                items=[],
            )

    items = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.category_id == cat.id, ChecklistItem.is_active == True)
        .order_by(ChecklistItem.display_order.asc(), ChecklistItem.id.asc())
        .all()
    )

    # Fetch existing documents uploaded by this institute
    doc_query = db.query(Document).filter(Document.institute_id == user.institute_id)
    if application_id:
        doc_query = doc_query.filter(
            (Document.application_id == application_id) | (Document.application_id == None)
        )
    uploaded_docs = doc_query.order_by(Document.created_at.desc()).all()

    uploaded_by_type = {}
    for d in uploaded_docs:
        if d.document_type_code and d.document_type_code not in uploaded_by_type:
            uploaded_by_type[d.document_type_code] = d

    checklist_results = []
    uploaded_count = 0
    missing_count = 0

    for ci in items:
        dt = ci.document_type
        if not dt or not dt.is_active:
            continue

        matched_doc = uploaded_by_type.get(dt.code)
        if matched_doc:
            status_val = "uploaded"
            uploaded_count += 1
            doc_id = matched_doc.id
            doc_name = matched_doc.original_filename
            up_at = matched_doc.created_at
        else:
            status_val = "missing"
            if ci.is_mandatory:
                missing_count += 1
            doc_id = None
            doc_name = None
            up_at = None

        checklist_results.append(
            InstituteChecklistItem(
                id=ci.id,
                document_type_code=dt.code,
                document_type_name=dt.name,
                description=dt.description,
                issuing_authority=dt.issuing_authority,
                is_mandatory=ci.is_mandatory,
                status=status_val,
                uploaded_document_id=doc_id,
                uploaded_filename=doc_name,
                uploaded_at=up_at,
                min_validity_days_remaining=ci.min_validity_days_remaining,
                help_text=ci.help_text,
            )
        )

    return InstituteChecklistResponse(
        category_code=cat.code,
        category_name=cat.name,
        total_required=sum(1 for i in checklist_results if i.is_mandatory),
        uploaded_count=uploaded_count,
        missing_count=missing_count,
        items=checklist_results,
    )


@router.get("/documents", response_model=List[DocumentItem])
def get_documents(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Document)
        .filter(Document.institute_id == user.institute_id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.institute_id == user.institute_id)
        .first()
    )
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Document not found or inaccessible.")

    AuditService.log_event(
        db=db,
        action="DOCUMENT_DOWNLOADED",
        user_id=user.id,
        role=user.role,
        reason=f"Downloaded document: {doc.original_filename} (ID: {doc.id})",
    )

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type,
        filename=doc.original_filename,
    )


@router.delete("/documents/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.institute_id == user.institute_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or not owned by your institute.")

    # Remove file from disk
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    filename = doc.original_filename
    db.delete(doc)
    db.commit()

    AuditService.log_event(
        db=db,
        action="DOCUMENT_DELETED",
        user_id=user.id,
        role=user.role,
        reason=f"Deleted document: {filename} (ID: {document_id})",
    )

    return {"message": f"Document '{filename}' deleted successfully."}


@router.post("/documents/cleanup-placeholders")
@router.delete("/documents/cleanup-placeholders")
def cleanup_placeholder_documents(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Deletes 46-byte demo placeholder documents for the user's institute.
    Unlinks associated certificates, removes files from disk, and deletes document records.
    """
    from backend.app.models.certificate import Certificate, CertificateRenewal

    placeholders = (
        db.query(Document)
        .filter(Document.file_size == 46, Document.institute_id == user.institute_id)
        .all()
    )
    deleted_ids = []

    for doc in placeholders:
        # Unlink certificates if referenced
        db.query(Certificate).filter(Certificate.document_id == doc.id).update({Certificate.document_id: None})
        db.query(CertificateRenewal).filter(CertificateRenewal.document_id == doc.id).update({CertificateRenewal.document_id: None})

        # Remove file from disk
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

        deleted_ids.append(doc.id)
        db.delete(doc)

    db.commit()

    if deleted_ids:
        AuditService.log_event(
            db=db,
            action="PLACEHOLDER_DOCUMENTS_CLEANED",
            user_id=user.id,
            role=user.role,
            reason=f"Cleaned up {len(deleted_ids)} placeholder documents (IDs: {deleted_ids})",
            details={"deleted_ids": deleted_ids},
        )

    return {
        "message": f"Successfully deleted {len(deleted_ids)} placeholder document(s).",
        "deleted_count": len(deleted_ids),
        "deleted_ids": deleted_ids,
    }


# ==============================================================================
# 6. VALIDATION REPORT ENDPOINT (Live Findings)
# ==============================================================================
@router.get("/validation/{application_id}", response_model=ValidationResponse)
def get_validation_report(
    application_id: str,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    app = _resolve_application_record(application_id, user.institute_id, db)

    val_run = (
        db.query(ValidationRun)
        .filter(ValidationRun.application_id == app.id)
        .order_by(ValidationRun.id.desc())
        .first()
    )
    if not val_run:
        val_run = ValidationRunner.run_validation(
            db=db,
            application_id=app.id,
            triggered_by=user.id,
        )

    checks = []
    for f in val_run.findings:
        if f.status == "PASS":
            res = "Pass"
        elif f.status in ["WARNING", "NEEDS_REVIEW"]:
            res = "Warning"
        else:
            res = "Fail"

        ev_text = f.reason or ""
        v_status = None
        v_source = None
        if isinstance(f.evidence_json, list):
            for ev in f.evidence_json:
                if isinstance(ev, dict):
                    if ev.get("verification_status"):
                        v_status = str(ev.get("verification_status"))
                    if ev.get("source_name"):
                        v_source = str(ev.get("source_name"))

        checks.append(
            ValidationCheckItem(
                check=f.rule_title or f.rule_code,
                result=res,
                evidence=ev_text,
                suggested_action=f.suggested_action or "No remediation required.",
                verification_status=v_status,
                source_name=v_source,
            )
        )

    return ValidationResponse(
        application_id=app.application_id,
        status=val_run.overall_status,
        checks=checks,
    )


# ==============================================================================
# 7. COMPLAINTS & TICKETING ENDPOINTS
# ==============================================================================
@router.get("/complaints", response_model=List[ComplaintItem])
def get_complaints(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    complaints = (
        db.query(Complaint)
        .filter(Complaint.institute_id == user.institute_id)
        .order_by(Complaint.created_at.desc())
        .all()
    )
    # Sanitize events to omit internal admin notes
    for c in complaints:
        c.events = [e for e in c.events if not getattr(e, "is_internal", False)]
    return complaints


@router.get("/complaints/{complaint_id}", response_model=ComplaintItem)
def get_complaint_detail(
    complaint_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id, Complaint.institute_id == user.institute_id)
        .first()
    )
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint ticket not found.",
        )
    complaint.events = [e for e in complaint.events if not getattr(e, "is_internal", False)]
    return complaint


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def raise_complaint(
    payload: CreateComplaintRequest,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    ticket_id = f"TCK-2026-{uuid.uuid4().hex[:5].upper()}"

    complaint = Complaint(
        ticket_id=ticket_id,
        institute_id=user.institute_id,
        application_id=payload.related_application_id,
        category=payload.category,
        subject=payload.subject,
        description=payload.description,
        attachment_document_id=payload.attachment_document_id,
        status="Open",
        priority="MEDIUM",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    # Initial event
    event = ComplaintEvent(
        complaint_id=complaint.id,
        action="Ticket Created",
        notes=f"Complaint lodged by Institute under category '{payload.category}'.",
        created_by="Institute Officer",
        is_internal=False,
    )
    db.add(event)
    db.commit()

    AuditService.log_event(
        db=db,
        action="COMPLAINT_LODGED",
        user_id=user.id,
        role=user.role,
        reason=f"Raised ticket {ticket_id}: {payload.subject}",
    )

    return {"message": "Complaint registered successfully.", "ticket_id": ticket_id, "id": complaint.id}


@router.post("/complaints/{complaint_id}/reply", response_model=ComplaintItem)
def institute_reply_complaint(
    complaint_id: int,
    payload: InstituteComplaintReplyRequest,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id, Complaint.institute_id == user.institute_id)
        .first()
    )
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint ticket not found.",
        )

    event = ComplaintEvent(
        complaint_id=complaint.id,
        action="Institute Response",
        notes=payload.notes.strip(),
        created_by="Institute Officer",
        is_internal=False,
    )
    db.add(event)
    complaint.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(complaint)

    AuditService.log_event(
        db=db,
        action="COMPLAINT_REPLY",
        user_id=user.id,
        role=user.role,
        reason=f"Institute response added to ticket {complaint.ticket_id}",
    )

    complaint.events = [e for e in complaint.events if not getattr(e, "is_internal", False)]
    return complaint


# ==============================================================================
# 8. REPORTS ENDPOINTS
# ==============================================================================
@router.post("/reports/generate", response_model=ReportItem, status_code=status.HTTP_201_CREATED)
def generate_report(
    req: GenerateReportRequest,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    report_record = ReportService.generate_report(
        db=db,
        institute_id=user.institute_id,
        report_type=req.report_type,
        report_format=req.format,
        date_range=req.date_range,
        application_id=req.application_id,
    )

    AuditService.log_event(
        db=db,
        action="REPORT_GENERATED",
        user_id=user.id,
        role=user.role,
        reason=f"Generated {req.format} report for '{req.report_type}' ({req.date_range})",
    )

    return report_record


@router.get("/reports", response_model=List[ReportItem])
def get_reports(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Report)
        .filter(Report.institute_id == user.institute_id)
        .order_by(Report.created_at.desc())
        .all()
    )


@router.get("/reports/{report_id}/download")
def download_report(
    report_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    rep = (
        db.query(Report)
        .filter(Report.id == report_id, Report.institute_id == user.institute_id)
        .first()
    )
    if not rep or not os.path.exists(rep.file_path):
        raise HTTPException(status_code=404, detail="Report not found on server.")

    AuditService.log_event(
        db=db,
        action="REPORT_DOWNLOADED",
        user_id=user.id,
        role=user.role,
        reason=f"Downloaded report file: {rep.filename}",
    )

    media_type = "application/pdf" if rep.format == "PDF" else "text/csv"
    return FileResponse(path=rep.file_path, media_type=media_type, filename=rep.filename)


# ==============================================================================
# 9. NOTIFICATIONS ENDPOINTS
# ==============================================================================
@router.get("/notifications")
def get_notifications(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Notification)
        .filter(Notification.institute_id == user.institute_id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    unread_count = sum(1 for n in items if not n.is_read)
    return {"items": items, "unread_count": unread_count}


@router.patch("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    n = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.institute_id == user.institute_id)
        .first()
    )
    if n:
        n.is_read = True
        db.commit()
    return {"message": "Notification marked as read."}


@router.patch("/notifications/read-all")
def mark_all_notifications_read(
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.institute_id == user.institute_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read."}


# =========================================================================
# Stage 5: Anomaly Detection Endpoints (Institute View)
# =========================================================================

@router.post("/applications/{application_id}/anomaly-scan")
def run_institute_application_anomaly_scan(
    application_id: Union[int, str],
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Triggers an on-demand anomaly scan across all documents of an application.
    Enforces institute isolation.
    """
    app = None
    if isinstance(application_id, int) or (isinstance(application_id, str) and application_id.isdigit()):
        app = db.query(Application).filter(Application.id == int(application_id)).first()
    if not app:
        app = db.query(Application).filter(Application.application_id == str(application_id)).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    if app.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Application does not belong to your institute.",
        )

    run, flags = AnomalyService.scan_application(
        db=db,
        application_id=app.id,
        triggered_by=user.id,
    )

    sanitized_flags = [
        InstituteAnomalyFlagOut.model_validate(f) for f in flags
    ]

    return {
        "run_id": run.id,
        "application_id": app.id,
        "flag_count": len(sanitized_flags),
        "flags": sanitized_flags,
        "status": "COMPLETED",
    }


@router.get("/documents/{document_id}/anomalies", response_model=List[InstituteAnomalyFlagOut])
def get_institute_document_anomalies(
    document_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves preliminary anomaly indicators for a document.
    Enforces institute isolation.
    Outputs are preliminary indicators worded as 'needs verification' with NO internal scores.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )

    if doc.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Document does not belong to your institute.",
        )

    flags = AnomalyService.get_flags_for_document(db=db, document_id=doc.id)
    return [InstituteAnomalyFlagOut.model_validate(f) for f in flags]


@router.get("/applications/{application_id}/evidence-graph", response_model=EvidenceGraphResponse)
def get_institute_application_evidence_graph(
    application_id: Union[int, str],
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Builds the multi-entity cross-document evidence graph for an application.
    Enforces institute isolation.
    Outputs preliminary indicators worded as 'needs verification' with NO internal confidence scores.
    """
    app = None
    if isinstance(application_id, int) or (isinstance(application_id, str) and application_id.isdigit()):
        app = db.query(Application).filter(Application.id == int(application_id)).first()
    if not app:
        app = db.query(Application).filter(Application.application_id == str(application_id)).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{application_id}' not found.",
        )

    if app.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Application does not belong to your institute.",
        )

    graph_data = EvidenceGraphBuilder.build_graph(db=db, application_id=app.id, is_admin=False)
    return graph_data


@router.get("/documents/{document_id}/anomalies/{flag_id}/overlay")
def get_institute_anomaly_overlay_image(
    document_id: int,
    flag_id: int,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    """
    Stream the visual heatmap / bounding-box overlay PNG for an anomaly flag.
    Enforces institute isolation.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document #{document_id} not found.",
        )

    if doc.institute_id != user.institute_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Document does not belong to your institute.",
        )

    from backend.app.models.anomaly import AnomalyFlag
    flag = db.query(AnomalyFlag).filter(AnomalyFlag.id == flag_id, AnomalyFlag.document_id == doc.id).first()
    if not flag or not flag.overlay_image_path or not os.path.exists(flag.overlay_image_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No overlay image available for anomaly flag #{flag_id}.",
        )

    return FileResponse(flag.overlay_image_path, media_type="image/png")


