from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# --- Dashboard Schemas ---
class StatCount(BaseModel):
    filed: int
    approved: int
    pending: int
    rejected: int


class AccreditationData(BaseModel):
    nirf_rank: int
    naac_grade: str
    nba_accredited_courses: int
    college_code: str
    location_address: str
    phone: str

    class Config:
        from_attributes = True


class CourseItem(BaseModel):
    id: int
    name: str
    level: str
    intake: int
    accreditation_status: Optional[str] = 'NBA accredited'
    approved_year: Optional[str] = '2026'

    class Config:
        from_attributes = True


class InstituteDashboardResponse(BaseModel):
    institute_id: int
    aicte_institute_id: str
    name: str
    state: str
    stats: StatCount
    accreditation: Optional[AccreditationData] = None
    courses: List[CourseItem] = []


# --- Certificate Schemas ---
class CertificateItem(BaseModel):
    id: int
    application_id: Optional[str] = None
    name: str
    certificate_id: str
    issue_date: date
    expiry_date: date
    document_id: Optional[int] = None
    status: str  # Valid, Expiring Soon, Expired
    days_until_expiry: int

    class Config:
        from_attributes = True


class CertificateStats(BaseModel):
    total: int
    expiring_soon: int
    expired: int
    renewed: int


class CertificateListResponse(BaseModel):
    items: List[CertificateItem]
    total: int
    page: int
    page_size: int
    stats: CertificateStats


class UpcomingExpiryItem(BaseModel):
    id: int
    name: str
    certificate_id: str
    expiry_date: date
    days_until_expiry: int
    day: int
    month_name: str
    year: int


class CertificateRenewRequest(BaseModel):
    new_issue_date: date
    new_expiry_date: date
    document_id: Optional[int] = None


# --- Application Schemas ---
class ApplicationItem(BaseModel):
    id: int
    application_id: str
    category: str
    academic_year: str
    programme: str
    status: str
    filed_on: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationStats(BaseModel):
    draft: int
    submitted: int
    under_review: int
    approved: int
    rejected: int
    total: int


class ApplicationListResponse(BaseModel):
    items: List[ApplicationItem]
    stats: ApplicationStats


class CreateApplicationDraft(BaseModel):
    category: str
    academic_year: str
    programme: str


# --- Rule Schemas ---
class RuleItem(BaseModel):
    id: int
    rule_code: str
    category: str
    title: str
    description: str
    handbook_reference: str
    version: str
    is_mandatory: bool
    rule_type: str = "MANDATORY"
    ai_checks: List[str] = []
    evidence_required: List[str] = []
    applies_to: List[str] = []
    version_history: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleGroup(BaseModel):
    category: str
    total_count: int
    mandatory_count: int
    advisory_count: int
    rules: List[RuleItem]


class RuleSummary(BaseModel):
    total: int
    mandatory: int
    advisory: int
    categories_count: int
    category_counts: Dict[str, int]


class RulesResponse(BaseModel):
    summary: RuleSummary
    groups: List[RuleGroup]


# --- Document Schemas ---
class DocumentItem(BaseModel):
    id: int
    original_filename: str
    document_type_id: Optional[int] = None
    document_type_code: Optional[str] = None
    file_size: int
    mime_type: str
    sha256_hash: str
    status: str
    ocr_status: Optional[str] = "PENDING"
    ocr_confidence: Optional[float] = None
    verification_status: Optional[str] = "VERIFICATION_PENDING"
    verification_source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentPageOut(BaseModel):
    page_no: int
    text: str
    width: float
    height: float
    words_count: int = 0
    words: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True


class DocumentOCRResponse(BaseModel):
    document_id: int
    filename: str
    ocr_status: str
    ocr_engine: Optional[str] = None
    ocr_confidence: Optional[float] = None
    page_count: Optional[int] = 0
    language: Optional[str] = "en"
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    pages: List[DocumentPageOut] = []


class DocumentReprocessResponse(BaseModel):
    message: str
    document_id: int
    ocr_status: str


