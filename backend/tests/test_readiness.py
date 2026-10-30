import io
import pytest
from datetime import date, timedelta
import pymupdf as fitz
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.application import Application
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.document_classification import DocumentClassification
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.seed_catalog import seed_catalog_document_types
from backend.app.services.document_pipeline.readiness import ReadinessService


@pytest.fixture
def readiness_setup(db_session):
    seed_catalog_document_types(db_session)

    # Categories
    eoa_cat = db_session.query(ApplicationCategory).filter(ApplicationCategory.code == "EOA").first()
    if not eoa_cat:
        eoa_cat = ApplicationCategory(code="EOA", name="Extension of Approval", is_active=True)
        db_session.add(eoa_cat)
        db_session.commit()
        db_session.refresh(eoa_cat)

    # Checklist items for EOA
    fire_dt = db_session.query(DocumentType).filter(DocumentType.code == "FIRE_NOC").first()
    plan_dt = db_session.query(DocumentType).filter(DocumentType.code == "BUILDING_PLAN").first()
    nba_dt = db_session.query(DocumentType).filter(DocumentType.code == "NBA_CERT").first()

    # Clear existing checklist items for test isolation
    db_session.query(ChecklistItem).filter(ChecklistItem.category_id == eoa_cat.id).delete()
    db_session.commit()

    ci_fire = ChecklistItem(
        category_id=eoa_cat.id,
        document_type_id=fire_dt.id,
        is_mandatory=True,
        min_validity_days_remaining=30,
        display_order=1,
        help_text="Fire and Life Safety NOC",
        is_active=True,
    )
    ci_plan = ChecklistItem(
        category_id=eoa_cat.id,
        document_type_id=plan_dt.id,
        is_mandatory=True,
        min_validity_days_remaining=0,
        display_order=2,
        help_text="Approved Building Sanction Plan",
        is_active=True,
    )
    ci_nba = ChecklistItem(
        category_id=eoa_cat.id,
        document_type_id=nba_dt.id,
        is_mandatory=False,
        min_validity_days_remaining=60,
        display_order=3,
        help_text="NBA Accreditation Certificate",
        is_active=True,
    )
    db_session.add_all([ci_fire, ci_plan, ci_nba])
    db_session.commit()

    # Institute 1
    inst1 = Institute(aicte_institute_id="INST_RDY_01", name="Ready Tech College", state="Delhi", status="ACTIVE")
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="inst1_rdy@aicte.edu.in",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # Institute 2
    inst2 = Institute(aicte_institute_id="INST_RDY_02", name="Second Tech Institute", state="Kerala", status="ACTIVE")
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="inst2_rdy@aicte.edu.in",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst2.id,
        is_active=True,
    )
    db_session.add(user2)

    # Admin User
    admin_user = User(
        email="admin_rdy@aicte-india.org",
        password_hash=hash_password("Admin@1234"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)

    # Applications
    app1 = Application(
        institute_id=inst1.id,
        application_id="APP-RDY-001",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="DRAFT",
    )
    app2 = Application(
        institute_id=inst2.id,
        application_id="APP-RDY-002",
        category="EOA",
        academic_year="2026-27",
        programme="Engineering",
        status="DRAFT",
    )
    db_session.add_all([app1, app2])
    db_session.commit()
    db_session.refresh(app1)
    db_session.refresh(app2)

    token1 = create_access_token(user_id=user1.id, role=user1.role)
    token2 = create_access_token(user_id=user2.id, role=user2.role)
    admin_token = create_access_token(user_id=admin_user.id, role=admin_user.role)

    return {
        "inst1": inst1,
        "user1": user1,
        "token1": token1,
        "app1": app1,
        "inst2": inst2,
        "user2": user2,
        "token2": token2,
        "app2": app2,
        "admin_user": admin_user,
        "admin_token": admin_token,
        "eoa_cat": eoa_cat,
        "fire_dt": fire_dt,
        "plan_dt": plan_dt,
        "nba_dt": nba_dt,
    }


def make_test_pdf(text_lines: list) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 80
    for line in text_lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 25
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ==============================================================================
# 1. READINESS STATES EVALUATION
# ==============================================================================
def test_readiness_states_evaluation(db_session, readiness_setup):
    """
    Test all readiness states for checklist items:
    MISSING | UPLOADED | PROCESSING | EXPIRED | EXPIRING_SOON | INCOMPLETE_FIELDS | NEEDS_REVIEW | READY
    """
    app = readiness_setup["app1"]
    fire_dt = readiness_setup["fire_dt"]
    today = date.today()

    # 1. State: MISSING (No documents uploaded)
    res_missing = ReadinessService.evaluate_application(db_session, app)
    fire_item = next(i for i in res_missing.items if i.document_type_code == "FIRE_NOC")
    assert fire_item.status == "MISSING"
    assert "Fire Safety Certificate / NOC" in res_missing.missing_items
    assert res_missing.readiness_percentage == 0.0

    # 2. State: UPLOADED (Document uploaded with ocr_status=PENDING)
    doc_uploaded = Document(
        institute_id=app.institute_id,
        application_id=app.id,
        document_type_id=fire_dt.id,
        document_type_code="FIRE_NOC",
        original_filename="fire_pending.pdf",
        stored_filename="fire_pending_uuid.pdf",
        file_path="mock/path.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_pending_111",
        status="Uploaded",
        ocr_status="PENDING",
    )
    db_session.add(doc_uploaded)
    db_session.commit()

    res_up = ReadinessService.evaluate_application(db_session, app)
    fire_item_up = next(i for i in res_up.items if i.document_type_code == "FIRE_NOC")
    assert fire_item_up.status == "UPLOADED"

    # 3. State: PROCESSING
    doc_uploaded.ocr_status = "PROCESSING"
    db_session.commit()
    res_proc = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_proc.items if i.document_type_code == "FIRE_NOC").status == "PROCESSING"

    # 4. State: EXPIRED (expiry_date < today)
    past_exp = today - timedelta(days=15)
    doc_uploaded.ocr_status = "DONE"
    doc_uploaded.extracted_data = {
        "expiry_date": past_exp.isoformat(),
        "days_remaining": -15,
        "is_expired": True,
    }
    db_session.commit()
    res_exp = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_exp.items if i.document_type_code == "FIRE_NOC").status == "EXPIRED"

    # 5. State: EXPIRING_SOON (days_remaining < min_validity_days_remaining of 30)
    soon_exp = today + timedelta(days=10)
    doc_uploaded.extracted_data = {
        "expiry_date": soon_exp.isoformat(),
        "days_remaining": 10,
        "is_expired": False,
    }
    db_session.commit()
    res_soon = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_soon.items if i.document_type_code == "FIRE_NOC").status == "EXPIRING_SOON"

    # 6. State: INCOMPLETE_FIELDS (valid date, but missing required extraction schema field 'noc_number')
    valid_exp = today + timedelta(days=120)
    doc_uploaded.extracted_data = {
        "expiry_date": valid_exp.isoformat(),
        "days_remaining": 120,
        "is_expired": False,
    }
    db_session.commit()
    res_incomp = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_incomp.items if i.document_type_code == "FIRE_NOC").status == "INCOMPLETE_FIELDS"

    # 7. State: NEEDS_REVIEW (mismatch flag set or field flagged for review)
    # Add fields satisfying schema
    db_session.add_all([
        ExtractedField(document_id=doc_uploaded.id, key="noc_number", value="NOC-777", confidence=0.9, page_no=1),
        ExtractedField(document_id=doc_uploaded.id, key="valid_upto", value=valid_exp.isoformat(), confidence=0.9, page_no=1),
        ExtractedField(document_id=doc_uploaded.id, key="building_name", value="Ready Tech", confidence=0.9, page_no=1),
    ])
    # Set mismatch
    new_dict = dict(doc_uploaded.extracted_data or {})
    new_dict["classification"] = {"mismatch_flag": True, "warning_message": "Type mismatch"}
    doc_uploaded.extracted_data = new_dict
    db_session.commit()
    res_rev = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_rev.items if i.document_type_code == "FIRE_NOC").status == "NEEDS_REVIEW"

    # 8. State: READY (all requirements satisfied)
    new_ready_dict = dict(doc_uploaded.extracted_data or {})
    new_ready_dict["classification"] = {"mismatch_flag": False}
    doc_uploaded.extracted_data = new_ready_dict
    db_session.commit()
    res_ready = ReadinessService.evaluate_application(db_session, app)
    assert next(i for i in res_ready.items if i.document_type_code == "FIRE_NOC").status == "READY"


