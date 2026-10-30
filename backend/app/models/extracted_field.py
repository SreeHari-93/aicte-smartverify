from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    page_no = Column(Integer, default=1, nullable=False)
    bbox_json = Column(JSON, nullable=True)  # [x0, y0, x1, y1] or list of bboxes
    source = Column(String(50), default="rule", nullable=False)  # "rule" | "llm" | "manual"
    needs_review = Column(Boolean, default=False, nullable=False)
    verified_by_user = Column(Boolean, default=False, nullable=False)
    corrected_value = Column(Text, nullable=True)
    corrected_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="extracted_fields")

