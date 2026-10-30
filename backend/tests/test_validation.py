import pytest
from datetime import datetime, date, timedelta, timezone
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.rule import Rule, RuleSet
from backend.app.models.document import Document
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.validation.runner import ValidationRunner


@pytest.fixture
def validation_fixture(db_session):
    # 1. Clean existing rules / rulesets / runs to isolate tests
    db_session.query(ValidationFinding).delete()
    db_session.query(ValidationRun).delete()
    db_session.query(Rule).delete()
    db_session.query(RuleSet).delete()
    db_session.commit()

    # 2. Institute 1 & User 1
    inst1 = Institute(
        aicte_institute_id="VAL_INST_01",
        name="Institute of Validation 1",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="val_user1@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # 3. Institute 2 & User 2
    inst2 = Institute(
        aicte_institute_id="VAL_INST_02",
        name="Institute of Validation 2",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="val_user2@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst2.id,
        is_active=True,
    )
    db_session.add(user2)

    # 4. Admin User
    admin_user = User(
        email="val_admin@aicte-india.org",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.commit()

    # 5. Application for Institute 1
    app1 = Application(
        institute_id=inst1.id,
        application_id="APP-VAL-101",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="SUBMITTED",
    )
    db_session.add(app1)
    db_session.commit()
    db_session.refresh(app1)

    role1 = user1.role.value if hasattr(user1.role, "value") else str(user1.role)
    role2 = user2.role.value if hasattr(user2.role, "value") else str(user2.role)
    admin_r = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)

    token1 = create_access_token(user_id=user1.id, role=role1)
    token2 = create_access_token(user_id=user2.id, role=role2)
    admin_token = create_access_token(user_id=admin_user.id, role=admin_r)

    return {
        "inst1": inst1,
        "inst2": inst2,
        "user1": user1,
        "user2": user2,
        "admin_user": admin_user,
        "app1": app1,
        "token1": token1,
        "token2": token2,
        "admin_token": admin_token,
    }


# ==============================================================================
# 1. TEST OVERALL STATUSES & SCORING
# ==============================================================================

def test_overall_status_ready_for_review(db_session, validation_fixture):
    """When all published rules pass, overall_status is READY_FOR_REVIEW and score is 100.0"""
    app = validation_fixture["app1"]

    # Rule that always passes (field_required on application.category)
    r1 = Rule(
        code="RULE_PASS_01",
        rule_code="RULE_PASS_01",
        title="Check Application Category Present",
        description="Application must have a category",
        handbook_ref="Section 1.1",
        category="EOA",
        rule_type="FIELD_REQUIRED",
        severity="MAJOR",
        mandatory=True,
        is_mandatory=True,
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "FIELD_REQUIRED", "field": "application.category"}},
    )
    db_session.add(r1)
    db_session.commit()

    run = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    assert run.overall_status == "READY_FOR_REVIEW"
    assert run.score == 100.0
    assert run.blocker_count == 0
    assert run.major_count == 0
    assert run.minor_count == 0
    assert len(run.findings) >= 1
    assert all(f.status == "PASS" for f in run.findings)


def test_overall_status_blocked_on_blocker_fail(db_session, validation_fixture):
    """When a BLOCKER rule fails, overall_status is BLOCKED and score is reduced by weight"""
    app = validation_fixture["app1"]

    # Blocker rule failing (missing document)
    r_blocker = Rule(
        code="RULE_BLOCKER_01",
        rule_code="RULE_BLOCKER_01",
        title="Mandatory Fire Safety Certificate",
        description="Fire NOC must be uploaded",
        handbook_ref="Section 2.1",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="BLOCKER",
        mandatory=True,
        is_mandatory=True,
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "FIRE_NOC"}},
    )
    db_session.add(r_blocker)
    db_session.commit()

    run = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    assert run.overall_status == "BLOCKED"
    assert run.blocker_count == 1
    # Deduction for BLOCKER is 40.0 -> score 60.0
    assert run.score == 60.0
    failed_finding = next(f for f in run.findings if f.rule_code == "RULE_BLOCKER_01")
    assert failed_finding.status == "FAIL"


