from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator


@EvaluatorRegistry.register("INFRASTRUCTURE")
class InfrastructureEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        metric = definition.get("metric") or definition.get("check_type") or "carpet_area"
        operator = definition.get("operator") or ">="
        target_val = (
            definition.get("target")
            or definition.get("min_carpet_area_sqm")
            or definition.get("min_bandwidth_mbps")
            or 0.0
        )
        try:
            target = float(target_val)
        except (ValueError, TypeError):
            target = 0.0

        # Check in institute or application or doc metrics
        actual_val, err = SafePathResolver.resolve(f"institute.{metric}", context)
        if err or actual_val is None:
            actual_val, err = SafePathResolver.resolve(f"application.{metric}", context)

        if err or actual_val is None:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Infrastructure metric '{metric}' is not recorded in the application or institute profile.",
                suggested_action=f"Provide certified architect carpet area statement for '{metric}'.",
            )

        passed, comp_err = SafeComparator.compare(actual_val, operator, target)
        if comp_err:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Infrastructure evaluation error: {comp_err}",
            )

        evidence = [{
            "metric": metric,
            "actual_value": actual_val,
            "operator": operator,
            "target": target,
        }]

        if not passed:
            return EvaluationResult(
                status="FAIL",
                reason=f"Infrastructure metric '{metric}' ({actual_val}) is below regulatory standard ({operator} {target}).",
                evidence=evidence,
                suggested_action=f"Augment institutional built-up area/facilities to achieve {operator} {target}.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Infrastructure norm satisfied for '{metric}': {actual_val} {operator} {target}.",
            evidence=evidence,
        )

