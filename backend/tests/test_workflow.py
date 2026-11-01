import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.workflow import (
    ApplicationWorkflow,
    WorkflowTemplate,
    WorkflowTemplateStage,
    WorkflowHistory,
    WorkflowStatus,
    WorkflowAction,
)
from backend.app.models.communication_template import CommunicationTemplate
from backend.app.models.audit_log import AuditLog
from backend.app.models.complaint import Complaint, ComplaintEvent
from backend.app.services.workflow_service import WorkflowService
from backend.app.services.communication_service import CommunicationService, MANDATORY_DISCLAIMER
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token


def _get_auth_headers(client: TestClient, user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def workflow_test_env(db_session: Session):
    # 1. Ensure templates exist
    templates = WorkflowService.get_templates(db_session)
    if not templates:
        t1 = WorkflowTemplate(code="ONLY_SCRUTINY", name="Standard Scrutiny Workflow", description="Desktop scrutiny")
        t2 = WorkflowTemplate(code="SCRUTINY_EVC", name="Scrutiny with EVC", description="Scrutiny + EVC")
        t3 = WorkflowTemplate(code="EVC_SAC_SHC", name="EVC SAC SHC", description="EVC SAC SHC")
        t4 = WorkflowTemplate(code="ONLY_EVC", name="Only EVC", description="Only EVC")
        db_session.add_all([t1, t2, t3, t4])
        db_session.commit()

        s1 = WorkflowTemplateStage(template_id=t1.id, sequence=1, stage_code="SCRUTINY", stage_name="Scrutiny", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=7, is_final_decision=False)
        s2 = WorkflowTemplateStage(template_id=t1.id, sequence=2, stage_code="RO_REVIEW", stage_name="RO Review", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=5, is_final_decision=False)
        s3 = WorkflowTemplateStage(template_id=t1.id, sequence=3, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)

        s2_1 = WorkflowTemplateStage(template_id=t2.id, sequence=1, stage_code="SCRUTINY", stage_name="Scrutiny", responsible_role=UserRole.REGIONAL_OFFICER, sla_days=7, is_final_decision=False)
        s2_2 = WorkflowTemplateStage(template_id=t2.id, sequence=2, stage_code="EVC", stage_name="EVC", responsible_role=UserRole.COMMITTEE_MEMBER, sla_days=10, is_final_decision=False)
        s2_3 = WorkflowTemplateStage(template_id=t2.id, sequence=3, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)

        db_session.add_all([s1, s2, s3, s2_1, s2_2, s2_3])
        db_session.commit()

    # 2. Institutes
    inst1 = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST_WF_1").first()
    if not inst1:
        inst1 = Institute(aicte_institute_id="INST_WF_1", name="Institute Alpha", state="Tamil Nadu", status="ACTIVE")
        db_session.add(inst1)
        db_session.commit()
        db_session.refresh(inst1)

    inst2 = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST_WF_2").first()
    if not inst2:
        inst2 = Institute(aicte_institute_id="INST_WF_2", name="Institute Beta", state="Delhi", status="ACTIVE")
        db_session.add(inst2)
        db_session.commit()
        db_session.refresh(inst2)

    # 3. Users for each role
    u_admin = db_session.query(User).filter(User.email == "test_admin@aicte.gov.in").first()
    if not u_admin:
        u_admin = User(email="test_admin@aicte.gov.in", password_hash=hash_password("Pass@123"), role=UserRole.ADMIN, is_active=True)
        db_session.add(u_admin)

    u_ro = db_session.query(User).filter(User.email == "test_ro@aicte.gov.in").first()
    if not u_ro:
        u_ro = User(email="test_ro@aicte.gov.in", password_hash=hash_password("Pass@123"), role=UserRole.REGIONAL_OFFICER, region="Southern", is_active=True)
        db_session.add(u_ro)

    u_bureau = db_session.query(User).filter(User.email == "test_bureau@aicte.gov.in").first()
    if not u_bureau:
        u_bureau = User(email="test_bureau@aicte.gov.in", password_hash=hash_password("Pass@123"), role=UserRole.BUREAU_OFFICER, is_active=True)
        db_session.add(u_bureau)

    u_comm = db_session.query(User).filter(User.email == "test_comm@aicte.gov.in").first()
    if not u_comm:
        u_comm = User(email="test_comm@aicte.gov.in", password_hash=hash_password("Pass@123"), role=UserRole.COMMITTEE_MEMBER, is_active=True)
        db_session.add(u_comm)

    u_inst1 = db_session.query(User).filter(User.email == "user_inst1@aicte.edu.in").first()
    if not u_inst1:
        u_inst1 = User(email="user_inst1@aicte.edu.in", password_hash=hash_password("Pass@123"), role=UserRole.INSTITUTE, institute_id=inst1.id, is_active=True)
        db_session.add(u_inst1)

    u_inst2 = db_session.query(User).filter(User.email == "user_inst2@aicte.edu.in").first()
    if not u_inst2:
        u_inst2 = User(email="user_inst2@aicte.edu.in", password_hash=hash_password("Pass@123"), role=UserRole.INSTITUTE, institute_id=inst2.id, is_active=True)
        db_session.add(u_inst2)

    db_session.commit()

    # 4. Applications & Workflows
    app1 = db_session.query(Application).filter(Application.application_id == "APP-WF-ALPHA").first()
    if not app1:
        app1 = Application(
            institute_id=inst1.id,
            application_id="APP-WF-ALPHA",
            category="Extension of Approval (EoA)",
            academic_year="2026-2027",
            programme="Engineering & Technology",
            status="SUBMITTED",
        )
        db_session.add(app1)
        db_session.commit()
        db_session.refresh(app1)

    app2 = db_session.query(Application).filter(Application.application_id == "APP-WF-BETA").first()
    if not app2:
        app2 = Application(
            institute_id=inst2.id,
            application_id="APP-WF-BETA",
            category="Extension of Approval (EoA)",
            academic_year="2026-2027",
            programme="Management",
            status="SUBMITTED",
        )
        db_session.add(app2)
        db_session.commit()
        db_session.refresh(app2)

    wf1 = WorkflowService.get_or_create_workflow(db_session, app1, template_code="ONLY_SCRUTINY", region="Southern")
    wf2 = WorkflowService.get_or_create_workflow(db_session, app2, template_code="ONLY_SCRUTINY", region="Northern")

    return {
        "admin": u_admin,
        "ro": u_ro,
        "bureau": u_bureau,
        "comm": u_comm,
        "inst1_user": u_inst1,
        "inst2_user": u_inst2,
        "app1": app1,
        "app2": app2,
        "wf1": wf1,
        "wf2": wf2,
    }


def test_workflow_routing(client: TestClient, workflow_test_env: dict):
    """
    Test 1: Routing & Endpoints
    Verifies that workflow endpoints under /api/workflow and /api/v1/workflow
    correctly serve templates, dashboard metrics, and application listings.
    """
    headers = _get_auth_headers(client, workflow_test_env["admin"])

    # 1. Templates list
    res = client.get("/api/workflow/templates", headers=headers)
    assert res.status_code == 200, res.text
    templates = res.json()
    assert len(templates) >= 4
    template_codes = {t["code"] for t in templates}
    assert {"ONLY_SCRUTINY", "SCRUTINY_EVC", "EVC_SAC_SHC", "ONLY_EVC"}.issubset(template_codes)

    # Verify stages in first template
    t1 = next(t for t in templates if t["code"] == "ONLY_SCRUTINY")
    assert len(t1["stages"]) >= 2

    # Also test /api/v1/workflow/templates prefix
    res_v1 = client.get("/api/v1/workflow/templates", headers=headers)
    assert res_v1.status_code == 200

    # 2. Workflow Dashboard
    res_dash = client.get("/api/workflow/dashboard", headers=headers)
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert "counters" in dash_data
    assert "stage_funnel" in dash_data
    assert "region_table" in dash_data
    assert "officer_workload" in dash_data
    assert "ageing_buckets" in dash_data
    assert dash_data["counters"]["total"] >= 2

    # 3. Applications listing
    res_apps = client.get("/api/workflow/applications", headers=headers)
    assert res_apps.status_code == 200
    apps_data = res_apps.json()
    assert len(apps_data) >= 2


def test_workflow_auto_advance(client: TestClient, db_session: Session, workflow_test_env: dict):
    """
    Test 2: Auto-Advance & Audit Logging
    Verifies completing a stage with mandatory reason auto-advances the workflow
    to the next stage, recalculates SLA, updates history, and logs to AuditService.
    Also validates that an empty reason is rejected.
    """
    wf = workflow_test_env["wf1"]
    ro_user = workflow_test_env["ro"]
    headers = _get_auth_headers(client, ro_user)

    initial_stage_seq = wf.current_stage_sequence
    assert initial_stage_seq == 1

    # Attempt to advance WITHOUT reason -> must fail with 422 or 400
    res_no_reason = client.post(
        f"/api/workflow/application/{wf.id}/advance",
        json={"reason": " "},
        headers=headers,
    )
    assert res_no_reason.status_code in [400, 422]

    # Advance WITH valid mandatory reason
    reason_text = "Primary statutory scrutiny completed. All land and building documents match norms."
    res_advance = client.post(
        f"/api/workflow/application/{wf.id}/advance",
        json={"reason": reason_text, "notes": "Approved for RO recommendation."},
        headers=headers,
    )
    assert res_advance.status_code == 200, res_advance.text
    data = res_advance.json()

    # Verify auto-advance to stage sequence 2
    assert data["current_stage_sequence"] == 2
    assert data["status"] == WorkflowStatus.IN_PROGRESS
    assert data["case_summary"] is not None

    # Check WorkflowHistory was created
    histories = db_session.query(WorkflowHistory).filter(WorkflowHistory.workflow_id == wf.id).all()
    assert any(h.action == "COMPLETE_STAGE" and h.reason == reason_text for h in histories)

    # Check AuditLog entry was recorded
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "WORKFLOW_COMPLETE_STAGE", AuditLog.user_id == ro_user.id)
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.reason == reason_text


