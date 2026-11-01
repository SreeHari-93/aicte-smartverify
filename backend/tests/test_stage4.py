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
from backend.app.models.workflow import ApplicationWorkflow, WorkflowTemplate, WorkflowTemplateStage
from backend.app.models.undertaking import Undertaking, UndertakingStatus
from backend.app.models.document_validity import DocumentValidityRecord, ValidityStatus
from backend.app.models.alert_event import AlertEvent
from backend.app.models.escalation import EscalationRecord
from backend.app.services.scheduler_service import (
    run_notification_scan,
    set_demo_clock,
    reset_demo_clock,
    assert_no_prohibited_words,
    auto_close_escalations,
    seed_rules_and_escalations_if_empty,
)
from backend.app.services.undertaking_service import UndertakingService
from backend.app.services.consolidated_report_service import ConsolidatedReportService
from backend.app.security.tokens import create_access_token


@pytest.fixture
def test_setup_stage4(db_session: Session):
    seed_rules_and_escalations_if_empty(db_session)

    # Institutes
    inst1 = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST-TEST-1").first()
    if not inst1:
        inst1 = Institute(aicte_institute_id="INST-TEST-1", name="Test Engineering College A", state="Tamil Nadu", status="ACTIVE")
        db_session.add(inst1)
        db_session.commit()
        db_session.refresh(inst1)

    inst2 = db_session.query(Institute).filter(Institute.aicte_institute_id == "INST-TEST-2").first()
    if not inst2:
        inst2 = Institute(aicte_institute_id="INST-TEST-2", name="Test Engineering College B", state="Karnataka", status="ACTIVE")
        db_session.add(inst2)
        db_session.commit()
        db_session.refresh(inst2)

    # Users
    admin = db_session.query(User).filter(User.email == "admin.test4@aicte.gov.in").first()
    if not admin:
        admin = User(email="admin.test4@aicte.gov.in", password_hash="pwd", role=UserRole.ADMIN, is_active=True)
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

    user_inst1 = db_session.query(User).filter(User.email == "inst1.test4@aicte.gov.in").first()
    if not user_inst1:
        user_inst1 = User(email="inst1.test4@aicte.gov.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst1.id, is_active=True)
        db_session.add(user_inst1)
        db_session.commit()
        db_session.refresh(user_inst1)

    user_inst2 = db_session.query(User).filter(User.email == "inst2.test4@aicte.gov.in").first()
    if not user_inst2:
        user_inst2 = User(email="inst2.test4@aicte.gov.in", password_hash="pwd", role=UserRole.INSTITUTE, institute_id=inst2.id, is_active=True)
        db_session.add(user_inst2)
        db_session.commit()
        db_session.refresh(user_inst2)

    return {
        "admin": admin,
        "inst1": inst1,
        "inst2": inst2,
        "user_inst1": user_inst1,
        "user_inst2": user_inst2,
    }


def test_scheduler_idempotency_fixed_date(db_session: Session, test_setup_stage4):
    """Scan runs idempotently at a fixed date with 0 duplicate alerts on second pass."""
    fixed_date = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)

    # First run
    log1 = run_notification_scan(db_session, simulated_time=fixed_date)
    assert log1.status == "SUCCESS"

    # Second run at same timestamp
    log2 = run_notification_scan(db_session, simulated_time=fixed_date)
    assert log2.status == "SUCCESS"
    assert log2.alerts_created == 0  # Idempotency: no duplicates created!


def test_offsets_and_escalation_thresholds(db_session: Session, test_setup_stage4):
    """Overdue undertaking transitions to ESCALATED when Level 1 triggers."""
    inst = test_setup_stage4["inst1"]
    fixed_time = datetime(2026, 11, 20, 10, 0, 0, tzinfo=timezone.utc)

    # Create an app and undertaking that is overdue by 4 days on fixed_time
    app_rec = Application(
        application_id="APP-TEST-ESC-01",
        institute_id=inst.id,
        academic_year="2026-2027",
        category="Extension of Approval (EoA)",
        programme="Engineering",
        status="SUBMITTED"
    )
    db_session.add(app_rec)
    db_session.commit()

    ut = Undertaking(
        application_id=app_rec.id,
        institute_id=inst.id,
        category="infrastructure",
        condition="Fire safety NOC renewal",
        due_date=fixed_time - timedelta(days=4),  # 4 days overdue
        status=UndertakingStatus.ACTIVE
    )
    db_session.add(ut)
    db_session.commit()
    db_session.refresh(ut)

    run_notification_scan(db_session, simulated_time=fixed_time)
    db_session.refresh(ut)

    # Must transition to ESCALATED because days_overdue >= 3
    assert ut.status == UndertakingStatus.ESCALATED

    # EscalationRecord must exist
    esc = db_session.query(EscalationRecord).filter(
        EscalationRecord.case_id == f"UT-{ut.id}",
        EscalationRecord.level == 1
    ).first()
    assert esc is not None
    assert esc.notified_role == "REGIONAL_OFFICER"
    assert esc.status == "ACTIVE"


