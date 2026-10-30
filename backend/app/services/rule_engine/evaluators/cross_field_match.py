from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator


@EvaluatorRegistry.register("CROSS_FIELD_MATCH")
class CrossFieldMatchEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        left_path = definition.get("left", "")
        right_path = definition.get("right", "")
        match_type = str(definition.get("match", "EXACT")).upper()
        if definition.get("fuzzy") is True:
            match_type = "FUZZY"
        threshold = float(definition.get("threshold", 0.8))

        left_val, left_err = SafePathResolver.resolve(left_path, context)
        right_val, right_err = SafePathResolver.resolve(right_path, context)

        if left_err or left_val is None:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not resolve left field '{left_path}': {left_err or 'Missing'}",
            )

        if right_err or right_val is None:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Could not resolve right field '{right_path}': {right_err or 'Missing'}",
            )

        evidence = [{
            "left_field": left_path,
            "left_value": str(left_val),
            "right_field": right_path,
            "right_value": str(right_val),
            "match_type": match_type,
        }]

        if match_type == "EXACT":
            matched = str(left_val).strip().lower() == str(right_val).strip().lower()
            if not matched:
                return EvaluationResult(
                    status="FAIL",
                    reason=f"Exact cross-field mismatch between '{left_path}' ('{left_val}') and '{right_path}' ('{right_val}').",
                    evidence=evidence,
                    suggested_action="Ensure information in uploaded document matches institutional records exactly.",
                )
        else:  # FUZZY
            matched, ratio = SafeComparator.fuzzy_match(left_val, right_val, threshold)
            evidence[0]["similarity_ratio"] = round(ratio, 3)
            evidence[0]["required_threshold"] = threshold
            if not matched:
                return EvaluationResult(
                    status="FAIL",
                    reason=f"Fuzzy match similarity {round(ratio, 2)} is below required threshold {threshold} between '{left_path}' ('{left_val}') and '{right_path}' ('{right_val}').",
                    evidence=evidence,
                    suggested_action="Verify institutional spelling and nomenclature across application and document.",
                )

        return EvaluationResult(
            status="PASS",
            reason=f"Cross-field match verified between '{left_path}' and '{right_path}'.",
            evidence=evidence,
        )
