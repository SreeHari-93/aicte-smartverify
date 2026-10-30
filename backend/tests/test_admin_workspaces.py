import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.document import Document
from backend.app.models.verification import VerificationResult, VerificationStatus
from backend.app.models.anomaly import AnomalyRun, AnomalyFlag, AnomalySeverity, AnomalyReviewStatus
from backend.app.models.complaint import Complaint, ComplaintEvent
from backend.app.models.notification import Notification
from backend.app.models.email_outbox import EmailOutbox
from backend.app.models.audit_log import AuditLog
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token


def get_auth_cookie(user: User):
    role_str = user.role.value if hasattr(user.role, 'value') else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)
    return {"aicte_access_token": token}


def test_rbac_admin_workspaces_protection(client: TestClient, seed_test_data):
    """
    Role protection: Institute users must receive 403 Forbidden on all admin review workspace routes.
    """
    inst_user = seed_test_data["inst_user"]
    inst_cookies = get_auth_cookie(inst_user)

    protected_endpoints = [
        ("GET", "/api/v1/admin/verification-queue", None),
        ("POST", "/api/v1/admin/documents/1/review-decision", {"decision": "APPROVED", "reason": "Test"}),
        ("GET", "/api/v1/admin/anomalies", None),
        ("POST", "/api/v1/admin/anomalies/1/decision", {"decision": "Verified – no concern", "note": "Valid"}),
        ("GET", "/api/v1/admin/complaints", None),
        ("GET", "/api/v1/admin/complaints/1", None),
        ("POST", "/api/v1/admin/complaints/1/reply", {"notes": "Test"}),
        ("GET", "/api/v1/admin/dashboard-stats", None),
    ]

    for method, path, payload in protected_endpoints:
        if method == "GET":
            res = client.get(path, cookies=inst_cookies)
        else:
            res = client.post(path, json=payload, cookies=inst_cookies)
        assert res.status_code == 403, f"Expected 403 for institute user on {path}, got {res.status_code}"


def test_verification_queue_and_decision_override(client: TestClient, db_session, seed_test_data):
    """
    Verification review decisions override automated status while preserving original automated status and audit trail.
    """
    admin_user = seed_test_data["admin_user"]
    inst = seed_test_data["institute"]
    cookies = get_auth_cookie(admin_user)

    # 1. Create a document with an automated mismatch status
    doc = Document(
        institute_id=inst.id,
        original_filename="FIRE_SAFETY_NOC.pdf",
        stored_filename="stored_fire_noc_001.pdf",
        file_path="uploads/stored_fire_noc_001.pdf",
        file_size=10240,
        mime_type="application/pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        status="Needs Attention",
        document_type_code="FIRE_NOC",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    ver = VerificationResult(
        document_id=doc.id,
        status=VerificationStatus.MISMATCH_DETECTED,
        source_name="State Fire Registry Mock",
        source_ref="FIRE-REG-9812",
        details_json={
            "original_automated_status": VerificationStatus.MISMATCH_DETECTED,
            "mismatched_fields": [{"field": "issue_date", "extracted": "2024-01-01", "expected": "2023-01-01"}],
            "message": "Automated date discrepancy detected against State Fire Registry.",
        },
    )
    db_session.add(ver)
    db_session.commit()

    # 2. Query verification queue
    res = client.get("/api/v1/admin/verification-queue", cookies=cookies)
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    target = next((item for item in items if item["document_id"] == doc.id), None)
    assert target is not None
    assert target["status"] == VerificationStatus.MISMATCH_DETECTED
    assert target["original_status"] == VerificationStatus.MISMATCH_DETECTED

    # 3. Officer overrides decision as APPROVED
    review_payload = {
        "decision": "APPROVED",
        "reason": "Physically verified original NOC with State Fire Service Commissioner stamp.",
    }
    decision_res = client.post(
        f"/api/v1/admin/documents/{doc.id}/review-decision",
        json=review_payload,
        cookies=cookies,
    )
    assert decision_res.status_code == 200
    updated_data = decision_res.json()
    assert updated_data["status"] == VerificationStatus.VERIFIED
    assert updated_data["original_status"] == VerificationStatus.MISMATCH_DETECTED
    assert updated_data["manual_decision"] == "APPROVED"
    assert updated_data["manual_reason"] == review_payload["reason"]

    # 4. Verify DB persistence and document status
    db_session.refresh(doc)
    db_session.refresh(ver)
    assert ver.status == VerificationStatus.VERIFIED
    assert doc.status == "Verified"
    assert ver.details_json["original_automated_status"] == VerificationStatus.MISMATCH_DETECTED

    # 5. Check audit trail
    audit = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "DOCUMENT_REVIEW_DECISION", AuditLog.user_id == admin_user.id)
        .first()
    )
    assert audit is not None
    assert "APPROVED" in audit.reason


