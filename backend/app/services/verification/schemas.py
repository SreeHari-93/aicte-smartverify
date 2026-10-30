from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class VerificationStatus:
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

    ALL = [
        VERIFIED,
        MISMATCH_DETECTED,
        EXPIRED,
        VERIFICATION_PENDING,
        SOURCE_UNAVAILABLE,
        MANUAL_REVIEW_REQUIRED,
    ]


class MismatchedField(BaseModel):
    field: str
    submitted: Any = None
    official: Any = None


class VerificationResultDTO(BaseModel):
    status: str
    source_name: str
    source_ref: Optional[str] = None
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    matched_fields: List[str] = Field(default_factory=list)
    mismatched_fields: List[Dict[str, Any]] = Field(default_factory=list)
    raw_response_hash: Optional[str] = None
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class VerificationResponseOut(BaseModel):
    id: int
    document_id: int
    status: str
    source_name: str
    source_ref: Optional[str] = None
    checked_at: datetime
    matched_fields: List[str] = Field(default_factory=list)
    mismatched_fields: List[Dict[str, Any]] = Field(default_factory=list)
    raw_response_hash: Optional[str] = None
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    manual_decision: Optional[str] = None
    manual_reason: Optional[str] = None
    manual_reviewed_by: Optional[int] = None
    manual_reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ManualConfirmRequest(BaseModel):
    decision: str = Field(..., description="Decision: APPROVED or REJECTED")
    reason: str = Field(..., description="Mandatory reason for manual verification decision")

    @field_validator("reason")
    @classmethod
    def validate_reason_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason is mandatory for manual confirmation.")
        return v.strip()

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in ["APPROVED", "REJECTED", "CONFIRMED"]:
            raise ValueError("Decision must be APPROVED, REJECTED, or CONFIRMED.")
        return "APPROVED" if norm in ["APPROVED", "CONFIRMED"] else "REJECTED"


class VerificationQueueItemOut(BaseModel):
    id: int
    document_id: int
    document_filename: str
    document_type_code: Optional[str] = None
    institute_id: int
    institute_name: str
    status: str
    source_name: str
    source_ref: Optional[str] = None
    checked_at: datetime
    message: Optional[str] = None
    mismatched_fields: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime

