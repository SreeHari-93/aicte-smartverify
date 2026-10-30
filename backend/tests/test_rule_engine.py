import pytest
from datetime import date, timedelta

from backend.app.services.rule_engine.context import EvaluationContext
from backend.app.services.rule_engine.schemas import RuleDefinition
from backend.app.services.rule_engine.resolver import SafePathResolver, SafeComparator
from backend.app.services.rule_engine.engine import RuleEngine, Finding


def test_safe_path_resolver_safety():
    ctx = EvaluationContext(
        application={"id": 101, "academic_year": "2026-27"},
        institute={"name": "Test Engineering College"},
        documents=[
            {
                "document_type_code": "FIRE_NOC",
                "extracted_data": {"noc_number": "NOC-123", "valid_upto": "2027-01-01"},
            }
        ],
    )

    # Valid resolves
    val, err = SafePathResolver.resolve("application.academic_year", ctx)
    assert val == "2026-27"
    assert err is None

    val, err = SafePathResolver.resolve("institute.name", ctx)
    assert val == "Test Engineering College"

    val, err = SafePathResolver.resolve("doc.FIRE_NOC.noc_number", ctx)
    assert val == "NOC-123"

    # Malicious or private access attempts return None safely
    val, err = SafePathResolver.resolve("__class__.__bases__", ctx)
    assert val is None
    assert err is not None

    val, err = SafePathResolver.resolve("application.__globals__", ctx)
    assert val is None

    val, err = SafePathResolver.resolve("non_existent_root.field", ctx)
    assert val is None

    val, err = SafePathResolver.resolve("", ctx)
    assert val is None


def test_safe_comparator_operations():
    res, _ = SafeComparator.compare(100, ">", 50)
    assert res is True

    res, _ = SafeComparator.compare(50, "<=", 50)
    assert res is True

    res, _ = SafeComparator.compare("Delhi", "==", "delhi")
    assert res is True

    res, _ = SafeComparator.compare("A", "in", ["A", "B", "C"])
    assert res is True

    res, _ = SafeComparator.compare("Z", "not_in", ["A", "B"])
    assert res is True

    res, _ = SafeComparator.compare("AICTE-2026", "matches", r"^AICTE-\d{4}$")
    assert res is True

    # Rejection of excessively long regex patterns
    res, _ = SafeComparator.compare("text", "matches", "a" * 250)
    assert res is False

    # Date comparisons
    res, _ = SafeComparator.compare("2026-05-01", "date_before", "2026-06-01")
    assert res is True

    res, _ = SafeComparator.compare("2026-07-01", "date_after", "2026-06-01")
    assert res is True


def test_evaluator_document_required():
    today = date.today()
    ctx = EvaluationContext(
        documents=[
            {
                "document_type_code": "FIRE_NOC",
                "status": "Uploaded",
                "expiry_date": (today + timedelta(days=60)).isoformat(),
            }
        ]
    )

    # 1. Document present and valid
    rule_def = {"type": "DOCUMENT_REQUIRED", "document": "FIRE_NOC", "min_validity_days": 30}
    res = RuleEngine.simulate(rule_def, ctx.to_dict())
    assert res.passed is True

    # 2. Document missing
    rule_def_missing = {"type": "DOCUMENT_REQUIRED", "document": "NBA_CERT"}
    res_missing = RuleEngine.simulate(rule_def_missing, ctx.to_dict())
    assert res_missing.passed is False

    # 3. Document expired or insufficient validity
    rule_def_strict = {"type": "DOCUMENT_REQUIRED", "document": "FIRE_NOC", "min_validity_days": 90}
    res_strict = RuleEngine.simulate(rule_def_strict, ctx.to_dict())
    assert res_strict.passed is False


def test_evaluator_field_required():
    ctx = EvaluationContext(
        application={"academic_year": "2026-27", "category": "EOA", "missing_val": None}
    )

    res_pass = RuleEngine.simulate({"type": "FIELD_REQUIRED", "field": "application.academic_year"}, ctx.to_dict())
    assert res_pass.passed is True

    res_fail = RuleEngine.simulate({"type": "FIELD_REQUIRED", "field": "application.intake_total"}, ctx.to_dict())
    assert res_fail.passed is False

    res_null = RuleEngine.simulate({"type": "FIELD_REQUIRED", "field": "application.missing_val"}, ctx.to_dict())
    assert res_null.passed is False


def test_evaluator_validity_period():
    today = date.today()
    ctx = EvaluationContext(
        documents=[
            {
                "document_type_code": "FIRE_NOC",
                "expiry_date": (today + timedelta(days=40)).isoformat(),
            }
        ]
    )

    # Buffer 30 days requires expiry >= today + 30 (40 >= 30: Pass)
    res_pass = RuleEngine.simulate(
        {"type": "VALIDITY_PERIOD", "document": "FIRE_NOC", "must_be_valid_on": "today", "buffer_days": 30},
        ctx.to_dict(),
    )
    assert res_pass.passed is True

    # Buffer 50 days requires expiry >= today + 50 (40 >= 50: Fail)
    res_fail = RuleEngine.simulate(
        {"type": "VALIDITY_PERIOD", "document": "FIRE_NOC", "must_be_valid_on": "today", "buffer_days": 50},
        ctx.to_dict(),
    )
    assert res_fail.passed is False


