from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class AnomalyFlagDTO(BaseModel):
    detector: str
    code: str
    group_key: Optional[str] = None
    severity: str  # INFO, LOW, MEDIUM, HIGH
    reason: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    recommended_action: str
    overlay_image_path: Optional[str] = None


class AnomalyReviewRequest(BaseModel):
    status: str = Field(..., description="Review status: CONFIRMED_OK, NEEDS_ACTION, or DISMISSED")
    note: str = Field(..., min_length=3, description="Mandatory reviewer rationale for audit trail")


class AnomalyFlagOut(BaseModel):
    id: int
    run_id: int
    document_id: int
    detector: str
    code: str
    group_key: Optional[str] = None
    severity: str
    reason: str
    evidence_json: List[Dict[str, Any]]
    confidence: float
    recommended_action: str
    review_status: str
    reviewed_by: Optional[int] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    overlay_image_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InstituteAnomalyFlagOut(BaseModel):
    """
    Sanitized anomaly view for institutes.
    Omit raw internal confidence scores to prevent gaming while providing
    transparent guidance on potential anomalies needing verification.
    """
    id: int
    document_id: int
    detector: str
    code: str
    group_key: Optional[str] = None
    severity: str
    reason: str
    recommended_action: str
    review_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyRunOut(BaseModel):
    id: int
    document_id: Optional[int] = None
    application_id: Optional[int] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    detectors_run: List[str]
    flag_count: int = 0
    flags: List[AnomalyFlagOut] = Field(default_factory=list)

    class Config:
        from_attributes = True