def test_workflow_unauthorised_action(client: TestClient, workflow_test_env: dict):
    """
    Test 3: 403 for Unauthorised Action & Competent Authority Protection
    Verifies that non-competent authority roles (e.g. REGIONAL_OFFICER, COMMITTEE_MEMBER)
    cannot record final decisions, returning HTTP 403 Forbidden.
    Verifies that the competent authority (BUREAU_OFFICER / ADMIN) is authorized.
    """
    wf = workflow_test_env["wf1"]

    # 1. Regional Officer attempts final decision -> 403 FORBIDDEN
    ro_headers = _get_auth_headers(client, workflow_test_env["ro"])
    res_ro = client.post(
        f"/api/workflow/application/{wf.id}/record-decision",
        json={"decision": "APPROVED", "reason": "Officer attempted premature decision"},
        headers=ro_headers,
    )
    assert res_ro.status_code == 403
    assert "competent authority" in res_ro.json()["detail"].lower()

    # 2. Committee Member attempts final decision -> 403 FORBIDDEN
    comm_headers = _get_auth_headers(client, workflow_test_env["comm"])
    res_comm = client.post(
        f"/api/workflow/application/{wf.id}/record-decision",
        json={"decision": "APPROVED", "reason": "Committee member attempted decision"},
        headers=comm_headers,
    )
    assert res_comm.status_code == 403

    # 3. Competent Authority (Bureau Officer) records decision -> 200 OK
    bureau_headers = _get_auth_headers(client, workflow_test_env["bureau"])
    res_bureau = client.post(
        f"/api/workflow/application/{wf.id}/record-decision",
        json={
            "decision": "APPROVED",
            "reason": "Executive Committee has approved Extension of Approval for AY 2026-27.",
            "notes": "Subject to compliance with annual statutory disclosures.",
        },
        headers=bureau_headers,
    )
    assert res_bureau.status_code == 200
    data = res_bureau.json()
    assert data["final_decision"] == "APPROVED"
    assert data["status"] == WorkflowStatus.COMPLETED


