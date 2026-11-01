from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# EVC Schemas
class CommitteeMemberSchema(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    role: Optional[str] = "Member"  # Chairman | Member | Convener
    institution: Optional[str] = None
    phone: Optional[str] = None


class EvcScheduleRequest(BaseModel):
    proposed_date: datetime
    confirmed_date: datetime
    committee_members: List[CommitteeMemberSchema]
    remarks: Optional[str] = None


class EvcRecordResponse(BaseModel):
    id: int
    application_id: int
    application_code: Optional[str] = None
    institute_name: Optional[str] = None
    institute_state: Optional[str] = None
    category: Optional[str] = None
    workflow_id: Optional[int] = None
    is_new_institution: bool
    committee_members: List[Dict[str, Any]] = []
    proposed_date: Optional[datetime] = None
    confirmed_date: Optional[datetime] = None
    status: str
    report_file_path: Optional[str] = None
    report_original_filename: Optional[str] = None
    report_uploaded_at: Optional[datetime] = None
    remarks: Optional[str] = None
    scheduling_deadline: datetime
    completion_deadline: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Undertaking Schemas
class UndertakingCreateRequest(BaseModel):
    application_id: int
    condition: str
    category: str = "other"  # lease, accreditation, infrastructure, faculty, other
    due_date: datetime


class UndertakingVerifyRequest(BaseModel):
    action: str  # ACCEPT, REQUEST_MORE, REJECT
    reason: str


class UndertakingResponse(BaseModel):
    id: int
    application_id: int
    application_code: Optional[str] = None
    institute_id: int
    institute_name: Optional[str] = None
    condition: str
    category: str
    due_date: datetime
    status: str
    evidence_original_filename: Optional[str] = None
    evidence_document_id: Optional[int] = None
    evidence_remarks: Optional[str] = None
    evidence_submitted_at: Optional[datetime] = None
    history: List[Dict[str, Any]] = []
    created_by_officer_id: Optional[int] = None
    verification_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Validity Schemas
class LeaseUpdatePayload(BaseModel):
    lessor: Optional[str] = None
    lessee: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    property_address: Optional[str] = None


class RenewalDecisionRequest(BaseModel):
    action: str  # ACCEPT, REJECT
    reason: str
    new_expiry_date: Optional[date] = None


class ValidityRecordResponse(BaseModel):
    id: int
    document_id: Optional[int] = None
    institute_id: int
    institute_name: Optional[str] = None
    application_id: Optional[int] = None
    application_code: Optional[str] = None
    document_type_code: str
    document_name: str
    certificate_number: Optional[str] = None
    issuing_authority: Optional[str] = None
    issue_date: Optional[date] = None
    expiry_date: date
    status: str
    days_left: Optional[int] = None
    expiring_soon_window_days: int
    renewal_document_id: Optional[int] = None
    renewal_status: Optional[str] = None
    renewal_submitted_at: Optional[datetime] = None
    renewal_decision_reason: Optional[str] = None
    is_lease: bool
    lessor: Optional[str] = None
    lessee: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    property_address: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

