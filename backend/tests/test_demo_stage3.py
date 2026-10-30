import os
import pytest
import pymupdf
from sqlalchemy.orm import Session

from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.validation_run import ValidationRun
from backend.app.services.demo_data import DemoDataSeeder
from backend.app.services.report_service import ReportService
from backend.app.services.validation.runner import ValidationRunner


def test_demo_applications_yield_expected_statuses(db_session: Session):
    """
    Verify that seeding the 4 demo applications produces the exact expected outcomes:
    - DEMO-READY -> READY_FOR_REVIEW
    - DEMO-ATTENTION -> NEEDS_ATTENTION
    - DEMO-LIKELY-FAIL -> LIKELY_TO_FAIL
    - DEMO-BLOCKED -> BLOCKED
    """
    app_ids = DemoDataSeeder.seed_all_demo_applications(db_session)
    assert len(app_ids) == 4

    expected = {
        "DEMO-READY": ("READY_FOR_REVIEW", 100.0),
        "DEMO-ATTENTION": ("NEEDS_ATTENTION", None),
        "DEMO-LIKELY-FAIL": ("LIKELY_TO_FAIL", None),
        "DEMO-BLOCKED": ("BLOCKED", None),
    }

    for app_id, (expected_status, expected_score) in expected.items():
        app = db_session.query(Application).filter(Application.application_id == app_id).first()
        assert app is not None, f"Application {app_id} was not created"

        val_run = ValidationRunner.run_validation(db=db_session, application_id=app.id)
        assert val_run.overall_status == expected_status, (
            f"Expected {app_id} to be {expected_status}, but got {val_run.overall_status}. "
            f"Findings: {[(f.rule_code, f.status, f.severity) for f in val_run.findings if f.status != 'PASS']}"
        )
        if expected_score is not None:
            assert abs(val_run.score - expected_score) < 0.01, f"Expected score {expected_score}, got {val_run.score}"


def test_demo_seeder_is_idempotent(db_session: Session):
    """
    Re-running the demo seeder multiple times must not crash, duplicate applications,
    or corrupt findings.
    """
    app_ids_1 = DemoDataSeeder.seed_all_demo_applications(db_session)
    total_apps_1 = db_session.query(Application).filter(Application.application_id.like("DEMO-%")).count()

    app_ids_2 = DemoDataSeeder.seed_all_demo_applications(db_session)
    total_apps_2 = db_session.query(Application).filter(Application.application_id.like("DEMO-%")).count()

    assert app_ids_1 == app_ids_2
    assert total_apps_1 == 4
    assert total_apps_2 == 4


def test_validation_summary_pdf_generation(db_session: Session):
    """
    Verify that the Validation Summary PDF generates successfully:
    - File exists and is non-empty (> 0 bytes)
    - Contains the application ID
    - Contains the mandatory disclaimer
    - Contains the SHA-256 reference and page numbering
    """
    DemoDataSeeder.seed_all_demo_applications(db_session)
    inst = db_session.query(Institute).first()
    assert inst is not None

    for target_app_id in ["DEMO-READY", "DEMO-BLOCKED"]:
        rep = ReportService.generate_report(
            db=db_session,
            institute_id=inst.id,
            report_type="Validation Summary",
            report_format="PDF",
            date_range="Current Academic Year",
            application_id=target_app_id,
        )

        assert rep is not None
        assert os.path.exists(rep.file_path)
        assert rep.file_size > 0
        assert os.path.getsize(rep.file_path) > 0

        # Inspect PDF content via PyMuPDF
        doc = pymupdf.open(rep.file_path)
        assert len(doc) >= 1

        all_text = " ".join([page.get_text() for page in doc])
        doc.close()

        # Must contain application id
        assert target_app_id in all_text

        # Must contain mandatory disclaimer
        expected_disclaimer = "AI-generated decision support; final decisions rest with authorised AICTE officials"
        assert expected_disclaimer in all_text

        # Must contain SHA-256 and Page numbering
        assert "SHA-256:" in all_text
        assert "Page 1 of" in all_text


def test_captcha_functionality(client, seed_test_data):
    """
    Verify that the captcha endpoint generates challenges, rejects invalid captcha,
    and accepts verified solutions / development bypass.
    """
    # 1. Fetch challenge
    resp = client.get("/api/auth/captcha")
    assert resp.status_code == 200
    data = resp.json()
    assert "captcha_id" in data
    assert "image_base64" in data
    assert len(data["captcha_id"]) > 0
    assert data["image_base64"].startswith("data:image/png;base64,")

    # 2. Login attempt with invalid captcha -> MUST fail with 400
    bad_login_resp = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",
            "captcha_id": data["captcha_id"],
            "captcha_text": "WRONG_CAPTCHA",
        },
    )
    assert bad_login_resp.status_code == 400
    assert "captcha" in bad_login_resp.json()["detail"].lower()

    # 3. Fetch a fresh challenge for next attempt (challenges are single-use)
    resp2 = client.get("/api/auth/captcha")
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Valid solution using dev bypass -> MUST succeed with 200
    good_login_resp = client.post(
        "/api/auth/login",
        json={
            "role": "INSTITUTE",
            "institute_id": "TEST001",
            "password": "Institute@123",
            "captcha_id": data2["captcha_id"],
            "captcha_text": "12345",
        },
    )
    assert good_login_resp.status_code == 200
    assert "csrf_token" in good_login_resp.json()