def test_overall_status_likely_to_fail_on_multiple_majors(db_session, validation_fixture):
    """When MAJOR fails >= VALIDATION_MAJOR_FAIL_THRESHOLD (default 2), overall_status is LIKELY_TO_FAIL"""
    app = validation_fixture["app1"]

    # 2 Major rules failing
    r_major_1 = Rule(
        code="RULE_MAJOR_01",
        rule_code="RULE_MAJOR_01",
        title="Check Mandatory Building Plan",
        description="Missing building plan",
        handbook_ref="Section 3.1",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        mandatory=True,
        is_mandatory=True,
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "BUILDING_PLAN"}},
    )
    r_major_2 = Rule(
        code="RULE_MAJOR_02",
        rule_code="RULE_MAJOR_02",
        title="Check Mandatory Land Deed",
        description="Missing land deed",
        handbook_ref="Section 3.2",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        mandatory=True,
        is_mandatory=True,
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "LAND_DEED"}},
    )
    db_session.add_all([r_major_1, r_major_2])
    db_session.commit()

    run = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    assert run.blocker_count == 0
    assert run.major_count == 2
    assert run.overall_status == "LIKELY_TO_FAIL"
    # Deductions: 2 * 15.0 = 30.0 -> score 70.0
    assert run.score == 70.0


def test_overall_status_needs_attention(db_session, validation_fixture):
    """When only 1 MAJOR rule fails (or 1 MINOR fail), overall_status is NEEDS_ATTENTION"""
    app = validation_fixture["app1"]

    r_major = Rule(
        code="RULE_SINGLE_MAJOR",
        rule_code="RULE_SINGLE_MAJOR",
        title="Single Major Deficiency",
        description="Missing certificate",
        handbook_ref="Section 4.1",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        mandatory=True,
        is_mandatory=True,
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "OCCUPANCY_CERT"}},
    )
    db_session.add(r_major)
    db_session.commit()

    run = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    assert run.blocker_count == 0
    assert run.major_count == 1
    assert run.overall_status == "NEEDS_ATTENTION"
    assert run.score == 85.0


# ==============================================================================
# 2. TEST DIFFS BETWEEN RUNS (newly_failed, newly_fixed, still_open)
# ==============================================================================

def test_validation_diff_between_runs(db_session, validation_fixture):
    """
    Run 1: Rule A fails, Rule B fails.
    State changes: Rule A passes, Rule B still fails, Rule C fails.
    Run 2 diff:
      newly_failed: [Rule C]
      newly_fixed: [Rule A]
      still_open: [Rule B]
    """
    app = validation_fixture["app1"]

    # Seed Document for Rule A initially missing
    rule_a = Rule(
        code="RULE_DIFF_A",
        rule_code="RULE_DIFF_A",
        title="Rule A Check",
        description="Document A required",
        handbook_ref="Sec A",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "DOC_A"}},
    )
    rule_b = Rule(
        code="RULE_DIFF_B",
        rule_code="RULE_DIFF_B",
        title="Rule B Check",
        description="Document B required",
        handbook_ref="Sec B",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "DOC_B"}},
    )
    db_session.add_all([rule_a, rule_b])
    db_session.commit()

    # --- Run 1: Both A and B fail ---
    run1 = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    assert run1.diff_json["previous_run_id"] is None
    assert run1.diff_json["newly_failed_count"] == 0

    # --- Upload DOC_A so Rule A now passes ---
    doc_a = Document(
        institute_id=validation_fixture["inst1"].id,
        application_id=app.id,
        document_type_code="DOC_A",
        original_filename="doc_a.pdf",
        stored_filename="doc_a_123.pdf",
        file_path="storage/doc_a.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_doc_a_unique",
        status="Uploaded",
        ocr_status="DONE",
    )
    # Add Rule C that fails
    rule_c = Rule(
        code="RULE_DIFF_C",
        rule_code="RULE_DIFF_C",
        title="Rule C Check",
        description="Document C required",
        handbook_ref="Sec C",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="MAJOR",
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "DOC_C"}},
    )
    db_session.add_all([doc_a, rule_c])
    db_session.commit()

    # --- Run 2: Rule A is fixed, Rule B still open, Rule C newly failed ---
    run2 = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    diff = run2.diff_json
    assert diff["previous_run_id"] == run1.id
    assert "RULE_DIFF_C" in diff["newly_failed"]
    assert "RULE_DIFF_A" in diff["newly_fixed"]
    assert "RULE_DIFF_B" in diff["still_open"]
    assert diff["newly_failed_count"] == 1
    assert diff["newly_fixed_count"] == 1
    assert diff["still_open_count"] == 1


