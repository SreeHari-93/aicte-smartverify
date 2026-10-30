from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    application_id = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100), nullable=False)  # e.g., Extension of Approval (EoA)
    academic_year = Column(String(20), nullable=False)  # e.g., 2026-2027
    programme = Column(String(100), nullable=False)  # Engineering & Technology
    status = Column(String(50), default="DRAFT", nullable=False, index=True)
    # Status options: DRAFT, SUBMITTED, UNDER_REVIEW, APPROVED, REJECTED
    filed_on = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")
    documents = relationship("Document", back_populates="application")
    anomaly_runs = relationship("AnomalyRun", back_populates="application", cascade="all, delete-orphan", order_by="desc(AnomalyRun.id)")

