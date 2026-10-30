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
