import io
from datetime import date, datetime, timedelta, timezone
import pytest
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.certificate import Certificate
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.notification import Notification
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.notification_service import check_and_create_certificate_notifications


@pytest.fixture
def institute_pair(db_session):
    """Fixture providing two distinct institutes and authenticated clients"""
    # Institute A
    inst_a = Institute(aicte_institute_id="INST_A_01", name="Institute Alpha", state="Delhi", status="ACTIVE")
    db_session.add(inst_a)
    db_session.commit()
    db_session.refresh(inst_a)

    user_a = User(
        email="user_a@alpha.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst_a.id,
        is_active=True,
    )
    db_session.add(user_a)

    # Institute B
    inst_b = Institute(aicte_institute_id="INST_B_02", name="Institute Beta", state="Maharashtra", status="ACTIVE")
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_b)

    user_b = User(
        email="user_b@beta.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst_b.id,
        is_active=True,
    )
    db_session.add(user_b)
    db_session.commit()

    return {"inst_a": inst_a, "user_a": user_a, "inst_b": inst_b, "user_b": user_b}


def test_institute_data_isolation(client, db_session, institute_pair):
    """Verify Institute A can never see or modify Institute B's data"""
    inst_a = institute_pair["inst_a"]
    user_a = institute_pair["user_a"]
    inst_b = institute_pair["inst_b"]
    user_b = institute_pair["user_b"]

    # Seed application & certificate for Institute B
    app_b = Application(
        institute_id=inst_b.id,
        application_id="APP-BETA-001",
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Engineering & Technology",
        status="APPROVED",
    )
    db_session.add(app_b)

    today = date.today()
    cert_b = Certificate(
        institute_id=inst_b.id,
        application_id="APP-BETA-001",
        name="Beta Secret Certificate",
        certificate_id="CERT-BETA-999",
        issue_date=today - timedelta(days=100),
        expiry_date=today + timedelta(days=200),
    )
    db_session.add(cert_b)
    db_session.commit()
    db_session.refresh(cert_b)

    # Generate token for User A
    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    client.cookies.set("aicte_access_token", token_a)

    # 1. User A lists certificates - cert_b MUST NOT be present
    res_certs = client.get("/api/institute/certificates")
    assert res_certs.status_code == 200
    cert_ids = [c["certificate_id"] for c in res_certs.json()["items"]]
    assert "CERT-BETA-999" not in cert_ids

    # 2. User A lists applications - app_b MUST NOT be present
    res_apps = client.get("/api/institute/applications")
    assert res_apps.status_code == 200
    app_ids = [a["application_id"] for a in res_apps.json()["items"]]
    assert "APP-BETA-001" not in app_ids

    # 3. User A attempts to renew Institute B's certificate directly -> MUST return 404
    renew_res = client.post(
        f"/api/institute/certificates/{cert_b.id}/renew",
        json={
            "new_issue_date": str(today),
            "new_expiry_date": str(today + timedelta(days=365)),
        },
    )
    assert renew_res.status_code == 404


def test_computed_certificate_status():
    """Verify certificate status and days remaining are dynamically computed on the server"""
    today = date(2026, 10, 30)

    # 1. Expired certificate (expiry date in the past)
    cert_expired = Certificate(
        institute_id=1,
        name="Fire NOC",
        certificate_id="C-EXP",
        issue_date=today - timedelta(days=380),
        expiry_date=today - timedelta(days=15),
    )
    st, days = cert_expired.compute_status(today)
    assert st == "Expired"
    assert days == -15

    # 2. Expiring soon (within 60 days)
    cert_soon = Certificate(
        institute_id=1,
        name="Building Safety",
        certificate_id="C-SOON",
        issue_date=today - timedelta(days=320),
        expiry_date=today + timedelta(days=45),
    )
    st_soon, days_soon = cert_soon.compute_status(today)
    assert st_soon == "Expiring Soon"
    assert days_soon == 45

    # 3. Valid (more than 60 days)
    cert_valid = Certificate(
        institute_id=1,
        name="AICTE Approval",
        certificate_id="C-VAL",
        issue_date=today - timedelta(days=60),
        expiry_date=today + timedelta(days=300),
    )
    st_val, days_val = cert_valid.compute_status(today)
    assert st_val == "Valid"
    assert days_val == 300


def test_upload_mime_and_magic_bytes_validation(client, db_session, institute_pair):
    """Test server-side magic byte validation: authentic PDF/JPG/PNG succeed, forged files fail"""
    user_a = institute_pair["user_a"]
    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    client.cookies.set("aicte_access_token", token_a)

    # 1. Valid PDF with authentic %PDF header
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res_pdf = client.post(
        "/api/institute/documents",
        files={"file": ("test_doc.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
    )
    assert res_pdf.status_code == 201
    assert res_pdf.json()["mime_type"] == "application/pdf"
    assert len(res_pdf.json()["sha256_hash"]) == 64

    # 2. Forged PDF: claims to be application/pdf but body is plain text
    fake_pdf_content = b"This is not a real PDF file! Plain text."
    res_fake = client.post(
        "/api/institute/documents",
        files={"file": ("malicious.pdf", io.BytesIO(fake_pdf_content), "application/pdf")},
    )
    assert res_fake.status_code == 415
    assert "Invalid file format or corrupted header" in res_fake.json()["detail"]

    # 3. Valid PNG with authentic \x89PNG header
    valid_png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res_png = client.post(
        "/api/institute/documents",
        files={"file": ("test_logo.png", io.BytesIO(valid_png_content), "image/png")},
    )
    assert res_png.status_code == 201


def test_certificate_expiry_notification_job(db_session):
    """Test that daily certificate evaluation generates notifications for 60, 30, 7 day, and expired certs"""
    inst = Institute(aicte_institute_id="INST_NOTIF", name="Notif Institute", state="Kerala", status="ACTIVE")
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    today = date.today()
    # Create certificates with exact target deltas
    c60 = Certificate(institute_id=inst.id, name="Cert 60 Days", certificate_id="C60", issue_date=today - timedelta(days=300), expiry_date=today + timedelta(days=60))
    c30 = Certificate(institute_id=inst.id, name="Cert 30 Days", certificate_id="C30", issue_date=today - timedelta(days=300), expiry_date=today + timedelta(days=30))
    c7 = Certificate(institute_id=inst.id, name="Cert 7 Days", certificate_id="C7", issue_date=today - timedelta(days=300), expiry_date=today + timedelta(days=7))
    cexp = Certificate(institute_id=inst.id, name="Cert Expired", certificate_id="CEXP", issue_date=today - timedelta(days=400), expiry_date=today - timedelta(days=5))

    db_session.add_all([c60, c30, c7, cexp])
    db_session.commit()

    created_count = check_and_create_certificate_notifications(db_session, today)
    assert created_count == 4

    # Verify notifications in database
    notifs = db_session.query(Notification).filter(Notification.institute_id == inst.id).all()
    types = [n.type for n in notifs]
    assert "CERT_EXPIRING_60" in types
    assert "CERT_EXPIRING_30" in types
    assert "CERT_EXPIRING_7" in types
    assert "CERT_EXPIRED" in types