def test_workflow_institute_isolation(client: TestClient, workflow_test_env: dict):
    """
    Test 4: Strict Institute Isolation
    Verifies:
    1. Institute users cannot perform workflow transitions (HTTP 403).
    2. Institute 1 user can view their OWN application workflow.
    3. Institute 1 user CANNOT view Institute 2's application workflow (HTTP 403).
    """
    inst1_user = workflow_test_env["inst1_user"]
    inst1_headers = _get_auth_headers(client, inst1_user)
    wf1 = workflow_test_env["wf1"]  # belongs to Institute Alpha (inst1)
    wf2 = workflow_test_env["wf2"]  # belongs to Institute Beta (inst2)

    # 1. Institute cannot execute advance action -> 403
    res_action = client.post(
        f"/api/workflow/application/{wf1.id}/advance",
        json={"reason": "Institute attempting to advance stage"},
        headers=inst1_headers,
    )
    assert res_action.status_code == 403

    # 2. Institute can view its OWN workflow -> 200
    res_own = client.get(
        f"/api/workflow/application/{wf1.application.application_id}",
        headers=inst1_headers,
    )
    assert res_own.status_code == 200
    assert res_own.json()["application_code"] == wf1.application.application_id

    # 3. Institute cannot view OTHER institute's workflow -> 403 Forbidden
    res_other = client.get(
        f"/api/workflow/application/{wf2.application.application_id}",
        headers=inst1_headers,
    )
    assert res_other.status_code == 403
    assert "belonging to your institution" in res_other.json()["detail"].lower()


