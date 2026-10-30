from datetime import datetime, date, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EvaluationContext(BaseModel):
    """
    Context for rule evaluation against an application and an institute.
    Pure, deterministic, and safe.
    """
    application: Dict[str, Any] = Field(default_factory=dict)
    institute: Dict[str, Any] = Field(default_factory=dict)
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    courses: List[Dict[str, Any]] = Field(default_factory=list)
    complaints: List[Dict[str, Any]] = Field(default_factory=list)
    evaluation_date: Optional[date] = None

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvaluationContext":
        return cls(**data)

    def get_today(self) -> date:
        if self.evaluation_date:
            return self.evaluation_date
        return datetime.now(timezone.utc).date()

    def get_documents_by_type(self, doc_type_code: str) -> List[Dict[str, Any]]:
        target = doc_type_code.upper().strip()
        matched = []
        for doc in self.documents:
            code = doc.get("document_type_code") or doc.get("type") or doc.get("category")
            if code and code.upper().strip() == target:
                matched.append(doc)
        return matched
