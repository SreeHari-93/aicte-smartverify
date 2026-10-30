import os
import json
import hashlib
import time
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.services.explainer.root_cause import RootCause
from backend.app.services.explainer.translations import (
    TRANSLATIONS_HI,
    TRANSLATIONS_EN,
)

PROHIBITED_WORDS = ["forgery", "fraud", "misconduct"]


class GroundingValidator:
    """
    STRICT GROUNDING:
    Validates that LLM responses do not invent rule codes, dates, numbers, or handbook sections.
    Ensures that every cited finding code exists in the input, every date and number in the output
    appears in the input, and strictly bans words like 'forgery', 'fraud', 'misconduct'.
    """

    @classmethod
    def extract_ground_truth(cls, input_data: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
        allowed_rule_codes: Set[str] = set()
        allowed_dates: Set[str] = set()
        allowed_numbers: Set[str] = set()

        # Standard small numbers for steps / enumeration
        for i in range(1, 15):
            allowed_numbers.add(str(i))

        # Application ID and Institute name numbers
        app_id = str(input_data.get("application_id", "") or "")
        for token in re.findall(r"\d+", app_id):
            allowed_numbers.add(token)

        # Year tokens
        allowed_numbers.add("2026")
        allowed_numbers.add("2027")

        root_causes = input_data.get("root_causes", [])
        for rc in root_causes:
            rc_dict = rc if isinstance(rc, dict) else (rc.to_dict() if hasattr(rc, "to_dict") else {})

            # Rule codes
            for code in rc_dict.get("affected_rule_codes", []):
                allowed_rule_codes.add(str(code).strip())
                # also add numeric segments of rule codes
                for num in re.findall(r"\d+", str(code)):
                    allowed_numbers.add(num)

            for fid in rc_dict.get("finding_ids", []):
                allowed_rule_codes.add(str(fid).strip())
                allowed_numbers.add(str(fid).strip())

            # Text content inside headline and actions
            text_blobs = [rc_dict.get("headline", "")] + rc_dict.get("ordered_suggested_actions", [])
            for blob in text_blobs:
                for num in re.findall(r"\b\d+\b", str(blob)):
                    allowed_numbers.add(num)

            # Evidence (dates, numbers)
            evidence_list = rc_dict.get("evidence", [])
            for ev in evidence_list:
                for v in ev.values():
                    if v is None:
                        continue
                    v_str = str(v)
                    # Dates (YYYY-MM-DD or DD-MM-YYYY)
                    for d in re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}-\d{2}-\d{4}\b|\b\d{2}/\d{2}/\d{4}\b", v_str):
                        allowed_dates.add(d)
                    # Numbers
                    for num in re.findall(r"\b\d+\b", v_str):
                        allowed_numbers.add(num)

        # Count of issues is also allowed
        allowed_numbers.add(str(len(root_causes)))

        return allowed_rule_codes, allowed_dates, allowed_numbers

    @classmethod
    def validate(
        cls,
        response_json: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        allowed_rule_codes, allowed_dates, allowed_numbers = cls.extract_ground_truth(input_data)

        # Convert full response to text for keyword & number scan
        resp_str = json.dumps(response_json, ensure_ascii=False).lower()

        # 1. Prohibited words check
        for pw in PROHIBITED_WORDS:
            if re.search(rf"\b{pw}\b", resp_str):
                errors.append(f"Prohibited word '{pw}' found in response; anomalies must be worded as 'needs verification'.")

        # 2. Rule codes check in reasons
        reasons = response_json.get("reasons", [])
        if isinstance(reasons, list):
            for r in reasons:
                if isinstance(r, dict):
                    codes = r.get("finding_codes", [])
                    if isinstance(codes, list):
                        for c in codes:
                            c_str = str(c).strip()
                            if c_str and c_str not in allowed_rule_codes:
                                errors.append(f"Invented or unauthorized rule code cited: '{c_str}'")

        # 3. Dates validation in headline, plain_summary, and explanations
        text_corpus = ""
        text_corpus += " " + str(response_json.get("headline", ""))
        text_corpus += " " + str(response_json.get("plain_summary", ""))
        text_corpus += " " + str(response_json.get("what_officials_will_review", ""))
        if isinstance(reasons, list):
            for r in reasons:
                if isinstance(r, dict):
                    text_corpus += " " + str(r.get("explanation", ""))

        found_dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{2}-\d{2}-\d{4}\b|\b\d{2}/\d{2}/\d{4}\b", text_corpus)
        for fd in found_dates:
            if fd not in allowed_dates:
                errors.append(f"Invented date in explanation text: '{fd}'")

        # 4. Number validation: verify numbers in text exist in allowed numbers
        # Filter out numbers that are already part of validated dates
        text_without_dates = text_corpus
        for d in found_dates:
            text_without_dates = text_without_dates.replace(d, " ")

        found_numbers = re.findall(r"\b\d+\b", text_without_dates)
        for num in found_numbers:
            if num not in allowed_numbers:
                errors.append(f"Invented number in explanation text: '{num}'")

        is_valid = len(errors) == 0
        return is_valid, errors


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout_seconds
        self.consecutive_failures = 0
        self.is_open = False
        self.last_failure_time: Optional[float] = None

    def record_success(self):
        self.consecutive_failures = 0
        self.is_open = False

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        if self.consecutive_failures >= self.failure_threshold:
            self.is_open = True

    def can_attempt(self) -> bool:
        if not self.is_open:
            return True
        if self.last_failure_time and (time.time() - self.last_failure_time > self.reset_timeout):
            # Attempt trial request after timeout
            self.is_open = False
            self.consecutive_failures = 0
            return True
        return False


# In-process singleton circuit breaker
_CIRCUIT_BREAKER = CircuitBreaker()
# In-process cache
_EXPLANATION_CACHE: Dict[str, Dict[str, Any]] = {}


class ExplainerNarrator:
    """
    Generates plain-language explanation for validation failures.
    Operates in TEMPLATE mode (deterministic, zero external API) by default,
    or LLM mode (Anthropic API with strict grounding and circuit breaker) when configured.
    """

    @classmethod
    def compute_prompt_hash(
        cls,
        root_causes: List[Any],
        application_id: str,
        institute_name: str,
        lang: str,
    ) -> str:
        data = {
            "application_id": application_id,
            "institute_name": institute_name,
            "lang": lang,
            "causes": [rc.to_dict() if hasattr(rc, "to_dict") else rc for rc in root_causes],
        }
        raw_json = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

    @classmethod
    def generate_template_explanation(
        cls,
        root_causes: List[RootCause],
        application_id: str,
        institute_name: str,
        lang: str = "en",
    ) -> Dict[str, Any]:
        """
        Deterministic sentence generation matching statutory guidelines.
        """
        is_hi = (lang == "hi")
        t_data = TRANSLATIONS_HI if is_hi else TRANSLATIONS_EN
        disclaimer = t_data["disclaimer"]

        if not root_causes:
            headline = t_data["headline_ready"]
            plain_summary = (
                f"आवेदन {application_id} (संस्थान: {institute_name}) ने सभी प्रकाशित वैधानिक नियम सफलतापूर्वक पास कर लिए हैं।"
                if is_hi else
                f"Application {application_id} for {institute_name} has satisfied all published statutory criteria without blocking deficiencies."
            )
            return {
                "headline": headline,
                "plain_summary": plain_summary,
                "reasons": [],
                "how_to_fix": [],
                "what_officials_will_review": t_data.get("what_officials_will_review", ""),
                "disclaimer": disclaimer,
                "lang": lang,
            }

        # Check severities
        has_blocker = any(rc.severity == "BLOCKER" for rc in root_causes)
        headline = t_data["headline_blocked"] if has_blocker else t_data["headline_review"]

        # Plain Summary (strictly concise, < 120 words)
        count = len(root_causes)
        if is_hi:
            plain_summary = (
                f"आपके आवेदन {application_id} (संस्थान: {institute_name}) में स्वतः जांच के दौरान {count} मुख्य अनुपालन विसंगतियां पाई गई हैं। "
                f"अनुमोदन प्रक्रिया को आगे बढ़ाने के लिए कृपया नीचे दिए गए सुधारात्मक कदमों का पालन करें।"
            )
        else:
            primary_cause = root_causes[0].cause_code.replace("_", " ").title()
            plain_summary = (
                f"Automated scrutiny of application {application_id} for {institute_name} identified {count} core compliance issues. "
                f"The primary concern involves {primary_cause}. "
                f"Please follow the prioritized remediation steps below to ensure eligibility for AICTE approval."
            )

        # Reasons
        reasons: List[Dict[str, Any]] = []
        how_to_fix_steps: List[Dict[str, Any]] = []

        for rc in root_causes:
            rules_str = ", ".join(rc.affected_rule_codes) if rc.affected_rule_codes else "General Check"
            clean_name = rc.headline.split(":")[-1].split("(")[0].strip() if ":" in rc.headline else rc.headline

            # Look for date in evidence
            ev_date = None
            for ev in rc.evidence:
                if ev.get("extracted") and re.search(r"\d{4}-\d{2}-\d{2}", str(ev.get("extracted"))):
                    ev_date = str(ev.get("extracted"))
                    break

            if is_hi:
                cause_info = TRANSLATIONS_HI["causes"].get(rc.cause_code, {})
                template = cause_info.get("template", "नियम {rule_ref} के तहत {doc_name} में विसंगति पाई गई है।")
                explanation = template.format(
                    doc_name=clean_name,
                    rule_ref=f"Rule {rules_str}",
                )
                effort_hi = cause_info.get("effort", "मध्यम")
                fix_step = cause_info.get("fix", rc.ordered_suggested_actions[0] if rc.ordered_suggested_actions else "सुधार करें।")
                fix_step = fix_step.format(doc_name=clean_name)
                effort_val = effort_hi
            else:
                if rc.cause_code == "EXPIRED_DOCUMENT":
                    date_part = f"expired on {ev_date}" if ev_date else "has expired"
                    explanation = f"Your application cannot proceed because the {clean_name} {date_part} (Rule {rules_str}). Upload a renewed certificate valid for at least 30 days."
                    effort_val = "Medium"
                elif rc.cause_code == "MISSING_DOCUMENT":
                    explanation = f"Your application cannot proceed because the mandatory document '{clean_name}' was not submitted (Rule {rules_str}). Upload the valid statutory document."
                    effort_val = "Low"
                elif rc.cause_code == "EXPIRING_SOON":
                    explanation = f"Statutory document '{clean_name}' is expiring soon (Rule {rules_str}). Renew the document to avoid approval delays."
                    effort_val = "Low"
                elif rc.cause_code == "DATA_MISMATCH":
                    explanation = f"Data discrepancy identified in '{clean_name}' against institutional application records (Rule {rules_str})."
                    effort_val = "Low"
                elif rc.cause_code == "ANOMALY_FLAG":
                    explanation = f"Document '{clean_name}' flagged for anomaly and needs verification (Rule {rules_str})."
                    effort_val = "High"
                elif rc.cause_code == "VERIFICATION_FAILED":
                    explanation = f"Statutory document '{clean_name}' needs verification against issuing authority records (Rule {rules_str}). Official confirmation required."
                    effort_val = "Medium"
                elif rc.cause_code == "INFRASTRUCTURE_GAP":
                    explanation = f"Reported institutional infrastructure in '{clean_name}' falls below AICTE mandated norms (Rule {rules_str})."
                    effort_val = "High"
                elif rc.cause_code == "INCOMPLETE_FIELD":
                    explanation = f"Mandatory information missing in '{clean_name}' (Rule {rules_str}). Complete the required details."
                    effort_val = "Low"
                else:
                    explanation = f"Statutory deficiency detected for '{clean_name}' (Rule {rules_str}). Rectification required."
                    effort_val = "Medium"

                if rc.cause_code == "VERIFICATION_FAILED":
                    fix_step = "Official confirmation required"
                else:
                    fix_step = rc.ordered_suggested_actions[0] if rc.ordered_suggested_actions else f"Remediate {clean_name}."

            reasons.append({
                "cause_code": rc.cause_code,
                "explanation": explanation,
                "finding_codes": rc.affected_rule_codes,
            })

            # Fix steps
            how_to_fix_steps.append({
                "step": fix_step,
                "effort": effort_val,
            })

        return {
            "headline": headline,
            "plain_summary": plain_summary,
            "reasons": reasons,
            "how_to_fix": how_to_fix_steps,
            "what_officials_will_review": t_data.get("what_officials_will_review", ""),
            "disclaimer": disclaimer,
            "lang": lang,
        }

    @classmethod
    def _call_anthropic_llm(
        cls,
        root_causes: List[RootCause],
        application_id: str,
        institute_name: str,
        lang: str = "en",
    ) -> Optional[Dict[str, Any]]:
        """
        Invokes Anthropic API if ANTHROPIC_API_KEY and EXPLAINER_MODEL are configured.
        Strictly passes only structured root causes and application/institute metadata.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", "")
        model = os.getenv("EXPLAINER_MODEL") or getattr(settings, "EXPLAINER_MODEL", "claude-3-7-sonnet-20250219")

        if not api_key or not api_key.strip():
            return None

        if not _CIRCUIT_BREAKER.can_attempt():
            return None

        # Build clean structured prompt with ground truth
        causes_data = [rc.to_dict() for rc in root_causes]
        system_instruction = (
            "You are an AI decision support explainer for the AICTE SmartVerify AI regulatory system. "
            "Your task is to explain statutory application validation results to institutions in plain, objective language. "
            "STRICT GROUNDING RULES: "
            "1. You must NOT invent any rule codes, dates, numbers, or handbook sections. Use ONLY the codes and dates provided in the input. "
            "2. Never use the words 'forgery', 'fraud', or 'misconduct'. Word any document anomalies strictly as 'needs verification'. "
            "3. Return ONLY a valid JSON object matching this schema: "
            "{\n"
            '  "headline": "string",\n'
            '  "plain_summary": "string (maximum 120 words)",\n'
            '  "reasons": [{"cause_code": "string", "explanation": "string", "finding_codes": ["string"]}],\n'
            '  "how_to_fix": [{"step": "string", "effort": "Low" | "Medium" | "High"}],\n'
            '  "what_officials_will_review": "string",\n'
            '  "disclaimer": "AI-generated decision support; final decisions rest with authorised AICTE officials."\n'
            "}\n"
            f"Generate all explanations in language '{lang}' (en = English, hi = Hindi)."
        )

        user_content = json.dumps({
            "application_id": application_id,
            "institute_name": institute_name,
            "language": lang,
            "root_causes": causes_data,
        }, ensure_ascii=False)

        import httpx

        timeout_sec = float(getattr(settings, "EXPLAINER_TIMEOUT_SECONDS", 20))
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": 1500,
            "system": system_instruction,
            "messages": [
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.0,
        }

        try:
            with httpx.Client(timeout=timeout_sec) as client:
                res = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                if res.status_code != 200:
                    _CIRCUIT_BREAKER.record_failure()
                    return None

                res_json = res.json()
                content_blocks = res_json.get("content", [])
                text_out = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])

                # Parse JSON
                # Clean any markdown fences if present
                clean_json_str = text_out.strip()
                if clean_json_str.startswith("```json"):
                    clean_json_str = clean_json_str[7:]
                if clean_json_str.endswith("```"):
                    clean_json_str = clean_json_str[:-3]
                parsed = json.loads(clean_json_str.strip())
                _CIRCUIT_BREAKER.record_success()
                return parsed
        except Exception:
            _CIRCUIT_BREAKER.record_failure()
            return None

    @classmethod
    def explain(
        cls,
        root_causes: List[RootCause],
        application_id: str,
        institute_name: str,
        lang: str = "en",
        run_id: Optional[int] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates explanation generation:
        1. Checks in-memory cache and DB by prompt_hash
        2. Attempts LLM mode if configured, validates strict grounding (retrying once)
        3. Falls back to deterministic TEMPLATE mode
        4. Saves explanation to DB
        """
        lang = lang if lang in ("en", "hi") else "en"
        prompt_hash = cls.compute_prompt_hash(root_causes, application_id, institute_name, lang)

        # 1. Check in-process cache
        cache_key = f"{prompt_hash}:{lang}"
        if cache_key in _EXPLANATION_CACHE:
            cached = _EXPLANATION_CACHE[cache_key]
            return cached

        # Check DB if run_id provided
        if db and run_id:
            try:
                from backend.app.models.validation_run import ValidationExplanation
                db_exp = (
                    db.query(ValidationExplanation)
                    .filter(
                        ValidationExplanation.run_id == run_id,
                        ValidationExplanation.prompt_hash == prompt_hash,
                        ValidationExplanation.lang == lang,
                    )
                    .first()
                )
                if db_exp:
                    _EXPLANATION_CACHE[cache_key] = db_exp.explanation_json
                    return db_exp.explanation_json
            except Exception:
                pass

        # 2. Attempt LLM mode if configured
        explanation_json = None
        source = "TEMPLATE"
        model_used = None

        api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(settings, "ANTHROPIC_API_KEY", "")
        model_name = os.getenv("EXPLAINER_MODEL") or getattr(settings, "EXPLAINER_MODEL", "claude-3-7-sonnet-20250219")

        if api_key and api_key.strip():
            input_grounding_data = {
                "application_id": application_id,
                "institute_name": institute_name,
                "root_causes": root_causes,
            }

            # Attempt 1
            candidate = cls._call_anthropic_llm(root_causes, application_id, institute_name, lang)
            is_valid, errors = (False, ["No candidate"])
            if candidate and isinstance(candidate, dict):
                is_valid, errors = GroundingValidator.validate(candidate, input_grounding_data)

            # Retry once if validation failed
            if not is_valid and candidate:
                candidate = cls._call_anthropic_llm(root_causes, application_id, institute_name, lang)
                if candidate and isinstance(candidate, dict):
                    is_valid, errors = GroundingValidator.validate(candidate, input_grounding_data)

            if is_valid and candidate:
                explanation_json = candidate
                source = "LLM"
                model_used = model_name

        # 3. Fallback to TEMPLATE mode
        if not explanation_json:
            explanation_json = cls.generate_template_explanation(root_causes, application_id, institute_name, lang)
            source = "TEMPLATE"
            model_used = None

        # Add language and prompt_hash to explanation response
        explanation_json["source"] = source
        explanation_json["model"] = model_used
        explanation_json["prompt_hash"] = prompt_hash
        explanation_json["lang"] = lang

        # Always enforce the official disclaimer
        if lang == "hi":
            explanation_json["disclaimer"] = TRANSLATIONS_HI["disclaimer"]
        else:
            explanation_json["disclaimer"] = TRANSLATIONS_EN["disclaimer"]

        # Cache in memory
        _EXPLANATION_CACHE[cache_key] = explanation_json

        # 4. Save to DB if run_id and db are provided
        if db and run_id:
            try:
                from backend.app.models.validation_run import ValidationExplanation
                new_exp = ValidationExplanation(
                    run_id=run_id,
                    explanation_json=explanation_json,
                    source=source,
                    model=model_used,
                    prompt_hash=prompt_hash,
                    lang=lang,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(new_exp)
                db.commit()
            except Exception:
                db.rollback()

        return explanation_json

