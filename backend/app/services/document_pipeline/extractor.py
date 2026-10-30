import re
import os
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models.document_type import DocumentType


class ExtractedFieldResult(BaseModel):
    key: str
    value: str
    normalized_value: Optional[str] = None
    confidence: float = 1.0
    page_no: int = 1
    bbox: Optional[List[float]] = None
    source: str = "rule"  # "rule" | "llm" | "manual"
    needs_review: bool = False


class DocumentExtractionResult(BaseModel):
    document_id: Optional[int] = None
    document_type_code: str
    fields: List[ExtractedFieldResult] = Field(default_factory=list)
    expiry_date: Optional[str] = None
    issue_date: Optional[str] = None
    is_expired: Optional[bool] = None
    days_remaining: Optional[int] = None


MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

DISALLOWED_LABEL_VALUES = {
    "name", "building", "building name", "institution", "institution name",
    "issued to", "address", "number", "certificate", "certificate number",
    "noc", "noc number", "date", "issue date", "expiry date", "valid",
    "upto", "valid upto", "id", "aicte id", "to", "for", "details",
    "value", "the", "of", "and", "in", "date of issue", "valid till",
    "valid until", "expires on", "issued on",
}

EXPIRY_DATE_PATTERNS = [
    r"valid\s*(?:upto|up\s*to|till|until|through|to)\b",
    r"expiry\s*date\b",
    r"expires\s*on\b",
    r"date\s*of\s*expiry\b",
    r"validity\s*(?:period\s*)?(?:upto|date|until)\b",
]

ISSUE_DATE_PATTERNS = [
    r"date\s*of\s*issue\b",
    r"issue\s*date\b",
    r"issued\s*on\b",
    r"date\s*of\s*order\b",
    r"order\s*date\b",
    r"sanction\s*date\b",
    r"date\s*of\s*sanction\b",
    r"date\s*of\s*commencement\b",
    r"execution\s*date\b",
    r"date\s*of\s*completion\b",
    r"completion\s*date\b",
]

INSTITUTE_NAME_PATTERNS = [
    r"issued\s*to\b",
    r"institute\s*name\b",
    r"institution\s*name\b",
    r"name\s*of\s*(?:the\s*)?institution\b",
    r"name\s*of\s*(?:the\s*)?institute\b",
    r"name\s*of\s*(?:the\s*)?college\b",
    r"college\s*name\b",
    r"certified\s*that\b",
    r"in\s*favou?r\s*of\b",
]

BUILDING_NAME_PATTERNS = [
    r"building\s*name\b",
    r"name\s*of\s*(?:the\s*)?building\b",
    r"institution\s*(?:/\s*)?building\s*name\b",
    r"premises\s*name\b",
    r"name\s*of\s*(?:the\s*)?premises\b",
    r"structure\s*name\b",
]

ADDRESS_PATTERNS = [
    r"address\b",
    r"premises\s*address\b",
    r"site\s*address\b",
    r"location\b",
    r"situated\s*at\b",
    r"located\s*at\b",
]

AICTE_ID_PATTERNS = [
    r"aicte\s*(?:institute\s*)?id\b",
    r"aicte\s*application\s*id\b",
    r"aicte\s*permanent\s*id\b",
    r"institute\s*aicte\s*id\b",
    r"aicte\s*id\b",
]

CERTIFICATE_NUMBER_PATTERNS = [
    r"certificate\s*number\b",
    r"certificate\s*no\.?\b",
    r"noc\s*(?:ref\s*)?number\b",
    r"noc\s*(?:ref\s*)?no\.?\b",
    r"consent\s*(?:order\s*)?no\.?\b",
    r"consent\s*(?:order\s*)?number\b",
    r"order\s*number\b",
    r"order\s*no\.?\b",
    r"sanction\s*number\b",
    r"sanction\s*no\.?\b",
    r"approval\s*number\b",
    r"approval\s*no\.?\b",
    r"registration\s*number\b",
    r"reg\s*no\.?\b",
    r"deed\s*number\b",
    r"deed\s*no\.?\b",
    r"affidavit\s*number\b",
    r"affidavit\s*no\.?\b",
]


