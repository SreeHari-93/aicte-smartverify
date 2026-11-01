from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ValidityStatus:
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    RENEWAL_SUBMITTED = "RENEWAL_SUBMITTED"
    RENEWED = "RENEWED"


class DocumentValidityRecord(Base):
    __tablename__ = "document_validity_records"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    document_type_code = Column(String(50), nullable=False, index=True)
    document_name = Column(String(255), nullable=False)
    certificate_number = Column(String(100), nullable=True, index=True)
    issuing_authority = Column(String(255), nullable=True)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=False, index=True)
    status = Column(String(50), default=ValidityStatus.VALID, nullable=False, index=True)
    days_left = Column(Integer, nullable=True)
    expiring_soon_window_days = Column(Integer, default=60, nullable=False)

    renewal_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    renewal_status = Column(String(50), nullable=True)  # PENDING, ACCEPTED, REJECTED
    renewal_submitted_at = Column(DateTime, nullable=True)
    renewal_decision_reason = Column(Text, nullable=True)
    renewal_decided_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    renewal_decided_at = Column(DateTime, nullable=True)

    # Lease specific fields
    is_lease = Column(Boolean, default=False, nullable=False, index=True)
    lessor = Column(String(255), nullable=True)
    lessee = Column(String(255), nullable=True)
    lease_start = Column(Date, nullable=True)
    lease_end = Column(Date, nullable=True)
    property_address = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", foreign_keys=[document_id])
    renewal_document = relationship("Document", foreign_keys=[renewal_document_id])
    institute = relationship("Institute")
    application = relationship("Application")
    renewal_decided_by = relationship("User", foreign_keys=[renewal_decided_by_id])

    @property
    def lease_lessor(self) -> str:
        return self.lessor

    @property
    def lease_lessee(self) -> str:
        return self.lessee


    def compute_status(self, today: date = None) -> tuple[str, int]:
        if today is None:
            today = date.today()
        if self.status in [ValidityStatus.RENEWAL_SUBMITTED, ValidityStatus.RENEWED]:
            days_remaining = (self.expiry_date - today).days if self.expiry_date else 0
            return self.status, days_remaining

        if not self.expiry_date:
            return ValidityStatus.VALID, 999

        days_remaining = (self.expiry_date - today).days
        if days_remaining < 0:
            status = ValidityStatus.EXPIRED
        elif days_remaining <= (self.expiring_soon_window_days or 60):
            status = ValidityStatus.EXPIRING_SOON
        else:
            status = ValidityStatus.VALID

        return status, days_remaining

