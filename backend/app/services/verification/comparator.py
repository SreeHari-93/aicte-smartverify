import re
from datetime import datetime, date, timezone
from difflib import SequenceMatcher
from typing import Dict, Any, List, Tuple, Optional


class VerificationComparator:
    """
    Compares submitted document fields against official records / authority source responses.
    Implements certificate number normalization, fuzzy institute name matching,
    and date parsing/expiry checks. Records every comparison for full auditability.
    """

    @classmethod
    def normalize_str(cls, val: Any) -> str:
        if val is None:
            return ""
        return re.sub(r"\s+", " ", str(val).strip())

    @classmethod
    def normalize_cert_number(cls, val: Any) -> str:
        if val is None:
            return ""
        s = str(val).strip().upper()
        # Remove hyphens, slashes, and spaces for canonical comparison
        return re.sub(r"[\s\-_/]", "", s)

    @classmethod
    def normalize_institute_name(cls, name: Any) -> str:
        if name is None:
            return ""
        s = str(name).lower()
        # Replace punctuation with space
        s = re.sub(r"[^\w\s]", " ", s)
        # Remove common tokens
        tokens = s.split()
        stopwords = {"of", "and", "&", "the", "in", "at", "for"}
        filtered = [t for t in tokens if t not in stopwords]
        return " ".join(filtered)

    @classmethod
    def fuzzy_institute_match(cls, submitted: str, official: str, threshold: float = 0.80) -> Tuple[bool, float]:
        if not submitted or not official:
            return False, 0.0

        norm_sub = cls.normalize_institute_name(submitted)
        norm_off = cls.normalize_institute_name(official)

        if not norm_sub or not norm_off:
            return False, 0.0

        # Exact match after normalization
        if norm_sub == norm_off:
            return True, 1.0

        # Substring containment
        if norm_sub in norm_off or norm_off in norm_sub:
            return True, 0.95

        # Token set overlap
        sub_tokens = set(norm_sub.split())
        off_tokens = set(norm_off.split())
        if sub_tokens and off_tokens:
            intersection = sub_tokens & off_tokens
            union = sub_tokens | off_tokens
            jaccard = len(intersection) / len(union)
            if jaccard >= 0.70:
                return True, round(jaccard, 2)

        # Sequence matcher ratio
        ratio = SequenceMatcher(None, norm_sub, norm_off).ratio()
        return ratio >= threshold, round(ratio, 2)

    @classmethod
    def parse_date(cls, val: Any) -> Optional[date]:
        if not val:
            return None
        if isinstance(val, date) and not isinstance(val, datetime):
            return val
        if isinstance(val, datetime):
            return val.date()

        s = str(val).strip()
        formats = [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ]
        # Try extracting just YYYY-MM-DD if ISO format with time
        if "T" in s:
            s = s.split("T")[0]

        for fmt in formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    @classmethod
    def extract_cert_number_from_fields(cls, fields: Dict[str, Any]) -> Optional[str]:
        keys = [
            "certificate_number",
            "noc_number",
            "approval_number",
            "deed_number",
            "accreditation_number",
            "accreditation_id",
            "certificate_id",
            "cert_id",
            "fdr_account_number",
            "ca_udin",
            "audit_id",
            "guarantee_no",
        ]
        for k in keys:
            val = fields.get(k)
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    @classmethod
    def extract_institute_name_from_fields(cls, fields: Dict[str, Any]) -> Optional[str]:
        keys = ["institute_name", "institution_name", "building_name", "college_name", "owner_name"]
        for k in keys:
            val = fields.get(k)
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    @classmethod
    def extract_issue_date_from_fields(cls, fields: Dict[str, Any]) -> Optional[Any]:
        keys = ["issue_date", "date_of_issue", "execution_date", "completion_date"]
        for k in keys:
            val = fields.get(k)
            if val is not None and str(val).strip():
                return val
        return None

    @classmethod
    def extract_expiry_date_from_fields(cls, fields: Dict[str, Any]) -> Optional[Any]:
        keys = ["expiry_date", "valid_upto", "valid_to", "maturity_date"]
        for k in keys:
            val = fields.get(k)
            if val is not None and str(val).strip():
                return val
        return None

    @classmethod
    def compare(
        cls,
        submitted_fields: Dict[str, Any],
        official_record: Dict[str, Any],
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Executes field-by-field comparison and returns:
        - matched_fields: List[str]
        - mismatched_fields: List[Dict[str, Any]] ([{field, submitted, official}])
        - all_comparisons: List[Dict[str, Any]]
        - is_expired: bool
        - official_status: str
        """
        today = today or datetime.now(timezone.utc).date()
        matched_fields: List[str] = []
        mismatched_fields: List[Dict[str, Any]] = []
        all_comparisons: List[Dict[str, Any]] = []
        is_expired = False

        # 1. Certificate Number Comparison
        sub_cert = cls.extract_cert_number_from_fields(submitted_fields)
        off_cert = cls.extract_cert_number_from_fields(official_record) or official_record.get("certificate_number")
        if sub_cert and off_cert:
            norm_sub_c = cls.normalize_cert_number(sub_cert)
            norm_off_c = cls.normalize_cert_number(off_cert)
            c_matched = norm_sub_c == norm_off_c
            all_comparisons.append({
                "field": "certificate_number",
                "submitted": sub_cert,
                "official": off_cert,
                "matched": c_matched,
            })
            if c_matched:
                matched_fields.append("certificate_number")
            else:
                mismatched_fields.append({
                    "field": "certificate_number",
                    "submitted": sub_cert,
                    "official": off_cert,
                })

        # 2. Institute Name (Fuzzy Match)
        sub_inst = cls.extract_institute_name_from_fields(submitted_fields)
        off_inst = cls.extract_institute_name_from_fields(official_record) or official_record.get("institute_name")
        if sub_inst and off_inst:
            i_matched, score = cls.fuzzy_institute_match(sub_inst, off_inst)
            all_comparisons.append({
                "field": "institute_name",
                "submitted": sub_inst,
                "official": off_inst,
                "matched": i_matched,
                "similarity_score": score,
            })
            if i_matched:
                matched_fields.append("institute_name")
            else:
                mismatched_fields.append({
                    "field": "institute_name",
                    "submitted": sub_inst,
                    "official": off_inst,
                })

        # 3. Issue Date Comparison
        sub_issue = cls.extract_issue_date_from_fields(submitted_fields)
        off_issue = cls.extract_issue_date_from_fields(official_record) or official_record.get("issue_date")
        if sub_issue and off_issue:
            d_sub_issue = cls.parse_date(sub_issue)
            d_off_issue = cls.parse_date(off_issue)
            if d_sub_issue and d_off_issue:
                iss_matched = d_sub_issue == d_off_issue
                all_comparisons.append({
                    "field": "issue_date",
                    "submitted": d_sub_issue.isoformat(),
                    "official": d_off_issue.isoformat(),
                    "matched": iss_matched,
                })
                if iss_matched:
                    matched_fields.append("issue_date")
                else:
                    mismatched_fields.append({
                        "field": "issue_date",
                        "submitted": d_sub_issue.isoformat(),
                        "official": d_off_issue.isoformat(),
                    })

        # 4. Expiry Date & Validity Check
        sub_exp = cls.extract_expiry_date_from_fields(submitted_fields)
        off_exp = cls.extract_expiry_date_from_fields(official_record) or official_record.get("expiry_date")
        
        parsed_off_exp = cls.parse_date(off_exp) if off_exp else None
        parsed_sub_exp = cls.parse_date(sub_exp) if sub_exp else None

        # Check if expired according to official date or submitted date
        if parsed_off_exp and parsed_off_exp < today:
            is_expired = True
        elif parsed_sub_exp and parsed_sub_exp < today:
            is_expired = True

        # Check explicit status on official record
        off_status = str(official_record.get("status") or "").upper()
        if off_status in ["EXPIRED", "REVOKED", "CANCELLED"]:
            is_expired = True

        if parsed_sub_exp and parsed_off_exp:
            exp_matched = parsed_sub_exp == parsed_off_exp
            all_comparisons.append({
                "field": "expiry_date",
                "submitted": parsed_sub_exp.isoformat(),
                "official": parsed_off_exp.isoformat(),
                "matched": exp_matched,
                "is_expired": is_expired,
            })
            if exp_matched:
                matched_fields.append("expiry_date")
            else:
                mismatched_fields.append({
                    "field": "expiry_date",
                    "submitted": parsed_sub_exp.isoformat(),
                    "official": parsed_off_exp.isoformat(),
                })

        return {
            "matched_fields": matched_fields,
            "mismatched_fields": mismatched_fields,
            "all_comparisons": all_comparisons,
            "is_expired": is_expired,
            "official_status": off_status,
        }

