from typing import Dict, Any, List
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafeComparator


@EvaluatorRegistry.register("COUNT_AT_LEAST")
class CountAtLeastEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        source_name = definition.get("source") or definition.get("collection") or "documents"
        filter_criteria = definition.get("filter") or {}
        min_count = int(definition.get("min_count") if definition.get("min_count") is not None else definition.get("min", 1))

        if source_name == "documents":
            items = context.documents
        elif source_name == "courses":
            items = context.courses
        elif source_name == "complaints":
            items = context.complaints
        else:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Unsupported count source '{source_name}'.",
            )

        field = definition.get("field")
        condition = definition.get("condition")

        matching = []
        for it in items:
            match = True
            for k, expected in filter_criteria.items():
                actual = it.get(k) or it.get(f"document_{k}") or it.get(f"{k}_code")
                if str(actual).upper() != str(expected).upper():
                    match = False
                    break
            if match and field and condition:
                op = condition.get("operator", "==")
                val = condition.get("value")
                item_val = it.get(field)
                cond_pass, _ = SafeComparator.compare(item_val, op, val)
                if not cond_pass:
                    match = False
            if match:
                matching.append(it)

        count = len(matching)
        evidence = [{
            "source": source_name,
            "filter": filter_criteria,
            "matched_count": count,
            "required_min": min_count,
        }]

        if count < min_count:
            return EvaluationResult(
                status="FAIL",
                reason=f"Found {count} item(s) in '{source_name}' matching criteria, but minimum {min_count} is required.",
                evidence=evidence,
                suggested_action=f"Ensure at least {min_count} item(s) are submitted.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Count check satisfied: {count} item(s) present (minimum {min_count} required).",
            evidence=evidence,
        )
