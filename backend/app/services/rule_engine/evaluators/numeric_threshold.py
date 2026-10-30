from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator


@EvaluatorRegistry.register("NUMERIC_THRESHOLD")
class NumericThresholdEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        val_path = definition.get("field") or (definition.get("value") if isinstance(definition.get("value"), str) else "")
        operator = definition.get("operator", ">=")
        target_raw = definition.get("target")
        if target_raw is None and isinstance(definition.get("value"), (int, float)):
            target_raw = definition.get("value")
        target = float(target_raw if target_raw is not None else 0.0)

        actual_val, err = SafePathResolver.resolve(val_path, context)
        if err or actual_val is None:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not resolve numeric field '{val_path}': {err or 'Missing'}",
            )

        passed, comp_err = SafeComparator.compare(actual_val, operator, target)
        if comp_err:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Numeric comparison error on '{val_path}': {comp_err}",
            )

        evidence = [{
            "field": val_path,
            "extracted_value": actual_val,
            "operator": operator,
            "target": target,
        }]

        if not passed:
            return EvaluationResult(
                status="FAIL",
                reason=f"Value for '{val_path}' ({actual_val}) does not satisfy condition '{operator} {target}'.",
                evidence=evidence,
                suggested_action=f"Increase '{val_path}' to meet regulatory standard {operator} {target}.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Numeric threshold satisfied: '{val_path}' ({actual_val}) {operator} {target}.",
            evidence=evidence,
        )
