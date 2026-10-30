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
    document_type_code: Optional[str] = None
    file_size: int
    mime_type: str
    sha256_hash: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


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
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintItem(BaseModel):
    id: int
    ticket_id: str
    application_id: Optional[int] = None
    category: str
    subject: str
    description: str
    status: str
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


# --- Report Schemas ---
class ReportItem(BaseModel):
    id: int
    report_type: str
    format: str
    date_range: str
    filename: str
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateReportRequest(BaseModel):
    report_type: str  # Application Summary, Certificate Expiry, Validation Summary
    format: str  # PDF, CSV
    date_range: str  # e.g., "Current Academic Year", "Past 30 Days", "Past 90 Days"


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

