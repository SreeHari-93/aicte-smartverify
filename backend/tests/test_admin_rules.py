import pytest
from fastapi.testclient import TestClient

from backend.app.models.user import User, UserRole
from backend.app.models.document_type import DocumentType
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.rule import Rule, RuleVersion, RuleSet
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token


def get_auth_cookie(user: User):
    role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)
    return {"aicte_access_token": token}


def test_rbac_admin_routes(client: TestClient, seed_test_data):
    inst_user = seed_test_data["inst_user"]
    inst_cookies = get_auth_cookie(inst_user)

    # Institute user attempting to access admin endpoints should receive 403 Forbidden
    res = client.get("/api/v1/admin/rules", cookies=inst_cookies)
    assert res.status_code == 403

    res2 = client.post("/api/v1/admin/document-types", json={"code": "TEST_DOC", "name": "Test"}, cookies=inst_cookies)
    assert res2.status_code == 403


def test_document_type_crud(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # 1. Create DocumentType
    payload = {
        "code": "SOLAR_NOC",
        "name": "Solar Energy NOC",
        "description": "Green campus solar installation certificate",
        "issuing_authority": "Ministry of New & Renewable Energy",
        "accepted_formats": ["PDF"],
        "max_size_mb": 10,
        "has_expiry": True,
        "default_validity_months": 24,
        "verification_method": "QR",
        "extraction_schema": [
            {"key": "capacity_kw", "label": "Capacity in kW", "type": "number", "required": True}
        ],
        "keywords": ["solar", "renewable", "energy"],
        "is_active": True,
    }
    create_res = client.post("/api/v1/admin/document-types", json=payload, cookies=cookies)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["code"] == "SOLAR_NOC"

    # 2. Get DocumentType
    get_res = client.get("/api/v1/admin/document-types/SOLAR_NOC", cookies=cookies)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Solar Energy NOC"

    # 3. Update DocumentType
    update_res = client.put(
        "/api/v1/admin/document-types/SOLAR_NOC",
        json={"name": "Renewable Solar Energy NOC", "max_size_mb": 15},
        cookies=cookies,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Renewable Solar Energy NOC"
    assert update_res.json()["max_size_mb"] == 15

    # 4. Deactivate (soft delete)
    del_res = client.delete("/api/v1/admin/document-types/SOLAR_NOC", cookies=cookies)
    assert del_res.status_code == 200

    check_res = client.get("/api/v1/admin/document-types/SOLAR_NOC", cookies=cookies)
    assert check_res.json()["is_active"] is False


def test_category_and_checklist_crud(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # 1. Create Category
    cat_payload = {
        "code": "TEST_EOA",
        "name": "Test EoA Category",
        "description": "Testing category flow",
    }
    cat_res = client.post("/api/v1/admin/categories", json=cat_payload, cookies=cookies)
    assert cat_res.status_code == 201
    cat_data = cat_res.json()

    # 2. Create DocumentType for checklist
    dt_res = client.post(
        "/api/v1/admin/document-types",
        json={"code": "CHK_DOC_1", "name": "Checklist Test Doc 1"},
        cookies=cookies,
    )
    assert dt_res.status_code == 201
    doc_type_id = dt_res.json()["id"]

    # 3. Add to checklist
    item_payload = {
        "document_type_id": doc_type_id,
        "is_mandatory": True,
        "min_validity_days_remaining": 30,
        "display_order": 1,
        "help_text": "Must be valid for 30 days.",
    }
    item_res = client.post("/api/v1/admin/checklists/TEST_EOA/items", json=item_payload, cookies=cookies)
    assert item_res.status_code == 201
    assert item_res.json()["is_mandatory"] is True

    # 4. Fetch checklist
    list_res = client.get("/api/v1/admin/checklists/TEST_EOA", cookies=cookies)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_rule_crud_optimistic_locking_and_versioning(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # 1. Create Rule
    rule_payload = {
        "code": "TEST-RULE-001",
        "title": "Solar Installation Verification",
        "description": "Requires active solar NOC",
        "handbook_ref": "Appendix 5.1",
        "rule_type": "INFRASTRUCTURE",
        "severity": "MAJOR",
        "mandatory": True,
        "applies_to_categories": ["EOA"],
        "definition": {
            "type": "DOCUMENT_REQUIRED",
            "document": "SOLAR_NOC",
            "min_validity_days": 30,
        },
        "status": "DRAFT",
    }
    create_res = client.post("/api/v1/admin/rules", json=rule_payload, cookies=cookies)
    assert create_res.status_code == 201
    rule_data = create_res.json()
    assert rule_data["code"] == "TEST-RULE-001"
    assert rule_data["current_version"] == 1

    # 2. Optimistic Concurrency Conflict (pass incorrect expected_version)
    conflict_res = client.put(
        "/api/v1/admin/rules/TEST-RULE-001",
        json={"expected_version": 99, "title": "Conflict Attempt"},
        cookies=cookies,
    )
    assert conflict_res.status_code == 409
    assert "Version conflict" in conflict_res.json()["detail"]

    # 3. Successful Update with correct expected_version
    update_res = client.put(
        "/api/v1/admin/rules/TEST-RULE-001",
        json={
            "expected_version": 1,
            "change_note": "Promoted to PUBLISHED and updated title",
            "title": "Mandatory Solar Installation Verification",
            "status": "PUBLISHED",
        },
        cookies=cookies,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["current_version"] == 2
    assert updated_data["title"] == "Mandatory Solar Installation Verification"

    # 4. Verify Version History Snapshot
    detail_res = client.get("/api/v1/admin/rules/TEST-RULE-001", cookies=cookies)
    assert detail_res.status_code == 200
    versions = detail_res.json()["versions"]
    assert len(versions) == 1
    assert versions[0]["version_no"] == 1
    assert versions[0]["snapshot"]["title"] == "Solar Installation Verification"


def test_rule_simulation_and_validation(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # 1. Validate Definition Syntax
    valid_syntax = {
        "definition": {
            "type": "FIELD_REQUIRED",
            "field": "application.academic_year",
        }
    }
    val_res = client.post("/api/v1/admin/rules/validate-definition", json=valid_syntax, cookies=cookies)
    assert val_res.status_code == 200
    assert val_res.json()["valid"] is True

    # 2. Simulate Rule
    sim_payload = {
        "definition": {
            "type": "NUMERIC_THRESHOLD",
            "field": "institute.nirf_rank",
            "operator": "<=",
            "value": 100,
        },
        "context": {
            "institute": {"nirf_rank": 73},
        },
        "rule_meta": {
            "code": "SIM-TEST-01",
            "title": "Top 100 NIRF Verification",
            "severity": "MINOR",
        },
    }
    sim_res = client.post("/api/v1/admin/rules/simulate", json=sim_payload, cookies=cookies)
    assert sim_res.status_code == 200
    assert sim_res.json()["passed"] is True
    assert sim_res.json()["rule_code"] == "SIM-TEST-01"


def test_ruleset_publish_and_rollback(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # Publish RuleSet
    pub_res = client.post(
        "/api/v1/admin/rulesets/publish",
        json={"name": "Test APH 2026", "version_label": "v1.0-test"},
        cookies=cookies,
    )
    assert pub_res.status_code == 200
    ruleset_data = pub_res.json()
    assert ruleset_data["name"] == "Test APH 2026"
    assert ruleset_data["status"] == "ACTIVE"

    # List RuleSets
    list_res = client.get("/api/v1/admin/rulesets", cookies=cookies)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_rule_draft_isolation_live_validations(client: TestClient, seed_test_data, db_session):
    admin_user = seed_test_data["admin_user"]
    inst_user = seed_test_data["inst_user"]
    institute = seed_test_data["institute"]
    admin_cookies = get_auth_cookie(admin_user)
    inst_cookies = get_auth_cookie(inst_user)

    from backend.app.models.application import Application
    application = Application(
        institute_id=institute.id,
        application_id="APP-DRAFT-ISO-01",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="SUBMITTED",
    )
    db_session.add(application)
    db_session.commit()
    db_session.refresh(application)

    # 1. First publish initial ruleset
    client.post(
        "/api/v1/admin/rulesets/publish",
        json={"name": "Initial Baseline Ruleset", "version_label": "v1.0-baseline"},
        cookies=admin_cookies,
    )

    # 2. Run live validation on application as institute
    val_res1 = client.post(
        f"/api/v1/institute/applications/{application.id}/validate",
        cookies=inst_cookies,
    )
    assert val_res1.status_code in [200, 201]
    findings1 = val_res1.json().get("findings", [])
    rule_codes_1 = [f["rule_code"] for f in findings1]

    # 3. Admin creates a brand new DRAFT rule that would FAIL if executed
    draft_rule_payload = {
        "code": "DRAFT-FAIL-TEST",
        "title": "Strict Draft Only Condition",
        "rule_type": "NUMERIC_THRESHOLD",
        "severity": "BLOCKER",
        "mandatory": True,
        "definition": {
            "type": "NUMERIC_THRESHOLD",
            "field": "institute.nirf_rank",
            "operator": "==",
            "value": 99999,  # This would fail
        },
        "status": "DRAFT",
    }
    create_draft_res = client.post("/api/v1/admin/rules", json=draft_rule_payload, cookies=admin_cookies)
    assert create_draft_res.status_code == 201
    assert create_draft_res.json()["status"] == "DRAFT"

    # 4. Run live validation again -> Verify DRAFT rule has ZERO effect on live validation (draft isolation!)
    val_res2 = client.post(
        f"/api/v1/institute/applications/{application.id}/validate",
        cookies=inst_cookies,
    )
    assert val_res2.status_code in [200, 201]
    findings2 = val_res2.json().get("findings", [])
    rule_codes_2 = [f["rule_code"] for f in findings2]
    assert "DRAFT-FAIL-TEST" not in rule_codes_2, "Draft rule must not affect live validations!"

    # 5. Check Preview Publish: it should show DRAFT-FAIL-TEST as pending to publish
    preview_res = client.get("/api/v1/admin/rulesets/preview-publish", cookies=admin_cookies)
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    new_rule_codes = [r["code"] for r in preview_data["new_rules"]]
    assert "DRAFT-FAIL-TEST" in new_rule_codes

    # 6. Now Admin Publishes the ruleset
    pub_res = client.post(
        "/api/v1/admin/rulesets/publish",
        json={"name": "Updated Live Ruleset", "version_label": "v2.0-live"},
        cookies=admin_cookies,
    )
    assert pub_res.status_code == 200

    # 7. Now live validation includes the newly published rule
    val_res3 = client.post(
        f"/api/v1/institute/applications/{application.id}/validate",
        cookies=inst_cookies,
    )
    assert val_res3.status_code in [200, 201]
    findings3 = val_res3.json().get("findings", [])
    rule_codes_3 = [f["rule_code"] for f in findings3]
    assert "DRAFT-FAIL-TEST" in rule_codes_3, "Published rule must now be included in live validation!"


def test_delete_rule_draft_vs_published(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    admin_cookies = get_auth_cookie(admin_user)

    # 1. Create a DRAFT rule
    payload = {
        "code": "DELETABLE-DRAFT",
        "title": "A draft rule meant to be deleted",
        "rule_type": "GENERAL",
        "severity": "INFO",
        "mandatory": False,
        "status": "DRAFT",
    }
    client.post("/api/v1/admin/rules", json=payload, cookies=admin_cookies)

    # 2. Deleting a DRAFT rule should succeed with 200
    del_draft_res = client.delete("/api/v1/admin/rules/DELETABLE-DRAFT", cookies=admin_cookies)
    assert del_draft_res.status_code == 200
    assert "deleted successfully" in del_draft_res.json()["message"]

    # 3. Create a PUBLISHED rule
    payload_pub = {
        "code": "PUBLISHED-NO-DELETE",
        "title": "A published rule that cannot be deleted",
        "rule_type": "GENERAL",
        "severity": "MAJOR",
        "mandatory": True,
        "status": "PUBLISHED",
    }
    client.post("/api/v1/admin/rules", json=payload_pub, cookies=admin_cookies)

    # 4. Attempting to delete a PUBLISHED rule should fail with 400
    del_pub_res = client.delete("/api/v1/admin/rules/PUBLISHED-NO-DELETE", cookies=admin_cookies)
    assert del_pub_res.status_code == 400
    assert "Only DRAFT rules can be deleted" in del_pub_res.json()["detail"]


def test_rule_toggle_active_and_diff(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    admin_cookies = get_auth_cookie(admin_user)

    # 1. Create Rule
    code = "DIFF-TEST-RULE"
    client.post(
        "/api/v1/admin/rules",
        json={"code": code, "title": "Initial Title", "severity": "INFO", "status": "DRAFT"},
        cookies=admin_cookies,
    )

    # 2. Toggle active state
    toggle_res = client.patch(f"/api/v1/admin/rules/{code}/toggle-active", cookies=admin_cookies)
    assert toggle_res.status_code == 200
    assert toggle_res.json()["is_active"] is False

    # Toggle back
    toggle_res2 = client.patch(f"/api/v1/admin/rules/{code}/toggle-active", cookies=admin_cookies)
    assert toggle_res2.status_code == 200
    assert toggle_res2.json()["is_active"] is True

    # 3. Update Rule to Version 2
    update_res = client.put(
        f"/api/v1/admin/rules/{code}",
        json={"expected_version": 1, "title": "Updated Title For Diff", "severity": "BLOCKER"},
        cookies=admin_cookies,
    )
    assert update_res.status_code == 200
    assert update_res.json()["current_version"] == 2

    # 4. Check Diff between version 1 and 2
    diff_res = client.get(f"/api/v1/admin/rules/{code}/diff?v1=1&v2=2", cookies=admin_cookies)
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["rule_code"] == code
    assert "title" in diff_data["differences"]
    assert diff_data["differences"]["title"]["from"] == "Initial Title"
    assert diff_data["differences"]["title"]["to"] == "Updated Title For Diff"


def test_checklist_assignment_and_document_type_fields(client: TestClient, seed_test_data):
    admin_user = seed_test_data["admin_user"]
    admin_cookies = get_auth_cookie(admin_user)

    # Ensure category EOA exists
    client.post(
        "/api/v1/admin/categories",
        json={"code": "EOA", "name": "Extension of Approval"},
        cookies=admin_cookies,
    )

    # 1. Create document type with authority adapter and statutory verification
    doc_res = client.post(
        "/api/v1/admin/document-types",
        json={
            "code": "FIRE_SAFETY_NOC",
            "name": "State Fire Safety Certificate",
            "authority_adapter": "FIRE_AUTHORITY",
            "statutory_verification_applies": True,
            "verification_method": "API",
        },
        cookies=admin_cookies,
    )
    assert doc_res.status_code == 201
    doc_data = doc_res.json()
    assert doc_data["authority_adapter"] == "FIRE_AUTHORITY"
    assert doc_data["statutory_verification_applies"] is True
    doc_id = doc_data["id"]

    # 2. Add checklist item with institute_type and min_count
    item_res = client.post(
        "/api/v1/admin/checklists/EOA/items",
        json={
            "document_type_id": doc_id,
            "institute_type": "ENGINEERING",
            "min_count": 2,
            "is_mandatory": True,
            "min_validity_days_remaining": 60,
        },
        cookies=admin_cookies,
    )
    assert item_res.status_code == 201
    item_data = item_res.json()
    assert item_data["institute_type"] == "ENGINEERING"
    assert item_data["min_count"] == 2


def test_admin_applications_and_audit_logs(client: TestClient, seed_test_data, db_session):
    admin_user = seed_test_data["admin_user"]
    inst_user = seed_test_data["inst_user"]
    institute = seed_test_data["institute"]
    admin_cookies = get_auth_cookie(admin_user)
    inst_cookies = get_auth_cookie(inst_user)

    from backend.app.models.application import Application
    app = Application(
        institute_id=institute.id,
        application_id="APP-TEST-999",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="SUBMITTED",
    )
    db_session.add(app)
    db_session.commit()

    # 1. Admin lists applications
    app_res = client.get("/api/v1/admin/applications", cookies=admin_cookies)
    assert app_res.status_code == 200
    assert len(app_res.json()) >= 1

    # 2. Trigger an action that creates an audit log
    client.post(
        "/api/v1/admin/rules",
        json={"code": "AUDIT-LOG-RULE", "title": "Audit Test", "status": "DRAFT"},
        cookies=admin_cookies,
    )

    # 3. Admin lists audit logs
    audit_res = client.get("/api/v1/admin/audit-logs", cookies=admin_cookies)
    assert audit_res.status_code == 200
    assert len(audit_res.json()) >= 1

    # 4. Institute user gets 403 on audit logs
    inst_audit_res = client.get("/api/v1/admin/audit-logs", cookies=inst_cookies)
    assert inst_audit_res.status_code == 403
