from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    ruleset_id = Column(Integer, ForeignKey("rulesets.id", ondelete="SET NULL"), nullable=True, index=True)
    ruleset_version = Column(String(50), nullable=True)
    status = Column(String(50), default="COMPLETED", nullable=False)  # PENDING | RUNNING | COMPLETED | FAILED
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    triggered_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    overall_status = Column(String(50), nullable=False)  # BLOCKED | LIKELY_TO_FAIL | NEEDS_ATTENTION | READY_FOR_REVIEW
    score = Column(Float, nullable=False, default=100.0)
    blocker_count = Column(Integer, default=0, nullable=False)
    major_count = Column(Integer, default=0, nullable=False)
    minor_count = Column(Integer, default=0, nullable=False)
    advisory_count = Column(Integer, default=0, nullable=False)
    diff_json = Column(JSON, default=dict, nullable=True)
    summary_json = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    findings = relationship("ValidationFinding", back_populates="run", cascade="all, delete-orphan", order_by="ValidationFinding.id")
    application = relationship("Application")
    ruleset = relationship("RuleSet")
    user = relationship("User")


class ValidationFinding(Base):
    __tablename__ = "validation_findings"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("validation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code = Column(String(100), nullable=False, index=True)
    rule_version = Column(String(50), nullable=True)
    rule_title = Column(String(255), nullable=True)
    severity = Column(String(50), nullable=False)  # BLOCKER | MAJOR | MINOR | ADVISORY
    status = Column(String(50), nullable=False)  # PASS | FAIL | WARNING | NEEDS_REVIEW
    reason = Column(Text, nullable=True)
    evidence_json = Column(JSON, default=list, nullable=False)
    suggested_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    run = relationship("ValidationRun", back_populates="findings")

