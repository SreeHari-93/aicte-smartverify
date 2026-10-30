from datetime import date, timedelta
from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator


@EvaluatorRegistry.register("VALIDITY_PERIOD")
class ValidityPeriodEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        doc_type = definition.get("document", "").upper()
        must_be_valid_on_path = definition.get("must_be_valid_on", "today")

        docs = context.get_documents_by_type(doc_type)
        if not docs:
            return EvaluationResult(
                status="FAIL",
                reason=f"Document of type '{doc_type}' is missing.",
                suggested_action=f"Upload document '{doc_type}'.",
            )

        target_date_val, err = SafePathResolver.resolve(must_be_valid_on_path, context)
        if err or not target_date_val:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not resolve reference target date '{must_be_valid_on_path}'. ({err or 'Missing date'})",
            )

        ref_date = SafeComparator._parse_date(target_date_val)
        if not ref_date:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not parse reference target date '{target_date_val}'.",
            )

        latest = docs[-1]
        issue_str = latest.get("issue_date")
        expiry_str = latest.get("expiry_date")

        if not expiry_str:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Document '{doc_type}' does not provide an expiry date for validity period check.",
                evidence=[{"document_id": latest.get("id"), "document_type": doc_type}],
            )

        expiry_date = SafeComparator._parse_date(expiry_str)
        if not expiry_date:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not parse document expiry date '{expiry_str}'.",
            )

        buffer_days = int(definition.get("buffer_days") or 0)
        min_expiry = (ref_date + timedelta(days=buffer_days)) if buffer_days else ref_date
        is_valid = expiry_date >= min_expiry
        if issue_str:
            issue_date = SafeComparator._parse_date(issue_str)
            if issue_date and issue_date > ref_date:
                is_valid = False

        evidence = [{
            "document_id": latest.get("id"),
            "document_type": doc_type,
            "expiry_date": expiry_str,
            "reference_date": ref_date.isoformat(),
            "buffer_days": buffer_days,
        }]

        if not is_valid:
            return EvaluationResult(
                status="FAIL",
                reason=f"Document '{doc_type}' is not valid on {ref_date.isoformat()} (Expires: {expiry_str}).",
                evidence=evidence,
                suggested_action=f"Obtain an extended or renewed '{doc_type}' certificate valid on {ref_date.isoformat()}.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Document '{doc_type}' is valid on {ref_date.isoformat()}.",
            evidence=evidence,
        )
