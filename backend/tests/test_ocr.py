import io
import tempfile
import pytest
import pymupdf as fitz
from PIL import Image, ImageDraw
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.document import Document
from backend.app.models.document_page import DocumentPage
from backend.app.models.audit_log import AuditLog
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.ocr import OCRService, PyMuPDFEngine, RapidOCREngine


@pytest.fixture
def ocr_institutes(db_session):
    """Fixture providing two distinct institutes and authentication tokens"""
    # Institute 1
    inst1 = Institute(
        aicte_institute_id="INST_OCR_01",
        name="Institute of Computer Science",
        state="Delhi",
        status="ACTIVE",
    )
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="inst1_admin@delhi.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # Institute 2
    inst2 = Institute(
        aicte_institute_id="INST_OCR_02",
        name="Institute of Applied Robotics",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="inst2_admin@blr.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst2.id,
        is_active=True,
    )
    db_session.add(user2)
    db_session.commit()

    token1 = create_access_token(user_id=user1.id, role=user1.role)
    token2 = create_access_token(user_id=user2.id, role=user2.role)

    return {
        "inst1": inst1,
        "user1": user1,
        "token1": token1,
        "inst2": inst2,
        "user2": user2,
        "token2": token2,
    }


def generate_text_pdf_bytes() -> bytes:
    """Generates an in-memory 2-page digital PDF with selectable text"""
    doc = fitz.open()

    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(
        (72, 100),
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION\nAPPROVAL PROCESS HANDBOOK 2026-27",
        fontsize=14,
    )
    page1.insert_text(
        (72, 150),
        "Institution Name: Institute of Computer Science\nApplication Category: Extension of Approval (EOA)",
        fontsize=11,
    )

    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(
        (72, 100),
        "MANDATORY REGULATORY COMPLIANCE CERTIFICATE\nFire Safety NOC Issued by State Disaster Management",
        fontsize=12,
    )

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def generate_scanned_image_bytes() -> bytes:
    """Generates an in-memory PNG image with rendered text to simulate a scanned document"""
    img = Image.new("RGB", (650, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "AICTE APPROVAL PROCESS 2026-27", fill=(0, 0, 0))
    draw.text((20, 70), "CERTIFICATE OF COMPLIANCE VERIFIED", fill=(0, 0, 0))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_text_pdf_extraction(client, ocr_institutes):
    """
    Test native text PDF extraction via PyMuPDF:
    - Extracts multi-page text
    - Returns word lists with bounding boxes and high confidence
    - Populates DocumentPage records and updates Document status
    """
    client.cookies.set("aicte_access_token", ocr_institutes["token1"])
    pdf_bytes = generate_text_pdf_bytes()

    # Upload digital PDF
    upload_res = client.post(
        "/api/institute/documents",
        files={"file": ("handbook_excerpt.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]

    # Verify OCR retrieval endpoint
    ocr_res = client.get(f"/api/institute/documents/{doc_id}/ocr")
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()

    assert ocr_data["document_id"] == doc_id
    assert ocr_data["ocr_status"] == "DONE"
    assert ocr_data["ocr_engine"] == "pymupdf"
    assert ocr_data["page_count"] == 2
    assert ocr_data["ocr_confidence"] >= 0.9
    assert len(ocr_data["pages"]) == 2

    # Verify Page 1
    p1 = ocr_data["pages"][0]
    assert p1["page_no"] == 1
    assert "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION" in p1["text"]
    assert "APPROVAL PROCESS HANDBOOK" in p1["text"]
    assert len(p1["words"]) > 0
    first_word = p1["words"][0]
    assert "word" in first_word
    assert len(first_word["bbox"]) == 4  # [x0, y0, x1, y1]
    assert first_word["confidence"] >= 0.9

    # Verify Page 2
    p2 = ocr_data["pages"][1]
    assert p2["page_no"] == 2
    assert "Fire Safety NOC" in p2["text"]


def test_image_ocr_generated_image(client, ocr_institutes):
    """
    Test neural image OCR via RapidOCR engine:
    - Processes image files (PNG/JPG)
    - Returns detected text lines and per-token word boxes with confidence
    """
    client.cookies.set("aicte_access_token", ocr_institutes["token1"])
    png_bytes = generate_scanned_image_bytes()

    # Upload test image
    upload_res = client.post(
        "/api/institute/documents",
        files={"file": ("certificate_scan.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Query OCR endpoint
    ocr_res = client.get(f"/api/institute/documents/{doc_id}/ocr")
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()

    assert ocr_data["document_id"] == doc_id
    assert ocr_data["ocr_status"] == "DONE"
    assert ocr_data["ocr_engine"] == "rapidocr"
    assert ocr_data["page_count"] == 1
    assert ocr_data["ocr_confidence"] > 0.5
    assert len(ocr_data["pages"]) == 1

    p1 = ocr_data["pages"][0]
    # Check that OCR recognized text keywords
    text_upper = p1["text"].upper()
    assert "AICTE" in text_upper or "APPROVAL" in text_upper or "CERTIFICATE" in text_upper
    assert len(p1["words"]) > 0
    assert "bbox" in p1["words"][0]


def test_corrupt_file_gives_failed_without_crash(client, ocr_institutes):
    """
    Test graceful error handling on corrupted documents:
    - Valid magic header passes upload filter, but corrupt body fails processing
    - System handles error gracefully: never crashes, marks ocr_status='FAILED'
    - Error message is recorded in database and returned to user
    """
    client.cookies.set("aicte_access_token", ocr_institutes["token1"])

    # Corrupt PDF: valid %PDF header followed by completely unparseable binary garbage
    corrupt_pdf_content = b"%PDF-1.4\n" + b"\xff\xfe\x00\xaa\xbb\xcc\xdd" * 80

    upload_res = client.post(
        "/api/institute/documents",
        files={"file": ("corrupted.pdf", io.BytesIO(corrupt_pdf_content), "application/pdf")},
    )
    # Upload succeeds without crash
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Check OCR endpoint
    ocr_res = client.get(f"/api/institute/documents/{doc_id}/ocr")
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()

    assert ocr_data["ocr_status"] == "FAILED"
    assert ocr_data["error_message"] is not None
    assert len(ocr_data["pages"]) == 0


def test_institute_isolation_for_ocr_endpoints(client, ocr_institutes):
    """
    Test strict multi-tenant institute isolation:
    - Institute 1 can access its own document OCR and reprocess endpoints
    - Institute 2 cannot access Institute 1's document OCR or trigger reprocessing (returns 404)
    """
    # 1. Upload document as Institute 1
    client.cookies.set("aicte_access_token", ocr_institutes["token1"])
    pdf_bytes = generate_text_pdf_bytes()
    upload_res = client.post(
        "/api/institute/documents",
        files={"file": ("inst1_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc1_id = upload_res.json()["id"]

    # Institute 1 can view its OCR
    res1 = client.get(f"/api/institute/documents/{doc1_id}/ocr")
    assert res1.status_code == 200

    # 2. Switch to Institute 2
    client.cookies.set("aicte_access_token", ocr_institutes["token2"])

    # Institute 2 GET OCR -> 404
    res2_get = client.get(f"/api/institute/documents/{doc1_id}/ocr")
    assert res2_get.status_code == 404
    assert "Document not found or access denied" in res2_get.json()["detail"]

    # Institute 2 POST Reprocess -> 404
    res2_reproc = client.post(f"/api/institute/documents/{doc1_id}/reprocess")
    assert res2_reproc.status_code == 404
    assert "Document not found or access denied" in res2_reproc.json()["detail"]


def test_reprocess_document_ocr(client, ocr_institutes, db_session):
    """
    Test document OCR reprocessing:
    - Institute triggers reprocessing for its own document
    - Endpoint returns 200 with status='PENDING'
    - Background task re-executes OCR and updates pages
    """
    client.cookies.set("aicte_access_token", ocr_institutes["token1"])
    pdf_bytes = generate_text_pdf_bytes()

    upload_res = client.post(
        "/api/institute/documents",
        files={"file": ("reprocess_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Trigger reprocess
    reproc_res = client.post(f"/api/institute/documents/{doc_id}/reprocess")
    assert reproc_res.status_code == 200
    reproc_data = reproc_res.json()
    assert reproc_data["document_id"] == doc_id
    assert "re-processing queued" in reproc_data["message"].lower()

    # TestClient runs background task synchronously
    ocr_res = client.get(f"/api/institute/documents/{doc_id}/ocr")
    assert ocr_res.status_code == 200
    assert ocr_res.json()["ocr_status"] == "DONE"
    assert ocr_res.json()["page_count"] == 2


def test_ocr_rotated_and_empty_pages():
    """
    Unit test for edge cases:
    - Empty PDF page
    - Rotated PDF page (90 degrees)
    Ensures safe bounding box calculation and dimensions without crash
    """
    doc = fitz.open()

    # Page 1: Empty page
    doc.new_page(width=595, height=842)

    # Page 2: Rotated page with text
    page2 = doc.new_page(width=595, height=842)
    page2.set_rotation(90)
    page2.insert_text((100, 100), "ROTATED LANDSCAPE ORIENTATION TEXT")

    pdf_bytes = doc.write()
    doc.close()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name

    try:
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)

        result = PyMuPDFEngine().process_document(
            file_path=tmp_path,
            mime_type="application/pdf",
            max_pages=20,
            timeout_sec=60,
        )

        assert result.page_count == 2
        assert result.pages[0].text == ""  # Empty page handled cleanly
        assert "ROTATED" in result.pages[1].text  # Rotated page text extracted
    finally:
        import os
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