def test_complaints_isolation_between_institutes(client: TestClient, db_session, seed_test_data):
    """
    Complaints must enforce strict institute isolation.
    An institute can only view and manage its own tickets.
    """
    inst_a = seed_test_data["institute"]
    inst_a_user = seed_test_data["inst_user"]
    admin_user = seed_test_data["admin_user"]

    # Create Institute B and user
    inst_b = Institute(
        aicte_institute_id="TEST002",
        name="Institute B Engineering College",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_b)

    inst_b_user = User(
        email="inst_b@aicte.edu.in",
        password_hash=hash_password("Pass@12345"),
        role=UserRole.INSTITUTE,
        institute_id=inst_b.id,
        is_active=True,
    )
    db_session.add(inst_b_user)
    db_session.commit()

    # Create tickets for A and B
    c_a = Complaint(
        ticket_id="TCK-INSTA-001",
        institute_id=inst_a.id,
        category="Payment Reconciliation",
        subject="Fee Receipt Delayed",
        description="Scrutiny fee paid via NEFT but not confirmed.",
        status="Open",
        priority="HIGH",
    )
    c_b = Complaint(
        ticket_id="TCK-INSTB-002",
        institute_id=inst_b.id,
        category="Technical Portal Issue",
        subject="Upload timeout on Land Deed",
        description="500 error encountered when uploading deed.",
        status="Open",
        priority="MEDIUM",
    )
    db_session.add(c_a)
    db_session.add(c_b)
    db_session.commit()

    cookies_a = get_auth_cookie(inst_a_user)
    cookies_b = get_auth_cookie(inst_b_user)
    cookies_admin = get_auth_cookie(admin_user)

    # Institute A only sees Institute A's complaints
    res_a = client.get("/api/v1/institute/complaints", cookies=cookies_a)
    assert res_a.status_code == 200
    ticket_ids_a = [t["ticket_id"] for t in res_a.json()]
    assert "TCK-INSTA-001" in ticket_ids_a
    assert "TCK-INSTB-002" not in ticket_ids_a

    # Institute A cannot access detail of Institute B's ticket (returns 404)
    res_cross = client.get(f"/api/v1/institute/complaints/{c_b.id}", cookies=cookies_a)
    assert res_cross.status_code == 404

    # Institute A cannot reply to Institute B's ticket
    res_cross_reply = client.post(
        f"/api/v1/institute/complaints/{c_b.id}/reply",
        json={"notes": "Hacked reply"},
        cookies=cookies_a,
    )
    assert res_cross_reply.status_code == 404

    # Admin sees both tickets in complaints inbox
    res_admin = client.get("/api/v1/admin/complaints", cookies=cookies_admin)
    assert res_admin.status_code == 200
    admin_tickets = [t["ticket_id"] for t in res_admin.json()]
    assert "TCK-INSTA-001" in admin_tickets
    assert "TCK-INSTB-002" in admin_tickets


def test_complaint_admin_reply_internal_notes_and_notifications(client: TestClient, db_session, seed_test_data):
    """
    Admin replies:
    1. Internal notes are invisible to the institute.
    2. Public replies create notifications and outbox emails (queued without failing if SMTP unconfigured).
    """
    admin_user = seed_test_data["admin_user"]
    inst_a = seed_test_data["institute"]
    inst_a_user = seed_test_data["inst_user"]

    complaint = Complaint(
        ticket_id="TCK-NOTIF-001",
        institute_id=inst_a.id,
        category="Application Processing Delay",
        subject="Processing query",
        description="When will scrutiny conclude?",
        status="Open",
        priority="MEDIUM",
    )
    db_session.add(complaint)
    db_session.commit()

    cookies_admin = get_auth_cookie(admin_user)
    cookies_inst = get_auth_cookie(inst_a_user)

    # 1. Admin adds an INTERNAL note
    internal_res = client.post(
        f"/api/v1/admin/complaints/{complaint.id}/reply",
        json={
            "notes": "Internal review: finance verified NEFT transaction #TX99102. Safe to resolve.",
            "is_internal": True,
        },
        cookies=cookies_admin,
    )
    assert internal_res.status_code == 200

    # Institute checks ticket detail -> internal note should NOT be present
    inst_check = client.get(f"/api/v1/institute/complaints/{complaint.id}", cookies=cookies_inst)
    assert inst_check.status_code == 200
    inst_events = inst_check.json()["events"]
    assert not any("finance verified NEFT" in e["notes"] for e in inst_events)

    # 2. Admin adds a PUBLIC reply and changes status to 'Resolved'
    public_res = client.post(
        f"/api/v1/admin/complaints/{complaint.id}/reply",
        json={
            "notes": "Transaction confirmed and deficiency cleared. Ticket is resolved.",
            "is_internal": False,
            "new_status": "Resolved",
        },
        cookies=cookies_admin,
    )
    assert public_res.status_code == 200
    assert public_res.json()["status"] == "Resolved"

    # Institute checks ticket detail -> public note IS present
    inst_check_2 = client.get(f"/api/v1/institute/complaints/{complaint.id}", cookies=cookies_inst)
    inst_events_2 = inst_check_2.json()["events"]
    assert any("Transaction confirmed and deficiency cleared" in e["notes"] for e in inst_events_2)

    # Check that in-app notification was created
    notif = (
        db_session.query(Notification)
        .filter(Notification.institute_id == inst_a.id, Notification.type == "COMPLAINT_UPDATE")
        .first()
    )
    assert notif is not None
    assert "TCK-NOTIF-001" in notif.title

    # Check that email was placed into email_outbox with status 'queued (SMTP not configured)'
    outbox = (
        db_session.query(EmailOutbox)
        .filter(EmailOutbox.recipient == inst_a_user.email)
        .first()
    )
    assert outbox is not None
    assert outbox.status == "queued (SMTP not configured)"
    assert "TCK-NOTIF-001" in outbox.subject


