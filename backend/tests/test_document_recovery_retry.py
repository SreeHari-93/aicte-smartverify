import os
import tempfile
from datetime import datetime, timezone, timedelta
import pytest
import pymupdf as fitz
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.document import Document
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.recovery import recover_stuck_documents


@pytest.fixture
def recovery_test_context(db_session):
    inst = Institute(
        aicte_institute_id="INST_REC_01",
        name="Recovery Test Institute",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    user = User(
        email="recovery_inst@test.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)
    auth_headers = {"Authorization": f"Bearer {token}"}

    return {"inst": inst, "user": user, "headers": auth_headers}


def test_recover_stuck_documents(db_session, recovery_test_context):
    inst = recovery_test_context["inst"]
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(minutes=5)
    recent_time = now - timedelta(seconds=30)

    # Stuck document (>2 mins in PROCESSING)
    stuck_doc = Document(
        institute_id=inst.id,
        original_filename="stuck.pdf",
        stored_filename="stuck_123.pdf",
        file_path="/tmp/stuck.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="abc123stuck",
        status="Processing",
        ocr_status="PROCESSING",
        created_at=old_time,
        processed_at=old_time,
    )

    # Active recent document (<2 mins in PROCESSING)
    active_doc = Document(
        institute_id=inst.id,
        original_filename="active.pdf",
        stored_filename="active_123.pdf",
        file_path="/tmp/active.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="abc123active",
        status="Processing",
        ocr_status="PROCESSING",
        created_at=recent_time,
        processed_at=recent_time,
    )

    db_session.add_all([stuck_doc, active_doc])
    db_session.commit()
    db_session.refresh(stuck_doc)
    db_session.refresh(active_doc)

    recovered = recover_stuck_documents(db_session, max_age_minutes=2)
    assert recovered >= 1

    db_session.refresh(stuck_doc)
    db_session.refresh(active_doc)

    # Stuck doc should now be failed with retry available
    assert stuck_doc.ocr_status == "FAILED"
    assert stuck_doc.status == "Failed – retry available"
    assert "retry available" in stuck_doc.error_message

    # Active doc should remain unchanged
    assert active_doc.ocr_status == "PROCESSING"


def test_retry_document_endpoint(client, db_session, recovery_test_context):
    inst = recovery_test_context["inst"]
    headers = recovery_test_context["headers"]

    # Create temporary PDF file
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        doc_fitz = fitz.open()
        p = doc_fitz.new_page(width=595, height=842)
        p.insert_text((72, 100), "FIRE SAFETY CERTIFICATE\nNOC No: FS-2026-999\nValid until 2027-12-31")
        doc_fitz.save(pdf_path)
        doc_fitz.close()

        doc = Document(
            institute_id=inst.id,
            original_filename="retry_test.pdf",
            stored_filename="retry_test_123.pdf",
            file_path=pdf_path,
            file_size=os.path.getsize(pdf_path),
            mime_type="application/pdf",
            sha256_hash="hash_retry_123",
            status="Failed – retry available",
            ocr_status="FAILED",
            error_message="Simulated failure",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Call POST /api/institute/documents/{id}/retry
        res = client.post(f"/api/institute/documents/{doc.id}/retry", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["document_id"] == doc.id
        assert data["ocr_status"] == "PENDING"

        db_session.refresh(doc)
        assert doc.ocr_status == "DONE"
        assert doc.error_message is None
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_cleanup_placeholders_endpoint(client, db_session, recovery_test_context):
    inst = recovery_test_context["inst"]
    headers = recovery_test_context["headers"]

    # 46-byte placeholder doc
    p_doc = Document(
        institute_id=inst.id,
        original_filename="DEMO-PLACEHOLDER.pdf",
        stored_filename="demo_placeholder_46.pdf",
        file_path="/tmp/demo_placeholder_46.pdf",
        file_size=46,
        mime_type="application/pdf",
        sha256_hash="placeholder_hash_46",
        status="Needs Attention",
        ocr_status="DONE",
    )
    # Real 2048-byte doc
    real_doc = Document(
        institute_id=inst.id,
        original_filename="REAL-DOC.pdf",
        stored_filename="real_doc_2048.pdf",
        file_path="/tmp/real_doc_2048.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="real_hash_2048",
        status="Verified",
        ocr_status="DONE",
    )
    db_session.add_all([p_doc, real_doc])
    db_session.commit()
    db_session.refresh(p_doc)
    db_session.refresh(real_doc)

    p_id = p_doc.id
    r_id = real_doc.id

    # Call POST /api/institute/documents/cleanup-placeholders
    res = client.post("/api/institute/documents/cleanup-placeholders", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert p_id in data["deleted_ids"]
    assert data["deleted_count"] >= 1

    # Verify placeholder is deleted and real document remains
    assert db_session.query(Document).filter(Document.id == p_id).first() is None
    assert db_session.query(Document).filter(Document.id == r_id).first() is not None
