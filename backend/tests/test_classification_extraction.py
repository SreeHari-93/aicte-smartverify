import io
import pytest
from datetime import date, timedelta
import pymupdf as fitz
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.document_classification import DocumentClassification
from backend.app.models.audit_log import AuditLog
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.seed_catalog import seed_catalog_document_types
from backend.app.services.document_pipeline.classifier import DocumentClassifier
from backend.app.services.document_pipeline.extractor import (
    DocumentExtractor,
    parse_and_normalize_date,
)


@pytest.fixture
def seeded_catalog(db_session):
    seed_catalog_document_types(db_session)


@pytest.fixture
def classification_institutes(db_session, seeded_catalog):
    # Institute 1
    inst1 = Institute(
        aicte_institute_id="INST_CLS_01",
        name="Institute of Fire Engineering",
        state="Tamil Nadu",
        status="ACTIVE",
    )
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="inst1_cls@test.edu",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # Institute 2
    inst2 = Institute(
        aicte_institute_id="INST_CLS_02",
        name="Institute of Planning & Architecture",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="inst2_cls@test.edu",
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


def make_pdf_bytes_from_text(lines: list) -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 80
    for line in lines:
        page.insert_text((72, y), line, fontsize=12)
        y += 24
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ==============================================================================
# 1. DATE PARSING VARIANTS
# ==============================================================================
def test_date_parsing_variants():
    """Verify regex and normalizer for diverse date formats to ISO"""
    # DD-MM-YYYY
    res1 = parse_and_normalize_date("Certificate Valid Upto: 24-03-2026")
    assert res1 is not None
    assert res1[1] == "2026-03-24"
    assert res1[2] == date(2026, 3, 24)

    # DD/MM/YYYY
    res2 = parse_and_normalize_date("Completion Date 15/08/2025 by Municipal Corp")
    assert res2 is not None
    assert res2[1] == "2025-08-15"

    # DD.MM.YYYY
    res3 = parse_and_normalize_date("Order issued on 01.12.2024")
    assert res3 is not None
    assert res3[1] == "2024-12-01"

    # ISO YYYY-MM-DD
    res4 = parse_and_normalize_date("Valid from 2026-01-10 to 2027-01-09")
    assert res4 is not None
    assert res4[1] == "2026-01-10"

    # Textual: "11 Nov 2026"
    res5 = parse_and_normalize_date("Expires on 11 Nov 2026 strictly")
    assert res5 is not None
    assert res5[1] == "2026-11-11"

    # Textual: "11th November 2026"
    res6 = parse_and_normalize_date("Signed this 11th November 2026 before Notary")
    assert res6 is not None
    assert res6[1] == "2026-11-11"

    # Textual: "November 11, 2026"
    res7 = parse_and_normalize_date("Execution Date: November 11, 2026")
    assert res7 is not None
    assert res7[1] == "2026-11-11"

    # Invalid / No date
    assert parse_and_normalize_date("Plain text with no numbers") is None


# ==============================================================================
# 2. CLASSIFICATION ON SAMPLE TEXTS
# ==============================================================================
def test_classification_on_sample_texts(db_session, seeded_catalog):
    """
    Test classifier scores weighted keyword hits, issuing authority, and title zone (first 20 lines)
    """
    active_dts = db_session.query(DocumentType).filter(DocumentType.is_active == True).all()

    # Sample A: Fire Safety NOC
    text_fire = """
    GOVERNMENT OF TAMIL NADU
    STATE FIRE & RESCUE SERVICES DEPARTMENT
    OFFICE OF THE DIVISIONAL FIRE OFFICER
    NO OBJECTION CERTIFICATE / FIRE SAFETY CLEARANCE
    NOC Ref Number: NOC-FIRE-2026-8941
    This is to certify that Institute building has installed necessary fire extinguishers,
    hydrant systems and complies with all fire safety regulations.
    Valid Upto: 25-10-2027
    """
    res_fire = DocumentClassifier.classify(ocr_text=text_fire, document_types=active_dts)
    assert res_fire.predicted_type == "FIRE_NOC"
    assert res_fire.score >= 0.5
    assert len(res_fire.candidates) >= 1
    assert any("fire" in kw for kw in res_fire.candidates[0].matched_keywords)

    # Sample B: NBA Accreditation
    text_nba = """
    NATIONAL BOARD OF ACCREDITATION (NBA)
    Accreditation Certificate for Tier-1 Technical Engineering Programmes
    File No: NBA-ENG-TIER1-2026-09
    This is to certify that Computer Science & Engineering programme is accredited
    under Washington Accord norms.
    Valid Upto: 30/06/2028
    """
    res_nba = DocumentClassifier.classify(ocr_text=text_nba, document_types=active_dts)
    assert res_nba.predicted_type == "NBA_CERT"
    assert res_nba.score >= 0.5

    # Sample C: Approved Building Plan
    text_plan = """
    DIRECTORATE OF TOWN AND COUNTRY PLANNING (DTCP)
    MUNICIPAL CORPORATION PLANNING AUTHORITY
    SANCTIONED BUILDING PLAN APPROVAL
    Sanction Order Number: DTCP/BLD/2026/890
    Total Built-Up Area: 12450.5 sq.m
    Survey Numbers: 104/1A, 104/2B
    Architect Blueprint Approved
    """
    res_plan = DocumentClassifier.classify(ocr_text=text_plan, document_types=active_dts)
    assert res_plan.predicted_type == "BUILDING_PLAN"
    assert res_plan.score >= 0.5


# ==============================================================================
# 3. EXPIRY COMPUTATION
# ==============================================================================
def test_expiry_computation(db_session, seeded_catalog):
    """
    Verify DocumentExtractor detects valid_upto, computes days_remaining and is_expired correctly
    """
    fire_dt = db_session.query(DocumentType).filter(DocumentType.code == "FIRE_NOC").first()

    # Case 1: Future expiry date (+45 days)
    future_date = date.today() + timedelta(days=45)
    text_future = f"""
    STATE FIRE & RESCUE SERVICES
    FIRE SAFETY NOC
    NOC Ref Number: NOC-FIRE-2026-777
    Institution Name: SKCET Engineering Campus
    Valid Upto: {future_date.strftime('%d-%m-%Y')}
    """
    ext_future = DocumentExtractor.extract_fields(ocr_text=text_future, doc_type=fire_dt)
    assert ext_future.is_expired is False
    assert ext_future.days_remaining == 45
    assert ext_future.expiry_date == future_date.isoformat()

    # Case 2: Past expiry date (-20 days)
    past_date = date.today() - timedelta(days=20)
    text_past = f"""
    STATE FIRE & RESCUE SERVICES
    FIRE SAFETY NOC
    NOC Ref Number: NOC-FIRE-2025-111
    Institution Name: SKCET Engineering Campus
    Valid Upto: {past_date.strftime('%d-%m-%Y')}
    """
    ext_past = DocumentExtractor.extract_fields(ocr_text=text_past, doc_type=fire_dt)
    assert ext_past.is_expired is True
    assert ext_past.days_remaining == -20
    assert ext_past.expiry_date == past_date.isoformat()


# ==============================================================================
# 4. MISMATCH FLAG AND WARNING
# ==============================================================================
def test_mismatch_flag_when_uploaded_as_different_type(client, classification_institutes, db_session):
    """
    If user uploads a file selecting FIRE_NOC, but content is clearly BUILDING_PLAN:
    - Classifier flags mismatch_flag=True
    - Sets warning message: "Uploaded as FIRE_NOC but content looks like BUILDING_PLAN"
    - Never blocks upload or pipeline execution
    """
    client.cookies.set("aicte_access_token", classification_institutes["token1"])

    plan_lines = [
        "DIRECTORATE OF TOWN AND COUNTRY PLANNING (DTCP)",
        "SANCTIONED BUILDING PLAN APPROVAL",
        "Sanction Order Number: DTCP/2026/BLD-441",
        "Total Built-Up Area: 14500 sq.m",
        "Survey Numbers: 44/1, 44/2",
        "Architect Blueprint Sanctioned by Town Planning Authority",
    ]
    pdf_bytes = make_pdf_bytes_from_text(plan_lines)

    # Upload as FIRE_NOC
    upload_res = client.post(
        "/api/institute/documents",
        data={"document_type_code": "FIRE_NOC"},
        files={"file": ("building_plan.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # Retrieve extraction
    ext_res = client.get(f"/api/institute/documents/{doc_id}/extraction")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()

    assert ext_data["classification"] is not None
    assert ext_data["classification"]["predicted_type"] == "BUILDING_PLAN"
    assert ext_data["classification"]["mismatch_flag"] is True
    assert "Uploaded as FIRE_NOC but content looks like BUILDING_PLAN" in ext_data["classification"]["warning_message"]


# ==============================================================================
# 5. FIELD EXTRACTION, CORRECTION & AUDIT LOGGING
# ==============================================================================
def test_field_correction_audit(client, classification_institutes, db_session):
    """
    Test extraction endpoint and field correction PATCH:
    - Extracted field preserved
    - Corrected value saved with verified_by_user=True
    - AuditLog records before and after values with user ID
    """
    client.cookies.set("aicte_access_token", classification_institutes["token1"])
    user1 = classification_institutes["user1"]

    fire_lines = [
        "STATE FIRE & RESCUE SERVICES DEPARTMENT",
        "FIRE SAFETY CERTIFICATE / NOC",
        "NOC Ref Number: NOC-FIRE-2026-RAW-88",
        "Institution Name: Sri Krishna College of Eng",
        "Valid Upto: 11-11-2027",
    ]
    pdf_bytes = make_pdf_bytes_from_text(fire_lines)

    # 1. Upload
    upload_res = client.post(
        "/api/institute/documents",
        data={"document_type_code": "FIRE_NOC"},
        files={"file": ("fire_noc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 2. GET Extraction
    get_res = client.get(f"/api/institute/documents/{doc_id}/extraction")
    assert get_res.status_code == 200
    get_data = get_res.json()

    fields_dict = {f["key"]: f for f in get_data["fields"]}
    assert "noc_number" in fields_dict
    assert "NOC-FIRE-2026-RAW-88" in fields_dict["noc_number"]["value"]
    assert get_data["expiry_date"] == "2027-11-11"

    # 3. PATCH Field Correction
    corrected_noc = "NOC-FIRE-2026-VERIFIED-99"
    patch_res = client.patch(
        f"/api/institute/documents/{doc_id}/fields/noc_number",
        json={"corrected_value": corrected_noc},
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()
    field_item = patch_data["field"]
    assert field_item["corrected_value"] == corrected_noc
    assert field_item["effective_value"] == corrected_noc
    assert field_item["verified_by_user"] is True
    # Original value preserved
    assert "NOC-FIRE-2026-RAW-88" in field_item["value"]

    # 4. Verify AuditLog
    audit_entry = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "DOCUMENT_FIELD_CORRECTED",
            AuditLog.user_id == user1.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_entry is not None
    assert audit_entry.details["field_key"] == "noc_number"
    assert audit_entry.details["corrected_value"] == corrected_noc


# ==============================================================================
# 6. INSTITUTE ISOLATION FOR EXTRACTION & CORRECTION
# ==============================================================================
def test_institute_isolation_for_extraction_endpoints(client, classification_institutes):
    """
    Institute 2 cannot view or patch Institute 1's extracted fields (returns 404)
    """
    # Upload as Institute 1
    client.cookies.set("aicte_access_token", classification_institutes["token1"])
    pdf_bytes = make_pdf_bytes_from_text(["FIRE SAFETY NOC", "Valid Upto: 25-10-2027"])
    up_res = client.post(
        "/api/institute/documents",
        data={"document_type_code": "FIRE_NOC"},
        files={"file": ("inst1_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # Institute 1 can access
    res1 = client.get(f"/api/institute/documents/{doc_id}/extraction")
    assert res1.status_code == 200

    # Switch to Institute 2
    client.cookies.set("aicte_access_token", classification_institutes["token2"])

    # Institute 2 cannot view
    res2_get = client.get(f"/api/institute/documents/{doc_id}/extraction")
    assert res2_get.status_code == 404
    assert "Document not found or access denied" in res2_get.json()["detail"]

    # Institute 2 cannot patch
    res2_patch = client.patch(
        f"/api/institute/documents/{doc_id}/fields/noc_number",
        json={"corrected_value": "ILLEGAL_CHANGE"},
    )
    assert res2_patch.status_code == 404
    assert "Document not found or access denied" in res2_patch.json()["detail"]

