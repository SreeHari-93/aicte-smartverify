from datetime import datetime, date
from typing import List, Optional, Any

from backend.app.config import settings
from backend.app.services.anomaly.detectors.base import BaseDetector, DetectionContext
from backend.app.services.anomaly.schemas import AnomalyFlagDTO


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


class DateAnomalyDetector(BaseDetector):
    @property
    def name(self) -> str:
        return "DateAnomalyDetector"

    def detect(self, context: DetectionContext) -> List[AnomalyFlagDTO]:
        flags: List[AnomalyFlagDTO] = []
        doc = context.document
        ext = context.extracted_fields

        ext_issue = ext.get("issue_date") or ext.get("date_of_issue")
        ext_expiry = ext.get("expiry_date") or ext.get("valid_upto") or ext.get("valid_to")

        issue_d = _parse_field_date(ext_issue)
        expiry_d = _parse_field_date(ext_expiry)
        today = date.today()

        # 1. Issue date after expiry
        if issue_d and expiry_d and issue_d > expiry_d:
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="DATE_ISSUE_AFTER_EXPIRY",
                    group_key="DATE_ANOMALY",
                    severity="HIGH",
                    reason=f"Stated issue date ({issue_d.isoformat()}) post-dates the stated expiry date ({expiry_d.isoformat()}); potential anomaly requiring verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "field": "issue_date",
                        "value": issue_d.isoformat(),
                        "expected": f"before {expiry_d.isoformat()}",
                    }],
                    confidence=0.95,
                    recommended_action="Verify certificate dates against statutory authority register.",
                )
            )

        # 2. Future issue dates
        if issue_d and issue_d > today:
            flags.append(
                AnomalyFlagDTO(
                    detector=self.name,
                    code="DATE_FUTURE_ISSUE",
                    group_key="DATE_ANOMALY",
                    severity="HIGH",
                    reason=f"Certificate issue date ({issue_d.isoformat()}) is recorded in the future; needs verification.",
                    evidence=[{
                        "document_id": doc.id,
                        "field": "issue_date",
                        "value": issue_d.isoformat(),
                        "expected": f"on or before {today.isoformat()}",
                    }],
                    confidence=0.95,
                    recommended_action="Verify document issuance timestamp with issuing authority.",
                )
            )

        # 3. Validity period unusual for the document type
        if issue_d and expiry_d and context.doc_type and context.doc_type.default_validity_months:
            months = (expiry_d.year - issue_d.year) * 12 + (expiry_d.month - issue_d.month)
            def_months = context.doc_type.default_validity_months
            max_allowed = int(def_months * settings.ANOMALY_DATE_MAX_VALIDITY_MONTHS_RATIO)
            if months > max_allowed or months < 1:
                doc_label = context.doc_type.name or context.doc_type.code
                if expiry_d < issue_d:
                    validity_reason = f"Document validity period shows expiry date is earlier than issue date for {doc_label}; potential anomaly requiring verification."
                else:
                    validity_reason = f"Document validity duration ({months} months) differs substantially from standard {def_months}-month statutory period for {doc_label}; potential anomaly requiring verification."

                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="DATE_UNUSUAL_VALIDITY_PERIOD",
                        group_key="DATE_ANOMALY",
                        severity="MEDIUM",
                        reason=validity_reason,
                        evidence=[{
                            "document_id": doc.id,
                            "field": "validity_months",
                            "value": months,
                            "expected": def_months,
                        }],
                        confidence=0.80,
                        recommended_action="Confirm statutory certificate duration terms with issuing guidelines.",
                    )
                )

        # 4. Weekend or implausible dates as LOW indicators
        if issue_d:
            if issue_d.weekday() in (5, 6):
                day_name = issue_d.strftime("%A")
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="DATE_WEEKEND_ISSUE",
                        group_key="DATE_ANOMALY",
                        severity="LOW",
                        reason=f"Document issue date ({issue_d.isoformat()}, {day_name}) falls on a weekend; potential anomaly requiring verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "field": "issue_date",
                            "value": issue_d.isoformat(),
                            "day_of_week": day_name,
                        }],
                        confidence=0.50,
                        recommended_action="Review document issue details during administrative review.",
                    )
                )
            elif issue_d.year < 1950:
                flags.append(
                    AnomalyFlagDTO(
                        detector=self.name,
                        code="DATE_IMPLAUSIBLE",
                        group_key="DATE_ANOMALY",
                        severity="LOW",
                        reason=f"Document issue date ({issue_d.isoformat()}) appears implausible; needs verification.",
                        evidence=[{
                            "document_id": doc.id,
                            "field": "issue_date",
                            "value": issue_d.isoformat(),
                        }],
                        confidence=0.70,
                        recommended_action="Confirm document date records.",
                    )
                )

        return flags

