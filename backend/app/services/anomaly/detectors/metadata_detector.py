import os
from datetime import datetime, date
from typing import List, Optional, Any
import pymupdf

from backend.app.config import settings
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


def _parse_pdf_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    s = str(date_str).strip()
    if s.startswith("D:"):
        s = s[2:]
    if len(s) >= 8 and s[:8].isdigit():
        try:
            return datetime.strptime(s[:8], "%Y%m%d").date()
        except ValueError:
            pass
    return None


def _parse_field_date(val: Any) -> Optional[date]:
    if not val:
        return None
    val_str = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(val_str[:10], fmt).date()
        except ValueError:
            continue
    return None


class MetadataDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "MetadataDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document
        file_path = doc.file_path

        if not file_path or not os.path.exists(file_path) or not file_path.lower().endswith(".pdf"):
            return flags

        try:
            pdf = pymupdf.open(file_path)
            meta = pdf.metadata or {}
            pdf.close()
        except Exception:
            return flags

        producer = (meta.get("producer") or "").strip()
        creator = (meta.get("creator") or "").strip()
        author = (meta.get("author") or "").strip()
        comb_text = f"{producer} {creator} {author}".lower()

        c_date = _parse_pdf_date(meta.get("creationDate"))
        m_date = _parse_pdf_date(meta.get("modDate"))

        # 1. Known image or PDF editor in producer/creator
        matched_editors = [
            prod for prod in settings.ANOMALY_SUSPICIOUS_PRODUCERS
            if prod.lower() in comb_text
        ]
        if matched_editors:
            editor_name = matched_editors[0].title()
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="METADATA_SUSPICIOUS_PRODUCER",
                    group_key="METADATA",
                    severity="MEDIUM",
                    reason=f"PDF metadata identifies design or editing software ('{editor_name}'); potential anomaly requiring verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "producer": producer,
                        "creator": creator,
                        "matched_editor": editor_name,
                    }],
                    confidence=0.85,
                    recommended_action="Request the original unmodified statutory document directly from the issuing authority.",
                )
            )

        # 2. Creation date after the issue date on the certificate
        ext_issue = context.extracted_fields.get("issue_date") or context.extracted_fields.get("date_of_issue")
        issue_d = _parse_field_date(ext_issue)
        if c_date and issue_d:
            # If PDF creation date is more than 30 days after the stated certificate issue date
            if (c_date - issue_d).days > 30:
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="METADATA_CREATION_POSTDATES_ISSUE",
                        group_key="METADATA",
                        severity="MEDIUM",
                        reason=f"Digital PDF creation date ({c_date.isoformat()}) post-dates stated certificate issue date ({issue_d.isoformat()}); potential anomaly requiring verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "stated_issue_date": issue_d.isoformat(),
                            "pdf_creation_date": c_date.isoformat(),
                            "days_difference": (c_date - issue_d).days,
                        }],
                        confidence=0.80,
                        recommended_action="Verify issuance timeline with statutory authority register.",
                    )
                )

        # 3. Modification after creation by an editing tool
        if c_date and m_date and (m_date - c_date).days > 1:
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="METADATA_POST_CREATION_MODIFIED",
                    group_key="METADATA",
                    severity="LOW",
                    reason="PDF metadata indicates document modification after initial generation; needs verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "creation_date": c_date.isoformat(),
                        "modification_date": m_date.isoformat(),
                    }],
                    confidence=0.65,
                    recommended_action="Verify that modifications represent authorized digital endorsements rather than structural changes.",
                )
            )

        # 4. Missing metadata on a document that normally has it
        is_statutory = any(k in (doc.document_type_code or "").upper() for k in ("NBA", "NAAC", "FIRE", "LAND", "NOC"))
        if is_statutory and not producer and not creator and not c_date:
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="METADATA_MISSING_HEADERS",
                    group_key="METADATA",
                    severity="INFO",
                    reason="Standard PDF document metadata attributes are absent; needs verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "metadata_present": False,
                    }],
                    confidence=0.50,
                    recommended_action="Confirm document authenticity via primary statutory authority register.",
                )
            )

        return flags
