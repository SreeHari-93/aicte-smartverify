from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from backend.app.database import Base


class VerificationStatus:
    VERIFIED = "VERIFIED"
    MISMATCH_DETECTED = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

    ALL = [
        VERIFIED,
        MISMATCH_DETECTED,
        EXPIRED,
        VERIFICATION_PENDING,
        SOURCE_UNAVAILABLE,
        MANUAL_REVIEW_REQUIRED,
    ]


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # VERIFIED | MISMATCH_DETECTED | EXPIRED | VERIFICATION_PENDING | SOURCE_UNAVAILABLE | MANUAL_REVIEW_REQUIRED
    source_name = Column(String(255), nullable=False)
    source_ref = Column(String(255), nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)
    response_hash = Column(String(64), nullable=True)
    triggered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Manual Review & Confirm support
    manual_decision = Column(String(50), nullable=True)  # APPROVED | REJECTED
    manual_reason = Column(Text, nullable=True)
    manual_reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    manual_reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="verification_results")
    user = relationship("User", foreign_keys=[triggered_by])
    reviewer = relationship("User", foreign_keys=[manual_reviewed_by])


class AuthoritySource(Base):
    __tablename__ = "authority_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)  # NBA, NAAC, Fire Dept, etc.
    base_url = Column(String(255), nullable=False)
    auth_type = Column(String(50), default="NONE", nullable=False)  # NONE | BEARER | API_KEY | HMAC
    enabled = Column(Boolean, default=True, nullable=False)
    env_secret_key = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class MockRegisterEntry(Base):
    __tablename__ = "mock_register_entries"

    id = Column(Integer, primary_key=True, index=True)
    authority = Column(String(100), index=True, nullable=False)  # NBA, NAAC, Fire Dept, etc.
    certificate_number = Column(String(100), index=True, nullable=False)
    institute_name = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=True)
    expiry_date = Column(String(50), nullable=True)
    status = Column(String(50), default="VALID", nullable=False)  # VALID | EXPIRED | REVOKED
    data_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

