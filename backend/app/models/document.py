from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    institute_id = Column(Integer, ForeignKey("institutes.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    document_type_id = Column(Integer, ForeignKey("document_types.id"), nullable=True, index=True)
    document_type_code = Column(String(50), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    mime_type = Column(String(100), nullable=False)
    sha256_hash = Column(String(64), index=True, nullable=False)
    status = Column(String(50), default="Uploaded", nullable=False)
    # Status options: Uploaded, Processing, Needs Attention, Verified
    extracted_data = Column(JSON, default=dict, nullable=True)

    # OCR Pipeline attributes
    ocr_status = Column(String(50), default="PENDING", nullable=False)  # PENDING | PROCESSING | DONE | FAILED | MANUAL
    ocr_engine = Column(String(50), nullable=True)  # pymupdf | rapidocr | fallback | none
    ocr_confidence = Column(Float, nullable=True)  # Overall document confidence (0.0 to 1.0)
    page_count = Column(Integer, default=0, nullable=True)
    language = Column(String(20), default="en", nullable=True)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    institute = relationship("Institute")
    application = relationship("Application", back_populates="documents")
    document_type = relationship("DocumentType")
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_no")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    classification = relationship("DocumentClassification", back_populates="document", uselist=False, cascade="all, delete-orphan")
    verification_results = relationship("VerificationResult", back_populates="document", cascade="all, delete-orphan", order_by="desc(VerificationResult.id)")
    anomaly_runs = relationship("AnomalyRun", back_populates="document", cascade="all, delete-orphan", order_by="desc(AnomalyRun.id)")
    anomaly_flags = relationship("AnomalyFlag", back_populates="document", cascade="all, delete-orphan", order_by="desc(AnomalyFlag.id)")

    @property
    def latest_verification(self):
        if self.verification_results:
            return self.verification_results[0]
        return None

    @property
    def verification_status(self) -> str:
        latest = self.latest_verification
        return latest.status if latest else "VERIFICATION_PENDING"

    @property
    def verification_source(self):
        latest = self.latest_verification
        return latest.source_name if latest else None
