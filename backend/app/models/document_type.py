from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from backend.app.database import Base


class DocumentType(Base):
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    issuing_authority = Column(String(255), nullable=True)
    accepted_formats = Column(JSON, default=lambda: ["application/pdf", "image/jpeg", "image/png"], nullable=False)
    max_size_mb = Column(Integer, default=10, nullable=False)
    has_expiry = Column(Boolean, default=True, nullable=False)
    default_validity_months = Column(Integer, default=12, nullable=False)
    # Verification methods: QR | API | PORTAL | DIGITAL_SIGNATURE | MANUAL
    verification_method = Column(String(50), default="MANUAL", nullable=False)
    # extraction_schema: JSON list of {key, label, type [text|date|number|id], required}
    extraction_schema = Column(JSON, default=list, nullable=False)
    # keywords: JSON list of string tokens for document classification in later stages
    keywords = Column(JSON, default=list, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

