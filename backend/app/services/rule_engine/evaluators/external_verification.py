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
        doc_id = latest.get("id")
        doc_status = (latest.get("status") or "Uploaded").upper()

        # Check VerificationResult from context
        ver_info = latest.get("verification")
        if not ver_info and hasattr(context, "verification") and isinstance(context.verification, dict):
            ver_info = context.verification.get(doc_id)

        evidence = [{
            "document_id": doc_id,
            "document_type": doc_type,
            "current_status": doc_status,
            "required_status": req_status,
        }]

        if ver_info and isinstance(ver_info, dict):
            v_status = str(ver_info.get("status") or "").upper()
            v_source = ver_info.get("source_name") or "External Authority"
            evidence[0]["verification_status"] = v_status
            evidence[0]["source_name"] = v_source
            evidence[0]["mismatched_fields"] = ver_info.get("mismatched_fields", [])

            if v_status == "VERIFIED":
                return EvaluationResult(
                    status="PASS",
                    reason=f"Document '{doc_type}' is verified by {v_source} with status 'VERIFIED'.",
                    evidence=evidence,
                )
            elif v_status == "MISMATCH_DETECTED":
                return EvaluationResult(
                    status="NEEDS_REVIEW",
                    reason=f"External verification for '{doc_type}' detected mismatched statutory records via {v_source}.",
                    evidence=evidence,
                    suggested_action="Review mismatched certificate fields against authority registers or conduct manual scrutiny.",
                )
            elif v_status == "SOURCE_UNAVAILABLE":
                return EvaluationResult(
                    status="NEEDS_REVIEW",
                    reason=f"External issuing authority source ({v_source}) for '{doc_type}' is currently unavailable. Routed to manual scrutiny.",
                    evidence=evidence,
                    suggested_action="Refer to admin verification queue for manual scrutiny by committee.",
                )
            elif v_status == "MANUAL_REVIEW_REQUIRED":
                return EvaluationResult(
                    status="NEEDS_REVIEW",
                    reason=f"Document '{doc_type}' requires physical or manual verification by an authorised committee.",
                    evidence=evidence,
                    suggested_action="Conduct physical inspection of submitted statutory document.",
                )
            elif v_status == "EXPIRED":
                return EvaluationResult(
                    status="FAIL",
                    reason=f"External statutory authority ({v_source}) confirmed certificate '{doc_type}' has expired.",
                    evidence=evidence,
                    suggested_action="Renew statutory certificate and upload valid document.",
                )

        # Fallback if no specific VerificationResult
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