class InstituteChecklistItem(BaseModel):
    id: int
    document_type_code: str
    document_type_name: str
    description: Optional[str] = None
    issuing_authority: Optional[str] = None
    is_mandatory: bool
    status: str  # missing | uploaded | expired
    uploaded_document_id: Optional[int] = None
    uploaded_filename: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    min_validity_days_remaining: Optional[int] = None
    help_text: Optional[str] = None


class InstituteChecklistResponse(BaseModel):
    category_code: str
    category_name: str
    total_required: int
    uploaded_count: int
    missing_count: int
    items: List[InstituteChecklistItem]


# --- Validation Demo Schemas ---
class ValidationCheckItem(BaseModel):
    check: str
    result: str  # Pass, Warning, Fail
    evidence: str
    suggested_action: str
    verification_status: Optional[str] = None
    source_name: Optional[str] = None


class ValidationResponse(BaseModel):
    application_id: str
    status: str
    checks: List[ValidationCheckItem]


# --- Complaint Schemas ---
class ComplaintEventItem(BaseModel):
    id: int
    action: str
    notes: str
    created_by: str
    is_internal: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintItem(BaseModel):
    id: int
    ticket_id: str
    application_id: Optional[int] = None
    attachment_document_id: Optional[int] = None
    category: str
    subject: str
    description: str
    status: str
    priority: Optional[str] = "MEDIUM"
    created_at: datetime
    updated_at: datetime
    events: List[ComplaintEventItem] = []

    class Config:
        from_attributes = True


class CreateComplaintRequest(BaseModel):
    category: str
    related_application_id: Optional[int] = None
    subject: str
    description: str
    attachment_document_id: Optional[int] = None


class InstituteComplaintReplyRequest(BaseModel):
    notes: str = Field(..., min_length=2)


# --- Report Schemas ---
class ReportItem(BaseModel):
    id: int
    report_type: str
    format: str
    date_range: str
    filename: str
    file_size: int
    created_at: datetime
    application_id: Optional[str] = None
    language: Optional[str] = "en"
    generated_by: Optional[str] = "INSTITUTE"
    institute_name: Optional[str] = None

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    report_type: str  # Application Summary, Certificate Expiry, Validation Summary
    format: str  # PDF, CSV
    date_range: str  # e.g., "Current Academic Year", "Past 30 Days", "Past 90 Days"
    application_id: Optional[str] = None
    language: Optional[str] = "en"


# --- Notification Schemas ---
class NotificationItem(BaseModel):
    id: int
    title: str
    message: str
    type: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Classification & Extraction Schemas ---
class CandidateOut(BaseModel):
    code: str
    name: str
    score: float
    matched_keywords: List[str] = []


class ClassificationOut(BaseModel):
    predicted_type: str
    score: float
    candidates: List[CandidateOut] = []
    mismatch_flag: bool = False
    warning_message: Optional[str] = None

    class Config:
        from_attributes = True


class ExtractedFieldOut(BaseModel):
    id: Optional[int] = None
    key: str
    value: Optional[str] = None
    normalized_value: Optional[str] = None
    confidence: float
    page_no: int = 1
    bbox: Optional[List[float]] = None
    source: str
    needs_review: bool
    verified_by_user: bool = False
    corrected_value: Optional[str] = None
    effective_value: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentExtractionResponse(BaseModel):
    document_id: int
    filename: str
    document_type_code: Optional[str] = None
    ocr_status: str
    classification: Optional[ClassificationOut] = None
    fields: List[ExtractedFieldOut] = []
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    is_expired: Optional[bool] = None
    days_remaining: Optional[int] = None
    verification: Optional[Dict[str, Any]] = None


class FieldCorrectionRequest(BaseModel):
    corrected_value: str = Field(..., description="The verified or corrected value for the field")


class FieldCorrectionResponse(BaseModel):
    message: str
    field: ExtractedFieldOut


# --- Readiness Schemas ---
class ChecklistItemReadinessOut(BaseModel):
    checklist_item_id: int
    document_type_code: str
    document_type_name: str
    is_mandatory: bool
    status: str
    document_id: Optional[int] = None
    document_filename: Optional[str] = None
    min_validity_days_remaining: Optional[int] = None
    days_remaining: Optional[int] = None
    expiry_date: Optional[str] = None
    is_duplicate: bool = False
    duplicate_with_id: Optional[int] = None
    help_text: Optional[str] = None