# ==============================================================================
# 3. TEST DRAFT RULE IMMUNITY
# ==============================================================================

def test_draft_rule_immunity(db_session, validation_fixture):
    """Draft rules (status='DRAFT') must NEVER be evaluated in validation runs"""
    app = validation_fixture["app1"]

    # 1. Published passing rule
    pub_rule = Rule(
        code="RULE_PUBLISHED_PASS",
        rule_code="RULE_PUBLISHED_PASS",
        title="Published Passing Rule",
        description="Must have category",
        handbook_ref="Section 1",
        category="EOA",
        rule_type="FIELD_REQUIRED",
        severity="MAJOR",
        status="PUBLISHED",
        is_active=True,
        definition={"root": {"type": "FIELD_REQUIRED", "field": "application.category"}},
    )
    # 2. Draft rule that would fail (BLOCKER)
    draft_rule = Rule(
        code="RULE_DRAFT_BLOCKER_FAIL",
        rule_code="RULE_DRAFT_BLOCKER_FAIL",
        title="Draft Experimental Check",
        description="Missing phantom document",
        handbook_ref="Section Draft",
        category="EOA",
        rule_type="DOCUMENT_REQUIRED",
        severity="BLOCKER",
        status="DRAFT",  # Strictly DRAFT
        is_active=True,
        definition={"root": {"type": "DOCUMENT_REQUIRED", "document": "PHANTOM_DOC"}},
    )
    db_session.add_all([pub_rule, draft_rule])
    db_session.commit()

    run = ValidationRunner.run_validation(db_session, app.id, triggered_by=validation_fixture["user1"].id)
    # Draft rule must NOT be in findings
    finding_codes = [f.rule_code for f in run.findings]
    assert "RULE_PUBLISHED_PASS" in finding_codes
    assert "RULE_DRAFT_BLOCKER_FAIL" not in finding_codes
    assert run.overall_status == "READY_FOR_REVIEW"
    assert run.blocker_count == 0
    assert run.score == 100.0


# ==============================================================================
# 4. TEST MULTI-TENANT INSTITUTE ISOLATION & ADMIN ENDPOINT
# ==============================================================================

def test_multi_tenant_institute_isolation_for_validation(client, validation_fixture):
    """
    Institute 1 can validate and query its own application.
    Institute 2 cannot validate or query Institute 1's application (404).
    Admin can query any application validation report.
    """
    app1 = validation_fixture["app1"]

    # 1. Institute 2 tries to trigger validation on App 1 -> 404
    client.cookies.set("aicte_access_token", validation_fixture["token2"])
    res_val_forbidden = client.post(f"/api/institute/applications/{app1.id}/validate")
    assert res_val_forbidden.status_code == 404

    # 2. Institute 2 tries to get latest validation for App 1 -> 404
    res_latest_forbidden = client.get(f"/api/institute/applications/{app1.id}/validation/latest")
    assert res_latest_forbidden.status_code == 404

    # 3. Institute 2 tries to get history for App 1 -> 404
    res_hist_forbidden = client.get(f"/api/institute/applications/{app1.id}/validation/history")
    assert res_hist_forbidden.status_code == 404

    # 4. Institute 1 triggers validation on App 1 -> 200
    client.cookies.set("aicte_access_token", validation_fixture["token1"])
    res_val_success = client.post(f"/api/institute/applications/{app1.id}/validate")
    assert res_val_success.status_code == 200
    val_data = res_val_success.json()
    assert val_data["application_number"] == app1.application_id
    assert "overall_status" in val_data
    assert "score" in val_data
    assert "findings" in val_data

    # 5. Institute 1 gets latest validation -> 200
    res_latest = client.get(f"/api/institute/applications/{app1.id}/validation/latest")
    assert res_latest.status_code == 200
    assert res_latest.json()["id"] == val_data["id"]

    # 6. Institute 1 gets history -> 200
    res_hist = client.get(f"/api/institute/applications/{app1.id}/validation/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1

    # 7. Admin queries validation for App 1 -> 200
    client.cookies.set("aicte_access_token", validation_fixture["admin_token"])
    res_admin = client.get(f"/api/admin/applications/{app1.id}/validation")
    assert res_admin.status_code == 200
    admin_data = res_admin.json()
    assert admin_data["application_number"] == app1.application_id
    assert admin_data["score"] == val_data["score"]
