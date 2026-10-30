import os
import tempfile
import pytest
import pymupdf as fitz

from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.extractor import (
    DocumentExtractor,
    parse_and_normalize_date,
)
from backend.app.services.document_pipeline.classifier import DocumentClassifier
from backend.app.services.document_pipeline.ocr import OCRService


@pytest.fixture
def doc_types_fixture(db_session):
    """Ensure standard DocumentTypes exist in DB"""
    dts = [
        DocumentType(
            code="FIRE_NOC",
            name="Fire Safety Certificate / NOC",
            issuing_authority="State Fire & Rescue Services Department",
            has_expiry=True,
            default_validity_months=12,
            extraction_schema=[
                {"key": "noc_number", "label": "NOC Ref Number", "type": "id", "required": True},
                {"key": "valid_upto", "label": "Valid Until Date", "type": "date", "required": True},
                {"key": "building_name", "label": "Institution / Building Name", "type": "text", "required": True},
            ],
            keywords=["fire", "safety", "noc", "rescue", "clearance"],
            is_active=True,
        ),
        DocumentType(
            code="OCCUPANCY_CERT",
            name="Occupancy / Completion Certificate",
            issuing_authority="Municipal Corporation / Town Planning Authority",
            has_expiry=False,
            extraction_schema=[
                {"key": "certificate_number", "label": "Certificate Number", "type": "id", "required": True},
                {"key": "completion_date", "label": "Date of Completion", "type": "date", "required": True},
            ],
            keywords=["occupancy", "completion", "fit"],
            is_active=True,
        ),
        DocumentType(
            code="NBA_ACCREDITATION",
            name="NBA Accreditation Certificate",
            issuing_authority="National Board of Accreditation",
            has_expiry=True,
            default_validity_months=36,
            extraction_schema=[
                {"key": "certificate_number", "label": "Accreditation Number", "type": "id", "required": True},
                {"key": "valid_upto", "label": "Valid Upto Date", "type": "date", "required": True},
            ],
            keywords=["nba", "accreditation", "tier"],
            is_active=True,
        ),
        DocumentType(
            code="POLLUTION_NOC",
            name="Pollution Control Board Consent / NOC",
            issuing_authority="State Pollution Control Board",
            has_expiry=True,
            default_validity_months=12,
            extraction_schema=[
                {"key": "certificate_number", "label": "Consent Number", "type": "id", "required": True},
                {"key": "valid_upto", "label": "Valid Upto Date", "type": "date", "required": True},
            ],
            keywords=["pollution", "consent", "operate", "pcb"],
            is_active=True,
        ),
        DocumentType(
            code="AFFIDAVIT",
            name="Statutory Affidavit (Rules & AICTE Hand Book)",
            issuing_authority="Judicial / Executive Magistrate",
            has_expiry=False,
            extraction_schema=[
                {"key": "affidavit_number", "label": "Notary / Stamp Number", "type": "id", "required": True},
            ],
            keywords=["affidavit", "notary", "stamp", "oath"],
            is_active=True,
        ),
    ]

    for dt in dts:
        existing = db_session.query(DocumentType).filter(DocumentType.code == dt.code).first()
        if not existing:
            db_session.add(dt)
        else:
            existing.extraction_schema = dt.extraction_schema
            existing.issuing_authority = dt.issuing_authority
            existing.keywords = dt.keywords
    db_session.commit()
    return db_session.query(DocumentType).filter(DocumentType.is_active == True).all()


def test_fire_noc_field_extraction(doc_types_fixture):
    """
    Test Fire NOC extraction using the exact test text specified by user:
      Certificate Number: FSNOC-SKCET-2026-VAL
      Issued To: Sri Krishna College of Engineering and Technology
      Building Name: Sri Krishna College of Engineering and Technology
      Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008
      AICTE Institute ID: SKCET01
      Date of Issue: 02-07-2026
      Valid Upto: 02-07-2027
    """
    text = (
        "Fire & Life Safety No Objection Certificate\n"
        "Certificate Number: FSNOC-SKCET-2026-VAL\n"
        "Issued To: Sri Krishna College of Engineering and Technology\n"
        "Building Name: Sri Krishna College of Engineering and Technology\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "AICTE Institute ID: SKCET01\n"
        "Date of Issue: 02-07-2026\n"
        "Valid Upto: 02-07-2027\n"
    )

    # 1. Classification
    cls_res = DocumentClassifier.classify(ocr_text=text, document_types=doc_types_fixture)
    assert cls_res.predicted_type == "FIRE_NOC"
    assert cls_res.score >= 0.80, f"Expected classification score >= 0.80, got {cls_res.score}"

    # 2. Extraction
    fire_dt = next(dt for dt in doc_types_fixture if dt.code == "FIRE_NOC")
    ext_res = DocumentExtractor.extract_fields(ocr_text=text, doc_type=fire_dt)
    field_map = {f.key: f for f in ext_res.fields}

    # Problem 1: valid_upto must be 2027-07-02, NOT 2026-07-02
    assert "valid_upto" in field_map, "valid_upto missing"
    assert field_map["valid_upto"].normalized_value == "2027-07-02"
    assert ext_res.expiry_date == "2027-07-02"

    # Problem 2: building_name must be full institute name, NEVER just 'Name'
    assert "building_name" in field_map, "building_name missing"
    assert field_map["building_name"].value == "Sri Krishna College of Engineering and Technology"
    assert field_map["building_name"].value != "Name"

    # Problem 3: Common fields extracted
    assert "institute_name" in field_map
    assert field_map["institute_name"].value == "Sri Krishna College of Engineering and Technology"

    assert "issue_date" in field_map
    assert field_map["issue_date"].normalized_value == "2026-07-02"
    assert ext_res.issue_date == "2026-07-02"

    assert "address" in field_map
    assert field_map["address"].value == "Kuniamuthur, Coimbatore, Tamil Nadu 641008"

    assert "aicte_id" in field_map
    assert field_map["aicte_id"].value == "SKCET01"

    # Check certificate number
    cert_field = field_map.get("noc_number") or field_map.get("certificate_number")
    assert cert_field is not None
    assert cert_field.value == "FSNOC-SKCET-2026-VAL"


