from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.document import Document
from backend.app.services.verification.adapters.base import VerificationAdapter, AdapterRegistry
from backend.app.services.verification.schemas import VerificationResultDTO, VerificationStatus


@AdapterRegistry.register("MANUAL")
class ManualVerificationAdapter(VerificationAdapter):
    """
    Adapter for documents that always require manual physical or visual review
    by an authorised committee (e.g. Building Plan blueprints, Notarized Affidavits).
    """

    def verify(
        self,
        document: Document,
        extracted_fields: Dict[str, Any],
        db: Session,
    ) -> VerificationResultDTO:
        doc_code = document.document_type_code or "DOCUMENT"
        return VerificationResultDTO(
            status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
            source_name="MANUAL_INSPECTION",
            source_ref=f"DOC-{document.id}",
            message=f"Document '{doc_code}' requires manual verification by an authorised scrutiny committee.",
            details={
                "requires_manual_review": True,
                "reason": "Statutory verification method is designated as MANUAL inspection.",
                "document_type": doc_code,
            },
        )