# ==============================================================================
# 2. DUPLICATE DETECTION
# ==============================================================================
def test_duplicate_detection(client, readiness_setup, db_session):
    """
    Test SHA-256 duplicate detection across documents and applications:
    - Same file uploaded for two different applications or document types
    - Readiness flags is_duplicate=True
    - Admin duplicates endpoint /api/admin/documents/duplicates returns the group
    """
    app1 = readiness_setup["app1"]
    app2 = readiness_setup["app2"]
    shared_hash = "abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    doc1 = Document(
        institute_id=app1.institute_id,
        application_id=app1.id,
        document_type_code="FIRE_NOC",
        original_filename="fire_cert_original.pdf",
        stored_filename="fire_1.pdf",
        file_path="storage/fire_1.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash=shared_hash,
        status="Uploaded",
        ocr_status="DONE",
    )
    doc2 = Document(
        institute_id=app2.institute_id,
        application_id=app2.id,
        document_type_code="BUILDING_PLAN",
        original_filename="building_plan_copy.pdf",
        stored_filename="plan_2.pdf",
        file_path="storage/plan_2.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash=shared_hash,
        status="Uploaded",
        ocr_status="DONE",
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    # 1. Readiness check flags duplicate
    readiness_app1 = ReadinessService.evaluate_application(db_session, app1)
    assert len(readiness_app1.duplicates) > 0
    assert readiness_app1.duplicates[0].duplicate_with_id == doc2.id

    # 2. Admin duplicates endpoint
    client.cookies.set("aicte_access_token", readiness_setup["admin_token"])
    dup_res = client.get("/api/admin/documents/duplicates")
    assert dup_res.status_code == 200
    dup_data = dup_res.json()
    assert len(dup_data) >= 1
    assert any(d["sha256_hash"] == shared_hash for d in dup_data)


# ==============================================================================
# 3. INSTITUTE ISOLATION FOR READINESS ENDPOINTS
# ==============================================================================
def test_institute_isolation_for_readiness_endpoints(client, readiness_setup):
    """
    Institute 1 can access its own application readiness.
    Institute 2 cannot access Institute 1's readiness (404).
    Admin can access any application readiness.
    """
    app1 = readiness_setup["app1"]

    # 1. Institute 1 accesses own readiness -> 200
    client.cookies.set("aicte_access_token", readiness_setup["token1"])
    res1 = client.get(f"/api/institute/applications/{app1.id}/readiness")
    assert res1.status_code == 200
    assert res1.json()["application_number"] == app1.application_id

    # 2. Institute 2 accesses Institute 1's readiness -> 404
    client.cookies.set("aicte_access_token", readiness_setup["token2"])
    res2 = client.get(f"/api/institute/applications/{app1.id}/readiness")
    assert res2.status_code == 404
    assert "Application not found or access denied" in res2.json()["detail"]

    # 3. Admin accesses Institute 1's readiness -> 200
    client.cookies.set("aicte_access_token", readiness_setup["admin_token"])
    res_admin = client.get(f"/api/admin/applications/{app1.id}/readiness")
    assert res_admin.status_code == 200
    assert res_admin.json()["application_id"] == app1.id


# ==============================================================================
# 4. END-TO-END DEMO TEST
# ==============================================================================
def test_end_to_end_demo(client, readiness_setup, db_session):
    """
    Full End-to-End Pipeline Demo:
    1. Institute uploads a sample Fire Safety NOC PDF
    2. OCR extracts digital text and word coordinates
    3. Classifier predicts 'FIRE_NOC' with high score
    4. Extractor extracts 'noc_number', 'valid_upto' (ISO), 'building_name'
    5. Application readiness is queried, showing FIRE_NOC transitioned to READY
    """
    app = readiness_setup["app1"]
    client.cookies.set("aicte_access_token", readiness_setup["token1"])

    future_exp = date.today() + timedelta(days=200)

    pdf_content = [
        "TAMIL NADU FIRE AND RESCUE SERVICES DEPARTMENT",
        "DIVISIONAL FIRE OFFICER CLEARANCE CERTIFICATE",
        "FIRE SAFETY CERTIFICATE / NOC",
        "NOC Ref Number: NOC-FIRE-2026-DEMO-001",
        "Institution / Building Name: Ready Tech College Campus",
        f"Valid Until Date: {future_exp.strftime('%d-%m-%Y')}",
        "This premises has met all statutory life safety installations.",
    ]
    pdf_bytes = make_test_pdf(pdf_content)

    # Step 1: Upload
    upload_res = client.post(
        "/api/institute/documents",
        data={
            "application_id": app.id,
            "document_type_code": "FIRE_NOC",
        },
        files={"file": ("fire_noc_demo.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Step 2: Check Extraction API
    ext_res = client.get(f"/api/institute/documents/{doc_id}/extraction")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()

    # Verify classification
    assert ext_data["classification"]["predicted_type"] == "FIRE_NOC"
    assert ext_data["classification"]["score"] >= 0.5
    assert ext_data["classification"]["mismatch_flag"] is False

    # Verify extraction
    assert ext_data["expiry_date"] == future_exp.isoformat()
    assert ext_data["is_expired"] is False
    assert ext_data["days_remaining"] >= 199

    fields = {f["key"]: f for f in ext_data["fields"]}
    assert "noc_number" in fields
    assert "NOC-FIRE-2026-DEMO-001" in fields["noc_number"]["value"]

    # Step 3: Check Readiness API
    readiness_res = client.get(f"/api/institute/applications/{app.id}/readiness")
    assert readiness_res.status_code == 200
    rdy = readiness_res.json()

    fire_item = next(i for i in rdy["items"] if i["document_type_code"] == "FIRE_NOC")
    assert fire_item["status"] == "READY"
    assert fire_item["document_id"] == doc_id
    assert fire_item["expiry_date"] == future_exp.isoformat()
    assert rdy["readiness_percentage"] > 0.0