def test_occupancy_cert_variant(doc_types_fixture):
    text = (
        "Building Occupancy Certificate\n"
        "Certificate Number: OCC-2026-8841\n"
        "Issued To: Sri Krishna College of Engineering and Technology\n"
        "Building Name: Engineering Block A\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "AICTE Institute ID: SKCET01\n"
        "Date of Issue: 15-03-2026\n"
        "Date of Completion: 10-03-2026\n"
    )

    cls_res = DocumentClassifier.classify(ocr_text=text, document_types=doc_types_fixture)
    assert cls_res.predicted_type == "OCCUPANCY_CERT"
    assert cls_res.score >= 0.80

    occ_dt = next(dt for dt in doc_types_fixture if dt.code == "OCCUPANCY_CERT")
    ext_res = DocumentExtractor.extract_fields(ocr_text=text, doc_type=occ_dt)
    field_map = {f.key: f for f in ext_res.fields}

    assert field_map["certificate_number"].value == "OCC-2026-8841"
    assert field_map["institute_name"].value == "Sri Krishna College of Engineering and Technology"
    assert field_map["building_name"].value == "Engineering Block A"
    assert field_map["completion_date"].normalized_value == "2026-03-10"
    assert field_map["issue_date"].normalized_value == "2026-03-15"
    assert field_map["address"].value == "Kuniamuthur, Coimbatore, Tamil Nadu 641008"
    assert field_map["aicte_id"].value == "SKCET01"


def test_nba_accreditation_variant(doc_types_fixture):
    text = (
        "NBA Accreditation Certificate\n"
        "Certificate Number: NBA-ACCR-2026-092\n"
        "Issued To: Sri Krishna College of Engineering and Technology\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "AICTE Institute ID: SKCET01\n"
        "Date of Issue: 01-06-2026\n"
        "Valid Upto: 30-06-2029\n"
    )

    cls_res = DocumentClassifier.classify(ocr_text=text, document_types=doc_types_fixture)
    assert cls_res.predicted_type == "NBA_ACCREDITATION"
    assert cls_res.score >= 0.80

    nba_dt = next(dt for dt in doc_types_fixture if dt.code == "NBA_ACCREDITATION")
    ext_res = DocumentExtractor.extract_fields(ocr_text=text, doc_type=nba_dt)
    field_map = {f.key: f for f in ext_res.fields}

    assert field_map["certificate_number"].value == "NBA-ACCR-2026-092"
    assert field_map["institute_name"].value == "Sri Krishna College of Engineering and Technology"
    assert field_map["valid_upto"].normalized_value == "2029-06-30"
    assert field_map["issue_date"].normalized_value == "2026-06-01"
    assert ext_res.expiry_date == "2029-06-30"
    assert ext_res.issue_date == "2026-06-01"


def test_pollution_noc_variant(doc_types_fixture):
    text = (
        "Consent to Operate\n"
        "Consent Order No: PCB-CTO-2026-441\n"
        "Issued To: Sri Krishna College of Engineering and Technology\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "AICTE Institute ID: SKCET01\n"
        "Date of Issue: 2026-04-01\n"
        "Valid Till: 2027-03-31\n"
    )

    cls_res = DocumentClassifier.classify(ocr_text=text, document_types=doc_types_fixture)
    assert cls_res.predicted_type == "POLLUTION_NOC"
    assert cls_res.score >= 0.80

    pcb_dt = next(dt for dt in doc_types_fixture if dt.code == "POLLUTION_NOC")
    ext_res = DocumentExtractor.extract_fields(ocr_text=text, doc_type=pcb_dt)
    field_map = {f.key: f for f in ext_res.fields}

    cert_field = field_map.get("certificate_number") or field_map.get("order_number")
    assert cert_field is not None
    assert cert_field.value == "PCB-CTO-2026-441"
    assert field_map["institute_name"].value == "Sri Krishna College of Engineering and Technology"
    assert field_map["valid_upto"].normalized_value == "2027-03-31"
    assert field_map["issue_date"].normalized_value == "2026-04-01"
    assert ext_res.expiry_date == "2027-03-31"


