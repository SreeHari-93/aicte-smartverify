import pytest
import io
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.workflow import ApplicationWorkflow, WorkflowTemplate, WorkflowTemplateStage
from backend.app.models.evc import EvcRecord, EvcStatus
from backend.app.models.undertaking import Undertaking, UndertakingStatus, UndertakingCategory
from backend.app.models.document_validity import DocumentValidityRecord, ValidityStatus
from backend.app.models.alert_event import AlertEvent
from backend.app.services.workflow_service import WorkflowService
from backend.app.services.evc_service import EvcService
from backend.app.services.undertaking_service import UndertakingService
from backend.app.services.validity_service import ValidityService
from backend.app.security.tokens import create_access_token


@pytest.fixture
def test_setup(db_session: Session):
    # Ensure workflow template ONLY_EVC exists with stages
    t_evc = db_session.query(WorkflowTemplate).filter(WorkflowTemplate.code == "ONLY_EVC").first()
    if not t_evc:
        t_evc = WorkflowTemplate(code="ONLY_EVC", name="Fast-Track Expert Inspection", description="Only EVC")
        db_session.add(t_evc)
        db_session.commit()

    if not t_evc.stages:
        s1 = WorkflowTemplateStage(template_id=t_evc.id, sequence=1, stage_code="EVC", stage_name="Expert Visit Committee (EVC)", responsible_role=UserRole.COMMITTEE_MEMBER, sla_days=10, is_final_decision=False)
        s2 = WorkflowTemplateStage(template_id=t_evc.id, sequence=2, stage_code="FINAL_DECISION", stage_name="Final Decision", responsible_role=UserRole.BUREAU_OFFICER, sla_days=3, is_final_decision=True)
        db_session.add_all([s1, s2])
        db_session.commit()
        db_session.refresh(t_evc)

    # Ensure admin, regional officer, and two institutes exist
    admin = db_session.query(User).filter(User.role == UserRole.ADMIN).first()
    if not admin:
        admin = User(email="admin.stage3@aicte-india.org", password_hash="pwd", role=UserRole.ADMIN, is_active=True)
        db_session.add(admin)
        db_session.commit()

    ro = db_session.query(User).filter(User.role == UserRole.REGIONAL_OFFICER).first()
    if not ro:
        ro = User(email="ro.stage3@aicte-india.org", password_hash="pwd", role=UserRole.REGIONAL_OFFICER, region="Southern", is_active=True)
        db_session.add(ro)
        db_session.commit()

    inst1 = db_session.query(Institute).filter(Institute.id == 1).first()
    if not inst1:
        inst1 = Institute(id=1, aicte_institute_id="INST-ALPHA", name="Alpha Engineering College", state="Tamil Nadu", status="Approved")
        db_session.add(inst1)
        db_session.commit()

    inst2 = db_session.query(Institute).filter(Institute.id == 2).first()
    if not inst2:
        inst2 = Institute(id=2, aicte_institute_id="INST-BETA", name="Beta Institute of Technology", state="Karnataka", status="Approved")
        db_session.add(inst2)
        db_session.commit()

    inst1_user = db_session.query(User).filter(User.institute_id == inst1.id).first()
    if not inst1_user:
        inst1_user = User(email="inst1.stage3@aicte.edu.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst1.id, is_active=True)
        db_session.add(inst1_user)
        db_session.commit()

    inst2_user = db_session.query(User).filter(User.institute_id == inst2.id).first()
    if not inst2_user:
        inst2_user = User(email="inst2.stage3@aicte.edu.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst2.id, is_active=True)
        db_session.add(inst2_user)
        db_session.commit()

    return {
        "admin": admin,
        "ro": ro,
        "inst1": inst1,
        "inst2": inst2,
        "inst1_user": inst1_user,
        "inst2_user": inst2_user,
    }


def test_evc_queue_placement(test_setup, db_session: Session):
    """
    Test 1: When a workflow reaches or starts in the EVC stage,
    it automatically creates an EVC record with appropriate deadlines (shorter for new institutions).
    """
    inst = test_setup["inst1"]
    app_new = Application(
        institute_id=inst.id,
        application_id=f"APP-EVC-{int(datetime.now().timestamp())}",
        category="Setting Up New Technical Campus",
        academic_year="2026-2027",
        programme="Engineering",
        status="SUBMITTED",
    )
    db_session.add(app_new)
    db_session.commit()
    db_session.refresh(app_new)

    # Initialize workflow with ONLY_EVC template
    wf = WorkflowService.get_or_create_workflow(db_session, app_new, template_code="ONLY_EVC")
    assert wf is not None
    assert "EVC" in wf.current_stage_name.upper()

    # Verify EVC record automatically created
    evc = db_session.query(EvcRecord).filter(EvcRecord.application_id == app_new.id).first()
    assert evc is not None
    assert evc.is_new_institution is True
    assert evc.status == EvcStatus.PENDING_SCHEDULING
    # Shorter scheduling deadline for new institutions (approx 5 days)
    delta_days = (evc.scheduling_deadline.date() - date.today()).days
    assert delta_days <= 6

    # Verify alert event
    event = db_session.query(AlertEvent).filter(
        AlertEvent.case_id == app_new.application_id,
        AlertEvent.event_type == "EVC_PENDING_SCHEDULING",
    ).first()
    assert event is not None
    assert event.recipient_role == "REGIONAL_OFFICER"


def test_evc_conflict_warning(test_setup, db_session: Session, client: TestClient):
    """
    Test 2: When scheduling a committee member who already has another EVC visit
    on that same date, the system generates a conflict warning.
    """
    admin_token = create_access_token(user_id=test_setup["admin"].id, role=UserRole.ADMIN)
    headers = {"Authorization": f"Bearer {admin_token}"}

    fixed_date = datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc)
    member_email = "prof.krishnan@aicte.edu"
    committee_members = [
        {"name": "Prof. R. Krishnan", "email": member_email, "role": "Chairman", "institution": "NIT Trichy"}
    ]

    # Create two EVC records
    app1 = Application(institute_id=1, application_id=f"APP-CONF-1-{int(datetime.now().timestamp())}", category="EoA", academic_year="2026-2027", programme="Engg")
    app2 = Application(institute_id=1, application_id=f"APP-CONF-2-{int(datetime.now().timestamp())}", category="EoA", academic_year="2026-2027", programme="Engg")
    db_session.add_all([app1, app2])
    db_session.commit()

    now = datetime.now(timezone.utc)
    evc1 = EvcRecord(application_id=app1.id, scheduling_deadline=now, completion_deadline=now + timedelta(days=20))
    evc2 = EvcRecord(application_id=app2.id, scheduling_deadline=now, completion_deadline=now + timedelta(days=20))
    db_session.add_all([evc1, evc2])
    db_session.commit()

    # Schedule evc1 on fixed_date with member
    payload1 = {
        "proposed_date": fixed_date.isoformat(),
        "confirmed_date": fixed_date.isoformat(),
        "committee_members": committee_members,
        "remarks": "Scheduled inspection #1",
    }
    res1 = client.post(f"/api/evc/{evc1.id}/schedule", json=payload1, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["conflict_warning"] is None

    # Now schedule evc2 on the SAME fixed_date with the SAME member
    payload2 = {
        "proposed_date": fixed_date.isoformat(),
        "confirmed_date": fixed_date.isoformat(),
        "committee_members": committee_members,
        "remarks": "Scheduled inspection #2",
    }
    res2 = client.post(f"/api/evc/{evc2.id}/schedule", json=payload2, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conflict_warning"] is not None
    assert "Conflict Warning" in data2["conflict_warning"]
    assert "Prof. R. Krishnan" in data2["conflict_warning"]


def test_undertaking_overdue_transition(test_setup, db_session: Session):
    """
    Test 3: Undertaking transitions automatically to OVERDUE when evaluated past due date,
    and triggers the required alert event.
    """
    fixed_now = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
    past_due = fixed_now - timedelta(days=3)

    app = Application(institute_id=1, application_id=f"APP-UND-{int(datetime.now().timestamp())}", category="EoA", academic_year="2026-2027", programme="Engg")
    db_session.add(app)
    db_session.commit()

    undertaking = Undertaking(
        application_id=app.id,
        institute_id=app.institute_id,
        condition="Submit registered lease deed for academic campus",
        category=UndertakingCategory.LEASE,
        due_date=past_due,
        status=UndertakingStatus.ACTIVE,
        created_at=past_due - timedelta(days=30),
    )
    db_session.add(undertaking)
    db_session.commit()
    db_session.refresh(undertaking)

    assert undertaking.status == UndertakingStatus.ACTIVE

    # Evaluate transition
    transitioned = UndertakingService.evaluate_and_transition_overdue(db_session, undertaking, now=fixed_now)
    assert transitioned is True
    assert undertaking.status == UndertakingStatus.OVERDUE

    # Verify alert event
    event = db_session.query(AlertEvent).filter(
        AlertEvent.case_id == str(undertaking.id),
        AlertEvent.event_type == "UNDERTAKING_OVERDUE",
    ).first()
    assert event is not None
    assert event.recipient_role == "REGIONAL_OFFICER"


def test_renewal_linking(test_setup, db_session: Session, client: TestClient):
    """
    Test 4: Submitting a renewal creates a new document linked to the existing validity record,
    sets RENEWAL_SUBMITTED, and subsequent admin approval extends the validity date.
    """
    inst_token = create_access_token(user_id=test_setup["inst1_user"].id, role=UserRole.INSTITUTE)
    admin_token = create_access_token(user_id=test_setup["admin"].id, role=UserRole.ADMIN)

    # Create monitored document record
    record = DocumentValidityRecord(
        institute_id=test_setup["inst1"].id,
        document_type_code="FIRE_NOC",
        document_name="Fire & Safety NOC",
        certificate_number="FS-NOC-2025-ORIG",
        expiry_date=date(2026, 8, 1),
        status=ValidityStatus.EXPIRED,
        expiring_soon_window_days=60,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)

    # 1. Institute submits renewal document
    file_bytes = b"%PDF-1.4 Mock Renewal Fire Safety NOC Document Content"
    renew_res = client.post(
        f"/api/validity/{record.id}/renew",
        headers={"Authorization": f"Bearer {inst_token}"},
        files={"renewal_file": ("fire_noc_renewed.pdf", io.BytesIO(file_bytes), "application/pdf")},
        data={"new_issue_date": "2026-08-01", "new_expiry_date": "2027-07-31"},
    )
    assert renew_res.status_code == 200
    renew_data = renew_res.json()
    assert renew_data["status"] == ValidityStatus.RENEWAL_SUBMITTED
    assert renew_data["renewal_document_id"] is not None

    # Check database link
    db_session.refresh(record)
    assert record.renewal_document_id is not None
    renewal_doc = db_session.query(Document).filter(Document.id == record.renewal_document_id).first()
    assert renewal_doc is not None
    assert "fire_noc_renewed.pdf" in renewal_doc.original_filename

    # 2. Admin accepts renewal
    decision_res = client.post(
        f"/api/validity/{record.id}/decide-renewal",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "action": "ACCEPT",
            "reason": "Fire NOC verified authentic with Municipal Fire Authority",
            "new_expiry_date": "2027-07-31",
        },
    )
    assert decision_res.status_code == 200
    decision_data = decision_res.json()
    assert decision_data["status"] == ValidityStatus.RENEWED
    assert decision_data["renewal_status"] == "ACCEPTED"
    assert decision_data["expiry_date"] == "2027-07-31"


def test_institute_isolation(test_setup, db_session: Session, client: TestClient):
    """
    Test 5: Strict Institute Isolation:
    - Institute 1 cannot see or modify Institute 2's undertakings or validity records.
    - Institutes cannot perform admin-only actions (schedule EVC, verify undertakings).
    """
    inst1_token = create_access_token(user_id=test_setup["inst1_user"].id, role=UserRole.INSTITUTE)
    inst1_headers = {"Authorization": f"Bearer {inst1_token}"}

    # Create undertaking for Institute 1 and Institute 2
    app1 = Application(institute_id=test_setup["inst1"].id, application_id=f"APP-ISO-1-{int(datetime.now().timestamp())}", category="EoA", academic_year="2026-2027", programme="Engg")
    app2 = Application(institute_id=test_setup["inst2"].id, application_id=f"APP-ISO-2-{int(datetime.now().timestamp())}", category="EoA", academic_year="2026-2027", programme="Engg")
    db_session.add_all([app1, app2])
    db_session.commit()

    u1 = Undertaking(application_id=app1.id, institute_id=test_setup["inst1"].id, condition="Inst 1 Condition", due_date=datetime.now(timezone.utc) + timedelta(days=30))
    u2 = Undertaking(application_id=app2.id, institute_id=test_setup["inst2"].id, condition="Inst 2 Condition", due_date=datetime.now(timezone.utc) + timedelta(days=30))
    db_session.add_all([u1, u2])
    db_session.commit()

    # Institute 1 lists undertakings
    list_res = client.get("/api/undertakings", headers=inst1_headers)
    assert list_res.status_code == 200
    ids = [item["id"] for item in list_res.json()]
    assert u1.id in ids
    assert u2.id not in ids  # Isolated!

    # Institute 1 tries to submit evidence for Institute 2 -> 403 Forbidden
    hack_res = client.post(
        f"/api/undertakings/{u2.id}/submit-evidence",
        headers=inst1_headers,
        files={"evidence_file": ("test.pdf", io.BytesIO(b"fake content"), "application/pdf")},
    )
    assert hack_res.status_code == 403

    # Institute 1 tries to verify undertaking -> 403 Forbidden (staff only)
    verify_res = client.post(
        f"/api/undertakings/{u1.id}/verify",
        headers=inst1_headers,
        json={"action": "ACCEPT", "reason": "Self verification attempt"},
    )
    assert verify_res.status_code == 403

    # Institute 1 tries to schedule EVC -> 403 Forbidden (staff only)
    evc_res = client.post(
        "/api/evc/1/schedule",
        headers=inst1_headers,
        json={
            "proposed_date": datetime.now(timezone.utc).isoformat(),
            "confirmed_date": datetime.now(timezone.utc).isoformat(),
            "committee_members": [],
        },
    )
    assert evc_res.status_code == 403
