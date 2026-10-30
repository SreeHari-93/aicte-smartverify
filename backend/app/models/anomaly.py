from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from backend.app.database import Base


class AnomalySeverity:
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    ALL = [INFO, LOW, MEDIUM, HIGH]


class AnomalyReviewStatus:
    OPEN = "OPEN"
    CONFIRMED_OK = "CONFIRMED_OK"
    NEEDS_ACTION = "NEEDS_ACTION"
    DISMISSED = "DISMISSED"

    ALL = [OPEN, CONFIRMED_OK, NEEDS_ACTION, DISMISSED]


class AnomalyRun(Base):
    __tablename__ = "anomaly_runs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    detectors_run = Column(JSON, default=list, nullable=False)  # List of detector names
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    document = relationship("Document", back_populates="anomaly_runs")
    application = relationship("Application", back_populates="anomaly_runs")
    flags = relationship("AnomalyFlag", back_populates="run", cascade="all, delete-orphan", order_by="desc(AnomalyFlag.id)")


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("anomaly_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    detector = Column(String(100), nullable=False, index=True)  # DuplicateDetector, MetadataDetector, etc.
    code = Column(String(100), nullable=False, index=True)      # Specific check code
    severity = Column(String(20), nullable=False)               # INFO, LOW, MEDIUM, HIGH
    reason = Column(Text, nullable=False)                       # Human-readable reason ("needs verification", "potential anomaly")
    evidence_json = Column(JSON, default=list, nullable=False)  # List of {document_id, page, field, bbox, value, expected}
    confidence = Column(Float, nullable=False, default=1.0)     # Internal scoring (0.0 to 1.0)
    recommended_action = Column(Text, nullable=False)
    review_status = Column(String(50), default=AnomalyReviewStatus.OPEN, nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    overlay_image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    run = relationship("AnomalyRun", back_populates="flags")
    document = relationship("Document", back_populates="anomaly_flags")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

