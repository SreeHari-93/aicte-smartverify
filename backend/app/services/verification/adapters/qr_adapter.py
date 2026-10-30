import os
import json
import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

import fitz  # PyMuPDF
import cv2
import numpy as np
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.document import Document
from backend.app.services.verification.adapters.base import VerificationAdapter, AdapterRegistry
from backend.app.services.verification.schemas import VerificationResultDTO, VerificationStatus
from backend.app.services.verification.comparator import VerificationComparator


@AdapterRegistry.register("QR")
class QRVerificationAdapter(VerificationAdapter):
    """
    Adapter that detects and decodes QR codes from statutory certificates (PDF or Image)
    using PyMuPDF and OpenCV QRCodeDetector. Parses signed payloads, URLs, or structured data,
    and validates submitted fields against official encoded content.
    """

    def _decode_from_image_array(self, img_bgr: np.ndarray) -> Optional[str]:
        if img_bgr is None or img_bgr.size == 0:
            return None

        # 1. Try PyZbar if installed
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            decoded_objects = pyzbar_decode(img_bgr)
            for obj in decoded_objects:
                if obj.data:
                    return obj.data.decode("utf-8", errors="ignore")
        except ImportError:
            pass

        # 2. Try OpenCV QRCodeDetector
        try:
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img_bgr)
            if data and str(data).strip():
                return str(data).strip()
        except Exception:
            pass

        # 3. Try with grayscale / thresholding
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(gray)
            if data and str(data).strip():
                return str(data).strip()
        except Exception:
            pass

        return None

    def _extract_qr_from_document(self, file_path: str, mime_type: str) -> Optional[str]:
        if not file_path or not os.path.exists(file_path):
            return None

        is_pdf = "pdf" in (mime_type or "").lower() or file_path.lower().endswith(".pdf")

        if is_pdf:
            try:
                doc = fitz.open(file_path)
                # Check first 3 pages
                for page_num in range(min(3, len(doc))):
                    page = doc[page_num]

                    # 1. Check embedded images first
                    image_list = page.get_images(full=True)
                    for img_info in image_list:
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        nparr = np.frombuffer(image_bytes, np.uint8)
                        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        decoded = self._decode_from_image_array(img_cv)
                        if decoded:
                            doc.close()
                            return decoded

                    # 2. Render page pixmap at higher resolution
                    pix = page.get_pixmap(dpi=150)
                    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                    if pix.n == 4:
                        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                    elif pix.n == 3:
                        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                    else:
                        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)

                    decoded = self._decode_from_image_array(img_bgr)
                    if decoded:
                        doc.close()
                        return decoded
                doc.close()
            except Exception:
                pass
        else:
            # Direct image file
            try:
                img = cv2.imread(file_path)
                if img is not None:
                    return self._decode_from_image_array(img)
            except Exception:
                pass

        return None

    def _parse_payload(self, raw_data: str) -> Dict[str, Any]:
        """
        Parses raw QR string which may be JSON, URL, or key-value pairs.
        """
        raw_str = raw_data.strip()

        # 1. JSON payload
        if (raw_str.startswith("{") and raw_str.endswith("}")) or (raw_str.startswith("[") and raw_str.endswith("]")):
            try:
                parsed = json.loads(raw_str)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

        # 2. URL payload
        if raw_str.startswith("http://") or raw_str.startswith("https://") or "verify" in raw_str:
            parsed_url = urllib.parse.urlparse(raw_str)
            params = urllib.parse.parse_qs(parsed_url.query)
            flat_params = {k: v[0] for k, v in params.items() if v}
            flat_params["_source_url"] = raw_str
            return flat_params

        # 3. Delimited string (key:value|key:value)
        record = {}
        for part in raw_str.split("|"):
            if ":" in part:
                k, v = part.split(":", 1)
                record[k.strip().lower()] = v.strip()
        if record:
            return record

        return {"raw_payload": raw_str}

    def verify(
        self,
        document: Document,
        extracted_fields: Dict[str, Any],
        db: Session,
    ) -> VerificationResultDTO:
        file_path = document.file_path
        mime_type = document.mime_type

        qr_text = self._extract_qr_from_document(file_path, mime_type)

        if not qr_text:
            return VerificationResultDTO(
                status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
                source_name="QR_CODE_SCANNER",
                source_ref=f"DOC-{document.id}",
                message="No machine-readable QR code detected in statutory certificate. Routing to manual review.",
                details={
                    "qr_detected": False,
                    "reason": "QR code unreadable, missing, or unsupported encoding format.",
                },
            )

        raw_hash = hashlib.sha256(qr_text.encode("utf-8")).hexdigest()
        official_data = self._parse_payload(qr_text)

        # Field comparison
        comp = VerificationComparator.compare(
            submitted_fields=extracted_fields,
            official_record=official_data,
        )

        matched_fields = comp["matched_fields"]
        mismatched_fields = comp["mismatched_fields"]
        is_expired = comp["is_expired"]

        if is_expired:
            status = VerificationStatus.EXPIRED
            message = "QR code payload decoded successfully, but certificate has expired."
        elif mismatched_fields:
            status = VerificationStatus.MISMATCH_DETECTED
            mismatch_names = ", ".join(m["field"] for m in mismatched_fields)
            message = f"QR code decoded successfully, but field mismatch detected in: {mismatch_names}."
        else:
            status = VerificationStatus.VERIFIED
            message = "Statutory certificate verified successfully via embedded QR code."

        cert_ref = (
            official_data.get("certificate_number")
            or official_data.get("noc_number")
            or official_data.get("cert_id")
            or official_data.get("cert")
            or f"QR-{raw_hash[:8]}"
        )

        return VerificationResultDTO(
            status=status,
            source_name="EMBEDDED_QR_CODE",
            source_ref=str(cert_ref),
            checked_at=datetime.now(timezone.utc),
            matched_fields=matched_fields,
            mismatched_fields=mismatched_fields,
            raw_response_hash=raw_hash,
            message=message,
            details={
                "qr_detected": True,
                "decoded_fields": official_data,
                "all_comparisons": comp["all_comparisons"],
                "disclaimer": "OFFICIAL QR DECODER (Client / Embedded Authority Source)",
            },
        )

