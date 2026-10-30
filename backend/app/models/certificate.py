from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    application_id = Column(String(50), nullable=True)  # Reference e.g. APP-2025-0142
    name = Column(String(255), nullable=False)  # Certificate Name e.g. Fire Safety Certificate
    certificate_id = Column(String(100), unique=True, index=True, nullable=False)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")
    document = relationship("Document")
    renewals = relationship("CertificateRenewal", back_populates="certificate", cascade="all, delete-orphan")

    def compute_status(self, today: date = None) -> tuple[str, int]:
        """
        Dynamically compute status and days remaining relative to today.
        Rule:
        - If expiry_date < today: Expired
        - Else if expiry_date <= today + 60 days: Expiring Soon
        - Else: Valid
        """
        if today is None:
            today = date.today()

        days_remaining = (self.expiry_date - today).days
        if days_remaining < 0:
            status = "Expired"
        elif days_remaining <= 60:
            status = "Expiring Soon"
        else:
            status = "Valid"

        return status, days_remaining


class CertificateRenewal(Base):
    __tablename__ = "certificate_renewals"

    id = Column(Integer, primary_key=True, index=True)
    certificate_id = Column(Integer, ForeignKey("certificates.id"), nullable=False, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False)
    new_issue_date = Column(Date, nullable=False)
    new_expiry_date = Column(Date, nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    status = Column(String(50), default="PENDING_VERIFICATION", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    certificate = relationship("Certificate", back_populates="renewals")
    document = relationship("Document")

