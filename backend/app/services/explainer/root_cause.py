from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
import re


ALLOWED_CAUSES = {
    "MISSING_DOCUMENT",
    "EXPIRED_DOCUMENT",
    "EXPIRING_SOON",
    "DATA_MISMATCH",
    "VERIFICATION_FAILED",
    "ANOMALY_FLAG",
    "INFRASTRUCTURE_GAP",
    "THRESHOLD_NOT_MET",
    "INCOMPLETE_FIELD",
}

SEVERITY_ORDER = {
    "BLOCKER": 0,
    "MAJOR": 1,
    "MINOR": 2,
    "ADVISORY": 3,
}


@dataclass
class EvidenceItem:
    document: Optional[str] = None
    page: Optional[int] = None
    field: Optional[str] = None
    extracted: Optional[Any] = None
    expected: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document": self.document,
            "page": self.page,
            "field": self.field,
            "extracted": self.extracted,
            "expected": self.expected,
        }


@dataclass
class RootCause:
    cause_code: str
    headline: str
    affected_rule_codes: List[str]
    severity: str
    evidence: List[Dict[str, Any]]
    fixable_by_institute: bool
    ordered_suggested_actions: List[str]
    needs_official_review: bool
    finding_ids: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cause_code": self.cause_code,
            "headline": self.headline,
            "affected_rule_codes": self.affected_rule_codes,
            "severity": self.severity,
            "evidence": self.evidence,
            "fixable_by_institute": self.fixable_by_institute,
            "ordered_suggested_actions": self.ordered_suggested_actions,
            "needs_official_review": self.needs_official_review,
            "finding_ids": self.finding_ids,
        }