class FieldProblemOut(BaseModel):
    document_id: Optional[int] = None
    document_type: str
    page_no: int = 1
    field_key: str
    problem: str
    value: Optional[str] = None


class DuplicateWarningOut(BaseModel):
    document_id: int
    document_type: Optional[str] = None
    original_filename: str
    duplicate_with_id: int
    duplicate_type: Optional[str] = None
    duplicate_filename: str
    application_id: Optional[int] = None
    institute_id: int
    sha256_hash: str
    message: str


class ApplicationReadinessResponse(BaseModel):
    application_id: int
    application_number: str
    category: str
    ruleset_name: str
    ruleset_version: str
    readiness_percentage: float
    status: str
    total_items: int
    ready_items: int
    missing_items: List[str] = []
    items: List[ChecklistItemReadinessOut] = []
    field_problems: List[FieldProblemOut] = []
    duplicates: List[DuplicateWarningOut] = []


# --- Validation Runner Schemas ---
class ValidationFindingOut(BaseModel):
    id: Optional[int] = None
    rule_code: str
    rule_version: Optional[str] = None
    rule_title: Optional[str] = None
    severity: str
    status: str
    reason: Optional[str] = None
    evidence_json: List[Any] = []
    suggested_action: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ValidationRunDiffOut(BaseModel):
    previous_run_id: Optional[int] = None
    newly_failed: List[str] = []
    newly_fixed: List[str] = []
    still_open: List[str] = []
    newly_failed_count: int = 0
    newly_fixed_count: int = 0
    still_open_count: int = 0


class ValidationRunResponse(BaseModel):
    id: int
    application_id: int
    application_number: str
    ruleset_id: Optional[int] = None
    ruleset_version: Optional[str] = None
    status: str
    overall_status: str
    score: float
    blocker_count: int
    major_count: int
    minor_count: int
    advisory_count: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    findings: List[ValidationFindingOut] = []
    diff: Optional[ValidationRunDiffOut] = None

    class Config:
        from_attributes = True


class ValidationRunSummaryOut(BaseModel):
    id: int
    application_id: int
    application_number: str
    overall_status: str
    score: float
    blocker_count: int
    major_count: int
    minor_count: int
    advisory_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class RootCauseOut(BaseModel):
    cause_code: str
    headline: str
    affected_rule_codes: List[str]
    severity: str
    evidence: List[Dict[str, Any]] = []
    fixable_by_institute: bool
    ordered_suggested_actions: List[str] = []
    needs_official_review: bool
    finding_ids: List[int] = []

    class Config:
        from_attributes = True


class HowToFixItem(BaseModel):
    step: str
    effort: str


class WhyFailedReasonOut(BaseModel):
    cause_code: str
    explanation: str
    finding_codes: List[str] = []


class WhyFailedResponse(BaseModel):
    headline: str
    plain_summary: str
    root_causes: List[RootCauseOut] = []
    how_to_fix: List[HowToFixItem] = []
    reasons: List[WhyFailedReasonOut] = []
    what_officials_will_review: Optional[str] = None
    disclaimer: str
    lang: str = "en"


class AdminWhyFailedResponse(WhyFailedResponse):
    source: str = "TEMPLATE"
    model: Optional[str] = None
    prompt_hash: Optional[str] = None
    validation_run_id: Optional[int] = None
    raw_root_causes: List[Dict[str, Any]] = []
    waived_findings_count: int = 0
    findings_detail: List[Dict[str, Any]] = []


class FindingNoteCreateRequest(BaseModel):
    action: str  # NOTE | WAIVE
    reason: str


class FindingNoteResponse(BaseModel):
    success: bool
    message: str
    finding_id: int
    rule_code: str
    action: str
    is_waived: bool
    waived_by: Optional[int] = None
    waiver_reason: Optional[str] = None


class AssessmentStatsResponse(BaseModel):
    total_applications_evaluated: int
    total_findings_recorded: int
    total_waived_findings: int
    common_causes: List[Dict[str, Any]] = []
    most_failed_rules: List[Dict[str, Any]] = []