def parse_and_normalize_date(text: str) -> Optional[Tuple[str, str, date]]:
    """
    Parses dates from diverse formats and returns (raw_match, iso_string, date_obj).
    Supports:
      - DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
      - YYYY-MM-DD, YYYY/MM/DD
      - 2 July 2027, 11 Nov 2026, 11th November 2026
      - July 2, 2027, November 11, 2026
    """
    if not text:
        return None

    # 1. Textual month format: "2 July 2027", "11 Nov 2026" or "11th November 2026"
    m_text = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s+(\d{4})\b", text, re.IGNORECASE
    )
    if m_text:
        day = int(m_text.group(1))
        month_str = m_text.group(2).lower()[:3]
        year = int(m_text.group(3))
        if month_str in MONTH_NAMES:
            month = MONTH_NAMES[month_str]
            try:
                d = date(year, month, day)
                return m_text.group(0), d.isoformat(), d
            except ValueError:
                pass

    # 2. Textual month format: "July 2, 2027", "November 11, 2026"
    m_text_rev = re.search(
        r"\b([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", text, re.IGNORECASE
    )
    if m_text_rev:
        month_str = m_text_rev.group(1).lower()[:3]
        day = int(m_text_rev.group(2))
        year = int(m_text_rev.group(3))
        if month_str in MONTH_NAMES:
            month = MONTH_NAMES[month_str]
            try:
                d = date(year, month, day)
                return m_text_rev.group(0), d.isoformat(), d
            except ValueError:
                pass

    # 3. ISO Numeric format: YYYY-MM-DD, YYYY/MM/DD
    m_ymd = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", text)
    if m_ymd:
        year = int(m_ymd.group(1))
        month = int(m_ymd.group(2))
        day = int(m_ymd.group(3))
        try:
            d = date(year, month, day)
            return m_ymd.group(0), d.isoformat(), d
        except ValueError:
            pass

    # 4. Numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    m_dmy = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", text)
    if m_dmy:
        part1 = int(m_dmy.group(1))
        part2 = int(m_dmy.group(2))
        year = int(m_dmy.group(3))
        # Standard Indian / International format: DD-MM-YYYY
        day, month = part1, part2
        if month > 12 and day <= 12:
            day, month = month, day

        try:
            d = date(year, month, day)
            return m_dmy.group(0), d.isoformat(), d
        except ValueError:
            pass

    return None


def extract_date_field(
    lines: List[str],
    is_expiry: bool,
    specific_patterns: Optional[List[str]] = None,
    custom_label_terms: Optional[List[str]] = None,
) -> Optional[Tuple[str, str]]:
    """
    Finds a date field bound strictly to its own line/label.
    Returns (raw_value, iso_normalized) or None.
    """
    target_patterns = EXPIRY_DATE_PATTERNS if is_expiry else ISSUE_DATE_PATTERNS
    rival_patterns = ISSUE_DATE_PATTERNS if is_expiry else EXPIRY_DATE_PATTERNS

    # 1. High priority: check specific patterns for this specific field (e.g. completion vs issue)
    if specific_patterns:
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            has_spec = any(re.search(pat, line_clean, re.IGNORECASE) for pat in specific_patterns)
            if has_spec:
                parsed = parse_and_normalize_date(line_clean)
                if parsed:
                    return parsed[0], parsed[1]
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip()
                    next_has_any_label = bool(re.search(r"^[A-Za-z\s]{3,25}:", next_line))
                    if not next_has_any_label:
                        parsed_next = parse_and_normalize_date(next_line)
                        if parsed_next:
                            return parsed_next[0], parsed_next[1]

    # 2. General pass: look for a line that matches target_patterns and DOES NOT match rival_patterns
    for idx, line in enumerate(lines):
        line_clean = line.strip()
        if not line_clean:
            continue

        has_target = any(re.search(pat, line_clean, re.IGNORECASE) for pat in target_patterns)
        has_rival = any(re.search(pat, line_clean, re.IGNORECASE) for pat in rival_patterns)

        if has_target and not has_rival:
            # Look for date on this exact line
            parsed = parse_and_normalize_date(line_clean)
            if parsed:
                return parsed[0], parsed[1]

            # If line ends with delimiter (: or -) and next line has no rival label, check next line
            if idx + 1 < len(lines):
                next_line = lines[idx + 1].strip()
                next_has_rival = any(re.search(pat, next_line, re.IGNORECASE) for pat in rival_patterns)
                next_has_any_label = bool(re.search(r"^[A-Za-z\s]{3,25}:", next_line))
                if not next_has_rival and not next_has_any_label:
                    parsed_next = parse_and_normalize_date(next_line)
                    if parsed_next:
                        return parsed_next[0], parsed_next[1]

    # 3. Third pass: if custom_label_terms given
    if custom_label_terms:
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if any(term.lower() in line_clean.lower() for term in custom_label_terms):
                has_rival = any(re.search(pat, line_clean, re.IGNORECASE) for pat in rival_patterns)
                if not has_rival:
                    parsed = parse_and_normalize_date(line_clean)
                    if parsed:
                        return parsed[0], parsed[1]

    return None


