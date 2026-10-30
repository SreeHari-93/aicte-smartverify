from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver


@EvaluatorRegistry.register("FIELD_REQUIRED")
class FieldRequiredEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        field_path = definition.get("field", "")
        val, err = SafePathResolver.resolve(field_path, context)

        if err or val is None or val == "":
            return EvaluationResult(
                status="FAIL",
                reason=f"Mandatory field '{field_path}' is missing or empty. ({err or 'Value is empty'})",
                suggested_action=f"Provide a valid value for '{field_path}'.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Required field '{field_path}' is present with value '{val}'.",
            evidence=[{"field": field_path, "extracted_value": val}],
        )