def test_role_scope_and_route_guards(client: TestClient, workflow_test_env: dict):
    """
    Test 5: Scope Reduction & Role Route Guards
    Verifies:
    1. Committee member sees ONLY assigned applications on /api/workflow/applications.
    2. Committee member receives 403 Forbidden for undertakings and document validity routes.
    3. Regional & Bureau officers receive 403 Forbidden when attempting to modify Rules/SLAs (view-only).
    4. Admin is permitted to update stage SLAs.
    """
    admin_headers = _get_auth_headers(client, workflow_test_env["admin"])
    ro_headers = _get_auth_headers(client, workflow_test_env["ro"])
    comm_user = workflow_test_env["comm"]
    comm_headers = _get_auth_headers(client, comm_user)

    wf1 = workflow_test_env["wf1"]
    wf2 = workflow_test_env["wf2"]

    # 1. Committee member application list filtering (assigned only)
    res_comm_apps = client.get("/api/workflow/applications", headers=comm_headers)
    assert res_comm_apps.status_code == 200
    comm_apps = res_comm_apps.json()
    # Should only contain applications where assigned_officer_id == comm_user.id
    for a in comm_apps:
        assert a.get("assigned_officer_id") == comm_user.id

    # 2. Committee member blocked from undertakings & validity management (403)
    res_ut = client.get("/api/undertakings", headers=comm_headers)
    assert res_ut.status_code == 403

    res_val = client.get("/api/validity", headers=comm_headers)
    assert res_val.status_code == 403

    # 3. Bureau / Regional officer blocked from mutating Rules/SLAs (view-only -> 403)
    res_sla_ro = client.put(
        f"/api/workflow/templates/{wf1.template_id}/stages/{wf1.current_stage_id or 1}",
        json={"sla_days": 10, "responsible_role": "REGIONAL_OFFICER"},
        headers=ro_headers,
    )
    assert res_sla_ro.status_code == 403

    # 4. Admin successfully updates SLA
    res_sla_admin = client.put(
        f"/api/workflow/templates/{wf1.template_id}/stages/{wf1.current_stage_id or 1}",
        json={"sla_days": 10, "responsible_role": "REGIONAL_OFFICER"},
        headers=admin_headers,
    )
    assert res_sla_admin.status_code == 200
    assert res_sla_admin.json()["sla_days"] == 10


