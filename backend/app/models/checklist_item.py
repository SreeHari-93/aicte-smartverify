from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("application_categories.id"), nullable=False, index=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=False, index=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    condition = Column(JSON, default=dict, nullable=True)  # optional condition when this checklist item triggers
    min_validity_days_remaining = Column(Integer, default=30, nullable=False)
    max_age_days = Column(Integer, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    help_text = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    category = relationship("ApplicationCategory", back_populates="checklist_items")
    document_type = relationship("DocumentType")

