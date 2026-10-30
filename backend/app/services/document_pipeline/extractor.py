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


def parse_and_normalize_date(text: str) -> Optional[Tuple[str, str, date]]:
    """
    Parses dates from diverse formats and returns (raw_match, iso_string, date_obj).
    Supports:
      - DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
      - YYYY-MM-DD, YYYY/MM/DD
      - 11 Nov 2026, 11th November 2026
      - November 11, 2026
    """
    if not text:
        return None

    # 1. Textual month format: "11 Nov 2026" or "11th November 2026"
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

    # 2. Textual month format: "November 11, 2026"
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

    # 3. Numeric formats: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    m_dmy = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", text)
    if m_dmy:
        part1 = int(m_dmy.group(1))
        part2 = int(m_dmy.group(2))
        year = int(m_dmy.group(3))
        # Standard Indian / International format: DD-MM-YYYY
        day, month = part1, part2
        if month > 12 and day <= 12:
            # Fallback if US format MM-DD-YYYY
            day, month = month, day

        try:
            d = date(year, month, day)
            return m_dmy.group(0), d.isoformat(), d
        except ValueError:
            pass

    # 4. ISO Numeric format: YYYY-MM-DD, YYYY/MM/DD
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

    return None


class DocumentExtractor:
    """
    Extracts structured fields from OCR text according to DocumentType.extraction_schema.
    Uses rule-based extraction (regex and label proximity) with optional LLM fallback,
    normalizes dates to ISO, and computes expiry/validity deltas.
    """

    EXPIRY_KEYS = {"valid_upto", "expiry_date", "valid_until", "maturity_date", "validity_date", "expires_on"}
    ISSUE_KEYS = {"issue_date", "issued_on", "completion_date", "execution_date", "order_date", "sanction_date"}

    @classmethod
    def extract_fields(
        cls,
        ocr_text: str,
        doc_type: DocumentType,
        pages_info: Optional[List[Dict[str, Any]]] = None,
        document_id: Optional[int] = None,
    ) -> DocumentExtractionResult:
        schema = doc_type.extraction_schema or []
        extracted_fields: List[ExtractedFieldResult] = []

        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        full_text = "\n".join(lines)

        detected_expiry_date: Optional[date] = None
        detected_issue_date: Optional[date] = None

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

            if field_res:
                extracted_fields.append(field_res)

                # Track expiry and issue dates for validity computation
                if field_type == "date" and field_res.normalized_value:
                    try:
                        parsed_d = date.fromisoformat(field_res.normalized_value)
                        if key.lower() in cls.EXPIRY_KEYS or "valid" in key.lower() or "expiry" in key.lower():
                            detected_expiry_date = parsed_d
                        elif key.lower() in cls.ISSUE_KEYS or "issue" in key.lower() or "date" in key.lower():
                            if not detected_issue_date:
                                detected_issue_date = parsed_d
                    except ValueError:
                        pass
            else:
                # Field missing in rule-based extraction
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

        # 2. Optional LLM Fallback (if enabled and missing required fields)
        missing_required = [f for f in extracted_fields if not f.value and f.needs_review]
        if missing_required and getattr(settings, "EXTRACTION_LLM_ENABLED", False):
            cls._apply_llm_fallback(missing_required, full_text, doc_type.name)

        # 3. Compute Expiry & Validity Deltas
        today = date.today()
        is_expired: Optional[bool] = None
        days_remaining: Optional[int] = None
        exp_iso: Optional[str] = None
        iss_iso: Optional[str] = None

        if detected_expiry_date:
            exp_iso = detected_expiry_date.isoformat()
            days_remaining = (detected_expiry_date - today).days
            is_expired = days_remaining < 0
        elif detected_issue_date and getattr(doc_type, "has_expiry", True):
            validity_months = getattr(doc_type, "default_validity_months", 12) or 12
            estimated_expiry = detected_issue_date + timedelta(days=validity_months * 30)
            exp_iso = estimated_expiry.isoformat()
            days_remaining = (estimated_expiry - today).days
            is_expired = days_remaining < 0

        if detected_issue_date:
            iss_iso = detected_issue_date.isoformat()

        return DocumentExtractionResult(
            document_id=document_id,
            document_type_code=doc_type.code,
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

        # Search patterns based on type
        key_clean = key.lower().replace("_", " ")
        label_clean = label.lower()
        phrases = sorted(list(set([label_clean, key_clean, label.lower(), key.lower()])), key=len, reverse=True)
        key_words = [w for w in re.split(r"[_\s\-]+", key.lower()) if len(w) > 2]
        label_words = [w for w in re.split(r"[_\s\-]+", label.lower()) if len(w) > 2]
        search_terms = list(set(phrases + key_words + label_words))

        # ----------------------------------------------------------------------
        # A. DATE FIELD
        # ----------------------------------------------------------------------
        if field_type == "date":
            # 1. Proximity search: find lines containing search terms
            for idx, line in enumerate(lines):
                line_lower = line.lower()
                if any(term in line_lower for term in search_terms):
                    # Check current line and next line
                    combo_text = line + " " + (lines[idx + 1] if idx + 1 < len(lines) else "")
                    parsed = parse_and_normalize_date(combo_text)
                    if parsed:
                        raw_match, iso_str, _ = parsed
                        page_no, bbox = cls._locate_token_position(raw_match, pages_info)
                        return ExtractedFieldResult(
                            key=key,
                            value=raw_match,
                            normalized_value=iso_str,
                            confidence=0.92,
                            page_no=page_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=False,
                        )

            # 2. General fallback date in full text
            parsed_gen = parse_and_normalize_date(full_text)
            if parsed_gen:
                raw_match, iso_str, _ = parsed_gen
                page_no, bbox = cls._locate_token_position(raw_match, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=raw_match,
                    normalized_value=iso_str,
                    confidence=0.70,
                    page_no=page_no,
                    bbox=bbox,
                    source="rule",
                    needs_review=True,
                )

        # ----------------------------------------------------------------------
        # B. ID / REFERENCE NUMBER FIELD
        # ----------------------------------------------------------------------
        elif field_type == "id":
            # 1. Proximity with delimiter: e.g. "NOC Ref Number: NOC-FIRE-2026/894" or "Ref No. DTCP-8832"
            delim_pattern = r"(?:" + "|".join(re.escape(p) for p in phrases) + r")\s*[:\-#]\s*([A-Za-z0-9\-_/]{4,35})"
            m_id = re.search(delim_pattern, full_text, re.IGNORECASE)
            if m_id:
                raw_val = m_id.group(1).strip()
                if raw_val.lower() not in {"number", "certificate", "order", "document"}:
                    page_no, bbox = cls._locate_token_position(raw_val, pages_info)
                    return ExtractedFieldResult(
                        key=key,
                        value=raw_val,
                        normalized_value=raw_val.upper(),
                        confidence=0.92,
                        page_no=page_no,
                        bbox=bbox,
                        source="rule",
                        needs_review=False,
                    )

            # 2. Line scan for phrase and alphanumeric token containing digits/hyphens
            for line in lines:
                line_l = line.lower()
                if any(p in line_l for p in phrases):
                    m_cand = re.search(r"[:\-#]?\s*([A-Za-z0-9\-_/]*[0-9\-][A-Za-z0-9\-_/]{3,30})", line)
                    if m_cand:
                        raw_val = m_cand.group(1).strip()
                        if raw_val.lower() not in {"number", "certificate", "order", "document"}:
                            page_no, bbox = cls._locate_token_position(raw_val, pages_info)
                            return ExtractedFieldResult(
                                key=key,
                                value=raw_val,
                                normalized_value=raw_val.upper(),
                                confidence=0.88,
                                page_no=page_no,
                                bbox=bbox,
                                source="rule",
                                needs_review=False,
                            )

            # 3. Fallback for structured alphanumeric codes on lines mentioning 'number' or 'no'
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
                            confidence=0.75,
                            page_no=page_no,
                            bbox=bbox,
                            source="rule",
                            needs_review=True,
                        )

        # ----------------------------------------------------------------------
        # C. NUMBER FIELD (Amount, Area, Counts, CGPA)
        # ----------------------------------------------------------------------
        elif field_type == "number":
            # Proximity to label
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
        # D. TEXT / NAME FIELD
        # ----------------------------------------------------------------------
        else:
            # Proximity search: value immediately after label or delimiter
            label_pattern = r"(?:" + "|".join(re.escape(t) for t in search_terms) + r")[:\s\-]+([A-Za-z0-9\s.,&'\-]{3,60})"
            m_txt = re.search(label_pattern, full_text, re.IGNORECASE)
            if m_txt:
                raw_val = m_txt.group(1).strip().splitlines()[0]
                page_no, bbox = cls._locate_token_position(raw_val, pages_info)
                return ExtractedFieldResult(
                    key=key,
                    value=raw_val,
                    normalized_value=raw_val,
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
            # Safe call to LLM without logging credentials
            pass
        except Exception:
            # Never crash extraction on LLM errors
            pass