def test_auto_close_on_resolution(db_session: Session, test_setup_stage4):
    """Active escalation records close automatically when the undertaking is fulfilled."""
    inst = test_setup_stage4["inst1"]
    admin = test_setup_stage4["admin"]
    now = datetime.now(timezone.utc)

    app_rec = Application(
        application_id="APP-TEST-ESC-AUTO-CLOSE",
        institute_id=inst.id,
        academic_year="2026-2027",
        category="Extension of Approval (EoA)",
        programme="Engineering",
        status="SUBMITTED"
    )
    db_session.add(app_rec)
    db_session.commit()

    ut = Undertaking(
        application_id=app_rec.id,
        institute_id=inst.id,
        category="infrastructure",
        condition="Fire safety NOC renewal",
        due_date=now - timedelta(days=5),
        status=UndertakingStatus.OVERDUE
    )
    db_session.add(ut)
    db_session.commit()
    db_session.refresh(ut)

    # Create an active escalation record for this undertaking
    esc_rec = EscalationRecord(
        case_id=f"UT-{ut.id}",
        case_type="undertaking",
        event_type="UNDERTAKING_OVERDUE",
        level=1,
        notified_role="REGIONAL_OFFICER",
        notified_user_email="ro@aicte.gov.in",
        days_overdue=5,
        status="ACTIVE",
        created_at=now
    )
    db_session.add(esc_rec)
    db_session.commit()

    # Verify undertaking as ACCEPT
    UndertakingService.verify_undertaking(
        db=db_session,
        undertaking_id=ut.id,
        action="ACCEPT",
        reason="Compliance evidence verified and acceptable under APH 2026-27.",
        user=admin
    )

    db_session.refresh(ut)
    assert ut.status == UndertakingStatus.FULFILLED

    # Check that escalation record is AUTO_CLOSED
    esc = db_session.query(EscalationRecord).filter(
        EscalationRecord.case_id == f"UT-{ut.id}"
    ).first()
    assert esc.status == "AUTO_CLOSED"
    assert esc.resolved_at is not None


def test_consolidated_report_generation(db_session: Session, test_setup_stage4):
    """Consolidated reports export CSV and PDF with official disclaimers."""
    csv_out = ConsolidatedReportService.generate_csv(db_session, "application_pendency")
    assert "Application ID" in csv_out
    assert "SLA Status" in csv_out

    pdf_bytes = ConsolidatedReportService.generate_pdf(db_session, "undertaking_compliance")
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-")


def test_prohibited_words_enforcement():
    """Assert strictly no prohibited words (forgery, fraud, misconduct) in statutory communications."""
    with pytest.raises(ValueError):
        assert_no_prohibited_words("Suspicion of forgery detected in document.")

    with pytest.raises(ValueError):
        assert_no_prohibited_words("Financial fraud allegations reported.")

    with pytest.raises(ValueError):
        assert_no_prohibited_words("Official misconduct reported by committee.")

    # Compliant phrasing must pass without error
    assert_no_prohibited_words("Potential anomaly detected in stamp clarity. Standard procedural verification required.")


def test_institute_alerts_isolation(client: TestClient, db_session: Session, test_setup_stage4):
    """Institutes strictly see ONLY their own institution's alerts."""
    inst1 = test_setup_stage4["inst1"]
    inst2 = test_setup_stage4["inst2"]
    user1 = test_setup_stage4["user_inst1"]

    # Add an alert for inst1 and an alert for inst2
    al1 = AlertEvent(
        event_type="UNDERTAKING_DUE_SOON",
        case_id="CASE-INST-1",
        recipient_role="INSTITUTE",
        offset_days=7,
        institute_id=inst1.id,
        title="Notice for Institute 1",
        message="Compliance due soon. This is a system reminder. Decisions remain with the competent authority."
    )
    al2 = AlertEvent(
        event_type="UNDERTAKING_DUE_SOON",
        case_id="CASE-INST-2",
        recipient_role="INSTITUTE",
        offset_days=7,
        institute_id=inst2.id,
        title="Notice for Institute 2",
        message="Compliance due soon. This is a system reminder. Decisions remain with the competent authority."
    )
    db_session.add_all([al1, al2])
    db_session.commit()

    token = create_access_token(user_id=user1.id, role=user1.role)
    res = client.get("/api/alerts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    case_ids = [item["case_id"] for item in data["items"]]
    assert "CASE-INST-1" in case_ids
    assert "CASE-INST-2" not in case_ids  # Absolute isolation!
