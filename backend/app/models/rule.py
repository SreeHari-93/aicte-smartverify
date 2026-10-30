from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_code = Column(String(50), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)  # Extension of Approval, Change of Name, Intake Change, Closure/Merger
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    handbook_reference = Column(String(255), nullable=False)  # e.g., Section 2.4.1
    version = Column(String(50), default="v2026.1", nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    # rule_type: DOCUMENT_REQUIRED | FIELD_REQUIRED | VALIDITY_PERIOD | CROSS_FIELD_MATCH | NUMERIC_THRESHOLD | COUNT_AT_LEAST | EXTERNAL_VERIFICATION | INFRASTRUCTURE | COMPOSITE
    rule_type = Column(String(50), default="MANDATORY", nullable=False)
    severity = Column(String(50), default="MAJOR", nullable=False)  # BLOCKER | MAJOR | MINOR | ADVISORY
    applies_to_categories = Column(JSON, default=list, nullable=False)  # ["EOA", "CHANGE_OF_NAME", ...]
    definition = Column(JSON, default=dict, nullable=False)  # Declarative condition tree
    ai_checks = Column(JSON, default=list, nullable=False)
    evidence_required = Column(JSON, default=list, nullable=False)  # List of document type codes
    suggested_action = Column(Text, nullable=True)
    status = Column(String(50), default="PUBLISHED", nullable=False)  # DRAFT | PUBLISHED | ARCHIVED
    current_version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, nullable=True)
    updated_by = Column(Integer, nullable=True)
    applies_to = Column(JSON, default=list, nullable=False)  # Legacy compatibility
    version_history = Column(JSON, default=list, nullable=False)  # Legacy compatibility
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    versions = relationship("RuleVersion", back_populates="rule", cascade="all, delete-orphan", order_by="desc(RuleVersion.version_no)")

    # Property aliases for seamless field access
    @property
    def code(self) -> str:
        return self.rule_code

    @code.setter
    def code(self, value: str):
        self.rule_code = value

    @property
    def handbook_ref(self) -> str:
        return self.handbook_reference

    @handbook_ref.setter
    def handbook_ref(self, value: str):
        self.handbook_reference = value

    @property
    def mandatory(self) -> bool:
        return self.is_mandatory

    @mandatory.setter
    def mandatory(self, value: bool):
        self.is_mandatory = value


class RuleVersion(Base):
    __tablename__ = "rule_versions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # Full rule state snapshot
    change_note = Column(Text, nullable=True)
    changed_by = Column(Integer, nullable=True)
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    rule = relationship("Rule", back_populates="versions")


class RuleSet(Base):
    __tablename__ = "rulesets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # e.g., "APH 2026-27"
    version_label = Column(String(50), nullable=False)  # e.g., "v1.0"
    status = Column(String(50), default="PUBLISHED", nullable=False)  # DRAFT | PUBLISHED | ARCHIVED
    published_at = Column(DateTime, nullable=True)
    published_by = Column(Integer, nullable=True)
    snapshot = Column(JSON, nullable=False)  # Frozen dictionary containing all active rules, checklists, document types
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class RuleChangeRequest(Base):
    __tablename__ = "rule_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("rules.id"), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE | UPDATE | ARCHIVE | PUBLISH
    proposed_payload = Column(JSON, nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING | APPROVED | REJECTED
    requested_by = Column(Integer, nullable=False)
    reviewed_by = Column(Integer, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