class RootCauseAnalyzer:
    """
    Deterministic root cause analysis engine before any AI or LLM processing.
    Groups failed findings by 9 statutory causes, merges cascading rule failures
    originating from the same missing/expired document or evidence, and ranks them
    by severity and number of affected rules.
    """

    @classmethod
    def classify_finding(
        cls,
        finding: Any,
        rule_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Determines the canonical cause_code for a single finding.
        """
        rule_code = str(getattr(finding, "rule_code", "") or "")
        reason = str(getattr(finding, "reason", "") or "")
        title = str(getattr(finding, "rule_title", "") or "")
        reason_lower = reason.lower()
        title_lower = title.lower()

        # 1. Document pipeline specific prefixes
        if rule_code.startswith("DOC_EXP_SOON_"):
            return "EXPIRING_SOON"
        if rule_code.startswith("DOC_EXP_"):
            return "EXPIRED_DOCUMENT"
        if rule_code.startswith("DOC_DUP_"):
            return "ANOMALY_FLAG"
        if rule_code.startswith("DOC_MISMATCH_") or rule_code.startswith("DOC_NAME_MISMATCH_"):
            return "DATA_MISMATCH"

        # 2. Check for missing document first across all rules (a missing document causes cascade failures)
        if any(w in reason_lower for w in ["missing", "not uploaded", "not provided", "not found", "mandatory document", "upload required"]):
            return "MISSING_DOCUMENT"

        # 3. Rule definition metadata if available
        rule_type = ""
        if rule_meta:
            rule_type = str(rule_meta.get("rule_type", "") or "").upper()

        if rule_type == "DOCUMENT_REQUIRED":
            return "MISSING_DOCUMENT"
        elif rule_type == "VALIDITY_PERIOD":
            if "expired" in reason_lower or "expired" in title_lower:
                return "EXPIRED_DOCUMENT"
            return "EXPIRING_SOON"
        elif rule_type == "CROSS_FIELD_MATCH":
            return "DATA_MISMATCH"
        elif rule_type == "EXTERNAL_VERIFICATION":
            return "VERIFICATION_FAILED"
        elif rule_type == "INFRASTRUCTURE":
            return "INFRASTRUCTURE_GAP"
        elif rule_type in ("NUMERIC_THRESHOLD", "COUNT_AT_LEAST"):
            return "THRESHOLD_NOT_MET"
        elif rule_type == "FIELD_REQUIRED":
            return "INCOMPLETE_FIELD"

        # 4. Deterministic semantic keywords from reason & title
        if any(w in reason_lower for w in ["duplicate", "tamper", "hash", "anomaly", "forged", "altered"]):
            return "ANOMALY_FLAG"

        if any(w in reason_lower for w in ["expired on", "has expired", "is expired", "certificate expired"]):
            return "EXPIRED_DOCUMENT"

        if any(w in reason_lower for w in ["expiring soon", "validity period", "expires within", "days remaining"]):
            return "EXPIRING_SOON"

        if any(w in reason_lower for w in ["missing", "not uploaded", "not provided", "not found", "mandatory document", "upload required"]):
            return "MISSING_DOCUMENT"

        if any(w in reason_lower for w in ["external verification", "unverified", "failed verification", "verification failed"]):
            return "VERIFICATION_FAILED"

        if any(w in reason_lower for w in ["mismatch", "inconsistent", "differs", "does not match", "discrepancy"]):
            return "DATA_MISMATCH"

        if any(w in reason_lower for w in ["carpet area", "land area", "built up", "infrastructure", "classroom", "laboratory", "sqm", "sq m", "sqft"]):
            return "INFRASTRUCTURE_GAP"

        if any(w in reason_lower for w in ["incomplete", "empty field", "field is required", "missing field", "not specified"]):
            return "INCOMPLETE_FIELD"

        if any(w in reason_lower for w in ["threshold", "ratio", "intake", "minimum", "exceed", "less than", "count"]):
            return "THRESHOLD_NOT_MET"

        # Default fallback
        return "THRESHOLD_NOT_MET"

    @classmethod
    def _extract_doc_key(
        cls,
        finding: Any,
        rule_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Extracts document type or key from rule.evidence_required or finding evidence.
        Used to merge cascades (one missing document failing multiple rules).
        """
        # 1. Check rule.evidence_required
        if rule_meta:
            evidence_req = rule_meta.get("evidence_required")
            if isinstance(evidence_req, list) and len(evidence_req) > 0:
                return str(evidence_req[0]).strip().upper()
            elif isinstance(evidence_req, str) and evidence_req.strip():
                return evidence_req.strip().upper()

        # 2. Check evidence_json on finding
        ev_json = getattr(finding, "evidence_json", None)
        if isinstance(ev_json, list) and len(ev_json) > 0:
            first_ev = ev_json[0]
            if isinstance(first_ev, dict):
                doc_val = (
                    first_ev.get("document_type")
                    or first_ev.get("document")
                    or first_ev.get("declared_type")
                    or first_ev.get("filename")
                )
                if doc_val:
                    return str(doc_val).strip().upper()

        # 3. Check rule_code suffix (e.g., DOC_EXP_FIRE_SAFETY -> FIRE_SAFETY)
        rule_code = str(getattr(finding, "rule_code", "") or "")
        for pfx in ("DOC_EXP_SOON_", "DOC_EXP_", "DOC_DUP_", "DOC_MISMATCH_", "DOC_NAME_MISMATCH_"):
            if rule_code.startswith(pfx):
                return rule_code[len(pfx):].strip().upper()

        # 4. Extract common known document keywords from reason/title
        reason = str(getattr(finding, "reason", "") or "")
        title = str(getattr(finding, "rule_title", "") or "")
        combined = f"{title} {reason}".upper()

        known_docs = [
            "FIRE & SAFETY NOC",
            "FIRE SAFETY NOC",
            "FIRE_SAFETY_NOC",
            "BUILDING COMPLETION CERTIFICATE",
            "BUILDING_PLAN",
            "LAND OCCUPANCY CERTIFICATE",
            "LAND_DEED",
            "LAND_REGISTRATION",
            "OCCUPANCY_CERTIFICATE",
            "AICTE_APPROVAL_LETTER",
            "AFFILIATION_CERTIFICATE",
            "BALANCE_SHEET",
            "AUDITED_FINANCIAL_STATEMENTS",
        ]
        for kd in known_docs:
            if kd in combined:
                return kd.replace(" ", "_")

        return rule_code or "GENERAL_DOCUMENT"

    @classmethod
    def _extract_standardized_evidence(cls, finding: Any) -> List[Dict[str, Any]]:
        ev_items: List[Dict[str, Any]] = []
        raw_ev = getattr(finding, "evidence_json", None)

        if isinstance(raw_ev, list):
            for item in raw_ev:
                if isinstance(item, dict):
                    doc_name = (
                        item.get("filename")
                        or item.get("document")
                        or item.get("document_type")
                        or item.get("declared_type")
                    )
                    page = item.get("page")
                    field_name = item.get("field") or item.get("key") or item.get("metric")
                    extracted = (
                        item.get("extracted")
                        or item.get("extracted_value")
                        or item.get("actual")
                        or item.get("expiry_date")
                        or item.get("predicted_type")
                    )
                    expected = item.get("expected") or item.get("required") or item.get("standard")
                    ev_items.append(
                        EvidenceItem(
                            document=str(doc_name) if doc_name is not None else None,
                            page=int(page) if page is not None and str(page).isdigit() else None,
                            field=str(field_name) if field_name is not None else None,
                            extracted=extracted,
                            expected=expected,
                        ).to_dict()
                    )
        if not ev_items:
            # Fallback single evidence item from reason
            ev_items.append(
                EvidenceItem(
                    document=str(getattr(finding, "rule_title", "") or getattr(finding, "rule_code", "")),
                    extracted=getattr(finding, "reason", None),
                ).to_dict()
            )

        return ev_items

    @classmethod
    def analyze_findings(
        cls,
        findings: List[Any],
        rules_by_code: Optional[Dict[str, Any]] = None,
    ) -> List[RootCause]:
        """
        Takes raw ValidationFinding models or dicts, filters for failed/blocking
        findings (ignoring PASS and waived findings), merges cascades, and returns
        ranked RootCause objects.
        """
        rules_by_code = rules_by_code or {}

        # 1. Filter findings: only failed / un-waived findings
        failed_findings = []
        for f in findings:
            status = getattr(f, "status", None) or (f.get("status") if isinstance(f, dict) else "")
            is_waived = getattr(f, "is_waived", False) or (f.get("is_waived", False) if isinstance(f, dict) else False)
            if status != "PASS" and not is_waived:
                failed_findings.append(f)

        if not failed_findings:
            return []

        # 2. Group and Merge Cascades
        # Groups map: cascade_group_key -> dict of aggregated data
        groups: Dict[tuple, Dict[str, Any]] = {}

        for f in failed_findings:
            rule_code = getattr(f, "rule_code", None) or (f.get("rule_code") if isinstance(f, dict) else "")
            rule_meta = rules_by_code.get(rule_code, {})
            if hasattr(rule_meta, "__dict__"):
                rule_meta_dict = {
                    "rule_type": getattr(rule_meta, "rule_type", None),
                    "evidence_required": getattr(rule_meta, "evidence_required", None),
                    "title": getattr(rule_meta, "title", None),
                }
            elif isinstance(rule_meta, dict):
                rule_meta_dict = rule_meta
            else:
                rule_meta_dict = {}

            cause_code = cls.classify_finding(f, rule_meta_dict)
            doc_key = cls._extract_doc_key(f, rule_meta_dict)

            # Cascade merge key:
            # - For MISSING_DOCUMENT: group by (cause, doc_key)
            # - For EXPIRED_DOCUMENT: group by (cause, doc_key)
            # - For EXPIRING_SOON: group by (cause, doc_key)
            # - For ANOMALY_FLAG: group by (cause, doc_key)
            # - For other causes: group by (cause, doc_key) or rule_code
            if cause_code in ("MISSING_DOCUMENT", "EXPIRED_DOCUMENT", "EXPIRING_SOON", "ANOMALY_FLAG"):
                cascade_key = (cause_code, doc_key)
            else:
                # Group by cause and doc_key or specific metric
                cascade_key = (cause_code, doc_key if doc_key != "GENERAL_DOCUMENT" else rule_code)

            if cascade_key not in groups:
                groups[cascade_key] = {
                    "cause_code": cause_code,
                    "doc_key": doc_key,
                    "findings": [],
                    "rule_codes": [],
                    "severities": [],
                    "actions": [],
                    "evidence_list": [],
                    "finding_ids": [],
                    "needs_official_review": False,
                }

            group = groups[cascade_key]
            group["findings"].append(f)
            if rule_code and rule_code not in group["rule_codes"]:
                group["rule_codes"].append(rule_code)

            finding_id = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
            if finding_id and finding_id not in group["finding_ids"]:
                group["finding_ids"].append(finding_id)

            sev = getattr(f, "severity", None) or (f.get("severity") if isinstance(f, dict) else "MAJOR")
            group["severities"].append(sev)

            action = getattr(f, "suggested_action", None) or (f.get("suggested_action") if isinstance(f, dict) else None)
            if action and action.strip() and action.strip() not in group["actions"]:
                group["actions"].append(action.strip())

            # Check if review is needed
            f_status = getattr(f, "status", None) or (f.get("status") if isinstance(f, dict) else "")
            if f_status == "NEEDS_REVIEW" or cause_code in ("ANOMALY_FLAG", "VERIFICATION_FAILED"):
                group["needs_official_review"] = True

            # Evidence
            ev_items = cls._extract_standardized_evidence(f)
            group["evidence_list"].extend(ev_items)

        # 3. Construct RootCause instances from merged groups
        root_causes: List[RootCause] = []

        for cascade_key, grp in groups.items():
            cause_code = grp["cause_code"]
            doc_key = grp["doc_key"]
            rule_codes = grp["rule_codes"]
            rule_count = len(rule_codes)

            # Determine dominant severity (highest severity in group)
            sorted_sevs = sorted(grp["severities"], key=lambda s: SEVERITY_ORDER.get(s, 99))
            highest_sev = sorted_sevs[0] if sorted_sevs else "MAJOR"

            # Fixability
            if cause_code in ("MISSING_DOCUMENT", "EXPIRED_DOCUMENT", "EXPIRING_SOON", "INCOMPLETE_FIELD"):
                fixable = True
            elif cause_code == "DATA_MISMATCH":
                fixable = True
            else:
                fixable = False

            # Needs official review
            needs_review = grp["needs_official_review"] or (not fixable) or (highest_sev == "BLOCKER" and cause_code in ("ANOMALY_FLAG", "VERIFICATION_FAILED", "INFRASTRUCTURE_GAP"))

            # Format Headline:
            clean_doc_name = doc_key.replace("_", " ").title()
            if cause_code == "MISSING_DOCUMENT":
                if rule_count > 1:
                    headline = f"Missing Statutory Document: {clean_doc_name} (affects {rule_count} rules)"
                else:
                    rule_ref = rule_codes[0] if rule_codes else "Compliance Check"
                    headline = f"Missing Statutory Document: {clean_doc_name} (Rule {rule_ref})"
            elif cause_code == "EXPIRED_DOCUMENT":
                if rule_count > 1:
                    headline = f"Expired Document: {clean_doc_name} (affects {rule_count} rules)"
                else:
                    rule_ref = rule_codes[0] if rule_codes else "Compliance Check"
                    headline = f"Expired Document: {clean_doc_name} (Rule {rule_ref})"
            elif cause_code == "EXPIRING_SOON":
                headline = f"Document Expiring Soon: {clean_doc_name} (Rule {rule_codes[0] if rule_codes else ''})"
            elif cause_code == "DATA_MISMATCH":
                headline = f"Data Mismatch Detected: {clean_doc_name} (affects {rule_count} rules)"
            elif cause_code == "ANOMALY_FLAG":
                headline = f"Document Anomaly Flagged: {clean_doc_name} (needs verification)"
            elif cause_code == "VERIFICATION_FAILED":
                headline = f"External Verification Failed for {clean_doc_name}"
            elif cause_code == "INFRASTRUCTURE_GAP":
                headline = f"Infrastructure Capacity Deficiency: {clean_doc_name}"
            elif cause_code == "THRESHOLD_NOT_MET":
                headline = f"Statutory Threshold Not Met: {clean_doc_name}"
            elif cause_code == "INCOMPLETE_FIELD":
                headline = f"Incomplete Mandatory Field: {clean_doc_name}"
            else:
                headline = f"Compliance Issue: {clean_doc_name}"

            # Suggested actions
            actions = grp["actions"]
            if not actions:
                if cause_code == "MISSING_DOCUMENT":
                    actions = [f"Upload the valid {clean_doc_name} in the document portal."]
                elif cause_code == "EXPIRED_DOCUMENT":
                    actions = [f"Renew the certificate and upload the valid renewed {clean_doc_name}."]
                elif cause_code == "EXPIRING_SOON":
                    actions = [f"Initiate renewal process for {clean_doc_name} with the competent authority."]
                elif cause_code == "DATA_MISMATCH":
                    actions = ["Review extracted document data and update institutional profile to match official records."]
                elif cause_code == "ANOMALY_FLAG":
                    actions = ["Ensure genuine, unmodified statutory documents are uploaded and request verification."]
                else:
                    actions = ["Consult AICTE Approval Process Handbook guidelines and submit rectified records."]

            # Deduplicate evidence
            seen_ev = set()
            deduped_ev = []
            for ev in grp["evidence_list"]:
                ev_str = f"{ev.get('document')}:{ev.get('field')}:{ev.get('extracted')}"
                if ev_str not in seen_ev:
                    seen_ev.add(ev_str)
                    deduped_ev.append(ev)

            rc = RootCause(
                cause_code=cause_code,
                headline=headline,
                affected_rule_codes=rule_codes,
                severity=highest_sev,
                evidence=deduped_ev,
                fixable_by_institute=fixable,
                ordered_suggested_actions=actions,
                needs_official_review=needs_review,
                finding_ids=grp["finding_ids"],
            )
            root_causes.append(rc)

        # 4. Rank by severity, then by the number of rules affected
        root_causes.sort(
            key=lambda item: (
                SEVERITY_ORDER.get(item.severity, 99),
                -len(item.affected_rule_codes),
                item.cause_code,
            )
        )

        return root_causes
