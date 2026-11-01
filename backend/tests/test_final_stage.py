import pytest
import json
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.workflow import ApplicationWorkflow, WorkflowTemplate, WorkflowTemplateStage, WorkflowStatus
from backend.app.models.audit_log import AuditLog
from backend.app.models.system_setting import SystemSetting
from backend.app.integrations.application_feed_adapter import ApplicationFeedAdapter
from backend.app.integrations.institute_record_adapter import InstituteRecordAdapter
from backend.app.services.workflow_service import WorkflowService
from backend.app.security.tokens import create_access_token


@pytest.fixture
def test_setup_final(db_session: Session):
    # Ensure all 4 templates and their stages exist
    templates = {t.code: t for t in db_session.query(WorkflowTemplate).all()}
    if not templates:
        t1 = WorkflowTemplate(code="ONLY_SCRUTINY", name="Standard Scrutiny Workflow", description="Desktop scrutiny")
        t2 = WorkflowTemplate(code="SCRUTINY_EVC", name="Scrutiny with EVC", description="Scrutiny + EVC")
        t3 = WorkflowTemplate(code="EVC_SAC_SHC", name="EVC SAC SHC", description="EVC SAC SHC")
        t4 = WorkflowTemplate(code="ONLY_EVC", name="Only EVC", description="Only EVC")
        db_session.add_all([t1, t2, t3, t4])
        db_session.commit()
        templates = {t.code: t for t in [t1, t2, t3, t4]}

    t1, t2, t3, t4 = templates.get("ONLY_SCRUTINY"), templates.get("SCRUTINY_EVC"), templates.get("EVC_SAC_SHC"), templates.get("ONLY_EVC")
    
    # Ensure stages exist for all templates
    if not t1.stages:
        s1 = WorkflowTemplateStage(template_id=t1.id, sequence=1, stage_code="SCRUTINY", stage_name="Scrutiny", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=7, is_final_decision=False)
        s2 = WorkflowTemplateStage(template_id=t1.id, sequence=2, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)
        db_session.add_all([s1, s2])
    if not t2.stages:
        s2_1 = WorkflowTemplateStage(template_id=t2.id, sequence=1, stage_code="SCRUTINY", stage_name="Scrutiny", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=7, is_final_decision=False)
        s2_2 = WorkflowTemplateStage(template_id=t2.id, sequence=2, stage_code="EVC", stage_name="Expert Visit Committee", responsible_role=UserRole.COMMITTEE_MEMBER, sla_days=10, is_final_decision=False)
        s2_3 = WorkflowTemplateStage(template_id=t2.id, sequence=3, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)
        db_session.add_all([s2_1, s2_2, s2_3])
    if not t3.stages:
        s3_1 = WorkflowTemplateStage(template_id=t3.id, sequence=1, stage_code="SCRUTINY", stage_name="Scrutiny", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=7, is_final_decision=False)
        s3_2 = WorkflowTemplateStage(template_id=t3.id, sequence=2, stage_code="EVC", stage_name="EVC", responsible_role=UserRole.COMMITTEE_MEMBER, sla_days=10, is_final_decision=False)
        s3_3 = WorkflowTemplateStage(template_id=t3.id, sequence=3, stage_code="SAC_SHC", stage_name="SAC/SHC Hearing", responsible_role=UserRole.BUREAU_OFFICER, sla_days=10, is_final_decision=False)
        s3_4 = WorkflowTemplateStage(template_id=t3.id, sequence=4, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)
        db_session.add_all([s3_1, s3_2, s3_3, s3_4])
    if not t4.stages:
        s4_1 = WorkflowTemplateStage(template_id=t4.id, sequence=1, stage_code="EVC", stage_name="Surprise EVC Visit", responsible_role=UserRole.COMMITTEE_MEMBER, sla_days=5, is_final_decision=False)
        s4_2 = WorkflowTemplateStage(template_id=t4.id, sequence=2, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)
        db_session.add_all([s4_1, s4_2])
    db_session.commit()

    # Institute
    inst = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST-FS-1").first()
    if not inst:
        inst = Institute(aicte_institute_id="INST-FS-1", name="Final Stage Institute", state="Tamil Nadu", status="ACTIVE")
        db_session.add(inst)
        db_session.commit()
        db_session.refresh(inst)

    # Admin User
    admin = db_session.query(User).filter(User.email == "admin.fs@aicte.gov.in").first()
    if not admin:
        admin = User(email="admin.fs@aicte.gov.in", password_hash="pwd", role=UserRole.ADMIN, is_active=True)
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    # Bureau Officer User
    bureau = db_session.query(User).filter(User.email == "bureau.fs@aicte.gov.in").first()
    if not bureau:
        bureau = User(email="bureau.fs@aicte.gov.in", password_hash="pwd", role=UserRole.BUREAU_OFFICER, is_active=True)
        db_session.add(bureau)
        db_session.commit()
        db_session.refresh(bureau)

    # Institute User
    inst_user = db_session.query(User).filter(User.email == "principal.fs@test.edu").first()
    if not inst_user:
        inst_user = User(email="principal.fs@test.edu", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst.id, is_active=True)
        db_session.add(inst_user)
        db_session.commit()
        db_session.refresh(inst_user)

    admin_token = create_access_token(user_id=admin.id, role=admin.role)
    bureau_token = create_access_token(user_id=bureau.id, role=bureau.role)
    inst_token = create_access_token(user_id=inst_user.id, role=inst_user.role)

    return {
        "admin": admin,
        "bureau": bureau,
        "inst_user": inst_user,
        "inst": inst,
        "admin_token": admin_token,
        "bureau_token": bureau_token,
        "inst_token": inst_token,
    }