def test_affidavit_variant(doc_types_fixture):
    text = (
        "Notarized Affidavit\n"
        "Affidavit Number: AFF-2026-9021\n"
        "Issued To: Sri Krishna College of Engineering and Technology\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "AICTE Institute ID: SKCET01\n"
        "Date of Issue: 2 July 2026\n"
    )

    cls_res = DocumentClassifier.classify(ocr_text=text, document_types=doc_types_fixture)
    assert cls_res.predicted_type == "AFFIDAVIT"
    assert cls_res.score >= 0.80

    aff_dt = next(dt for dt in doc_types_fixture if dt.code == "AFFIDAVIT")
    ext_res = DocumentExtractor.extract_fields(ocr_text=text, doc_type=aff_dt)
    field_map = {f.key: f for f in ext_res.fields}

    cert_field = field_map.get("affidavit_number") or field_map.get("certificate_number")
    assert cert_field is not None
    assert cert_field.value == "AFF-2026-9021"
    assert field_map["institute_name"].value == "Sri Krishna College of Engineering and Technology"
    assert field_map["issue_date"].normalized_value == "2026-07-02"
    assert ext_res.issue_date == "2026-07-02"


def test_date_normalization_formats():
    """
    Assert support for DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD, '2 July 2027', etc.
    """
    cases = [
        ("02-07-2026", "2026-07-02"),
        ("02/07/2026", "2026-07-02"),
        ("2026-07-02", "2026-07-02"),
        ("2 July 2027", "2027-07-02"),
        ("2nd July 2027", "2027-07-02"),
        ("July 2, 2027", "2027-07-02"),
        ("31-12-2026", "2026-12-31"),
        ("15/03/2026", "2026-03-15"),
    ]
    for raw, expected_iso in cases:
        parsed = parse_and_normalize_date(f"Text before {raw} text after")
        assert parsed is not None, f"Failed to parse '{raw}'"
        raw_m, iso_str, _ = parsed
        assert iso_str == expected_iso, f"Expected {expected_iso} for '{raw}', got {iso_str}"


def test_re_extract_on_retry(client, db_session, doc_types_fixture):
    """
    Test that an existing document re-extracts all fields properly on Retry.
    """
    inst = Institute(
        aicte_institute_id="SKCET_INST",
        name="Sri Krishna College of Engineering and Technology",
        state="Tamil Nadu",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    user = User(
        email="skcet_retry_test@aicte.edu.in",
        password_hash=hash_password("Pass@1234"),
        role=UserRole.INSTITUTE,
        institute_id=inst.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user_id=user.id, role="INSTITUTE")
    headers = {"Authorization": f"Bearer {token}"}

    # Create temporary PDF with exact test content
    fd, pdf_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        doc_fitz = fitz.open()
        p = doc_fitz.new_page(width=595, height=842)
        content = (
            "Fire & Life Safety No Objection Certificate\n"
            "Certificate Number: FSNOC-SKCET-2026-VAL\n"
            "Issued To: Sri Krishna College of Engineering and Technology\n"
            "Building Name: Sri Krishna College of Engineering and Technology\n"
            "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
            "AICTE Institute ID: SKCET01\n"
            "Date of Issue: 02-07-2026\n"
            "Valid Upto: 02-07-2027\n"
        )
        p.insert_text((72, 100), content, fontsize=12)
        doc_fitz.save(pdf_path)
        doc_fitz.close()

        # Insert doc in DB in a prior state
        doc = Document(
            institute_id=inst.id,
            original_filename="test_fire_noc_retry.pdf",
            stored_filename="test_fire_noc_retry.pdf",
            file_path=pdf_path,
            file_size=os.path.getsize(pdf_path),
            mime_type="application/pdf",
            sha256_hash="hash_retry_fire_noc",
            status="Failed – retry available",
            ocr_status="FAILED",
            document_type_code="FIRE_NOC",
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)

        # Trigger Retry endpoint
        res = client.post(f"/api/institute/documents/{doc.id}/retry", headers=headers)
        assert res.status_code == 200

        # Background task executes synchronously in TestClient
        db_session.refresh(doc)
        assert doc.ocr_status == "DONE"

        # Verify re-extracted fields in extracted_data
        data = doc.extracted_data or {}
        assert data.get("valid_upto") in ("2027-07-02", "02-07-2027")
        assert data.get("expiry_date") == "2027-07-02"
        assert data.get("issue_date") == "2026-07-02"
        assert data.get("building_name") == "Sri Krishna College of Engineering and Technology"
        assert data.get("building_name") != "Name"
        assert data.get("institute_name") == "Sri Krishna College of Engineering and Technology"
        assert data.get("address") == "Kuniamuthur, Coimbatore, Tamil Nadu 641008"
        assert data.get("aicte_id") == "SKCET01"

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

