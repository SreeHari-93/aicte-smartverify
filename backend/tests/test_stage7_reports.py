import os
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import fitz  # PyMuPDF

from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.validation_run import ValidationRun, ValidationFinding
from backend.app.models.report import Report
from backend.app.models.notification import Notification
from backend.app.security.tokens import create_access_token
from backend.app.security.password import hash_password
from backend.app.services.report_service import ReportService
from backend.app.services.validation.runner import ValidationRunner


def get_auth_cookie(user: User):
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)
    return {"aicte_access_token": token}


def test_pdf_generates_and_non_empty_for_all_four_statuses(db_session, seed_test_data):
    """
    Ensure ReportService generates non-empty PDFs for all 4 overall statuses:
    BLOCKED, LIKELY_TO_FAIL, NEEDS_ATTENTION, and READY_FOR_REVIEW.
    """
    inst = seed_test_data["institute"]

    app = Application(
        institute_id=inst.id,
        application_id="APP-TEST-STAGE7-01",
        category="Extension of Approval (EOA)",
        academic_year="2026-27",
        programme="Engineering & Technology",
        status="Submitted",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Document
    doc = Document(
        institute_id=inst.id,
        application_id=app.id,
        document_type_code="FIRE_SAFETY",
        original_filename="fire_safety_noc.pdf",
        stored_filename="test_fire.pdf",
        file_path="backend/demo_data/test_fire.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="abc123hash",
        status="Uploaded",
        ocr_status="COMPLETED",
    )
    db_session.add(doc)
    db_session.commit()

    statuses_and_findings = [
        ("BLOCKED", [
            {"code": "RULE_LAND_001", "sev": "BLOCKER", "st": "FAIL", "reason": "Land title deed deficient. Minimum 5.0 acres required."}
        ]),
        ("LIKELY_TO_FAIL", [
            {"code": "RULE_FAC_001", "sev": "MAJOR", "st": "FAIL", "reason": "Faculty cadre ratio non-compliant."},
            {"code": "RULE_LAB_002", "sev": "MAJOR", "st": "FAIL", "reason": "Computer lab capacity below threshold."}
        ]),
        ("NEEDS_ATTENTION", [
            {"code": "RULE_DOC_003", "sev": "MINOR", "st": "WARNING", "reason": "Minor ambiguity in affidavit notarization date."}
        ]),
        ("READY_FOR_REVIEW", [
            {"code": "RULE_ALL_PASS", "sev": "ADVISORY", "st": "PASS", "reason": "All statutory parameters verified successfully."}
        ]),
    ]

    for expected_status, findings in statuses_and_findings:
        val_run = ValidationRun(
            application_id=app.id,
            ruleset_version="v2026.1",
            status="COMPLETED",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            overall_status=expected_status,
            score=85.0 if expected_status == "READY_FOR_REVIEW" else 45.0,
            blocker_count=1 if expected_status == "BLOCKED" else 0,
            major_count=2 if expected_status == "LIKELY_TO_FAIL" else 0,
            minor_count=1 if expected_status == "NEEDS_ATTENTION" else 0,
            advisory_count=0,
            summary_json={"total_checks": len(findings)},
        )
        db_session.add(val_run)
        db_session.commit()
        db_session.refresh(val_run)

        for f in findings:
            vf = ValidationFinding(
                run_id=val_run.id,
                rule_code=f["code"],
                rule_version="v2026.1",
                rule_title=f["code"],
                severity=f["sev"],
                status=f["st"],
                reason=f["reason"],
                evidence_json=[],
                suggested_action="Remediate deficiency in line with AICTE handbook.",
            )
            db_session.add(vf)
        db_session.commit()

        # Generate report
        rep = ReportService.generate_report(
            db=db_session,
            institute_id=inst.id,
            report_type="Validation Summary",
            report_format="PDF",
            date_range="Current",
            application_id=app.application_id,
            language="en",
            generated_by="TEST_RUNNER",
        )

        assert rep is not None
        assert os.path.exists(rep.file_path)
        file_size = os.path.getsize(rep.file_path)
        assert file_size > 1000, f"PDF for {expected_status} is suspiciously small: {file_size} bytes"

        # Verify PDF is valid via PyMuPDF
        doc_pdf = fitz.open(rep.file_path)
        assert doc_pdf.page_count >= 1
        full_text = "".join(page.get_text() for page in doc_pdf)
        doc_pdf.close()

        # Assert status text or related badge exists in document
        assert expected_status.replace("_", " ") in full_text or expected_status in full_text


def test_forbidden_words_never_appear_in_pdf_text(db_session, seed_test_data):
    """
    Ensure forbidden words ('forgery', 'fraud', 'misconduct') are strictly sanitized
    and replaced across all generated PDF text, and that the AICTE principle
    'Rules decide, AI explains, Officials approve.' is present.
    """
    inst = seed_test_data["institute"]

    app = Application(
        institute_id=inst.id,
        application_id="APP-TEST-SANITIZE-01",
        category="Extension of Approval (EOA)",
        academic_year="2026-27",
        programme="Engineering & Technology",
        status="Submitted",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Inject finding with forbidden words
    val_run = ValidationRun(
        application_id=app.id,
        ruleset_version="v2026.1",
        status="COMPLETED",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        overall_status="BLOCKED",
        score=20.0,
        blocker_count=1,
        major_count=1,
        minor_count=0,
        advisory_count=0,
    )
    db_session.add(val_run)
    db_session.commit()
    db_session.refresh(val_run)

    vf1 = ValidationFinding(
        run_id=val_run.id,
        rule_code="DOC_TAMPER_01",
        rule_version="v2026.1",
        rule_title="Potential Document Discrepancy",
        severity="BLOCKER",
        status="FAIL",
        reason="Suspected forgery and fraud detected in land document. Gross misconduct noted.",
        evidence_json=[],
        suggested_action="Investigate suspected forgery and fraud immediately.",
    )
    db_session.add(vf1)
    db_session.commit()

    rep = ReportService.generate_report(
        db=db_session,
        institute_id=inst.id,
        report_type="Validation Summary",
        report_format="PDF",
        date_range="Current",
        application_id=app.application_id,
        language="en",
        generated_by="TEST_OFFICIAL",
    )

    doc_pdf = fitz.open(rep.file_path)
    full_text = "".join(page.get_text() for page in doc_pdf).lower()
    doc_pdf.close()

    # Assert forbidden words do not appear anywhere in the PDF
    assert "forgery" not in full_text, "Found forbidden word 'forgery' in generated PDF!"
    assert "fraud" not in full_text, "Found forbidden word 'fraud' in generated PDF!"
    assert "misconduct" not in full_text, "Found forbidden word 'misconduct' in generated PDF!"

    # Assert AICTE principle is present
    raw_pdf = fitz.open(rep.file_path)
    full_raw = "".join(page.get_text() for page in raw_pdf)
    raw_pdf.close()
    assert "Rules decide, AI explains, Officials approve." in full_raw


def test_institute_isolation_report_endpoints(client: TestClient, db_session, seed_test_data):
    """
    Ensure institute isolation:
    Institute A cannot access or download Application or Report of Institute B (returns 403 Forbidden).
    """
    inst_a = seed_test_data["institute"]
    user_a = seed_test_data["inst_user"]

    # Create Institute B
    inst_b = Institute(
        aicte_institute_id="TEST002-ISOLATE",
        name="Second Isolated Institute",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_b)

    user_b = User(
        email="inst_b_user@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst_b.id,
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()
    db_session.refresh(user_b)

    # Create Application for Institute A
    app_a = Application(
        institute_id=inst_a.id,
        application_id="APP-INST-A-001",
        category="New Institute Approval",
        academic_year="2026-27",
        programme="Management",
        status="Submitted",
    )
    db_session.add(app_a)
    db_session.commit()
    db_session.refresh(app_a)

    # User B tries to download Institute A's report.pdf -> should be 403 Forbidden
    cookie_b = get_auth_cookie(user_b)
    res_forbidden = client.get(
        f"/api/institute/applications/{app_a.application_id}/report.pdf",
        cookies=cookie_b,
    )
    assert res_forbidden.status_code == 403, f"Expected 403 Forbidden, got {res_forbidden.status_code}"

    # User A downloads own report.pdf -> should be 200 OK
    cookie_a = get_auth_cookie(user_a)
    res_ok = client.get(
        f"/api/institute/applications/{app_a.application_id}/report.pdf",
        cookies=cookie_a,
    )
    assert res_ok.status_code == 200, f"Expected 200 OK, got {res_ok.status_code}"
    assert res_ok.headers["content-type"] == "application/pdf"
    assert "attachment" in res_ok.headers.get("content-disposition", "").lower()

    # Report download by report ID isolation test
    rep_a = db_session.query(Report).filter(Report.institute_id == inst_a.id).first()
    assert rep_a is not None

    # User B tries to download rep_a by ID -> 403 Forbidden
    res_rep_forbidden = client.get(
        f"/api/institute/reports/{rep_a.id}/download",
        cookies=cookie_b,
    )
    assert res_rep_forbidden.status_code == 403, f"Expected 403 Forbidden, got {res_rep_forbidden.status_code}"

    # User A downloads rep_a by ID -> 200 OK
    res_rep_ok = client.get(
        f"/api/institute/reports/{rep_a.id}/download",
        cookies=cookie_a,
    )
    assert res_rep_ok.status_code == 200


def test_hindi_report_generates(client: TestClient, db_session, seed_test_data):
    """
    Ensure report generation in Hindi (lang=hi) works without Devanagari font crashes
    and produces non-empty output.
    """
    inst = seed_test_data["institute"]
    admin = seed_test_data["admin_user"]

    app = Application(
        institute_id=inst.id,
        application_id="APP-TEST-HINDI-01",
        category="Extension of Approval (EOA)",
        academic_year="2026-27",
        programme="Engineering",
        status="Submitted",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Admin requests Hindi report
    admin_cookie = get_auth_cookie(admin)
    res = client.get(
        f"/api/admin/applications/{app.application_id}/report.pdf?lang=hi",
        cookies=admin_cookie,
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000

    # Query DB report record
    saved_rep = (
        db_session.query(Report)
        .filter(Report.application_id == app.application_id, Report.language == "hi")
        .first()
    )
    assert saved_rep is not None
    assert saved_rep.language == "hi"
    assert "OFFICIAL" in saved_rep.generated_by or "admin" in saved_rep.generated_by.lower()


def test_in_app_notification_on_validation_status_change(db_session, seed_test_data):
    """
    Ensure that when a validation run finishes and the overall status changes,
    an in-app notification is created for the institute with link='/institute/reports'.
    """
    inst = seed_test_data["institute"]

    app = Application(
        institute_id=inst.id,
        application_id="APP-TEST-NOTIF-01",
        category="Extension of Approval (EOA)",
        academic_year="2026-27",
        programme="Engineering",
        status="Submitted",
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    # Initial count of notifications
    initial_notifs = db_session.query(Notification).filter(Notification.institute_id == inst.id).count()

    # Run validation
    val_run = ValidationRunner.run_validation(
        db=db_session,
        application_id=app.id,
        triggered_by=seed_test_data["inst_user"].id,
    )

    # Assert notification was created
    new_notifs = (
        db_session.query(Notification)
        .filter(
            Notification.institute_id == inst.id,
            Notification.type == "VALIDATION_STATUS_CHANGED",
        )
        .all()
    )
    assert len(new_notifs) > 0
    latest_notif = new_notifs[-1]
    assert latest_notif.link == "/institute/reports"
    assert "Validation Status Updated" in latest_notif.title