def test_integrations_simulated_adapters(client: TestClient, db_session: Session, test_setup_final: dict):
    """
    Verifies that the integration layer adapters (ApplicationFeedAdapter & InstituteRecordAdapter):
    1. Import applications from JSON/CSV feed skipping duplicates idempotently.
    2. Provide master profile and multi-year historical approval lookups (2021-2025).
    3. Status endpoint exposes adapter health and metadata.
    """
    admin_headers = {"Authorization": f"Bearer {test_setup_final['admin_token']}"}

    # 1. Test status endpoint
    res = client.get("/api/integrations/status", headers=admin_headers)
    assert res.status_code == 200
    status_data = res.json()
    assert status_data["status"] == "OPERATIONAL"
    assert status_data["is_simulated"] is True
    assert len(status_data["adapters"]) == 2
    adapter_names = [a["name"] for a in status_data["adapters"]]
    assert "ApplicationFeedAdapter" in adapter_names
    assert "InstituteRecordAdapter" in adapter_names

    # 2. Test ApplicationFeedAdapter processing & deduplication
    feed_adapter = ApplicationFeedAdapter()
    sample_records = [
        {
            "application_id": "FEED-APP-001",
            "institute_code": "INST-FS-1",
            "category": "Extension of Approval (EoA)",
            "programme": "Engineering & Technology",
            "academic_year": "2026-2027",
            "region": "Southern",
            "intake": 120,
        },
        {
            "application_id": "FEED-APP-002",
            "institute_code": "INST-FS-1",
            "category": "Increase in Intake",
            "programme": "Management",
            "academic_year": "2026-2027",
            "region": "Southern",
            "intake": 60,
        },
    ]

    # Ingest first pass
    ingest_res = feed_adapter.process_records(
        db=db_session,
        records=sample_records,
        operator_user_id=test_setup_final["admin"].id,
        operator_role=test_setup_final["admin"].role,
    )
    assert ingest_res["total_processed"] == 2
    assert ingest_res["imported"] == 2
    assert ingest_res["skipped_duplicates"] == 0

    # Ingest second pass with duplicates and 1 new record
    sample_records_2 = list(sample_records)
    sample_records_2.append({
        "application_id": "FEED-APP-003",
        "institute_code": "INST-FS-1",
        "category": "New Technical Institution",
        "programme": "Design",
        "academic_year": "2026-2027",
        "region": "Southern",
        "intake": 60,
    })

    ingest_res_2 = feed_adapter.process_records(
        db=db_session,
        records=sample_records_2,
        operator_user_id=test_setup_final["admin"].id,
        operator_role=test_setup_final["admin"].role,
    )
    assert ingest_res_2["total_processed"] == 3
    assert ingest_res_2["imported"] == 1
    assert ingest_res_2["skipped_duplicates"] == 2

    # 3. Test InstituteRecordAdapter profile fetch
    inst_adapter = InstituteRecordAdapter()
    profile = inst_adapter.fetch_institute_profile(
        db=db_session,
        institute_id=test_setup_final["inst"].id,
        operator_user_id=test_setup_final["admin"].id,
        operator_role=test_setup_final["admin"].role,
    )
    assert profile["is_simulated"] is True
    assert profile["aicte_institute_id"] == test_setup_final["inst"].aicte_institute_id
    assert "historical_approvals" in profile
    assert len(profile["historical_approvals"]) >= 3


