from typing import Dict, Any
from backend.app.services.rule_engine.evaluators.base import BaseEvaluator, EvaluatorRegistry, EvaluationResult
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator


@EvaluatorRegistry.register("INFRASTRUCTURE")
class InfrastructureEvaluator(BaseEvaluator):
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        metric = (
            definition.get("metric")
            or definition.get("field")
            or definition.get("check_type")
            or "total_built_up_area"
        )
        if metric.startswith("infrastructure."):
            metric = metric.split(".", 1)[1]
        elif metric.startswith("application."):
            metric = metric.split(".", 1)[1]

        metric_aliases = {
            "library_area_sqm": "library_area",
            "built_up_area": "total_built_up_area",
            "carpet_area": "total_built_up_area",
            "instructional_area": "total_built_up_area",
        }
        metric = metric_aliases.get(metric, metric)

        operator = definition.get("operator") or ">="
        target_val = (
            definition.get("target")
            if definition.get("target") is not None
            else (
                definition.get("min_carpet_area_sqm")
                or definition.get("min_bandwidth_mbps")
                or 0.0
            )
        )
        if isinstance(target_val, bool):
            target = target_val
        else:
            try:
                target = float(target_val)
            except (ValueError, TypeError):
                target = target_val

        # 1. Resolve from infrastructure scope, then institute or application
        actual_val, err = SafePathResolver.resolve(f"infrastructure.{metric}", context)
        if err or actual_val is None:
            actual_val, err = SafePathResolver.resolve(f"institute.{metric}", context)
        if err or actual_val is None:
            actual_val, err = SafePathResolver.resolve(f"application.{metric}", context)

        # Missing data produces a clear "Not provided" result
        if err or actual_val is None:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Infrastructure metric '{metric}' was not provided (Not provided).",
                suggested_action=f"Provide institutional data for '{metric}' in the Infrastructure Details section.",
            )

        passed, comp_err = SafeComparator.compare(actual_val, operator, target)
        if comp_err:
            return EvaluationResult(
                status="NEEDS_REVIEW",
                reason=f"Infrastructure evaluation comparison error on '{metric}': {comp_err}",
            )

        unit_str = f" {definition['unit']}" if definition.get("unit") else ""
        evidence = [{
            "metric": metric,
            "field": f"infrastructure.{metric}",
            "actual_value": actual_val,
            "extracted_value": actual_val,
            "operator": operator,
            "target": target,
            "unit": definition.get("unit", ""),
        }]

        if not passed:
            return EvaluationResult(
                status="FAIL",
                reason=f"Infrastructure metric '{metric}' ({actual_val}{unit_str}) does not meet the regulatory threshold ({operator} {target}{unit_str}).",
                evidence=evidence,
                suggested_action=f"Augment institutional facilities for '{metric}' to achieve {operator} {target}{unit_str}.",
            )

        return EvaluationResult(
            status="PASS",
            reason=f"Infrastructure norm satisfied for '{metric}': {actual_val}{unit_str} {operator} {target}{unit_str}.",
            evidence=evidence,
        )