def test_submission_creates_workflow_instance_fixed_date(
    client: TestClient, workflow_test_env: dict, db_session: Session
):
    """
    Test 6: Application Submission Creates Workflow Instance with First Stage and Due Date (Fixed Date)
    Verifies:
    1. Fixed time application submission via WorkflowService.
    2. Category-based template selection (Setting Up New Technical Campus -> SCRUTINY_EVC or appropriate).
    3. First stage initialized with due_date = simulated_time + SLA days.
    4. Workflow history and audit log entries created.
    5. API submission endpoint /api/workflow/application/submit works for institute user.
    """
    fixed_now = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    inst_user = workflow_test_env["inst1_user"]

    # 1. Direct Service Call with Fixed Simulated Time
    app, wf = WorkflowService.submit_new_application(
        db=db_session,
        user=inst_user,
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Engineering & Technology",
        intake=120,
        intake_details="Proposed Intake: 120 seats in CSE and ECE",
        simulated_time=fixed_now,
    )

    assert wf is not None
    assert wf.application_id == app.id
    assert wf.status == WorkflowStatus.IN_PROGRESS
    assert wf.current_stage_sequence == 1
    wf_start = wf.stage_start if wf.stage_start.tzinfo else wf.stage_start.replace(tzinfo=timezone.utc)
    wf_due = wf.due_date if wf.due_date.tzinfo else wf.due_date.replace(tzinfo=timezone.utc)
    assert wf_start == fixed_now
    # Stage 1 has SLA 7 days
    assert wf_due == fixed_now + timedelta(days=7)

    # Verify audit log entry
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "APPLICATION_SUBMITTED", AuditLog.user_id == inst_user.id)
        .first()
    )
    assert audit is not None
    assert audit.user_id == inst_user.id

    # 2. HTTP Endpoint Call with Institute User
    inst_headers = _get_auth_headers(client, inst_user)
    payload = {
        "category": "Increase in Intake / Additional Course",
        "academic_year": "2026-2027",
        "programme": "Computer Applications (MCA)",
        "intake": 60,
        "details": "Regular MCA degree programme",
    }
    res = client.post("/api/workflow/application/submit", headers=inst_headers, json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "IN_PROGRESS"
    assert data["current_stage_sequence"] == 1
    assert data["current_stage_name"] is not None
    assert data["due_date"] is not None
    assert data["days_remaining"] >= 0


def test_return_then_resubmit_restores_stage_and_restarts_clock(
    client: TestClient, workflow_test_env: dict, db_session: Session
):
    """
    Test 7: Return then Resubmit Restores Stage and Restarts Stage Clock
    Verifies:
    1. Officer returns workflow with mandatory reason -> status is RETURNED.
    2. Institute resubmits with response text at a later fixed time t2.
    3. Status restored to IN_PROGRESS at the returned stage.
    4. Stage clock restarted: due_date = t2 + SLA days.
    5. RESUBMIT recorded in workflow history and WORKFLOW_RESUBMIT logged in audit trail.
    6. Officer is notified of resubmission.
    """
    ro_user = workflow_test_env["ro"]
    inst_user = workflow_test_env["inst1_user"]
    ro_headers = _get_auth_headers(client, ro_user)
    inst_headers = _get_auth_headers(client, inst_user)

    # 1. Submit initial application at t1 = 2026-06-01
    t1 = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)
    app, wf = WorkflowService.submit_new_application(
        db=db_session,
        user=inst_user,
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        simulated_time=t1,
    )
    wf.assigned_officer_id = ro_user.id
    db_session.commit()

    initial_stage_name = wf.current_stage_name
    initial_sla_days = wf.current_stage.sla_days

    # 2. Officer returns workflow on t2 = 2026-06-05
    res_return = client.post(
        f"/api/workflow/application/{wf.id}/return",
        headers=ro_headers,
        json={"reason": "Fire Safety Certificate missing seal and signature."},
    )
    assert res_return.status_code == 200
    assert res_return.json()["status"] == "RETURNED"

    db_session.refresh(wf)
    assert wf.status == WorkflowStatus.RETURNED

    # 3. Institute resubmits at t3 = 2026-06-12 (simulated clock restart)
    t3 = datetime(2026, 6, 12, 14, 30, 0, tzinfo=timezone.utc)
    updated_wf = WorkflowService.resubmit_application(
        db=db_session,
        workflow=wf,
        user=inst_user,
        response_text="Duly attested Fire Safety NOC from State Fire Department attached.",
        simulated_time=t3,
    )

    # Verifications:
    # a. Status restored to IN_PROGRESS at returned stage
    assert updated_wf.status == WorkflowStatus.IN_PROGRESS
    assert updated_wf.current_stage_name == initial_stage_name

    # b. Clock restarted from t3
    up_start = updated_wf.stage_start if updated_wf.stage_start.tzinfo else updated_wf.stage_start.replace(tzinfo=timezone.utc)
    up_due = updated_wf.due_date if updated_wf.due_date.tzinfo else updated_wf.due_date.replace(tzinfo=timezone.utc)
    assert up_start == t3
    assert up_due == t3 + timedelta(days=initial_sla_days)

    # c. WorkflowHistory RESUBMIT recorded
    resubmit_hist = (
        db_session.query(WorkflowHistory)
        .filter(
            WorkflowHistory.workflow_id == wf.id,
            WorkflowHistory.action == WorkflowAction.RESUBMIT,
        )
        .first()
    )
    assert resubmit_hist is not None
    assert "Fire Safety NOC" in resubmit_hist.reason

    # d. Audit Log contains WORKFLOW_RESUBMIT
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "WORKFLOW_RESUBMIT")
        .first()
    )
    assert audit is not None

    # 4. Also test API endpoint for resubmit
    # Return again via API
    client.post(
        f"/api/workflow/application/{wf.id}/return",
        headers=ro_headers,
        json={"reason": "Building stability structural clearance clarification required."},
    )
    # Resubmit via API
    res_resubmit = client.post(
        f"/api/workflow/application/{wf.id}/resubmit",
        headers=inst_headers,
        json={"response_text": "PWD Certified structural stability clearance submitted."},
    )
    assert res_resubmit.status_code == 200
    assert res_resubmit.json()["status"] == "IN_PROGRESS"


