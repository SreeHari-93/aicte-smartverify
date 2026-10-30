from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.database import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_version = Column(String(50), default="v1.0", nullable=False)
    status = Column(String(50), default="COMPLETED", nullable=False, index=True)  # RUNNING, COMPLETED, FAILED
    overall_accuracy = Column(Float, default=0.0, nullable=False)
    total_samples = Column(Integer, default=0, nullable=False)
    passed_samples = Column(Integer, default=0, nullable=False)

    # metrics_json contains:
    # - classification: { accuracy, macro_precision, macro_recall, macro_f1, per_type: {...}, confusion_matrix: {classes: [...], matrix: [[...]]} }
    # - field_extraction: { exact_match_rate, normalized_match_rate, per_field: { certificate_number: {...}, ... } }
    # - expiry_accuracy: { accuracy, total_evaluated, correct_count }
    # - anomaly_detection: { overall_fpr, overall_precision, overall_recall, per_detector: {...} }
    # - ocr_performance: { success_rate, avg_processing_time_ms }
    # - explainer_grounding: { grounding_rate, total_statements_checked, grounded_statements, violations: [...] }
    metrics_json = Column(JSON, default=dict, nullable=False)

    # failed_cases_json: List of { file, document_type, error_category, expected, got, notes }
    failed_cases_json = Column(JSON, default=list, nullable=False)

    git_commit = Column(String(40), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, default=0.0, nullable=False)


class AIFeedback(Base):
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    target_type = Column(String(50), nullable=False, index=True)  # CLASSIFICATION, EXTRACTION, ANOMALY, VERIFICATION
    target_id = Column(Integer, nullable=False, index=True)  # ID of the document, anomaly flag, or verification result
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    is_correct = Column(Boolean, nullable=False)  # True = Correct, False = Incorrect
    correction_notes = Column(Text, nullable=True)
    feedback_metadata = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User")
    document = relationship("Document")