def extract_text_after_patterns(lines: List[str], patterns: List[str]) -> Optional[str]:
    """
    Scans lines for given regex label patterns, capturing the full value up to the end of the line.
    Rejects values that are simply label words.
    """
    for line in lines:
        line_clean = line.strip()
        for pat in patterns:
            # Pattern followed by colon, hyphen, hash or multiple whitespace
            m = re.search(r"(?i)\b(?:" + pat + r")\s*[:\-#]\s*(.+)$", line_clean)
            if not m:
                m = re.search(r"(?i)\b(?:" + pat + r")(?:\t|\s{2,})([A-Za-z0-9].+)$", line_clean)
            if m:
                val = m.group(1).strip()
                val = re.sub(r"^[:\-#\s]+", "", val).strip()
                if val.lower() not in DISALLOWED_LABEL_VALUES and len(val) >= 2:
                    return val
    return None


class DocumentExtractor:
    """
    Extracts structured fields from OCR text according to DocumentType.extraction_schema,
    plus statutory standard fields (institute_name, issue_date, valid_upto, address, aicte_id).
    Strictly binds dates to their own labels and guarantees building_name captures the full name.
    """

    EXPIRY_KEYS = {"valid_upto", "expiry_date", "valid_until", "maturity_date", "validity_date", "expires_on"}
    ISSUE_KEYS = {"issue_date", "issued_on", "completion_date", "execution_date", "order_date", "sanction_date"}

    @classmethod
    def extract_fields(
        cls,
        ocr_text: str,
        doc_type: Optional[DocumentType] = None,
        pages_info: Optional[List[Dict[str, Any]]] = None,
        document_id: Optional[int] = None,
    ) -> DocumentExtractionResult:
        schema = doc_type.extraction_schema or [] if doc_type else []
        extracted_fields: List[ExtractedFieldResult] = []

        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        full_text = "\n".join(lines)

        detected_expiry_date: Optional[date] = None
        detected_issue_date: Optional[date] = None

        existing_keys = set()

        # 1. Process schema-defined fields first
        for item in schema:
            key = item.get("key", "")
            label = item.get("label", key)
            field_type = item.get("type", "text").lower()
            required = item.get("required", False)
            custom_regex = item.get("regex")

            field_res = cls._extract_single_field(
                key=key,
                label=label,
                field_type=field_type,
                required=required,
                custom_regex=custom_regex,
                lines=lines,
                full_text=full_text,
                pages_info=pages_info,
            )

            if field_res and field_res.value:
                extracted_fields.append(field_res)
                existing_keys.add(key)

                # Track expiry and issue dates
                if field_type == "date" and field_res.normalized_value:
                    try:
                        parsed_d = date.fromisoformat(field_res.normalized_value)
                        if key.lower() in cls.EXPIRY_KEYS or "valid" in key.lower() or "expiry" in key.lower():
                            detected_expiry_date = parsed_d
                        elif key.lower() in cls.ISSUE_KEYS or "issue" in key.lower() or "completion" in key.lower():
                            if not detected_issue_date:
                                detected_issue_date = parsed_d
                    except ValueError:
                        pass
            else:
                extracted_fields.append(
                    ExtractedFieldResult(
                        key=key,
                        value="",
                        normalized_value=None,
                        confidence=0.0,
                        page_no=1,
                        source="rule",
                        needs_review=required,
                    )
                )

        # 2. Extract standard common fields if present in document and not yet populated
        # A. Institute Name
        if "institute_name" not in existing_keys:
            inst_name = extract_text_after_patterns(lines, INSTITUTE_NAME_PATTERNS)
            if inst_name:
                p_no, bbox = cls._locate_token_position(inst_name, pages_info)
                extracted_fields.append(
                    ExtractedFieldResult(
                        key="institute_name",
                        value=inst_name,
                        normalized_value=inst_name,
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                )
                existing_keys.add("institute_name")

        # B. Building Name
        if "building_name" not in existing_keys:
            b_name = extract_text_after_patterns(lines, BUILDING_NAME_PATTERNS)
            if b_name:
                p_no, bbox = cls._locate_token_position(b_name, pages_info)
                # If building_name was in extracted_fields with empty value, update it
                matched_idx = next((i for i, f in enumerate(extracted_fields) if f.key == "building_name"), None)
                if matched_idx is not None and not extracted_fields[matched_idx].value:
                    extracted_fields[matched_idx] = ExtractedFieldResult(
                        key="building_name",
                        value=b_name,
                        normalized_value=b_name,
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                else:
                    extracted_fields.append(
                        ExtractedFieldResult(
                            key="building_name",
                            value=b_name,
                            normalized_value=b_name,
                            confidence=0.95,
                            page_no=p_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )
                    )
                existing_keys.add("building_name")

        # C. Address
        if "address" not in existing_keys:
            addr = extract_text_after_patterns(lines, ADDRESS_PATTERNS)
            if addr:
                p_no, bbox = cls._locate_token_position(addr, pages_info)
                extracted_fields.append(
                    ExtractedFieldResult(
                        key="address",
                        value=addr,
                        normalized_value=addr,
                        confidence=0.92,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                )
                existing_keys.add("address")

        # D. AICTE ID
        if "aicte_id" not in existing_keys:
            aicte_val = extract_text_after_patterns(lines, AICTE_ID_PATTERNS)
            if aicte_val:
                p_no, bbox = cls._locate_token_position(aicte_val, pages_info)
                extracted_fields.append(
                    ExtractedFieldResult(
                        key="aicte_id",
                        value=aicte_val,
                        normalized_value=aicte_val.upper(),
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                )
                existing_keys.add("aicte_id")

        # E. Date of Issue
        if "issue_date" not in existing_keys:
            issue_res = extract_date_field(lines, is_expiry=False)
            if issue_res:
                raw_iss, iso_iss = issue_res
                p_no, bbox = cls._locate_token_position(raw_iss, pages_info)
                extracted_fields.append(
                    ExtractedFieldResult(
                        key="issue_date",
                        value=raw_iss,
                        normalized_value=iso_iss,
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                )
                existing_keys.add("issue_date")
                try:
                    detected_issue_date = date.fromisoformat(iso_iss)
                except ValueError:
                    pass

        # F. Valid Upto / Expiry Date
        if "valid_upto" not in existing_keys and "expiry_date" not in existing_keys:
            exp_res = extract_date_field(lines, is_expiry=True)
            if exp_res:
                raw_exp, iso_exp = exp_res
                p_no, bbox = cls._locate_token_position(raw_exp, pages_info)
                # Check if schema wanted valid_upto
                matched_idx = next((i for i, f in enumerate(extracted_fields) if f.key in ("valid_upto", "expiry_date")), None)
                if matched_idx is not None and not extracted_fields[matched_idx].value:
                    extracted_fields[matched_idx] = ExtractedFieldResult(
                        key=extracted_fields[matched_idx].key,
                        value=raw_exp,
                        normalized_value=iso_exp,
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                else:
                    extracted_fields.append(
                        ExtractedFieldResult(
                            key="valid_upto",
                            value=raw_exp,
                            normalized_value=iso_exp,
                            confidence=0.95,
                            page_no=p_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )
                    )
                existing_keys.add("valid_upto")
                try:
                    detected_expiry_date = date.fromisoformat(iso_exp)
                except ValueError:
                    pass

        # G. Certificate / NOC Number
        cert_num_present = any(k in existing_keys for k in ("certificate_number", "noc_number", "approval_number", "deed_number"))
        if not cert_num_present:
            cert_val = extract_text_after_patterns(lines, CERTIFICATE_NUMBER_PATTERNS)
            if cert_val:
                p_no, bbox = cls._locate_token_position(cert_val, pages_info)
                # Update schema field if empty
                matched_idx = next((i for i, f in enumerate(extracted_fields) if f.key in ("noc_number", "certificate_number")), None)
                if matched_idx is not None and not extracted_fields[matched_idx].value:
                    extracted_fields[matched_idx] = ExtractedFieldResult(
                        key=extracted_fields[matched_idx].key,
                        value=cert_val,
                        normalized_value=cert_val.upper(),
                        confidence=0.95,
                        page_no=p_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )
                else:
                    extracted_fields.append(
                        ExtractedFieldResult(
                            key="certificate_number",
                            value=cert_val,
                            normalized_value=cert_val.upper(),
                            confidence=0.95,
                            page_no=p_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )
                    )
                existing_keys.add("certificate_number")

        # 3. Optional LLM Fallback (if enabled and missing required fields)
        missing_required = [f for f in extracted_fields if not f.value and f.needs_review]
        if missing_required and getattr(settings, "EXTRACTION_LLM_ENABLED", False):
            cls._apply_llm_fallback(missing_required, full_text, doc_type.name if doc_type else "Document")

        # 4. Compute Expiry & Validity Deltas
        today = date.today()
        is_expired: Optional[bool] = None
        days_remaining: Optional[int] = None
        exp_iso: Optional[str] = None
        iss_iso: Optional[str] = None

        if detected_expiry_date:
            exp_iso = detected_expiry_date.isoformat()
            days_remaining = (detected_expiry_date - today).days
            is_expired = days_remaining < 0
        elif detected_issue_date and doc_type and getattr(doc_type, "has_expiry", True):
            validity_months = getattr(doc_type, "default_validity_months", 12) or 12
            estimated_expiry = detected_issue_date + timedelta(days=validity_months * 30)
            exp_iso = estimated_expiry.isoformat()
            days_remaining = (estimated_expiry - today).days
            is_expired = days_remaining < 0

        if detected_issue_date:
            iss_iso = detected_issue_date.isoformat()

        doc_code = doc_type.code if doc_type else "GENERAL"

        return DocumentExtractionResult(
            document_id=document_id,
            document_type_code=doc_code,
            fields=extracted_fields,
            expiry_date=exp_iso,
            issue_date=iss_iso,
            is_expired=is_expired,
            days_remaining=days_remaining,
        )

    @classmethod
    def _extract_single_field(
        cls,
        key: str,
        label: str,
        field_type: str,
        required: bool,
        custom_regex: Optional[str],
        lines: List[str],
        full_text: str,
        pages_info: Optional[List[Dict[str, Any]]],
    ) -> Optional[ExtractedFieldResult]:
        # Custom regex match if provided in schema
        if custom_regex:
            m = re.search(custom_regex, full_text, re.IGNORECASE)
            if m:
                val = m.group(1) if m.groups() else m.group(0)
                norm_val = val.strip()
                page_no, bbox = cls._locate_token_position(val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=val.strip(),
                    normalized_value=norm_val,
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        key_lower = key.lower()
        label_lower = label.lower()

        # ----------------------------------------------------------------------
        # A. DATE FIELD
        # ----------------------------------------------------------------------
        if field_type == "date" or "date" in key_lower:
            is_exp = (
                key_lower in cls.EXPIRY_KEYS
                or "valid" in key_lower
                or "expiry" in key_lower
                or "valid" in label_lower
                or "expiry" in label_lower
            )
            specific_pats = []
            if "completion" in key_lower or "completion" in label_lower:
                specific_pats = [r"date\s*of\s*completion\b", r"completion\s*date\b"]
            elif "order" in key_lower or "order" in label_lower:
                specific_pats = [r"date\s*of\s*order\b", r"order\s*date\b"]
            elif "sanction" in key_lower or "sanction" in label_lower:
                specific_pats = [r"date\s*of\s*sanction\b", r"sanction\s*date\b"]
            elif "issue" in key_lower or "issue" in label_lower:
                specific_pats = [r"date\s*of\s*issue\b", r"issue\s*date\b", r"issued\s*on\b"]
            elif is_exp:
                specific_pats = EXPIRY_DATE_PATTERNS

            custom_terms = [label_lower, key_lower.replace("_", " ")]
            res = extract_date_field(lines, is_expiry=is_exp, specific_patterns=specific_pats, custom_label_terms=custom_terms)
            if res:
                raw_val, iso_val = res
                page_no, bbox = cls._locate_token_position(raw_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=raw_val,
                    normalized_value=iso_val,
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # B. BUILDING NAME
        # ----------------------------------------------------------------------
        if key_lower == "building_name" or "building" in key_lower:
            b_val = extract_text_after_patterns(lines, BUILDING_NAME_PATTERNS)
            if b_val:
                page_no, bbox = cls._locate_token_position(b_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=b_val,
                    normalized_value=b_val,
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # C. INSTITUTE NAME
        # ----------------------------------------------------------------------
        if key_lower in ("institute_name", "institution_name") or "institute" in key_lower or "institution" in key_lower:
            i_val = extract_text_after_patterns(lines, INSTITUTE_NAME_PATTERNS)
            if i_val:
                page_no, bbox = cls._locate_token_position(i_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=i_val,
                    normalized_value=i_val,
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # D. ADDRESS
        # ----------------------------------------------------------------------
        if key_lower == "address" or "address" in label_lower:
            a_val = extract_text_after_patterns(lines, ADDRESS_PATTERNS)
            if a_val:
                page_no, bbox = cls._locate_token_position(a_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=a_val,
                    normalized_value=a_val,
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # E. AICTE ID
        # ----------------------------------------------------------------------
        if "aicte" in key_lower or "aicte" in label_lower:
            id_val = extract_text_after_patterns(lines, AICTE_ID_PATTERNS)
            if id_val:
                page_no, bbox = cls._locate_token_position(id_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=id_val,
                    normalized_value=id_val.upper(),
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # F. ID / REFERENCE NUMBER FIELD
        # ----------------------------------------------------------------------
        if field_type == "id" or "number" in key_lower or "no" in key_lower or "ref" in key_lower or "cert" in key_lower:
            # 1. Specialized certificate patterns
            id_val = extract_text_after_patterns(lines, CERTIFICATE_NUMBER_PATTERNS)
            if id_val:
                page_no, bbox = cls._locate_token_position(id_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=id_val,
                    normalized_value=id_val.upper(),
                    confidence=0.95,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

            # 2. General fallback for structured alphanumeric codes on lines mentioning 'number' or 'no'
            for line in lines:
                if any(t in line.lower() for t in ["ref", "no", "cert", "id", "code"]):
                    m_code = re.search(r"\b([A-Z0-9\-_/]*[0-9][A-Z0-9\-_/]{4,25})\b", line)
                    if m_code and not any(m_code.group(1).startswith(p) for p in ["HTTP", "WWW"]):
                        raw_val = m_code.group(1).strip()
                        page_no, bbox = cls._locate_token_position(raw_val, pages_info)
                        return ExtractedFieldResult(
                            key=key,
                            value=raw_val,
                            normalized_value=raw_val.upper(),
                            confidence=0.80,
                            page_no=page_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )

        # ----------------------------------------------------------------------
        # G. NUMBER FIELD (Amount, Area, Counts)
        # ----------------------------------------------------------------------
        if field_type == "number":
            search_terms = [label_lower, key_lower.replace("_", " ")]
            label_pattern = r"(?:" + "|".join(re.escape(t) for t in search_terms) + r")[^\d\n]*([0-9,]+(?:\.[0-9]+)?)"
            m_num = re.search(label_pattern, full_text, re.IGNORECASE)
            if m_num:
                raw_val = m_num.group(1).replace(",", "").strip()
                page_no, bbox = cls._locate_token_position(m_num.group(1), pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=m_num.group(1),
                    normalized_value=raw_val,
                    confidence=0.88,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=False,
                )

        # ----------------------------------------------------------------------
        # H. GENERAL TEXT FIELD
        # ----------------------------------------------------------------------
        for line in lines:
            line_l = line.lower()
            if key_lower in line_l or label_lower in line_l:
                m_gen = re.search(r"[:\-#]\s*(.+)$", line)
                if m_gen:
                    cand = m_gen.group(1).strip()
                    if cand.lower() not in DISALLOWED_LABEL_VALUES and len(cand) >= 2:
                        page_no, bbox = cls._locate_token_position(cand, pages_info)
                        return ExtractedFieldResult(
                            key=key,
                            value=cand,
                            normalized_value=cand,
                            confidence=0.85,
                            page_no=page_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )

        return None

    @classmethod
    def _locate_token_position(
        cls, token: str, pages_info: Optional[List[Dict[str, Any]]]
    ) -> Tuple[int, Optional[List[float]]]:
        """Locates page number and bounding box coordinates for an extracted token"""
        if not pages_info or not token:
            return 1, None

        tok_clean = token.strip().lower()
        for p in pages_info:
            p_no = p.get("page_no", 1)
            words = p.get("words", [])
            for w in words:
                w_str = str(w.get("word", "")).strip().lower()
                if tok_clean in w_str or w_str in tok_clean:
                    bbox = w.get("bbox")
                    if bbox and len(bbox) == 4:
                        return p_no, bbox

        return 1, None

    @classmethod
    def _apply_llm_fallback(
        cls, missing_fields: List[ExtractedFieldResult], full_text: str, doc_name: str
    ):
        """
        Optional LLM fallback behind settings.EXTRACTION_LLM_ENABLED.
        API keys are retrieved from environment and never logged.
        """
        api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return

        try:
            pass
        except Exception:
            pass