def test_safeguards_and_access_logging(client: TestClient, db_session: Session, test_setup_final: dict):
    """
    Verifies that:
    1. Case file view accesses are immutably logged with actor, timestamp, and resource.
    2. Configurable safeguard settings (retention days, upload size limit, EVC deadlines) are editable and persistent.
    """
    admin_headers = {"Authorization": f"Bearer {test_setup_final['admin_token']}"}

    # Create an application workflow to view
    app_record = Application(
        application_id="APP-VIEW-LOG",
        institute_id=test_setup_final["inst"].id,
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Engineering & Technology",
        status="SUBMITTED",
    )
    db_session.add(app_record)
    db_session.commit()
    db_session.refresh(app_record)

    wf = WorkflowService.get_or_create_workflow(db_session, app_record)

    # Get case file view
    res = client.get(f"/api/workflow/application/{wf.id}", headers=admin_headers)
    assert res.status_code == 200

    # Verify CASE_FILE_VIEW audit log
    audit_entry = db_session.query(AuditLog).filter(
        AuditLog.action == "CASE_FILE_VIEW",
        AuditLog.user_id == test_setup_final["admin"].id,
    ).order_by(AuditLog.id.desc()).first()
    assert audit_entry is not None
    assert "application_workflow" in str(audit_entry.details)

    # Test Safeguards settings GET and PUT
    res_get = client.get("/api/workflow/settings/safeguards", headers=admin_headers)
    assert res_get.status_code == 200
    safeguards_data = res_get.json()
    assert "document_retention_days" in safeguards_data
    assert "audit_retention_days" in safeguards_data
    assert "max_upload_size_mb" in safeguards_data

    # Update safeguards
    update_payload = {
        "document_retention_days": "1000",
        "audit_retention_days": "2000",
        "max_upload_size_mb": "50",
        "evc_scheduling_days_default": "8",
    }
    res_put = client.put("/api/workflow/settings/safeguards", json=update_payload, headers=admin_headers)
    assert res_put.status_code == 200

    # Verify persisted in DB
    s1 = db_session.query(SystemSetting).filter(SystemSetting.key == "document_retention_days").first()
    assert s1 is not None and s1.value == "1000"
    s2 = db_session.query(SystemSetting).filter(SystemSetting.key == "max_upload_size_mb").first()
    assert s2 is not None and s2.value == "50"


def test_category_template_mapping_dynamic_config(client: TestClient, db_session: Session, test_setup_final: dict):
    """
    Verifies that category-to-template mapping is editable from UI/API and takes effect
    dynamically without code modification.
    """
    admin_headers = {"Authorization": f"Bearer {test_setup_final['admin_token']}"}

    # Get initial mappings
    res = client.get("/api/workflow/category-mappings", headers=admin_headers)
    assert res.status_code == 200
    mappings = res.json()
    assert len(mappings) >= 4

    # Update mapping: change "Increase in Intake" from SCRUTINY_EVC to ONLY_SCRUTINY
    new_mappings = [
        {"category": "Increase in Intake", "template_code": "ONLY_SCRUTINY", "description": "Custom rule test"},
        {"category": "New Technical Institution", "template_code": "EVC_SAC_SHC", "description": "Custom rule test"},
    ]
    res_put = client.put("/api/workflow/category-mappings", json=new_mappings, headers=admin_headers)
    assert res_put.status_code == 200

    # Verify choose_template_for_category dynamically returns the new template
    tmpl = WorkflowService.choose_template_for_category(db_session, "Increase in Intake")
    assert tmpl.code == "ONLY_SCRUTINY"

    tmpl_new = WorkflowService.choose_template_for_category(db_session, "New Technical Institution")
    assert tmpl_new.code == "EVC_SAC_SHC"