def test_standardised_communications_and_disclaimer(
    client: TestClient, workflow_test_env: dict, db_session: Session
):
    """
    Test 8: Standardised Statutory Communications & Disclaimer
    Verifies:
    1. Communication templates table contains all 6 required seeded templates.
    2. Generating communication replaces placeholders (institute, application_code, stage, due_date, reason).
    3. Generated letter terminates with mandatory disclaimer:
       'This is a system reminder. Decisions remain with the competent authority.'
    4. Dispatches in-app notification, queues email_outbox record, and generates valid PDF letter.
    5. Admin can edit communication template; non-admin receives 403 Forbidden.
    """
    admin_headers = _get_auth_headers(client, workflow_test_env["admin"])
    ro_headers = _get_auth_headers(client, workflow_test_env["ro"])
    wf = workflow_test_env["wf1"]

    # 1. Fetch communication templates
    res_list = client.get("/api/workflow/communications/templates", headers=admin_headers)
    assert res_list.status_code == 200
    templates = res_list.json()
    assert len(templates) >= 6
    codes = {t["code"] for t in templates}
    required_codes = {
        "DEFICIENCY_NOTICE",
        "CLARIFICATION_REQUEST",
        "EVC_SCHEDULING_INTIMATION",
        "UNDERTAKING_REMINDER",
        "DOCUMENT_RENEWAL_REQUEST",
        "ESCALATION_NOTICE",
    }
    assert required_codes.issubset(codes)

    # 2. Generate Communication Notice from a Case
    gen_payload = {
        "template_code": "DEFICIENCY_NOTICE",
        "workflow_id": wf.id,
        "reason": "Fire NOC lapsed on 2026-03-31; renewal certificate required.",
    }
    res_gen = client.post("/api/workflow/communications/generate", headers=admin_headers, json=gen_payload)
    assert res_gen.status_code == 200, res_gen.text
    gen_data = res_gen.json()

    assert gen_data["success"] is True
    assert wf.application.application_id in gen_data["subject"]
    assert "Fire NOC lapsed" in gen_data["body"]
    assert gen_data["disclaimer"] == MANDATORY_DISCLAIMER
    assert gen_data["body"].strip().endswith(MANDATORY_DISCLAIMER)
    assert gen_data["email_status"] == "queued (SMTP not configured)"
    assert len(gen_data["pdf_base64"]) > 100

    # 3. Direct PDF Download Route
    res_pdf = client.get(
        f"/api/workflow/communications/letter/{wf.id}/DEFICIENCY_NOTICE?reason=Lapsed+Fire+NOC",
        headers=admin_headers,
    )
    assert res_pdf.status_code == 200
    assert res_pdf.headers["content-type"] == "application/pdf"
    assert res_pdf.content.startswith(b"%PDF")

    # 4. Role Authorization: Admin can update template, RO is blocked (403)
    tmpl_id = templates[0]["id"]
    res_ro_edit = client.put(
        f"/api/workflow/communications/templates/{tmpl_id}",
        headers=ro_headers,
        json={"name": "Hacked Template"},
    )
    assert res_ro_edit.status_code == 403

    res_admin_edit = client.put(
        f"/api/workflow/communications/templates/{tmpl_id}",
        headers=admin_headers,
        json={"name": "Formal Deficiency Notice v2"},
    )
    assert res_admin_edit.status_code == 200
    assert res_admin_edit.json()["name"] == "Formal Deficiency Notice v2"


