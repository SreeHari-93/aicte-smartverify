from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base


class EvcStatus:
    PENDING_SCHEDULING = "PENDING_SCHEDULING"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EvcRecord(Base):
    __tablename__ = "evc_records"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    is_new_institution = Column(Boolean, default=False, nullable=False)
    committee_members = Column(JSON, default=list, nullable=False)
    proposed_date = Column(DateTime, nullable=True)
    confirmed_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(50), default=EvcStatus.PENDING_SCHEDULING, nullable=False, index=True)
    report_file_path = Column(String(500), nullable=True)
    report_original_filename = Column(String(255), nullable=True)
    report_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    report_uploaded_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    scheduling_deadline = Column(DateTime, nullable=False)
    completion_deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("Application")
    workflow = relationship("ApplicationWorkflow")
    report_document = relationship("Document", foreign_keys=[report_document_id])

    @property
    def case_id(self) -> str:
        return self.application.application_id if self.application else f"EVC-{self.id}"

    @property
    def institute_name(self) -> str:
        if self.application and self.application.institute:
            return self.application.institute.name
        return "Institution"

    @property
    def institute_id(self):
        return self.application.institute_id if self.application else None

    @property
    def completed_at(self):
        return self.confirmed_date or self.updated_at



