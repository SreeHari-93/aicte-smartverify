from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult


@EvaluatorRegistry.register("EXTERNAL_VERIFICATION")
class ExternalVerificationEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        doc_type = definition.get("document", "").upper()
        req_status = definition.get("required_status", "VERIFIED").upper()

        docs = context.get_documents_by_type(doc_type)
        if not docs:
            return EvaluationResult(
                status="FAIL",
                reason=f"Document '{doc_type}' is missing for external verification.",
                suggested_action=f"Upload document '{doc_type}' to undergo external verification.",
            )

        latest = docs[-1]
        doc_status = (latest.get("status") or "Uploaded").upper()

        evidence = [{
            "document_id": latest.get("id"),
            "document_type": doc_type,
            "current_status": doc_status,
            "required_status": req_status,
        }]

        if doc_status != req_status:
            return EvaluationResult(
                status="NEEDS_REVIEW" if doc_status in ["UPLOADED", "PROCESSING"] else "FAIL",
                reason=f"External verification for '{doc_type}' is '{doc_status}' (Required: '{req_status}').",
                evidence=evidence,
                suggested_action="Wait for external authority digital signature / API verification to complete.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Document '{doc_type}' is verified with status '{req_status}'.",
            evidence=evidence,
        )

