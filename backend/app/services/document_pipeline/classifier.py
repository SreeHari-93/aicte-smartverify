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


class DocumentClassifier:
    """
    Intelligent document classifier scoring OCR text against active DocumentTypes.
    Weighs keyword hits, issuing authority matching, and gives 3x weight to title/header
    position (first 20 lines of text).
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

        # 1. Split lines and partition into Header Zone (first 20 lines) and Body Zone
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        header_lines = lines[:20]
        body_lines = lines[20:]

        header_text = " ".join(header_lines).lower()
        body_text = " ".join(body_lines).lower()
        full_text = f"{header_text} {body_text}"

        candidates: List[Candidate] = []

        for dt in document_types:
            if not getattr(dt, "is_active", True):
                continue

            raw_score = 0.0
            matched_kws: List[str] = []

            # A. Title / Issuing Authority Proximity (Header Zone weighs more)
            if dt.issuing_authority:
                auth_lower = dt.issuing_authority.lower()
                # Check for whole authority or key words
                if auth_lower in header_text:
                    raw_score += 4.0
                    matched_kws.append(f"authority:{dt.issuing_authority[:25]}")
                elif auth_lower in body_text:
                    raw_score += 2.0
                    matched_kws.append(f"authority:{dt.issuing_authority[:25]}")
                else:
                    # Match significant tokens in authority (e.g., "disaster", "fire", "nba")
                    auth_tokens = [w for w in re.findall(r"\b\w{4,}\b", auth_lower) if w not in {"state", "department", "board", "council", "office"}]
                    for tok in auth_tokens:
                        if tok in header_text:
                            raw_score += 1.5
                            matched_kws.append(tok)
                            break

            # B. Document Code or Name Match
            clean_code = dt.code.lower().replace("_", " ")
            if clean_code in header_text:
                raw_score += 3.0
                matched_kws.append(dt.code)
            elif clean_code in body_text:
                raw_score += 1.5
                matched_kws.append(dt.code)

            # C. Keyword Matching
            keywords = dt.keywords or []
            for kw in keywords:
                kw_clean = str(kw).strip().lower()
                if not kw_clean:
                    continue

                # Exact boundary search or substring match
                pattern = r"\b" + re.escape(kw_clean) + r"\b"
                if re.search(pattern, header_text):
                    raw_score += 3.0  # First 20 lines weigh 3x
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
            # Maximum anticipated score for strong match
            benchmark = (kw_count * 2.0) + 4.0
            norm_score = min(round(raw_score / benchmark, 2), 1.0)

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

            # If user uploaded as A but content strongly matches B
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

