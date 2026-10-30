from datetime import date
from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafeComparator


@EvaluatorRegistry.register("DOCUMENT_REQUIRED")
class DocumentRequiredEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        doc_type = definition.get("document", "").upper()
        min_validity = definition.get("min_validity_days", 0)

        docs = context.get_documents_by_type(doc_type)
        if not docs:
            return EvaluationResult(
                status="FAIL",
                reason=f"Mandatory document of type '{doc_type}' is missing from the application package.",
                suggested_action=f"Upload a valid '{doc_type}' document issued by the competent authority.",
            )

        latest = docs[-1]
        evidence = [{
            "document_id": latest.get("id"),
            "document_type": doc_type,
            "filename": latest.get("original_filename"),
            "status": latest.get("status"),
        }]

        if min_validity > 0:
            expiry_str = latest.get("expiry_date")
            if not expiry_str:
                return EvaluationResult(
                    status="NEEDS_REVIEW",
                    reason=f"Document '{doc_type}' is uploaded but does not specify a valid expiry date.",
                    evidence=evidence,
                    suggested_action=f"Ensure '{doc_type}' contains a clear expiry date.",
                )

            expiry_date = SafeComparator._parse_date(expiry_str)
            if not expiry_date:
                return EvaluationResult(
                    status="NEEDS_REVIEW",
                    reason=f"Could not parse expiry date '{expiry_str}' for document '{doc_type}'.",
                    evidence=evidence,
                )

            today = context.get_today()
            days_remaining = (expiry_date - today).days

            evidence[0]["expiry_date"] = expiry_str
            evidence[0]["days_remaining"] = days_remaining

            if days_remaining < min_validity:
                return EvaluationResult(
                    status="FAIL",
                    reason=f"Document '{doc_type}' expires in {days_remaining} days, which is less than the required {min_validity} days validity.",
                    evidence=evidence,
                    suggested_action=f"Renew document '{doc_type}' before submission.",
                )

        return EvaluationResult(
            status="PASS",
            reason=f"Mandatory document '{doc_type}' is present and meets validity requirements.",
            evidence=evidence,
        )

