from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from backend.app.database import Base


class WorkflowStatus:
    IN_PROGRESS = "IN_PROGRESS"
    RETURNED = "RETURNED"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"


class WorkflowAction:
    SUBMIT = "SUBMIT"
    COMPLETE_STAGE = "COMPLETE_STAGE"
    RETURN = "RETURN"
    RESUBMIT = "RESUBMIT"
    REASSIGN = "REASSIGN"
    HOLD = "HOLD"
    RESUME = "RESUME"
    RECORD_DECISION = "RECORD_DECISION"


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    stages = relationship("WorkflowTemplateStage", back_populates="template", order_by="WorkflowTemplateStage.sequence", cascade="all, delete-orphan")


class WorkflowTemplateStage(Base):
    __tablename__ = "workflow_template_stages"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("workflow_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    stage_code = Column(String(50), nullable=False)
    stage_name = Column(String(150), nullable=False)
    responsible_role = Column(String(50), nullable=False)  # REGIONAL_OFFICER, COMMITTEE_MEMBER, BUREAU_OFFICER, ADMIN
    sla_days = Column(Integer, nullable=False, default=7)
    is_final_decision = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    template = relationship("WorkflowTemplate", back_populates="stages")


class ApplicationWorkflow(Base):
    __tablename__ = "application_workflows"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("workflow_templates.id"), nullable=False, index=True)
    current_stage_id = Column(Integer, ForeignKey("workflow_template_stages.id"), nullable=True)
    current_stage_sequence = Column(Integer, nullable=False, default=1)
    current_stage_name = Column(String(150), nullable=False)
    assigned_officer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    assigned_officer_name = Column(String(150), nullable=True)
    region = Column(String(100), nullable=False, index=True, default="Southern")
    stage_start = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    due_date = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False, default=WorkflowStatus.IN_PROGRESS, index=True)
    final_decision = Column(String(50), nullable=True)  # APPROVED or REJECTED
    final_decision_notes = Column(Text, nullable=True)
    final_decision_by = Column(String(150), nullable=True)
    final_decision_at = Column(DateTime, nullable=True)
    case_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    application = relationship("Application", backref=backref("workflow", uselist=False))
    template = relationship("WorkflowTemplate")
    current_stage = relationship("WorkflowTemplateStage", foreign_keys=[current_stage_id])
    assigned_officer = relationship("User", foreign_keys=[assigned_officer_id])
    history = relationship("WorkflowHistory", back_populates="workflow", order_by="desc(WorkflowHistory.created_at)", cascade="all, delete-orphan")


class WorkflowHistory(Base):
    __tablename__ = "workflow_histories"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("application_workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    from_stage = Column(String(150), nullable=True)
    to_stage = Column(String(150), nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    performed_by_role = Column(String(50), nullable=False)
    performed_by_name = Column(String(150), nullable=True)
    reason = Column(Text, nullable=False)  # Mandatory reason
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    workflow = relationship("ApplicationWorkflow", back_populates="history")

