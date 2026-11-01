from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class UndertakingStatus:
    ACTIVE = "ACTIVE"
    SUBMITTED = "SUBMITTED"
    UNDER_VERIFICATION = "UNDER_VERIFICATION"
    FULFILLED = "FULFILLED"
    OVERDUE = "OVERDUE"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class UndertakingCategory:
    LEASE = "lease"
    ACCREDITATION = "accreditation"
    INFRASTRUCTURE = "infrastructure"
    FACULTY = "faculty"
    OTHER = "other"


class Undertaking(Base):
    __tablename__ = "undertakings"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id", ondelete="CASCADE"), nullable=False, index=True)
    condition = Column(Text, nullable=False)
    category = Column(String(50), default=UndertakingCategory.OTHER, nullable=False, index=True)
    due_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default=UndertakingStatus.ACTIVE, nullable=False, index=True)
    evidence_file_path = Column(String(500), nullable=True)
    evidence_original_filename = Column(String(255), nullable=True)
    evidence_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    evidence_remarks = Column(Text, nullable=True)
    evidence_submitted_at = Column(DateTime, nullable=True)
    history = Column(JSON, default=list, nullable=False)
    created_by_officer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application")
    institute = relationship("Institute")
    evidence_document = relationship("Document", foreign_keys=[evidence_document_id])
    created_by_officer = relationship("User", foreign_keys=[created_by_officer_id])

    @property
    def condition_title(self) -> str:
        return self.condition

    @property
    def condition_description(self) -> str:
        return self.condition


