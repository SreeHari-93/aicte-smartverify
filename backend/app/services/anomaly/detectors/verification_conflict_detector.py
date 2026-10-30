from typing import List
from sqlalchemy.orm import Session

from backend.app.models.verification import VerificationResult, VerificationStatus
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


class VerificationConflictDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "VerificationConflictDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document
        db: Session = context.db

        # Retrieve latest statutory verification outcome
        ver_res = doc.latest_verification
        if not ver_res:
            ver_res = (
                db.query(VerificationResult)
                .filter(VerificationResult.document_id == doc.id)
                .order_by(VerificationResult.id.desc())
                .first()
            )

        if not ver_res:
            return flags

        # 1. Authority mismatch conflict
        if ver_res.status == VerificationStatus.MISMATCH_DETECTED:
            details = ver_res.details_json or {}
            mismatches = details.get("mismatched_fields", [])
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="VERIFICATION_CONFLICT_MISMATCH",
                    severity="HIGH",
                    reason=f"External statutory authority ({ver_res.source_name}) reported MISMATCH_DETECTED while document is submitted as valid; potential anomaly requiring verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "verification_status": ver_res.status,
                        "source_name": ver_res.source_name,
                        "mismatches": mismatches,
                    }],
                    confidence=0.95,
                    recommended_action="Submit corrected statutory certificate or obtain official issuing authority confirmation.",
                )
            )

        # 2. Authority expired conflict
        elif ver_res.status == VerificationStatus.EXPIRED:
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="VERIFICATION_CONFLICT_EXPIRED",
                    severity="HIGH",
                    reason=f"External statutory authority ({ver_res.source_name}) records indicate certificate has expired; potential anomaly requiring verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "verification_status": ver_res.status,
                        "source_name": ver_res.source_name,
                    }],
                    confidence=0.95,
                    recommended_action="Obtain and upload renewed certificate from issuing authority.",
                )
            )

        return flags

