from typing import Dict, Any, List
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult


@EvaluatorRegistry.register("COMPOSITE")
class CompositeEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        all_rules: List[Dict[str, Any]] = definition.get("all") or []
        any_rules: List[Dict[str, Any]] = definition.get("any") or []
        not_rule: Dict[str, Any] = definition.get("not") or {}

        collected_evidence = []

        # 1. Evaluate 'all'
        if all_rules:
            for sub_def in all_rules:
                sub_type = sub_def.get("type", "").upper()
                evaluator = EvaluatorRegistry.get(sub_type)
                if not evaluator:
                    return EvaluationResult(
                        status="NEEDS_REVIEW",
                        reason=f"Unsupported evaluator '{sub_type}' in composite 'all' branch.",
                    )
                sub_res = evaluator.evaluate(sub_def, context)
                collected_evidence.extend(sub_res.evidence)
                if sub_res.status in ["FAIL", "NEEDS_REVIEW"]:
                    return EvaluationResult(
                        status=sub_res.status,
                        reason=f"Composite 'all' requirement failed: {sub_res.reason}",
                        evidence=collected_evidence,
                        suggested_action=sub_res.suggested_action,
                    )

        # 2. Evaluate 'any'
        if any_rules:
            any_passed = False
            last_reason = ""
            for sub_def in any_rules:
                sub_type = sub_def.get("type", "").upper()
                evaluator = EvaluatorRegistry.get(sub_type)
                if not evaluator:
                    continue
                sub_res = evaluator.evaluate(sub_def, context)
                collected_evidence.extend(sub_res.evidence)
                if sub_res.status == "PASS":
                    any_passed = True
                    break
                last_reason = sub_res.reason

            if not any_passed:
                return EvaluationResult(
                    status="FAIL",
                    reason=f"None of the alternative conditions in composite 'any' were met: {last_reason}",
                    evidence=collected_evidence,
                    suggested_action="Satisfy at least one of the alternative compliance requirements.",
                )

        # 3. Evaluate 'not'
        if not_rule:
            sub_type = not_rule.get("type", "").upper()
            evaluator = EvaluatorRegistry.get(sub_type)
            if evaluator:
                sub_res = evaluator.evaluate(not_rule, context)
                collected_evidence.extend(sub_res.evidence)
                if sub_res.status == "PASS":
                    return EvaluationResult(
                        status="FAIL",
                        reason=f"Negated rule condition was unexpectedly satisfied: {sub_res.reason}",
                        evidence=collected_evidence,
                    )

        return EvaluationResult(
            status="PASS",
            reason="All composite conditions were successfully satisfied.",
            evidence=collected_evidence,
        )

