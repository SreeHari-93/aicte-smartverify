"""
Stage 6 Tests: Infrastructure Compliance
Covers:
1. Pass: Fully compliant institutional infrastructure parameters
2. Fail: Deficient parameters triggering BLOCKER/WARNING findings with AI explainer values
3. Missing Data: Clean 'Not provided' / NEEDS_REVIEW handling without crashes
4. Admin Threshold Change: Admin altering editable rule threshold affects evaluation
5. Institute Isolation: Cross-tenant access forbidden
6. PDF Report: Generated validation summary PDF contains Infrastructure Compliance table
"""

import os
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.application import Application
from backend.app.models.infrastructure import InfrastructureDetail
from backend.app.models.rule import Rule, RuleSet
from backend.app.services.demo_data import DemoDataSeeder
from backend.app.services.demo_rules import seed_published_rules_if_needed
from backend.app.services.validation.runner import ValidationRunner
from backend.app.services.report_service import ReportService
from backend.app.security.tokens import create_access_token


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        seed_published_rules_if_needed(db)
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


def get_token_for_user(user: User) -> str:
    return create_access_token(
        user_id=user.id,
        role=user.role,
        extra_claims={
            "institute_id": user.institute_id,
            "email": user.email,
        },
    )


def test_infrastructure_compliance_pass(db_session: Session):
    """
    1. PASS test: Application with compliant infrastructure satisfies all infrastructure rules.
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)
    app_ready = db_session.query(Application).filter(Application.application_id == "DEMO-READY").first()
    assert app_ready is not None

    val_run = ValidationRunner.run_validation(db=db_session, application_id=app_ready.id)
    assert val_run.overall_status == "READY_FOR_REVIEW"

    infra_findings = [f for f in val_run.findings if f.rule_code.startswith("INFRA-")]
    assert len(infra_findings) >= 5

    for f in infra_findings:
        assert f.status == "PASS", f"Expected PASS for {f.rule_code}, got {f.status} ({f.reason})"


def test_infrastructure_compliance_fail(db_session: Session):
    """
    2. FAIL test: Deficient infrastructure triggers BLOCKER / FAIL and AI explainer quotes values.
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)
    skcet = db_session.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
    assert skcet is not None

    # Create application with failing infrastructure
    app_fail = db_session.query(Application).filter(Application.application_id == "APP-TEST-INFRA-FAIL").first()
    if not app_fail:
        app_fail = Application(
            institute_id=skcet.id,
            application_id="APP-TEST-INFRA-FAIL",
            category="EOA",
            academic_year="2026-27",
            programme="Engineering",
            status="SUBMITTED",
        )
        db_session.add(app_fail)
        db_session.commit()
        db_session.refresh(app_fail)

    infra_detail = db_session.query(InfrastructureDetail).filter(InfrastructureDetail.application_id == app_fail.id).first()
    if not infra_detail:
        infra_detail = InfrastructureDetail(
            institute_id=skcet.id,
            application_id=app_fail.id,
            total_built_up_area=1200.0,      # For 600 intake -> 2.0 sq m (< 4.0 required -> FAIL BLOCKER)
            total_sanctioned_intake=600,
            classroom_count=8,               # < 16 required -> FAIL BLOCKER
            average_classroom_area=45.0,     # < 66.0 required -> FAIL BLOCKER
            laboratory_count=10,             # < 20 required -> FAIL WARNING
            library_area=250.0,              # < 400.0 required -> FAIL BLOCKER
            library_books_count=4000,        # < 10000 required -> FAIL WARNING
            faculty_count=15,                # For 600 students -> 40:1 (> 20:1 required -> FAIL BLOCKER)
            student_count=600,
            computers_available=50,          # 50 / 600 = 0.083 (< 0.20 required -> FAIL BLOCKER)
            barrier_free_facilities=False,   # FAIL WARNING
            fire_safety_installed=False,     # FAIL WARNING
            status="SUBMITTED",
        )
        db_session.add(infra_detail)
    else:
        infra_detail.total_built_up_area = 1200.0
        infra_detail.total_sanctioned_intake = 600
        infra_detail.classroom_count = 8
        infra_detail.average_classroom_area = 45.0
        infra_detail.laboratory_count = 10
        infra_detail.library_area = 250.0
        infra_detail.library_books_count = 4000
        infra_detail.faculty_count = 15
        infra_detail.student_count = 600
        infra_detail.computers_available = 50
        infra_detail.barrier_free_facilities = False
        infra_detail.fire_safety_installed = False
    db_session.commit()

    val_run = ValidationRunner.run_validation(db=db_session, application_id=app_fail.id)
    assert val_run.overall_status == "BLOCKED"
    assert val_run.blocker_count > 0

    failed_infra = [f for f in val_run.findings if f.rule_code.startswith("INFRA-") and f.status != "PASS"]
    assert len(failed_infra) >= 5

    # Verify classroom count failure
    cls_finding = next((f for f in failed_infra if f.rule_code == "INFRA-CLASSROOM-COUNT"), None)
    assert cls_finding is not None
    assert cls_finding.status == "FAIL"
    assert "8" in cls_finding.reason
    assert "16" in cls_finding.reason


