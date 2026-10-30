from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class DocumentClassification(Base):
    __tablename__ = "document_classifications"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    predicted_type = Column(String(50), nullable=False)
    score = Column(Float, default=0.0, nullable=False)
    candidates_json = Column(JSON, default=list, nullable=False)  # list of {code, name, score, matched_keywords}
    mismatch_flag = Column(Boolean, default=False, nullable=False)
    warning_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="classification")

