import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models.document_type import DocumentType


class Candidate(BaseModel):
    code: str
    name: str
    score: float
    matched_keywords: List[str] = Field(default_factory=list)


class ClassificationResult(BaseModel):
    predicted_type: str
    score: float
    candidates: List[Candidate] = Field(default_factory=list)
    mismatch_flag: bool = False
    warning_message: Optional[str] = None
    needs_manual_review: bool = False


TITLE_PATTERNS_BY_DOC_TYPE: Dict[str, List[str]] = {
    "FIRE_NOC": [
        r"fire\s*(?:&|and)?\s*life\s*safety\s*(?:no\s*objection\s*certificate|noc)",
        r"fire\s*safety\s*(?:certificate|noc|clearance|no\s*objection)",
        r"no\s*objection\s*certificate\s*.*fire",
        r"fire\s*(?:and|&)\s*rescue\s*services",
        r"fire\s*clearance",
        r"fire\s*noc",
    ],
    "BUILDING_PLAN": [
        r"approved\s*building\s*plan",
        r"building\s*plan\s*(?:approval|sanction)",
        r"sanctioned\s*building\s*plan",
        r"building\s*permit\s*order",
    ],
    "OCCUPANCY_CERT": [
        r"(?:building\s*)?occupancy\s*certificate",
        r"(?:building\s*)?completion\s*certificate",
        r"occupancy\s*(?:/|and)?\s*completion\s*certificate",
        r"certificate\s*of\s*occupancy",
        r"structural\s*fitness\s*for\s*occupancy",
    ],
    "LAND_DOC": [
        r"land\s*title\s*deed",
        r"registered\s*(?:sale|lease)\s*deed",
        r"title\s*deed",
        r"lease\s*deed",
        r"land\s*ownership\s*certificate",
    ],
    "AFFIDAVIT": [
        r"notarized\s*affidavit",
        r"statutory\s*affidavit",
        r"affidavit\s*under\s*oath",
        r"affidavit\s*for\s*aicte",
        r"non[- ]judicial\s*stamp\s*paper",
        r"\baffidavit\b",
    ],
    "NBA_ACCREDITATION": [
        r"nba\s*accreditation\s*certificate",
        r"national\s*board\s*of\s*accreditation",
        r"accreditation\s*status\s*.*nba",
        r"nba\s*accredited",
        r"nba\s*certificate",
    ],
    "BARRIER_FREE": [
        r"barrier\s*free\s*(?:built\s*environment)?\s*certificate",
        r"accessibility\s*certificate",
        r"physically\s*handicapped\s*accessibility",
    ],
    "AUDITED_ACCOUNTS": [
        r"audited\s*(?:financial\s*)?statements?",
        r"audited\s*balance\s*sheet",
        r"chartered\s*accountants?\s*report",
        r"independent\s*auditor'?s?\s*report",
    ],
    "EQUIP_SOFTWARE": [
        r"equipment[,\s]+software\s*(?:&|and)\s*library",
        r"laboratory\s*equipment\s*list",
        r"equipment\s*declaration",
    ],
    "BANK_GUARANTEE": [
        r"bank\s*guarantee",
        r"fixed\s*deposit\s*receipt",
        r"fdr\s*(?:guarantee|receipt)",
    ],
    "CYBER_AUDIT": [
        r"cyber\s*security\s*audit",
        r"it\s*infrastructure\s*audit",
        r"vulnerability\s*assessment",
    ],
    "NAAC_CERT": [
        r"naac\s*accreditation\s*certificate",
        r"national\s*assessment\s*and\s*accreditation\s*council",
        r"naac\s*certificate",
        r"institutional\s*accreditation\s*.*naac",
    ],
    "POLLUTION_NOC": [
        r"consent\s*to\s*operate",
        r"consent\s*to\s*establish",
        r"pollution\s*control\s*board\s*(?:consent|noc|certificate)",
        r"state\s*pollution\s*control\s*board",
        r"air\s*.*water\s*pollution\s*consent",
        r"pollution\s*noc",
        r"consent\s*order",
    ],
    "STRUCTURAL_STABILITY": [
        r"structural\s*stability\s*certificate",
        r"structural\s*fitness\s*certificate",
        r"stability\s*certificate",
        r"structural\s*soundness\s*certificate",
    ],
}


