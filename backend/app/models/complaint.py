from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)
    category = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    attachment_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    status = Column(String(50), default="Open", nullable=False, index=True)
    # Status options: Open, In Progress, Resolved, Rejected
    priority = Column(String(50), default="MEDIUM", nullable=True)  # LOW, MEDIUM, HIGH, URGENT
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")
    application = relationship("Application")
    attachment = relationship("Document")
    assigned_officer = relationship("User", foreign_keys=[assigned_to])
    events = relationship("ComplaintEvent", back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintEvent.created_at.asc()")


class ComplaintEvent(Base):
    __tablename__ = "complaint_events"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # e.g., Ticket Created, Remark Added, Resolved
    notes = Column(Text, nullable=False)
    created_by = Column(String(100), nullable=False)  # e.g., Institute Officer, AICTE Helpdesk
    is_internal = Column(Boolean, default=False, nullable=False)  # Admin only note vs public thread
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="events")