def test_infrastructure_missing_data(db_session: Session):
    """
    3. Missing Data test: When infrastructure details are missing, rules produce clear 'Not provided' result.
    """
    skcet = db_session.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
    assert skcet is not None

    app_missing = db_session.query(Application).filter(Application.application_id == "APP-TEST-MISSING-INFRA").first()
    if not app_missing:
        app_missing = Application(
            institute_id=skcet.id,
            application_id="APP-TEST-MISSING-INFRA",
            category="EOA",
            academic_year="2026-27",
            programme="Engineering",
            status="SUBMITTED",
        )
        db_session.add(app_missing)
        db_session.commit()
        db_session.refresh(app_missing)

    # Delete any existing infrastructure for this application
    db_session.query(InfrastructureDetail).filter(InfrastructureDetail.application_id == app_missing.id).delete()
    db_session.commit()

    context = ValidationRunner.build_evaluation_context(db_session, app_missing)
    assert context.infrastructure == {}

    rule_builtup = db_session.query(Rule).filter(Rule.rule_code == "INFRA-BUILTUP-PER-INTAKE").first()
    assert rule_builtup is not None

    from backend.app.services.rule_engine.engine import RuleEngine
    finding = RuleEngine.evaluate_rule(rule_builtup, context)
    assert finding is not None
    assert finding.details.get("status") == "NEEDS_REVIEW"
    assert "Not provided" in finding.message or "not provided" in finding.message.lower()


def test_admin_threshold_change_affects_result(db_session: Session):
    """
    4. Admin threshold edit test: Modifying rule target in definition affects evaluation outcome.
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)
    app_ready = db_session.query(Application).filter(Application.application_id == "DEMO-READY").first()
    assert app_ready is not None

    rule_cls = db_session.query(Rule).filter(Rule.rule_code == "INFRA-CLASSROOM-COUNT").first()
    assert rule_cls is not None

    orig_def = dict(rule_cls.definition)
    try:
        # Increase required classroom count threshold from 16 to 100
        high_threshold_def = dict(orig_def)
        high_threshold_def["target"] = 100
        rule_cls.definition = high_threshold_def
        db_session.commit()

        context = ValidationRunner.build_evaluation_context(db_session, app_ready)
        from backend.app.services.rule_engine.engine import RuleEngine
        f_high = RuleEngine.evaluate_rule(rule_cls, context)
        assert f_high is not None
        assert f_high.passed is False
        assert "100" in f_high.message

        # Lower threshold to 10
        low_threshold_def = dict(orig_def)
        low_threshold_def["target"] = 10
        rule_cls.definition = low_threshold_def
        db_session.commit()

        f_low = RuleEngine.evaluate_rule(rule_cls, context)
        assert f_low is not None
        assert f_low.passed is True
    finally:
        # Restore original definition
        rule_cls.definition = orig_def
        db_session.commit()


def test_infrastructure_institute_isolation(client: TestClient, db_session: Session):
    """
    5. Institute isolation test: User from institute B cannot access or mutate institute A's infrastructure.
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)

    # Institute A: SKCET
    skcet = db_session.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
    assert skcet is not None

    skcet_user = db_session.query(User).filter(User.institute_id == skcet.id).first()
    if not skcet_user:
        from backend.app.security.password import hash_password
        skcet_user = User(
            email="skcet@aicte.edu.in",
            password_hash=hash_password("Institute@123"),
            role=UserRole.INSTITUTE,
            institute_id=skcet.id,
            is_active=True,
        )
        db_session.add(skcet_user)
        db_session.commit()
        db_session.refresh(skcet_user)

    # Institute B: Delhi Institute
    del_inst = db_session.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
    if not del_inst:
        del_inst = Institute(aicte_institute_id="DEL0101", name="Delhi Institute", state="Delhi", status="ACTIVE")
        db_session.add(del_inst)
        db_session.commit()
        db_session.refresh(del_inst)

    del_user = db_session.query(User).filter(User.institute_id == del_inst.id).first()
    if not del_user:
        from backend.app.security.password import hash_password
        del_user = User(
            email="del0101@aicte.edu.in",
            password_hash=hash_password("Pass@123"),
            role=UserRole.INSTITUTE,
            institute_id=del_inst.id,
            is_active=True,
        )
        db_session.add(del_user)
        db_session.commit()
        db_session.refresh(del_user)

    del_token = get_token_for_user(del_user)
    headers = {"Authorization": f"Bearer {del_token}"}

    # Institute B attempts to read SKCET's DEMO-READY infrastructure
    res_get = client.get("/api/v1/institute/applications/DEMO-READY/infrastructure", headers=headers)
    assert res_get.status_code == 404
    assert "not found or access denied" in res_get.json()["detail"].lower()

    # Institute B attempts to overwrite SKCET's DEMO-READY infrastructure
    res_put = client.put(
        "/api/v1/institute/applications/DEMO-READY/infrastructure",
        json={
            "total_built_up_area": 9999.0,
            "land_area": 9999.0,
            "classroom_count": 50,
            "average_classroom_area": 70.0,
            "laboratory_count": 30,
            "library_area": 500.0,
            "library_books_count": 12000,
            "total_sanctioned_intake": 600,
            "faculty_count": 40,
            "student_count": 600,
            "computers_available": 200,
            "internet_bandwidth_mbps": 500.0,
            "barrier_free_facilities": True,
            "fire_safety_installed": True,
            "status": "SUBMITTED",
        },
        headers=headers,
    )
    assert res_put.status_code == 404


def test_infrastructure_pdf_report_contains_section(db_session: Session):
    """
    6. PDF report test: Validation Summary PDF contains Infrastructure compliance section & table.
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)
    skcet = db_session.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
    assert skcet is not None

    rep = ReportService.generate_report(
        db=db_session,
        institute_id=skcet.id,
        report_type="Validation Summary",
        report_format="PDF",
        date_range="Current Academic Year",
        application_id="DEMO-READY",
    )
    assert rep is not None
    assert os.path.exists(rep.file_path)

    import fitz  # PyMuPDF
    doc = fitz.open(rep.file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    assert "Infrastructure Compliance" in full_text
    assert "Built-up Area per Intake" in full_text
    assert "Instructional Classrooms" in full_text
    assert "Faculty-to-Student Ratio" in full_text
