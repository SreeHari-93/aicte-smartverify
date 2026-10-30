from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .schemas import RuleDefinition
from .context import EvaluationContext
from .evaluators import EvaluatorRegistry, EvaluationResult


class Finding(BaseModel):
    rule_code: str
    rule_title: str
    handbook_ref: Optional[str] = None
    rule_type: str
    severity: str
    mandatory: bool
    passed: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    suggested_action: Optional[str] = None
    evidence_required: List[str] = Field(default_factory=list)
    ai_checks: List[str] = Field(default_factory=list)


class EvaluationSummary(BaseModel):
    total_rules: int
    passed_count: int
    failed_count: int
    blocker_count: int
    major_count: int
    minor_count: int
    advisory_count: int
    is_compliant: bool
    evaluated_at: str


class EvaluationReport(BaseModel):
    ruleset_id: Optional[int] = None
    ruleset_name: Optional[str] = None
    application_id: Optional[int] = None
    summary: EvaluationSummary
    findings: List[Finding]


class RuleEngine:
    @classmethod
    def evaluate_rule(cls, rule: Any, context: EvaluationContext) -> Optional[Finding]:
        """
        Evaluate a single rule against an EvaluationContext.
        rule can be a Rule SQLAlchemy model, or a dict / RuleSnapshot.
        """
        # Determine attributes whether rule is ORM model or dict
        if isinstance(rule, dict):
            rule_code = rule.get("code") or rule.get("rule_code", "")
            title = rule.get("title", "")
            handbook_ref = rule.get("handbook_ref")
            rule_type = rule.get("rule_type", "GENERAL")
            severity = rule.get("severity", "MAJOR")
            mandatory = rule.get("mandatory", True)
            applies_to_categories = rule.get("applies_to_categories")
            definition_data = rule.get("definition")
            suggested_action = rule.get("suggested_action")
            evidence_required = rule.get("evidence_required") or []
            ai_checks = rule.get("ai_checks") or []
            is_active = rule.get("is_active", True)
            status = rule.get("status", "PUBLISHED")
        else:
            rule_code = getattr(rule, "code", getattr(rule, "rule_code", ""))
            title = getattr(rule, "title", "")
            handbook_ref = getattr(rule, "handbook_ref", None)
            rule_type = getattr(rule, "rule_type", "GENERAL")
            severity = getattr(rule, "severity", "MAJOR")
            mandatory = getattr(rule, "mandatory", True)
            applies_to_categories = getattr(rule, "applies_to_categories", None)
            definition_data = getattr(rule, "definition", None)
            suggested_action = getattr(rule, "suggested_action", None)
            evidence_required = getattr(rule, "evidence_required", []) or []
            ai_checks = getattr(rule, "ai_checks", []) or []
            is_active = getattr(rule, "is_active", True)
            status = getattr(rule, "status", "PUBLISHED")

        if not is_active:
            return None

        # Check category applicability
        app_category = context.application.get("category")
        if applies_to_categories and app_category:
            if app_category not in applies_to_categories:
                return None  # Does not apply to this application category

        # If no definition is provided, rule passes by default with advisory note
        if not definition_data:
            return Finding(
                rule_code=rule_code,
                rule_title=title,
                handbook_ref=handbook_ref,
                rule_type=rule_type,
                severity=severity,
                mandatory=mandatory,
                passed=True,
                message="No executable definition configured for this rule.",
                details={},
                suggested_action=suggested_action,
                evidence_required=evidence_required,
                ai_checks=ai_checks,
            )

        try:
            # Validate definition structure safely
            parsed_def = RuleDefinition.model_validate(definition_data)
            def_root = parsed_def.root
            evaluator = EvaluatorRegistry.get(def_root.type)
            if not evaluator:
                return Finding(
                    rule_code=rule_code,
                    rule_title=title,
                    handbook_ref=handbook_ref,
                    rule_type=rule_type,
                    severity=severity,
                    mandatory=mandatory,
                    passed=False,
                    message=f"No evaluator registered for rule type '{def_root.type}'.",
                    details={"error": "missing_evaluator"},
                    suggested_action=suggested_action,
                    evidence_required=evidence_required,
                    ai_checks=ai_checks,
                )

            # Pass dict or model to evaluate
            def_input = def_root.model_dump(by_alias=True) if hasattr(def_root, "model_dump") else def_root
            result = evaluator.evaluate(def_input, context)

            is_pass = (getattr(result, "status", "") == "PASS")
            msg = getattr(result, "reason", "")
            ev = getattr(result, "evidence", [])
            act = getattr(result, "suggested_action", None) or suggested_action

            return Finding(
                rule_code=rule_code,
                rule_title=title,
                handbook_ref=handbook_ref,
                rule_type=rule_type,
                severity=severity,
                mandatory=mandatory,
                passed=is_pass,
                message=msg,
                details={"status": getattr(result, "status", ""), "evidence": ev},
                suggested_action=act,
                evidence_required=evidence_required,
                ai_checks=ai_checks,
            )

        except Exception as e:
            return Finding(
                rule_code=rule_code,
                rule_title=title,
                handbook_ref=handbook_ref,
                rule_type=rule_type,
                severity=severity,
                mandatory=mandatory,
                passed=False,
                message=f"Rule evaluation error: {str(e)}",
                details={"error": str(e)},
                suggested_action=suggested_action,
                evidence_required=evidence_required,
                ai_checks=ai_checks,
            )

    @classmethod
    def evaluate(
        cls,
        rules: List[Any],
        context: EvaluationContext,
        ruleset_id: Optional[int] = None,
        ruleset_name: Optional[str] = None,
    ) -> EvaluationReport:
        findings: List[Finding] = []
        for r in rules:
            finding = cls.evaluate_rule(r, context)
            if finding:
                findings.append(finding)

        total = len(findings)
        passed = sum(1 for f in findings if f.passed)
        failed = total - passed

        blockers = sum(1 for f in findings if not f.passed and f.severity == "BLOCKER")
        majors = sum(1 for f in findings if not f.passed and f.severity == "MAJOR")
        minors = sum(1 for f in findings if not f.passed and f.severity == "MINOR")
        advisories = sum(1 for f in findings if not f.passed and f.severity == "ADVISORY")

        # Compliant if no blocker or major failures
        is_compliant = (blockers == 0 and majors == 0)

        app_id = context.application.get("id")

        return EvaluationReport(
            ruleset_id=ruleset_id,
            ruleset_name=ruleset_name,
            application_id=app_id,
            summary=EvaluationSummary(
                total_rules=total,
                passed_count=passed,
                failed_count=failed,
                blocker_count=blockers,
                major_count=majors,
                minor_count=minors,
                advisory_count=advisories,
                is_compliant=is_compliant,
                evaluated_at=datetime.utcnow().isoformat() + "Z",
            ),
            findings=findings,
        )

    @classmethod
    def simulate(
        cls,
        definition: Dict[str, Any],
        context_data: Dict[str, Any],
        rule_meta: Optional[Dict[str, Any]] = None,
    ) -> Finding:
        """
        Simulate a rule condition against mock context data without database access.
        """
        meta = rule_meta or {}
        context = EvaluationContext.from_dict(context_data)
        synthetic_rule = {
            "code": meta.get("code", "SIM-RULE-001"),
            "title": meta.get("title", "Simulation Rule"),
            "handbook_ref": meta.get("handbook_ref", "SIM-REF"),
            "rule_type": meta.get("rule_type", "GENERAL"),
            "severity": meta.get("severity", "MAJOR"),
            "mandatory": meta.get("mandatory", True),
            "applies_to_categories": meta.get("applies_to_categories"),
            "definition": definition,
            "suggested_action": meta.get("suggested_action"),
            "evidence_required": meta.get("evidence_required", []),
            "ai_checks": meta.get("ai_checks", []),
            "is_active": True,
            "status": "DRAFT",
        }
        res = cls.evaluate_rule(synthetic_rule, context)
        return res or Finding(
            rule_code=synthetic_rule["code"],
            rule_title=synthetic_rule["title"],
            rule_type=synthetic_rule["rule_type"],
            severity=synthetic_rule["severity"],
            mandatory=synthetic_rule["mandatory"],
            passed=False,
            message="Rule did not apply to the provided context.",
            details={"skipped": True},
        )
