from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowStageOut(BaseModel):
    id: int
    template_id: int
    sequence: int
    stage_code: str
    stage_name: str
    responsible_role: str
    sla_days: int
    is_final_decision: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowTemplateOut(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    stages: List[WorkflowStageOut] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkflowHistoryOut(BaseModel):
    id: int
    workflow_id: int
    action: str
    from_stage: Optional[str] = None
    to_stage: Optional[str] = None
    performed_by_id: Optional[int] = None
    performed_by_role: str
    performed_by_name: Optional[str] = None
    reason: str
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationWorkflowOut(BaseModel):
    id: int
    application_id: int
    application_code: str
    institute_id: int
    institute_name: str
    category: str
    template_code: str
    template_name: str
    current_stage_id: Optional[int] = None
    current_stage_sequence: int
    current_stage_name: str
    assigned_officer_id: Optional[int] = None
    assigned_officer_name: Optional[str] = None
    region: str
    stage_start: datetime
    due_date: datetime
    status: str
    final_decision: Optional[str] = None
    final_decision_notes: Optional[str] = None
    final_decision_by: Optional[str] = None
    final_decision_at: Optional[datetime] = None
    case_summary: Optional[str] = None
    is_overdue: bool
    days_remaining: int
    created_at: datetime
    updated_at: datetime
    stages: List[WorkflowStageOut] = []
    history: List[WorkflowHistoryOut] = []

    class Config:
        from_attributes = True


class WorkflowActionRequest(BaseModel):
    reason: str = Field(..., min_length=2, description="Mandatory reason for workflow action")
    notes: Optional[str] = None


class WorkflowReassignRequest(BaseModel):
    new_officer_id: int = Field(..., description="Target officer user ID")
    reason: str = Field(..., min_length=2, description="Mandatory reason for reassigning")


class WorkflowDecisionRequest(BaseModel):
    decision: str = Field(..., description="APPROVED or REJECTED")
    reason: str = Field(..., min_length=2, description="Mandatory reason for regulatory decision")
    notes: Optional[str] = None


class StageSlaUpdateRequest(BaseModel):
    sla_days: int = Field(..., gt=0, description="SLA duration in calendar days")
    responsible_role: Optional[str] = Field(None, description="Updated responsible officer role")


class WorkflowOfficerOut(BaseModel):
    id: int
    email: str
    role: str
    region: Optional[str] = None


class ApplicationSubmissionRequest(BaseModel):
    category: str = Field(..., description="Application category, e.g. Extension of Approval, New Institution")
    academic_year: str = Field("2026-2027", description="Academic Year")
    programme: Optional[str] = Field(None, description="Engineering & Technology, Management, etc.")
    intake: Optional[int] = Field(None, description="Proposed or existing student intake capacity")
    details: Optional[str] = Field(None, description="Additional submission notes or programme details")
    document_ids: Optional[List[int]] = Field(default=[], description="Attached checklist document IDs")


class ApplicationResubmitRequest(BaseModel):
    response_text: str = Field(..., min_length=2, description="Institute formal response to deficiency / clarification notice")
    document_ids: Optional[List[int]] = Field(default=[], description="Optional uploaded document IDs")


class CommunicationTemplateOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    subject_template: str
    body_template: str
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommunicationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    is_enabled: Optional[bool] = None


class GenerateCommunicationRequest(BaseModel):
    template_code: str = Field(..., description="Template code, e.g. DEFICIENCY_NOTICE")
    workflow_id: int = Field(..., description="Target application workflow ID")
    reason: str = Field(..., min_length=2, description="Reason or deficiency / clarification details")
    target_email: Optional[str] = None


