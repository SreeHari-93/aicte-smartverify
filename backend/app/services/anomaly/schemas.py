from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


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
    has_overlay: bool = False
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
    evidence_json: List[Dict[str, Any]] = Field(default_factory=list)
    has_overlay: bool = False
    recommended_action: str
    review_status: str
    created_at: datetime

    @field_validator("evidence_json", mode="before")
    def sanitize_evidence(cls, v):
        if not v or not isinstance(v, list):
            return []
        sanitized = []
        for item in v:
            if isinstance(item, dict):
                clean = {k: val for k, val in item.items() if k not in ["confidence", "internal_confidence"]}
                sanitized.append(clean)
            else:
                sanitized.append(item)
        return sanitized

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


class EvidenceGraphNode(BaseModel):
    id: str
    type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraphConflict(BaseModel):
    type: str
    field: str
    doc_id_1: int
    doc_id_2: int
    doc_file_1: str
    doc_file_2: str
    value_1: Any
    value_2: Any
    reason: str


class EvidenceGraphSummary(BaseModel):
    node_count: int
    edge_count: int
    conflict_count: int
    anomaly_flag_count: int
    documents_count: int


class EvidenceGraphResponse(BaseModel):
    application_id: str
    application_pk: int
    institute_id: int
    institute_name: str
    nodes: List[EvidenceGraphNode]
    edges: List[EvidenceGraphEdge]
    conflicts: List[EvidenceGraphConflict]
    summary: EvidenceGraphSummary