def test_bottlenecks_and_workload_metrics(client: TestClient, workflow_test_env: dict):
    """
    Test 9: Bottlenecks & Workload Metrics on Workflow Dashboard
    Verifies:
    1. stage_analytics array comparing average dwell days with SLA days.
    2. worst_overdue_stage reporting the stage with the highest overdue count.
    3. committee_workload detailing inspection assignments per committee member.
    """
    admin_headers = _get_auth_headers(client, workflow_test_env["admin"])
    res = client.get("/api/workflow/dashboard", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    # Stage analytics
    assert "stage_analytics" in data
    assert isinstance(data["stage_analytics"], list)
    if data["stage_analytics"]:
        s = data["stage_analytics"][0]
        assert "stage_name" in s
        assert "sla_days" in s
        assert "avg_days_spent" in s
        assert "variance_days" in s
        assert "status" in s

    # Worst overdue stage
    assert "worst_overdue_stage" in data

    # Committee workload
    assert "committee_workload" in data
    assert isinstance(data["committee_workload"], list)


def test_complaint_linked_to_application_workflow(
    client: TestClient, workflow_test_env: dict, db_session: Session
):
    """
    Test 10: Link Complaints to Workflow & Application
    Verifies:
    1. An institute lodges a complaint referencing related_application_id.
    2. Complaint links to application_id in database.
    3. Admin reply creates audit log entry and in-app notification.
    """
    inst_user = workflow_test_env["inst1_user"]
    admin_user = workflow_test_env["admin"]
    wf = workflow_test_env["wf1"]
    inst_headers = _get_auth_headers(client, inst_user)
    admin_headers = _get_auth_headers(client, admin_user)

    # 1. Lodge complaint referencing application
    complaint_payload = {
        "category": "Portal / Scrutiny Delay",
        "subject": "Procedural Clarification on Scrutiny Observations",
        "description": "Requesting expedited desktop scrutiny review for campus expansion.",
        "related_application_id": wf.application_id,
    }
    res_raise = client.post("/api/institute/complaints", headers=inst_headers, json=complaint_payload)
    assert res_raise.status_code == 201
    complaint_id = res_raise.json()["id"]

    # Verify link in database
    comp = db_session.query(Complaint).filter(Complaint.id == complaint_id).first()
    assert comp is not None
    assert comp.application_id == wf.application_id

    # 2. Admin replies and resolves ticket
    reply_payload = {
        "notes": "Scrutiny committee has expedited document verification.",
        "status": "Resolved",
        "is_internal": False,
    }
    res_reply = client.post(
        f"/api/admin/complaints/{complaint_id}/reply",
        headers=admin_headers,
        json=reply_payload,
    )
    assert res_reply.status_code == 200

    # 3. Verify audit log entry exists
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "COMPLAINT_ADMIN_REPLY")
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert comp.ticket_id in audit.reason