def test_forbidden_words_sanitization_in_anomalies(client: TestClient, db_session, seed_test_data):
    """
    Mandatory Wording Rule:
    Never output or store inflammatory terms: 'forgery', 'fraud', or 'misconduct'.
    Always use 'needs verification' or 'potential anomaly'.
    """
    admin_user = seed_test_data["admin_user"]
    inst = seed_test_data["institute"]
    cookies = get_auth_cookie(admin_user)

    doc = Document(
        institute_id=inst.id,
        original_filename="AFFILIATION_LETTER.pdf",
        stored_filename="affil_letter_001.pdf",
        file_path="uploads/affil_letter_001.pdf",
        file_size=20480,
        mime_type="application/pdf",
        sha256_hash="abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        status="Needs Attention",
        document_type_code="AFFILIATION",
    )
    db_session.add(doc)
    db_session.commit()

    run = AnomalyRun(
        document_id=doc.id,
        started_at=datetime.now(timezone.utc),
        detectors_run=["ImageTamperDetector"],
    )
    db_session.add(run)
    db_session.commit()

    # Create a flag with simulated legacy or raw detector text
    flag = AnomalyFlag(
        run_id=run.id,
        document_id=doc.id,
        detector="ImageTamperDetector",
        code="SEAL_TAMPER",
        severity=AnomalySeverity.HIGH,
        reason="Detected potential anomaly: digital manipulation around University seal needs verification.",
        recommended_action="Document needs verification by University Registrar.",
        confidence=0.88,
        review_status=AnomalyReviewStatus.OPEN,
    )
    db_session.add(flag)
    db_session.commit()

    # 1. Fetch anomalies list
    res = client.get("/api/v1/admin/anomalies", cookies=cookies)
    assert res.status_code == 200
    flag_list = res.json()
    for f in flag_list:
        text_blob = f"{f['reason']} {f['recommended_action']} {f.get('review_note') or ''}".lower()
        assert "forgery" not in text_blob, "Forbidden word 'forgery' found in anomaly output!"
        assert "fraud" not in text_blob, "Forbidden word 'fraud' found in anomaly output!"
        assert "misconduct" not in text_blob, "Forbidden word 'misconduct' found in anomaly output!"

    # 2. Officer records decision with intentional test forbidden words in the note
    decision_payload = {
        "decision": "Verified – no concern",
        "note": "Examined physical copy; no sign of forgery or fraud observed in seal.",
    }
    decision_res = client.post(
        f"/api/v1/admin/anomalies/{flag.id}/decision",
        json=decision_payload,
        cookies=cookies,
    )
    assert decision_res.status_code == 200
    updated_flag = decision_res.json()
    assert updated_flag["review_status"] == AnomalyReviewStatus.CONFIRMED_OK

    # Ensure forbidden words were sanitized in review_note
    sanitized_note = updated_flag["review_note"].lower()
    assert "forgery" not in sanitized_note, "Forbidden word 'forgery' was not sanitized in review note!"
    assert "fraud" not in sanitized_note, "Forbidden word 'fraud' was not sanitized in review note!"
    assert "misconduct" not in sanitized_note, "Forbidden word 'misconduct' was not sanitized in review note!"

    # 3. Test decision with 'Needs institute clarification'
    clarify_res = client.post(
        f"/api/v1/admin/anomalies/{flag.id}/decision",
        json={
            "decision": "Needs institute clarification",
            "note": "Please submit clear 300 DPI scan of original university affiliation letter.",
        },
        cookies=cookies,
    )
    assert clarify_res.status_code == 200
    assert clarify_res.json()["review_status"] == AnomalyReviewStatus.NEEDS_ACTION


def test_dashboard_stats_endpoint(client: TestClient, seed_test_data):
    """
    Dashboard stats endpoint returns pending verifications, open anomalies, and open complaints counters.
    """
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    res = client.get("/api/v1/admin/dashboard-stats", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert "pending_verifications_count" in data
    assert "open_anomalies_count" in data
    assert "open_complaints_count" in data
    assert isinstance(data["pending_verifications_count"], int)
    assert isinstance(data["open_anomalies_count"], int)
    assert isinstance(data["open_complaints_count"], int)