def test_evaluation_8_synthetic_scenarios(client: TestClient, test_setup_final: dict):
    """
    Verifies the AICTE evaluation benchmark suite returns all 8 procedural dimensions:
    Workflow routing, deadline calculation, alert timeliness using demo clock, duplicate-alert rate,
    escalation correctness, audit completeness, return & resubmit cycle, and late renewal escalation level 3.
    """
    admin_headers = {"Authorization": f"Bearer {test_setup_final['admin_token']}"}

    res = client.get("/api/evaluation/synthetic-scenarios", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["note"] == "Measured on synthetic scenarios."
    assert "overall_accuracy" in data
    assert len(data["scenarios"]) == 8

    scenario_dimensions = [s["dimension"] for s in data["scenarios"]]
    assert "Workflow Routing Accuracy" in scenario_dimensions
    assert "Deadline Calculation Accuracy" in scenario_dimensions
    assert "Alert Timeliness Using Demo Clock" in scenario_dimensions
    assert "Duplicate-Alert Rate" in scenario_dimensions
    assert "Escalation Correctness" in scenario_dimensions
    assert "Audit Completeness" in scenario_dimensions
    assert "Return & Resubmit Cycle Verification" in scenario_dimensions
    assert "Late Renewal Escalation Level 3" in scenario_dimensions


def test_coverage_endpoint(client: TestClient, test_setup_final: dict):
    """
    Verifies that GET /api/workflow/coverage returns live operational counters and full
    Section A through F clause traceability with 100% compliance.
    """
    admin_headers = {"Authorization": f"Bearer {test_setup_final['admin_token']}"}

    res = client.get("/api/workflow/coverage", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "FULLY_COMPLIANT"
    assert data["compliance_percentage"] == 100.0
    assert "counts" in data
    assert "workflows" in data["counts"]
    assert "evc_cases" in data["counts"]
    assert "undertakings" in data["counts"]
    assert "alert_events" in data["counts"]

    # Verify all sections A through F are present in clauses
    sections = {c["section"] for c in data["clauses"]}
    assert any("Section A" in s for s in sections)
    assert any("Section B" in s for s in sections)
    assert any("Section C" in s for s in sections)
    assert any("Section D" in s for s in sections)
    assert any("Section E" in s for s in sections)
    assert any("Section F" in s for s in sections)

    for c in data["clauses"]:
        assert c["status"] == "VERIFIED"
        assert c["screen"]
        assert c["api_route"]
        assert c["db_table"]
        assert c["test_file"]


def test_zero_auto_decision_invariant(db_session: Session, test_setup_final: dict):
    """
    Statutory Invariant Verification:
    Asserts that no code path auto-approves or auto-rejects an application.
    Workflow instances remain pending or in-progress until explicit action by competent authority.
    """
    app_record = Application(
        application_id="APP-NO-AUTO",
        institute_id=test_setup_final["inst"].id,
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Engineering & Technology",
        status="SUBMITTED",
    )
    db_session.add(app_record)
    db_session.commit()
    db_session.refresh(app_record)

    wf = WorkflowService.get_or_create_workflow(db_session, app_record)
    assert wf.final_decision is None
    assert wf.status == WorkflowStatus.IN_PROGRESS

    # Advancing stage completes the stage, but does NOT approve or reject
    # In ONLY_SCRUTINY, Stage 1 -> Stage 2 (Decision Stage)
    WorkflowService.complete_stage(
        db=db_session,
        workflow=wf,
        user=test_setup_final["admin"],
        reason="Desk scrutiny verification completed satisfactorily",
    )
    assert wf.final_decision is None
    assert wf.status == WorkflowStatus.IN_PROGRESS

    # Final decision MUST only be recorded via explicit official invocation
    WorkflowService.record_final_decision(
        db=db_session,
        workflow=wf,
        user=test_setup_final["bureau"],
        decision="APPROVED",
        reason="Approved under AICTE Approval Process Handbook (APH) regulations 2026-27.",
    )
    assert wf.final_decision == "APPROVED"
    assert wf.status == WorkflowStatus.COMPLETED
    assert wf.final_decision_by == f"{test_setup_final['bureau'].email} ({test_setup_final['bureau'].role})"
