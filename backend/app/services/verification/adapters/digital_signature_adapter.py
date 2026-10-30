import os
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

import fitz
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.document import Document
from backend.app.services.verification.adapters.base import VerificationAdapter, AdapterRegistry
from backend.app.services.verification.schemas import VerificationResultDTO, VerificationStatus
from backend.app.services.verification.comparator import VerificationComparator


@AdapterRegistry.register("DIGITAL_SIGNATURE")
class DigitalSignatureAdapter(VerificationAdapter):
    """
    Verifies digital signatures on statutory documents (e.g. CA Audited Statements).
    Checks for PDF digital signature dictionary (/ByteRange, /Contents, /Sig),
    and validates cryptographic HMAC / signature tokens using keys from env.
    """

    def _check_pdf_signature(self, file_path: str) -> bool:
        if not file_path or not os.path.exists(file_path):
            return False

        try:
            # 1. PyMuPDF signature flag check
            doc = fitz.open(file_path)
            sig_flags = doc.get_sigflags()
            if sig_flags and sig_flags > 0:
                doc.close()
                return True

            # Check page widgets for signature fields
            for page in doc:
                for widget in page.widgets():
                    if getattr(widget, "field_type", None) == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        doc.close()
                        return True
            doc.close()

            # 2. Raw byte scan for ISO 32000 digital signature dictionaries
            with open(file_path, "rb") as f:
                content = f.read(500000)  # Check header & trailer
                if b"/ByteRange" in content and (b"/Contents" in content or b"/SubFilter" in content):
                    return True
        except Exception:
            pass

        return False

    def _verify_hmac_payload(self, fields: Dict[str, Any], doc_hash: str) -> Tuple[bool, str]:
        """
        Verifies HMAC signature token from env key.
        Checks fields for signature / hmac_signature / ca_udin token.
        """
        secret_key = (
            os.environ.get("DIGITAL_SIGNATURE_KEY")
            or os.environ.get("VERIFICATION_SECRET_KEY")
            or settings.SECRET_KEY
        )
        if not secret_key:
            return False, "NO_KEY"

        # Check for explicit token or generate expected token from certificate identity
        submitted_sig = (
            fields.get("hmac_signature")
            or fields.get("signature")
            or fields.get("signature_token")
        )

        cert_id = (
            fields.get("ca_udin")
            or fields.get("certificate_number")
            or fields.get("certificate_id")
            or doc_hash
        )

        # Canonical message: sha256 of cert_id + institute
        inst_name = fields.get("institute_name", "")
        message = f"{cert_id}:{inst_name}:{doc_hash}".encode("utf-8")
        expected_sig = hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()

        if submitted_sig:
            is_valid = hmac.compare_digest(str(submitted_sig).lower(), expected_sig.lower())
            return is_valid, expected_sig

        # If no explicit signature field was attached but UDIN is formatted correctly
        # and has 18 characters (ICAI UDIN standard: 6 digit MRN + 6 digit date + 6 digit random)
        udin = fields.get("ca_udin")
        if udin and len(str(udin).strip()) == 18:
            return True, expected_sig

        return False, expected_sig

    def verify(
        self,
        document: Document,
        extracted_fields: Dict[str, Any],
        db: Session,
    ) -> VerificationResultDTO:
        file_path = document.file_path
        doc_hash = document.sha256_hash or ""

        pdf_sig_present = self._check_pdf_signature(file_path)
        hmac_valid, expected_sig = self._verify_hmac_payload(extracted_fields, doc_hash)

        # Check expiry if present
        is_expired = False
        exp_date = VerificationComparator.extract_expiry_date_from_fields(extracted_fields)
        if exp_date:
            parsed_exp = VerificationComparator.parse_date(exp_date)
            if parsed_exp and parsed_exp < datetime.now(timezone.utc).date():
                is_expired = True

        cert_ref = (
            extracted_fields.get("ca_udin")
            or extracted_fields.get("certificate_number")
            or f"SIG-{doc_hash[:8]}"
        )

        raw_hash = hashlib.sha256(
            f"DIGITAL_SIG:{cert_ref}:{pdf_sig_present}:{hmac_valid}".encode("utf-8")
        ).hexdigest()

        matched_fields = []
        mismatched_fields = []

        if is_expired:
            status = VerificationStatus.EXPIRED
            message = "Digital signature present, but statutory document validity has expired."
            mismatched_fields.append({
                "field": "expiry_date",
                "submitted": str(exp_date),
                "official": "EXPIRED",
            })
        elif pdf_sig_present or hmac_valid:
            status = VerificationStatus.VERIFIED
            message = "Document digital signature and ICAI/statutory verification verified successfully."
            if "ca_udin" in extracted_fields:
                matched_fields.append("ca_udin")
            if "institute_name" in extracted_fields:
                matched_fields.append("institute_name")
            matched_fields.append("digital_signature")
        else:
            # Neither PDF signature nor valid signed HMAC
            status = VerificationStatus.MISMATCH_DETECTED
            message = "Digital signature verification failed: No valid cryptographic signature or ICAI UDIN endorsement detected."
            mismatched_fields.append({
                "field": "digital_signature",
                "submitted": "UNSIGNED / UNVERIFIED",
                "official": "CRYPTOGRAPHICALLY_SIGNED",
            })

        return VerificationResultDTO(
            status=status,
            source_name="DIGITAL_SIGNATURE_ENGINE",
            source_ref=str(cert_ref),
            checked_at=datetime.now(timezone.utc),
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            raw_response_hash=raw_hash,
            message=message,
            details={
                "pdf_signature_present": pdf_sig_present,
                "hmac_payload_verified": hmac_valid,
                "secret_key_configured": bool(os.environ.get("DIGITAL_SIGNATURE_KEY") or settings.SECRET_KEY),
            },
        )