def test_evaluator_cross_field_match():
    ctx = EvaluationContext(
        institute={"name": "Sri Krishna College of Engineering"},
        documents=[
            {
                "document_type_code": "AFFIDAVIT",
                "extracted_data": {"deponent_name": "Sri Krishna College of Engineering and Technology"},
            }
        ],
    )

    # Fuzzy match passes with reasonable threshold
    res_fuzzy = RuleEngine.simulate(
        {
            "type": "CROSS_FIELD_MATCH",
            "left": "institute.name",
            "right": "doc.AFFIDAVIT.deponent_name",
            "fuzzy": True,
            "threshold": 0.6,
        },
        ctx.to_dict(),
    )
    assert res_fuzzy.passed is True

    # Exact match fails due to slight wording difference
    res_exact = RuleEngine.simulate(
        {
            "type": "CROSS_FIELD_MATCH",
            "left": "institute.name",
            "right": "doc.AFFIDAVIT.deponent_name",
            "fuzzy": False,
        },
        ctx.to_dict(),
    )
    assert res_exact.passed is False


def test_evaluator_numeric_threshold():
    ctx = EvaluationContext(
        institute={"nirf_rank": 73},
        courses=[{"intake": 180}, {"intake": 120}],
    )

    res_nirf = RuleEngine.simulate(
        {"type": "NUMERIC_THRESHOLD", "field": "institute.nirf_rank", "operator": "<=", "target": 100},
        ctx.to_dict(),
    )
    assert res_nirf.passed is True

    res_intake = RuleEngine.simulate(
        {"type": "NUMERIC_THRESHOLD", "field": "courses.total_intake", "operator": ">", "target": 200},
        ctx.to_dict(),
    )
    assert res_intake.passed is True


def test_evaluator_count_at_least():
    ctx = EvaluationContext(
        courses=[
            {"name": "CSE", "intake": 180},
            {"name": "IT", "intake": 120},
            {"name": "Civil", "intake": 60},
        ]
    )

    res_count = RuleEngine.simulate(
        {
            "type": "COUNT_AT_LEAST",
            "collection": "courses",
            "field": "intake",
            "min_count": 2,
            "condition": {"operator": ">=", "value": 100},
        },
        ctx.to_dict(),
    )
    assert res_count.passed is True


def test_evaluator_composite():
    today = date.today()
    ctx = EvaluationContext(
        application={"academic_year": "2026-27"},
        documents=[
            {
                "document_type_code": "FIRE_NOC",
                "expiry_date": (today + timedelta(days=40)).isoformat(),
            }
        ],
    )

    # Composite 'all' pass
    all_def = {
        "type": "COMPOSITE",
        "operator": "all",
        "conditions": [
            {"type": "FIELD_REQUIRED", "field": "application.academic_year"},
            {"type": "DOCUMENT_REQUIRED", "document": "FIRE_NOC"},
        ],
    }
    assert RuleEngine.simulate(all_def, ctx.to_dict()).passed is True

    # Composite 'all' fail when one child fails
    all_fail_def = {
        "type": "COMPOSITE",
        "operator": "all",
        "conditions": [
            {"type": "FIELD_REQUIRED", "field": "application.academic_year"},
            {"type": "DOCUMENT_REQUIRED", "document": "MISSING_DOC"},
        ],
    }
    assert RuleEngine.simulate(all_fail_def, ctx.to_dict()).passed is False

    # Composite 'any' pass
    any_pass_def = {
        "type": "COMPOSITE",
        "operator": "any",
        "conditions": [
            {"type": "DOCUMENT_REQUIRED", "document": "MISSING_DOC"},
            {"type": "DOCUMENT_REQUIRED", "document": "FIRE_NOC"},
        ],
    }
    assert RuleEngine.simulate(any_pass_def, ctx.to_dict()).passed is True


def test_nesting_depth_validation():
    # Valid nesting (depth 3)
    valid_def = {
        "type": "COMPOSITE",
        "operator": "all",
        "conditions": [
            {
                "type": "COMPOSITE",
                "operator": "any",
                "conditions": [
                    {"type": "FIELD_REQUIRED", "field": "application.id"}
                ],
            }
        ],
    }
    parsed = RuleDefinition.model_validate(valid_def)
    assert parsed.calculate_depth() == 3

    # Deep nesting > 6 levels
    deep_def = {"type": "FIELD_REQUIRED", "field": "test"}
    for _ in range(7):
        deep_def = {"type": "COMPOSITE", "operator": "all", "conditions": [deep_def]}

    with pytest.raises(ValueError, match="exceeds maximum allowed limit of 6"):
        RuleDefinition.model_validate(deep_def)
