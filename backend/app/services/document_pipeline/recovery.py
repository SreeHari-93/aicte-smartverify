import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.app.models.document import Document
from backend.app.services.audit_service import AuditService

logger = logging.getLogger("document_pipeline.recovery")


def recover_stuck_documents(db: Session, max_age_minutes: int = 2) -> int:
    """
    On backend startup, identify documents whose processing was interrupted
    (status or ocr_status is Processing, Uploaded, or PENDING for longer than 2 minutes)
    and mark them 'Failed – retry available' with clear logging and audit records.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=max_age_minutes)

    # Query documents in an in-flight / non-completed state
    candidates = (
        db.query(Document)
        .filter(
            (Document.ocr_status.in_(["PROCESSING", "Processing", "PENDING", "Pending"])) |
            (Document.status.in_(["Processing", "Uploaded", "PROCESSING", "UPLOADED"]))
        )
        .filter(Document.ocr_status != "DONE")
        .all()
    )

    recovered_count = 0
    for doc in candidates:
        timestamp = doc.processed_at or doc.created_at
        if timestamp:
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            is_stuck = timestamp < cutoff
        else:
            is_stuck = True

        if is_stuck:
            prev_ocr = doc.ocr_status
            prev_status = doc.status

            doc.ocr_status = "FAILED"
            doc.status = "Failed – retry available"
            doc.error_message = "Failed – retry available"
            doc.processed_at = now
            recovered_count += 1

            logger.warning(
                f"[STARTUP RECOVERY] Document #{doc.id} ('{doc.original_filename}') was stuck in "
                f"ocr_status='{prev_ocr}', status='{prev_status}' for >{max_age_minutes} mins. "
                f"Marked as 'Failed – retry available'."
            )

            AuditService.log_event(
                db=db,
                action="DOCUMENT_STUCK_RECOVERED",
                user_id=None,
                role="SYSTEM",
                reason=f"Document #{doc.id} marked as 'Failed – retry available' on startup after remaining in '{prev_status}' for >{max_age_minutes} minutes.",
                details={
                    "document_id": doc.id,
                    "previous_ocr_status": prev_ocr,
                    "previous_status": prev_status,
                    "new_ocr_status": doc.ocr_status,
                    "new_status": doc.status,
                },
            )

    if recovered_count > 0:
        db.commit()
        logger.info(f"[STARTUP RECOVERY] Successfully recovered {recovered_count} stuck document(s).")
    else:
        logger.info("[STARTUP RECOVERY] No stuck documents detected.")

    return recovered_count

