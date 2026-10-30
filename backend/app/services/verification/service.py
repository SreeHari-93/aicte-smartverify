from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.institute import Institute
from backend.app.models.verification import VerificationResult, VerificationStatus
from backend.app.services.audit_service import AuditService
from backend.app.services.verification.schemas import (
    VerificationResultDTO,
    VerificationResponseOut,
    VerificationQueueItemOut,
)
from backend.app.services.verification.adapters import AdapterRegistry


class VerificationService:
    """
    Core verification engine orchestrating adapter execution,
    result persistence, document status updating, and immutable audit logging.
    """

    @classmethod
    def get_document_extracted_fields(cls, db: Session, document: Document) -> Dict[str, Any]:
        """
        Gathers extracted data preferring user-verified/corrected field values.
        """
        extracted = dict(document.extracted_data or {})
        fields = (
            db.query(ExtractedField)
            .filter(ExtractedField.document_id == document.id)
            .all()
        )
        for f in fields:
            val = f.effective_value if hasattr(f, "effective_value") else (f.corrected_value or f.value)
            if val is not None:
                extracted[f.key] = val

        # Ensure institute name is injected if missing
        if "institute_name" not in extracted:
            inst = db.query(Institute).filter(Institute.id == document.institute_id).first()
            if inst:
                extracted["institute_name"] = inst.name

        return extracted

    @classmethod
    def verify_document(
        cls,
        db: Session,
        document_id: int,
        triggered_by: Optional[int] = None,
        force_reverify: bool = True,
    ) -> VerificationResult:
        """
        Runs statutory verification on a document using its configured verification method.
        Saves or updates VerificationResult and creates an AuditLog record.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID {document_id} not found.")

        # Resolve DocumentType & verification method
        doc_type = doc.document_type
        if not doc_type and doc.document_type_code:
            doc_type = (
                db.query(DocumentType)
                .filter(DocumentType.code == doc.document_type_code)
                .first()
            )

        verification_method = doc_type.verification_method if doc_type else "MANUAL"
        adapter = AdapterRegistry.get_adapter(verification_method)

        extracted_fields = cls.get_document_extracted_fields(db, doc)

        # Run verification adapter
        result_dto: VerificationResultDTO = adapter.verify(
            document=doc,
            extracted_fields=extracted_fields,
            db=db,
        )

        checked_at = result_dto.checked_at or datetime.now(timezone.utc)

        # Build details JSON
        details_payload = {
            "matched_fields": result_dto.matched_fields,
            "mismatched_fields": result_dto.mismatched_fields,
            "message": result_dto.message,
            "adapter": adapter.__class__.__name__,
            "verification_method": verification_method,
            **result_dto.details,
        }

        # Query existing verification result or create new
        existing_res = (
            db.query(VerificationResult)
            .filter(VerificationResult.document_id == doc.id)
            .order_by(desc(VerificationResult.id))
            .first()
        )

        if existing_res and not force_reverify:
            return existing_res

        ver_res = VerificationResult(
            document_id=doc.id,
            status=result_dto.status,
            source_name=result_dto.source_name,
            source_ref=result_dto.source_ref,
            checked_at=checked_at,
            details_json=details_payload,
            response_hash=result_dto.raw_response_hash,
            triggered_by=triggered_by,
        )
        db.add(ver_res)

        # Update Document overall status based on verification outcome
        if result_dto.status == VerificationStatus.VERIFIED:
            doc.status = "Verified"
        elif result_dto.status in [
            VerificationStatus.MISMATCH_DETECTED,
            VerificationStatus.EXPIRED,
            VerificationStatus.SOURCE_UNAVAILABLE,
            VerificationStatus.MANUAL_REVIEW_REQUIRED,
        ]:
            doc.status = "Needs Attention"

        # Update document.extracted_data with verification summary
        current_ext = dict(doc.extracted_data or {})
        current_ext["verification"] = {
            "status": result_dto.status,
            "source_name": result_dto.source_name,
            "source_ref": result_dto.source_ref,
            "checked_at": checked_at.isoformat(),
            "matched_fields": result_dto.matched_fields,
            "mismatched_fields": result_dto.mismatched_fields,
            "message": result_dto.message,
        }
        doc.extracted_data = current_ext

        db.commit()
        db.refresh(ver_res)

        # AuditLog every check with source, timestamp and result
        AuditService.log_event(
            db=db,
            action="DOCUMENT_VERIFIED",
            user_id=triggered_by,
            role="INSTITUTE" if triggered_by else "SYSTEM",
            reason=f"Document #{doc.id} ({doc.original_filename}) verified via {result_dto.source_name}: {result_dto.status}",
            details={
                "document_id": doc.id,
                "verification_id": ver_res.id,
                "status": result_dto.status,
                "source_name": result_dto.source_name,
                "source_ref": result_dto.source_ref,
                "checked_at": checked_at.isoformat(),
                "matched_fields": result_dto.matched_fields,
                "mismatched_fields": result_dto.mismatched_fields,
                "response_hash": result_dto.raw_response_hash,
            },
        )

        return ver_res

    @classmethod
    def get_latest_verification(cls, db: Session, document_id: int) -> Optional[VerificationResult]:
        return (
            db.query(VerificationResult)
            .filter(VerificationResult.document_id == document_id)
            .order_by(desc(VerificationResult.id))
            .first()
        )

    @classmethod
    def manual_confirm(
        cls,
        db: Session,
        verification_id: int,
        admin_user_id: int,
        decision: str,
        reason: str,
    ) -> VerificationResult:
        """
        Allows an administrator to manually confirm or reject a verification
        that requires review or failed automated checks. Reason is mandatory.
        """
        if not reason or not reason.strip():
            raise ValueError("Reason is mandatory for manual confirmation.")

        norm_decision = decision.strip().upper()
        if norm_decision not in ["APPROVED", "REJECTED", "CONFIRMED"]:
            raise ValueError("Decision must be APPROVED, REJECTED, or CONFIRMED.")

        ver_res = (
            db.query(VerificationResult)
            .filter(VerificationResult.id == verification_id)
            .first()
        )
        if not ver_res:
            raise ValueError(f"VerificationResult with ID {verification_id} not found.")

        effective_decision = "APPROVED" if norm_decision in ["APPROVED", "CONFIRMED"] else "REJECTED"
        now = datetime.now(timezone.utc)

        ver_res.manual_decision = effective_decision
        ver_res.manual_reason = reason.strip()
        ver_res.manual_reviewed_by = admin_user_id
        ver_res.manual_reviewed_at = now

        if effective_decision == "APPROVED":
            ver_res.status = VerificationStatus.VERIFIED
            if ver_res.document:
                ver_res.document.status = "Verified"
        else:
            ver_res.status = VerificationStatus.MISMATCH_DETECTED
            if ver_res.document:
                ver_res.document.status = "Needs Attention"

        # Update details_json with manual confirmation record
        details = dict(ver_res.details_json or {})
        details["manual_confirmation"] = {
            "decision": effective_decision,
            "reason": reason.strip(),
            "reviewed_by": admin_user_id,
            "reviewed_at": now.isoformat(),
        }
        ver_res.details_json = details

        db.commit()
        db.refresh(ver_res)

        # AuditLog event
        AuditService.log_event(
            db=db,
            action="VERIFICATION_MANUAL_CONFIRMED",
            user_id=admin_user_id,
            role="ADMIN",
            reason=f"Manual verification decision '{effective_decision}' recorded for Verification #{ver_res.id}: {reason.strip()}",
            details={
                "verification_id": ver_res.id,
                "document_id": ver_res.document_id,
                "decision": effective_decision,
                "reason": reason.strip(),
                "resulting_status": ver_res.status,
            },
        )

        return ver_res

    @classmethod
    def get_verification_queue(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
    ) -> List[VerificationQueueItemOut]:
        """
        Retrieves verification items requiring admin attention:
        PENDING, UNAVAILABLE, MANUAL_REVIEW_REQUIRED, or MISMATCH_DETECTED.
        """
        query = (
            db.query(VerificationResult, Document, Institute)
            .join(Document, VerificationResult.document_id == Document.id)
            .join(Institute, Document.institute_id == Institute.id)
        )

        if status_filter:
            norm_filter = status_filter.upper().strip()
            if norm_filter == "PENDING":
                query = query.filter(VerificationResult.status == VerificationStatus.VERIFICATION_PENDING)
            elif norm_filter == "UNAVAILABLE":
                query = query.filter(VerificationResult.status == VerificationStatus.SOURCE_UNAVAILABLE)
            elif norm_filter == "MANUAL_REVIEW":
                query = query.filter(VerificationResult.status == VerificationStatus.MANUAL_REVIEW_REQUIRED)
            elif norm_filter == "MISMATCH":
                query = query.filter(VerificationResult.status == VerificationStatus.MISMATCH_DETECTED)
            else:
                query = query.filter(VerificationResult.status == norm_filter)
        else:
            # Default queue: all needing review / unresolved
            query = query.filter(
                VerificationResult.status.in_([
                    VerificationStatus.MANUAL_REVIEW_REQUIRED,
                    VerificationStatus.SOURCE_UNAVAILABLE,
                    VerificationStatus.VERIFICATION_PENDING,
                    VerificationStatus.MISMATCH_DETECTED,
                ])
            )

        items = query.order_by(desc(VerificationResult.id)).all()

        results = []
        for v_res, doc, inst in items:
            details = v_res.details_json or {}
            results.append(
                VerificationQueueItemOut(
                    id=v_res.id,
                    document_id=doc.id,
                    document_filename=doc.original_filename,
                    document_type_code=doc.document_type_code,
                    institute_id=inst.id,
                    institute_name=inst.name,
                    status=v_res.status,
                    source_name=v_res.source_name,
                    source_ref=v_res.source_ref,
                    checked_at=v_res.checked_at,
                    message=details.get("message"),
                    mismatched_fields=details.get("mismatched_fields", []),
                    created_at=v_res.created_at,
                )
            )

        return results