class DocumentClassifier:
    """
    Intelligent document classifier scoring OCR text against active DocumentTypes.
    Gives strong weight (>=80%) to explicit document titles and header declarations,
    along with issuing authority and keyword proximity.
    """

    @classmethod
    def classify(
        cls,
        ocr_text: str,
        document_types: List[DocumentType],
        uploaded_code: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> ClassificationResult:
        if threshold is None:
            threshold = getattr(settings, "CLASSIFICATION_CONFIDENCE_THRESHOLD", 0.4)

        if not ocr_text or not document_types:
            default_code = uploaded_code or (document_types[0].code if document_types else "UNKNOWN")
            return ClassificationResult(
                predicted_type=default_code,
                score=0.0,
                candidates=[],
                mismatch_flag=False,
                warning_message=None,
                needs_manual_review=True,
            )

        # 1. Split lines and partition into Header Zone (first 15 lines) and Body Zone
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        header_lines = lines[:15]
        body_lines = lines[15:]

        header_text = " ".join(header_lines).lower()
        body_text = " ".join(body_lines).lower()
        full_text = f"{header_text} {body_text}"

        candidates: List[Candidate] = []

        for dt in document_types:
            if not getattr(dt, "is_active", True):
                continue

            raw_score = 0.0
            matched_kws: List[str] = []
            has_title_match = False

            # A. Explicit Document Title Match in Header Zone (Strong Weight)
            title_pats = TITLE_PATTERNS_BY_DOC_TYPE.get(dt.code, [])
            for tp in title_pats:
                if re.search(tp, header_text, re.IGNORECASE):
                    has_title_match = True
                    raw_score += 14.0
                    matched_kws.append(f"title:{dt.code}")
                    break

            if not has_title_match and dt.name:
                name_clean = dt.name.lower()
                clean_name_pat = r"\b" + re.escape(name_clean.replace("/", " ")).replace(r"\ ", r"\s+") + r"\b"
                if re.search(clean_name_pat, header_text) or name_clean in header_text:
                    has_title_match = True
                    raw_score += 12.0
                    matched_kws.append(f"title:{dt.name[:25]}")

            # B. Document Code or Clean Code Match
            clean_code = dt.code.lower().replace("_", " ")
            if clean_code in header_text:
                raw_score += 4.0
                matched_kws.append(dt.code)
            elif clean_code in body_text:
                raw_score += 2.0
                matched_kws.append(dt.code)

            # C. Issuing Authority Match
            if dt.issuing_authority:
                auth_lower = dt.issuing_authority.lower()
                if auth_lower in header_text:
                    raw_score += 5.0
                    matched_kws.append(f"authority:{dt.issuing_authority[:25]}")
                elif auth_lower in body_text:
                    raw_score += 2.5
                    matched_kws.append(f"authority:{dt.issuing_authority[:25]}")
                else:
                    auth_tokens = [w for w in re.findall(r"\b\w{4,}\b", auth_lower) if w not in {"state", "department", "board", "council", "office"}]
                    for tok in auth_tokens:
                        if tok in header_text:
                            raw_score += 2.0
                            matched_kws.append(tok)
                            break

            # D. Keyword Matching
            keywords = dt.keywords or []
            for kw in keywords:
                kw_clean = str(kw).strip().lower()
                if not kw_clean:
                    continue

                pattern = r"\b" + re.escape(kw_clean) + r"\b"
                if re.search(pattern, header_text):
                    raw_score += 3.0
                    if kw_clean not in matched_kws:
                        matched_kws.append(kw_clean)
                elif re.search(pattern, body_text):
                    raw_score += 1.0
                    if kw_clean not in matched_kws:
                        matched_kws.append(kw_clean)
                elif kw_clean in header_text:
                    raw_score += 2.0
                    if kw_clean not in matched_kws:
                        matched_kws.append(kw_clean)
                elif kw_clean in body_text:
                    raw_score += 0.8
                    if kw_clean not in matched_kws:
                        matched_kws.append(kw_clean)

            # Calibrate score between 0.0 and 1.0
            kw_count = max(len(keywords), 3)
            benchmark = (kw_count * 1.5) + 6.0
            norm_score = min(round(raw_score / benchmark, 2), 1.0)

            # Strong title weight: guaranteed >= 0.85 when clear title matches in header
            if has_title_match:
                norm_score = max(norm_score, 0.88)

            candidates.append(
                Candidate(
                    code=dt.code,
                    name=dt.name,
                    score=norm_score,
                    matched_keywords=matched_kws,
                )
            )

        # 2. Sort candidates by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        top3 = candidates[:3]

        if not top3 or top3[0].score == 0.0:
            pred_code = uploaded_code or (top3[0].code if top3 else "UNKNOWN")
            return ClassificationResult(
                predicted_type=pred_code,
                score=0.0,
                candidates=top3,
                mismatch_flag=False,
                warning_message=None,
                needs_manual_review=True,
            )

        best = top3[0]
        mismatch_flag = False
        warning_msg = None

        # 3. Check for User Mismatch Flag
        if uploaded_code:
            up_clean = uploaded_code.strip().upper()
            best_clean = best.code.strip().upper()

            if up_clean != best_clean and best.score >= threshold:
                mismatch_flag = True
                warning_msg = f"Uploaded as {up_clean} but content looks like {best_clean} ({best.name})"

        needs_review = best.score < threshold

        return ClassificationResult(
            predicted_type=best.code,
            score=best.score,
            candidates=top3,
            mismatch_flag=mismatch_flag,
            warning_message=warning_msg,
            needs_manual_review=needs_review,
        )
