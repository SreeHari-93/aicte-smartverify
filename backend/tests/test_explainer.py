import pytest
import os
from datetime import datetime, timezone
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.rule import Rule
from backend.app.models.validation_run import ValidationRun, ValidationFinding, FindingNote, ValidationExplanation
from backend.app.models.audit_log import AuditLog
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.explainer.root_cause import RootCauseAnalyzer, RootCause
from backend.app.services.explainer.narrator import ExplainerNarrator, GroundingValidator, CircuitBreaker


@pytest.fixture
def explainer_fixture(db_session):
    # 1. Clean existing records for test isolation
    db_session.query(FindingNote).delete()
    db_session.query(ValidationExplanation).delete()
    db_session.query(ValidationFinding).delete()
    db_session.query(ValidationRun).delete()
    db_session.query(Application).delete()
    db_session.query(Rule).delete()
    db_session.query(AuditLog).delete()
    db_session.commit()

    # 2. Institute 1 & User 1
    inst1 = Institute(
        aicte_institute_id="INST_EXP_01",
        name="Institute of Technology One",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="inst1_user@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # 3. Institute 2 & User 2
    inst2 = Institute(
        aicte_institute_id="INST_EXP_02",
        name="Institute of Science Two",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="inst2_user@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst2.id,
        is_active=True,
    )
    db_session.add(user2)

    # 4. Admin User
    admin_user = User(
        email="exp_admin@aicte-india.org",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)

    # 5. Reviewer User
    reviewer_user = User(
        email="exp_reviewer@aicte-india.org",
        password_hash=hash_password("Reviewer@123"),
        role=UserRole.REVIEWER,
        is_active=True,
    )
    db_session.add(reviewer_user)
    db_session.commit()

    # 6. Applications
    app1 = Application(
        institute_id=inst1.id,
        application_id="APP-EXP-101",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="SUBMITTED",
    )
    app2 = Application(
        institute_id=inst2.id,
        application_id="APP-EXP-202",
        category="EOA",
        academic_year="2026-27",
        programme="Management",
        status="SUBMITTED",
    )
    db_session.add(app1)
    db_session.add(app2)
    db_session.commit()
    db_session.refresh(app1)
    db_session.refresh(app2)

    # 7. Rules
    r1 = Rule(
        rule_code="APH-2026-CH3-R01",
        category="EOA",
        title="Fire Safety NOC Submission",
        description="Mandatory submission of Fire & Safety NOC",
        handbook_reference="Section 3.1",
        severity="BLOCKER",
        rule_type="DOCUMENT_REQUIRED",
        evidence_required=["FIRE_SAFETY_NOC"],
        suggested_action="Upload valid Fire & Safety NOC certificate.",
        status="PUBLISHED",
    )
    r2 = Rule(
        rule_code="APH-2026-CH3-R02",
        category="EOA",
        title="Fire Exit Compliance",
        description="Clearance for exits verified from Fire NOC",
        handbook_reference="Section 3.2",
        severity="MAJOR",
        rule_type="DOCUMENT_REQUIRED",
        evidence_required=["FIRE_SAFETY_NOC"],
        suggested_action="Upload valid Fire & Safety NOC certificate.",
        status="PUBLISHED",
    )
    r3 = Rule(
        rule_code="APH-2026-CH3-R03",
        category="EOA",
        title="Fire Extinguisher Norms",
        description="Extinguisher readiness verified from Fire NOC",
        handbook_reference="Section 3.3",
        severity="MAJOR",
        rule_type="DOCUMENT_REQUIRED",
        evidence_required=["FIRE_SAFETY_NOC"],
        suggested_action="Upload valid Fire & Safety NOC certificate.",
        status="PUBLISHED",
    )
    r4 = Rule(
        rule_code="APH-2026-CH3-R07",
        category="EOA",
        title="Fire Certificate Validity",
        description="Fire safety NOC must be valid for at least 30 days",
        handbook_reference="Section 3.7",
        severity="BLOCKER",
        rule_type="VALIDITY_PERIOD",
        evidence_required=["FIRE_SAFETY_NOC"],
        suggested_action="Upload renewed Fire Safety NOC.",
        status="PUBLISHED",
    )
    r5 = Rule(
        rule_code="APH-2026-CH4-R10",
        category="EOA",
        title="Faculty Student Ratio",
        description="FSR must meet 1:15 minimum threshold",
        handbook_reference="Section 4.2",
        severity="MAJOR",
        rule_type="NUMERIC_THRESHOLD",
        evidence_required=[],
        suggested_action="Adjust course intake or recruit qualified faculty.",
        status="PUBLISHED",
    )
    db_session.add_all([r1, r2, r3, r4, r5])
    db_session.commit()

    token1 = create_access_token(user_id=user1.id, role="INSTITUTE")
    token2 = create_access_token(user_id=user2.id, role="INSTITUTE")
    admin_token = create_access_token(user_id=admin_user.id, role="ADMIN")
    reviewer_token = create_access_token(user_id=reviewer_user.id, role="REVIEWER")

    return {
        "inst1": inst1,
        "inst2": inst2,
        "user1": user1,
        "user2": user2,
        "admin_user": admin_user,
        "reviewer_user": reviewer_user,
        "app1": app1,
        "app2": app2,
        "token1": token1,
        "token2": token2,
        "admin_token": admin_token,
        "reviewer_token": reviewer_token,
        "rules": [r1, r2, r3, r4, r5],
    }


# ==============================================================================
# TEST 1: CASCADE MERGING
# ==============================================================================
def test_cascade_merging(explainer_fixture):
    """
    Verify that when 1 missing document fails 4 rules, it is merged into
    ONE root cause with 'affects 4 rules' (using rule.evidence_required).
    """
    rules_by_code = {r.rule_code: r for r in explainer_fixture["rules"]}

    # Simulate 4 failed findings all stemming from missing FIRE_SAFETY_NOC
    findings = [
        ValidationFinding(
            id=1,
            rule_code="APH-2026-CH3-R01",
            rule_title="Fire Safety NOC Submission",
            severity="BLOCKER",
            status="FAIL",
            reason="Required statutory document FIRE_SAFETY_NOC is missing.",
            evidence_json=[{"document_type": "FIRE_SAFETY_NOC"}],
            suggested_action="Upload valid Fire & Safety NOC certificate.",
        ),
        ValidationFinding(
            id=2,
            rule_code="APH-2026-CH3-R02",
            rule_title="Fire Exit Compliance",
            severity="MAJOR",
            status="FAIL",
            reason="Cannot evaluate fire exits because FIRE_SAFETY_NOC is not uploaded.",
            evidence_json=[{"document_type": "FIRE_SAFETY_NOC"}],
            suggested_action="Upload valid Fire & Safety NOC certificate.",
        ),
        ValidationFinding(
            id=3,
            rule_code="APH-2026-CH3-R03",
            rule_title="Fire Extinguisher Norms",
            severity="MAJOR",
            status="FAIL",
            reason="Extinguisher verification requires FIRE_SAFETY_NOC which is missing.",
            evidence_json=[{"document_type": "FIRE_SAFETY_NOC"}],
            suggested_action="Upload valid Fire & Safety NOC certificate.",
        ),
        ValidationFinding(
            id=4,
            rule_code="APH-2026-CH3-R07",
            rule_title="Fire Certificate Validity",
            severity="BLOCKER",
            status="FAIL",
            reason="Missing statutory document FIRE_SAFETY_NOC.",
            evidence_json=[{"document_type": "FIRE_SAFETY_NOC"}],
            suggested_action="Upload renewed Fire Safety NOC.",
        ),
        # And 1 unrelated finding
        ValidationFinding(
            id=5,
            rule_code="APH-2026-CH4-R10",
            rule_title="Faculty Student Ratio",
            severity="MAJOR",
            status="FAIL",
            reason="Faculty to student ratio is 1:22, below required threshold of 1:15.",
            evidence_json=[{"metric": "fsr", "extracted": 22, "expected": 15}],
            suggested_action="Adjust intake or recruit faculty.",
        ),
    ]

    root_causes = RootCauseAnalyzer.analyze_findings(findings, rules_by_code=rules_by_code)

    # 5 findings must be merged into 2 root causes:
    # Cause 1: MISSING_DOCUMENT for FIRE_SAFETY_NOC (4 rules merged!)
    # Cause 2: THRESHOLD_NOT_MET for FSR
    assert len(root_causes) == 2

    # Cause 1 must be ranked first due to BLOCKER severity and 4 affected rules
    primary_cause = root_causes[0]
    assert primary_cause.cause_code == "MISSING_DOCUMENT"
    assert len(primary_cause.affected_rule_codes) == 4
    assert set(primary_cause.affected_rule_codes) == {
        "APH-2026-CH3-R01",
        "APH-2026-CH3-R02",
        "APH-2026-CH3-R03",
        "APH-2026-CH3-R07",
    }
    assert "affects 4 rules" in primary_cause.headline
    assert primary_cause.severity == "BLOCKER"
    assert primary_cause.fixable_by_institute is True

    # Cause 2
    secondary_cause = root_causes[1]
    assert secondary_cause.cause_code == "THRESHOLD_NOT_MET"
    assert len(secondary_cause.affected_rule_codes) == 1
    assert secondary_cause.severity == "MAJOR"


# ==============================================================================
# TEST 2: GROUNDING VALIDATOR REJECTING INVENTED NUMBERS & PROHIBITED WORDS
# ==============================================================================
def test_grounding_validator_rejecting_invented_number():
    """
    Verify that GroundingValidator strictly rejects LLM responses containing:
    1) Invented numbers not present in the input
    2) Prohibited words ('forgery', 'fraud', 'misconduct')
    3) Invented rule codes
    """
    input_data = {
        "application_id": "APP-EXP-101",
        "institute_name": "Institute of Technology One",
        "root_causes": [
            {
                "cause_code": "EXPIRED_DOCUMENT",
                "headline": "Expired Document: Fire Safety NOC (Rule APH-2026-CH3-R07)",
                "affected_rule_codes": ["APH-2026-CH3-R07"],
                "finding_ids": [10],
                "ordered_suggested_actions": ["Upload a renewed certificate valid for at least 30 days."],
                "evidence": [
                    {
                        "document": "Fire Safety NOC",
                        "field": "expiry_date",
                        "extracted": "2026-11-11",
                        "expected": "2026-12-11",
                    }
                ],
            }
        ],
    }

    # 1. Valid response (using only numbers from input: 101, 2026, 3, 7, 30, 2026-11-11)
    valid_resp = {
        "headline": "Application Blocked: Expired Document",
        "plain_summary": "Application APP-EXP-101 has 1 compliance deficiency.",
        "reasons": [
            {
                "cause_code": "EXPIRED_DOCUMENT",
                "explanation": "Fire Safety NOC expired on 2026-11-11 (Rule APH-2026-CH3-R07). Renew for 30 days.",
                "finding_codes": ["APH-2026-CH3-R07"],
            }
        ],
        "how_to_fix": [
            {"step": "Upload renewed certificate valid for at least 30 days.", "effort": "Medium"}
        ],
        "what_officials_will_review": "AICTE officials will review renewed statutory certificates.",
        "disclaimer": "AI-generated decision support; final decisions rest with authorised AICTE officials.",
    }

    is_valid, errors = GroundingValidator.validate(valid_resp, input_data)
    assert is_valid is True, f"Expected valid response to pass, got errors: {errors}"

    # 2. Reject invented number (e.g., invented penalty '50000' or invented section '999')
    invented_num_resp = dict(valid_resp)
    invented_num_resp["plain_summary"] = "Application APP-EXP-101 is penalized 50000 rupees under rule 999."

    is_valid, errors = GroundingValidator.validate(invented_num_resp, input_data)
    assert is_valid is False
    assert any("Invented number" in err for err in errors)
    assert any("50000" in err for err in errors)

    # 3. Reject prohibited word 'fraud' or 'forgery'
    prohibited_word_resp = dict(valid_resp)
    prohibited_word_resp["plain_summary"] = "Application APP-EXP-101 contains suspected fraud in document submission."

    is_valid, errors = GroundingValidator.validate(prohibited_word_resp, input_data)
    assert is_valid is False
    assert any("Prohibited word" in err for err in errors)

    # 4. Reject invented rule code
    invented_rule_resp = dict(valid_resp)
    invented_rule_resp["reasons"] = [
        {
            "cause_code": "EXPIRED_DOCUMENT",
            "explanation": "Deficiency detected under invented rule.",
            "finding_codes": ["INVENTED-RULE-999"],
        }
    ]
    is_valid, errors = GroundingValidator.validate(invented_rule_resp, input_data)
    assert is_valid is False
    assert any("Invented or unauthorized rule code" in err for err in errors)


# ==============================================================================
# TEST 3: TEMPLATE FALLBACK WITH NO API KEY (DETERMINISTIC SENTENCES)
# ==============================================================================
def test_template_fallback_with_no_api_key(explainer_fixture, db_session, client):
    """
    Verify that when ANTHROPIC_API_KEY is not set, ExplainerNarrator safely falls
    back to TEMPLATE mode, generating deterministic sentences for English and Hindi.
    """
    app1 = explainer_fixture["app1"]
    token1 = explainer_fixture["token1"]

    # Ensure no API key in environment
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    try:
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Create a ValidationRun with 1 expired document finding
        val_run = ValidationRun(
            application_id=app1.id,
            status="COMPLETED",
            overall_status="BLOCKED",
            score=60.0,
            blocker_count=1,
        )
        db_session.add(val_run)
        db_session.commit()
        db_session.refresh(val_run)

        finding = ValidationFinding(
            run_id=val_run.id,
            rule_code="APH-2026-CH3-R07",
            rule_title="Fire & Life Safety NOC Validity",
            severity="BLOCKER",
            status="FAIL",
            reason="Fire & Life Safety NOC expired on 2026-11-11.",
            evidence_json=[{
                "document": "Fire & Life Safety NOC",
                "extracted": "2026-11-11",
            }],
            suggested_action="Upload a renewed certificate valid for at least 30 days.",
        )
        db_session.add(finding)
        db_session.commit()

        # 1. Test GET /api/institute/applications/{id}/why-failed in English
        res_en = client.get(
            f"/api/institute/applications/{app1.application_id}/why-failed?lang=en",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_en.status_code == 200, res_en.text
        data_en = res_en.json()

        assert "Application Blocked" in data_en["headline"]
        assert len(data_en["root_causes"]) == 1
        assert data_en["root_causes"][0]["cause_code"] == "EXPIRED_DOCUMENT"
        assert len(data_en["reasons"]) == 1
        # Check deterministic sentence structure matching prompt requirement:
        # "Your application cannot proceed because the Fire & Life Safety NOC expired on 2026-11-11 (Rule APH-2026-CH3-R07)..."
        assert "cannot proceed" in data_en["reasons"][0]["explanation"]
        assert "expired on 2026-11-11" in data_en["reasons"][0]["explanation"]
        assert "APH-2026-CH3-R07" in data_en["reasons"][0]["explanation"]
        assert "AI-generated decision support; final decisions rest with authorised AICTE officials." in data_en["disclaimer"]

        # 2. Test GET /api/institute/applications/{id}/why-failed in Hindi
        res_hi = client.get(
            f"/api/institute/applications/{app1.application_id}/why-failed?lang=hi",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert res_hi.status_code == 200, res_hi.text
        data_hi = res_hi.json()
        assert "आवेदन अवरुद्ध" in data_hi["headline"]
        assert "एआई-जनित निर्णय सहायता" in data_hi["disclaimer"]
        assert data_hi["lang"] == "hi"

        # Verify ValidationExplanation was persisted in database
        exp_record = (
            db_session.query(ValidationExplanation)
            .filter(ValidationExplanation.run_id == val_run.id)
            .first()
        )
        assert exp_record is not None
        assert exp_record.source == "TEMPLATE"
        assert exp_record.model is None

    finally:
        if old_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = old_key


# ==============================================================================
# TEST 4: WAIVER RULES (ADMIN CAN WAIVE, REVIEWER CAN ONLY ADD NOTES)
# ==============================================================================
def test_waiver_rules_and_notes(explainer_fixture, db_session, client):
    """
    Verify:
    1. ADMIN can waive a finding with mandatory reason -> is_waived becomes True
    2. REVIEWER can add a NOTE -> note recorded
    3. REVIEWER attempting to WAIVE returns 403 Forbidden
    4. Empty reason returns 400 Bad Request
    5. Original finding fields are NEVER altered
    6. All actions are audit logged in audit_logs table
    """
    app1 = explainer_fixture["app1"]
    admin_token = explainer_fixture["admin_token"]
    reviewer_token = explainer_fixture["reviewer_token"]

    val_run = ValidationRun(
        application_id=app1.id,
        status="COMPLETED",
        overall_status="BLOCKED",
        score=60.0,
        blocker_count=1,
    )
    db_session.add(val_run)
    db_session.commit()

    orig_rule_code = "APH-2026-CH3-R07"
    orig_severity = "BLOCKER"
    orig_reason = "Fire NOC expired on 2026-11-11."
    orig_action = "Upload renewed NOC."

    finding = ValidationFinding(
        run_id=val_run.id,
        rule_code=orig_rule_code,
        rule_title="Fire NOC Validity",
        severity=orig_severity,
        status="FAIL",
        reason=orig_reason,
        evidence_json=[{"extracted": "2026-11-11"}],
        suggested_action=orig_action,
        is_waived=False,
    )
    db_session.add(finding)
    db_session.commit()
    finding_id = finding.id

    # 1. REVIEWER adds a NOTE -> Success (200)
    res_note = client.post(
        f"/api/admin/applications/{app1.id}/findings/{orig_rule_code}/note",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"action": "NOTE", "reason": "Institute has submitted receipt of renewal application."},
    )
    assert res_note.status_code == 200, res_note.text
    note_data = res_note.json()
    assert note_data["success"] is True
    assert note_data["action"] == "NOTE"
    assert note_data["is_waived"] is False

    # Check FindingNote record
    notes = db_session.query(FindingNote).filter(FindingNote.finding_id == finding_id).all()
    assert len(notes) == 1
    assert notes[0].action == "NOTE"
    assert notes[0].author_role == "REVIEWER"

    # 2. REVIEWER attempts to WAIVE -> Forbidden (403)
    res_rev_waive = client.post(
        f"/api/admin/applications/{app1.id}/findings/{orig_rule_code}/note",
        headers={"Authorization": f"Bearer {reviewer_token}"},
        json={"action": "WAIVE", "reason": "Attempting waiver as reviewer."},
    )
    assert res_rev_waive.status_code == 403
    assert "Reviewers are not authorized to waive" in res_rev_waive.json()["detail"]

    # 3. Mandatory reason check -> Empty reason returns 400
    res_empty_reason = client.post(
        f"/api/admin/applications/{app1.id}/findings/{orig_rule_code}/note",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"action": "WAIVE", "reason": "   "},
    )
    assert res_empty_reason.status_code == 400

    # 4. ADMIN waives the finding -> Success (200)
    res_admin_waive = client.post(
        f"/api/admin/applications/{app1.id}/findings/{orig_rule_code}/note",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"action": "WAIVE", "reason": "Provisional exemption granted by Executive Committee."},
    )
    assert res_admin_waive.status_code == 200, res_admin_waive.text
    waive_data = res_admin_waive.json()
    assert waive_data["success"] is True
    assert waive_data["action"] == "WAIVE"
    assert waive_data["is_waived"] is True

    # 5. Verify original finding is NEVER altered
    db_session.refresh(finding)
    assert finding.rule_code == orig_rule_code
    assert finding.severity == orig_severity
    assert finding.status == "FAIL"  # Original status intact!
    assert finding.reason == orig_reason
    assert finding.suggested_action == orig_action
    # Only waiver metadata updated
    assert finding.is_waived is True
    assert finding.waiver_reason == "Provisional exemption granted by Executive Committee."
    assert finding.waived_at is not None

    # 6. Verify Audit Logs
    audit_entries = (
        db_session.query(AuditLog)
        .all()
    )
    actions = [a.action for a in audit_entries]
    assert "FINDING_NOTE" in actions
    assert "FINDING_WAIVE" in actions



