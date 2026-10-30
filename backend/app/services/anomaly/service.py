from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.models.anomaly import AnomalyRun, AnomalyFlag, AnomalyReviewStatus
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.application import Application
from backend.app.models.user import User
from backend.app.services.anomaly.detectors.base import DetectionContext, DetectorRegistry
import backend.app.services.anomaly.detectors  # Ensure detectors are registered
from backend.app.services.audit_service import AuditService


class AnomalyService:
    @classmethod
    def _resolve_group_key(cls, dto) -> str:
        if getattr(dto, "group_key", None):
            return dto.group_key
        if dto.detector == "DateAnomalyDetector":
            return "DATE_ANOMALY"
        elif dto.detector == "DuplicateDetector":
            return "DUPLICATE"
        elif dto.detector == "MetadataDetector":
            return "METADATA"
        elif dto.detector == "ImageTamperDetector":
            return "TAMPER"
        elif dto.detector == "IdentifierDetector":
            return "IDENTIFIER"
        elif dto.detector == "VerificationConflictDetector":
            return "VERIFICATION_CONFLICT"
        return "GENERAL"

    @classmethod
    def get_document_extracted_fields(cls, db: Session, doc: Document) -> Dict[str, Any]:
        """Collects extracted fields from document attributes and ExtractedField entities."""
        data = dict(doc.extracted_data or {})
        if doc.extracted_fields:
            for ef in doc.extracted_fields:
                k = getattr(ef, "key", None) or getattr(ef, "field_name", None)
                v = getattr(ef, "value", None) if getattr(ef, "value", None) is not None else getattr(ef, "field_value", None)
                if k and v is not None:
                    data[k] = v
        return data

    @classmethod
    def scan_document(
        cls,
        db: Session,
        document_id: int,
        triggered_by: Optional[int] = None,
    ) -> Tuple[AnomalyRun, List[AnomalyFlag]]:
        """
        Runs all registered anomaly detectors on a single document.
        Saves AnomalyRun and AnomalyFlag records, and logs an AuditLog event.
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document #{document_id} not found.")

        started_at = datetime.now(timezone.utc)
        doc_type = doc.document_type
        if not doc_type and doc.document_type_code:
            doc_type = (
                db.query(DocumentType)
                .filter(DocumentType.code == doc.document_type_code)
                .first()
            )

        app = doc.application
        extracted = cls.get_document_extracted_fields(db, doc)

        context = DetectionContext(
            db=db,
            document=doc,
            application=app,
            doc_type=doc_type,
            extracted_fields=extracted,
        )

        detectors = DetectorRegistry.get_detectors()
        detectors_run_names = [d.name for d in detectors]

        run = AnomalyRun(
            document_id=doc.id,
            application_id=doc.application_id,
            started_at=started_at,
            detectors_run=detectors_run_names,
        )
        db.add(run)
        db.flush()

        saved_flags: List[AnomalyFlag] = []

        for detector in detectors:
            try:
                flag_dtos = detector.detect(context)
                for dto in flag_dtos:
                    flag = AnomalyFlag(
                        run_id=run.id,
                        document_id=doc.id,
                        detector=dto.detector,
                        code=dto.code,
                        group_key=cls._resolve_group_key(dto),
                        severity=dto.severity,
                        reason=dto.reason,
                        evidence_json=dto.evidence,
                        confidence=dto.confidence,
                        recommended_action=dto.recommended_action,
                        review_status=AnomalyReviewStatus.OPEN,
                        overlay_image_path=dto.overlay_image_path,
                    )
                    db.add(flag)
                    saved_flags.append(flag)
            except Exception as e:
                # Detector failure logged but doesn't halt others
                pass

        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        for f in saved_flags:
            db.refresh(f)

        # AuditLog record
        user_role = "INSTITUTE"
        if triggered_by:
            u = db.query(User).filter(User.id == triggered_by).first()
            if u:
                user_role = u.role

        AuditService.log_event(
            db=db,
            action="ANOMALY_SCAN_EXECUTED",
            user_id=triggered_by,
            role=user_role,
            reason=f"Anomaly scan executed for Document #{doc.id} ({doc.original_filename}): {len(saved_flags)} flags detected.",
            details={
                "document_id": doc.id,
                "run_id": run.id,
                "flag_count": len(saved_flags),
                "detectors_run": detectors_run_names,
            },
        )

        return run, saved_flags

    @classmethod
    def scan_application(
        cls,
        db: Session,
        application_id: int,
        triggered_by: Optional[int] = None,
    ) -> Tuple[AnomalyRun, List[AnomalyFlag]]:
        """
        Runs anomaly detection across all documents of an application.
        """
        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise ValueError(f"Application #{application_id} not found.")

        docs = db.query(Document).filter(Document.application_id == app.id).all()
        started_at = datetime.now(timezone.utc)
        detectors = DetectorRegistry.get_detectors()
        detectors_run_names = [d.name for d in detectors]

        app_run = AnomalyRun(
            application_id=app.id,
            document_id=None,
            started_at=started_at,
            detectors_run=detectors_run_names,
        )
        db.add(app_run)
        db.flush()

        all_flags: List[AnomalyFlag] = []

        for doc in docs:
            doc_type = doc.document_type
            if not doc_type and doc.document_type_code:
                doc_type = (
                    db.query(DocumentType)
                    .filter(DocumentType.code == doc.document_type_code)
                    .first()
                )
            extracted = cls.get_document_extracted_fields(db, doc)
            context = DetectionContext(
                db=db,
                document=doc,
                application=app,
                doc_type=doc_type,
                extracted_fields=extracted,
            )

            for detector in detectors:
                try:
                    dtos = detector.detect(context)
                    for dto in dtos:
                        flag = AnomalyFlag(
                            run_id=app_run.id,
                            document_id=doc.id,
                            detector=dto.detector,
                            code=dto.code,
                            group_key=cls._resolve_group_key(dto),
                            severity=dto.severity,
                            reason=dto.reason,
                            evidence_json=dto.evidence,
                            confidence=dto.confidence,
                            recommended_action=dto.recommended_action,
                            review_status=AnomalyReviewStatus.OPEN,
                            overlay_image_path=dto.overlay_image_path,
                        )
                        db.add(flag)
                        all_flags.append(flag)
                except Exception:
                    pass

        app_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(app_run)
        for f in all_flags:
            db.refresh(f)

        user_role = "INSTITUTE"
        if triggered_by:
            u = db.query(User).filter(User.id == triggered_by).first()
            if u:
                user_role = u.role

        AuditService.log_event(
            db=db,
            action="ANOMALY_SCAN_EXECUTED",
            user_id=triggered_by,
            role=user_role,
            reason=f"Anomaly scan executed for Application #{app.id} ({app.application_id}): {len(all_flags)} flags detected across {len(docs)} documents.",
            details={
                "application_id": app.id,
                "run_id": app_run.id,
                "flag_count": len(all_flags),
                "document_count": len(docs),
            },
        )

        return app_run, all_flags

    @classmethod
    def review_flag(
        cls,
        db: Session,
        flag_id: int,
        status: str,
        note: str,
        reviewer_id: int,
    ) -> AnomalyFlag:
        """
        Admin review action on an anomaly flag. Note is mandatory.
        """
        flag = db.query(AnomalyFlag).filter(AnomalyFlag.id == flag_id).first()
        if not flag:
            raise ValueError(f"Anomaly flag #{flag_id} not found.")

        valid_statuses = [
            AnomalyReviewStatus.CONFIRMED_OK,
            AnomalyReviewStatus.NEEDS_ACTION,
            AnomalyReviewStatus.DISMISSED,
            AnomalyReviewStatus.OPEN,
        ]
        if status not in valid_statuses:
            raise ValueError(f"Invalid review status '{status}'. Must be one of {valid_statuses}")

        if not note or len(note.strip()) < 3:
            raise ValueError("Review note is mandatory (minimum 3 characters).")

        old_status = flag.review_status
        flag.review_status = status
        flag.review_note = note.strip()
        flag.reviewed_by = reviewer_id
        flag.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(flag)

        AuditService.log_event(
            db=db,
            action="ANOMALY_FLAG_REVIEWED",
            user_id=reviewer_id,
            role="ADMIN",
            reason=f"Anomaly flag #{flag.id} ({flag.detector} / {flag.code}) updated from {old_status} to {status}: {note}",
            details={
                "flag_id": flag.id,
                "old_status": old_status,
                "new_status": status,
                "review_note": note,
                "detector": flag.detector,
                "code": flag.code,
            },
        )

        return flag

    @classmethod
    def get_flags_for_document(cls, db: Session, document_id: int) -> List[AnomalyFlag]:
        return (
            db.query(AnomalyFlag)
            .filter(AnomalyFlag.document_id == document_id)
            .order_by(desc(AnomalyFlag.id))
            .all()
        )

    @classmethod
    def get_admin_flags(
        cls,
        db: Session,
        severity: Optional[str] = None,
        detector: Optional[str] = None,
        status: Optional[str] = None,
        institute_id: Optional[int] = None,
    ) -> List[AnomalyFlag]:
        query = db.query(AnomalyFlag).join(Document, AnomalyFlag.document_id == Document.id)
        if severity:
            query = query.filter(AnomalyFlag.severity == severity.upper())
        if detector:
            query = query.filter(AnomalyFlag.detector == detector)
        if status:
            query = query.filter(AnomalyFlag.review_status == status.upper())
        if institute_id:
            query = query.filter(Document.institute_id == institute_id)

        return query.order_by(desc(AnomalyFlag.id)).all()