# ==============================================================================
# TEST 5: ISOLATION AND STATS ENDPOINT
# ==============================================================================
def test_isolation_and_admin_stats(explainer_fixture, db_session, client):
    """
    Verify:
    1. Institute 1 user cannot access Institute 2's application why-failed endpoint (403 or 404)
    2. Institute user cannot access admin why-failed or waiver endpoints (403)
    3. Admin assessments stats endpoint aggregates common causes and most failed rules
    """
    app1 = explainer_fixture["app1"]
    app2 = explainer_fixture["app2"]
    token1 = explainer_fixture["token1"]
    token2 = explainer_fixture["token2"]
    admin_token = explainer_fixture["admin_token"]

    # 1. Institute 1 tries to access Institute 2's application
    res_iso = client.get(
        f"/api/institute/applications/{app2.application_id}/why-failed",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res_iso.status_code in (403, 404)

    # 2. Institute user tries to access admin endpoint
    res_admin_access = client.get(
        f"/api/admin/applications/{app1.id}/why-failed",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert res_admin_access.status_code == 403

    # 3. Test Admin Assessments Stats endpoint
    res_stats = client.get(
        "/api/admin/assessments/stats",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_stats.status_code == 200, res_stats.text
    stats_data = res_stats.json()
    assert "total_applications_evaluated" in stats_data
    assert "common_causes" in stats_data
    assert "most_failed_rules" in stats_data
    assert isinstance(stats_data["common_causes"], list)
