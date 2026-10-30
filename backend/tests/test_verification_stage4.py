import os
import pytest
import pymupdf
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.verification import (
    VerificationResult,
    VerificationStatus,
    AuthoritySource,
    MockRegisterEntry,
)
from backend.app.models.validation_run import ValidationFinding
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.document_pipeline.seed_catalog import seed_catalog_document_types
from backend.app.services.verification.service import VerificationService
from backend.app.services.explainer.root_cause import RootCauseAnalyzer
from backend.app.services.explainer.narrator import ExplainerNarrator, PROHIBITED_WORDS
from backend.app.services.report_service import ReportService
from scripts.demo_stage4 import run_stage4_demo


@pytest.fixture
def stage4_fixture(db_session: Session):
    db_session.query(VerificationResult).delete()
    db_session.query(MockRegisterEntry).delete()
    db_session.query(AuthoritySource).delete()
    db_session.query(ExtractedField).delete()
    db_session.query(Document).delete()
    db_session.commit()

    seed_catalog_document_types(db_session)

    inst = Institute(
        aicte_institute_id="INST_STAGE4_01",
        name="Coimbatore Institute of Engineering and Technology",
        state="Tamil Nadu",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()
    db_session.refresh(inst)

    user = User(
        email="stage4_user@ciet.edu",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.INSTITUTE,
        institute_id=inst.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)

    return {
        "inst": inst,
        "user": user,
        "token": token,
    }


def test_ui_facing_api_fields_in_documents_and_extraction(client: TestClient, db_session: Session, stage4_fixture: dict):
    inst = stage4_fixture["inst"]
    token = stage4_fixture["token"]
    client.cookies.set("aicte_access_token", token)

    # 1. Create Authority Source and Mock Register
    src = AuthoritySource(name="NBA", base_url="/mock-authorities/nba/verify", enabled=True)
    db_session.add(src)

    reg = MockRegisterEntry(
        authority="nba",
        certificate_number="NBA-CIET-2026",
        institute_name=inst.name,
        issue_date="2024-06-01",
        expiry_date="2027-05-31",
        status="VALID",
    )
    db_session.add(reg)
    db_session.commit()

    # 2. Create document with extracted fields
    doc = Document(
        institute_id=inst.id,
        document_type_code="NBA_CERT",
        original_filename="nba_accreditation_ciet.pdf",
        stored_filename="nba_accreditation_ciet.pdf",
        file_path="/tmp/fake_nba.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="abc1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
        status="Uploaded",
        ocr_status="DONE",
        extracted_data={
            "certificate_number": "NBA-CIET-2026",
            "institute_name": inst.name,
            "issue_date": "2024-06-01",
            "expiry_date": "2027-05-31",
        },
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Run verification
    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id, force_reverify=True)
    assert ver_res.status == VerificationStatus.VERIFIED

    # Test GET /api/institute/documents returns verification_status and verification_source
    resp_docs = client.get("/api/institute/documents")
    assert resp_docs.status_code == 200
    docs_data = resp_docs.json()
    assert len(docs_data) >= 1
    found_doc = next(d for d in docs_data if d["id"] == doc.id)
    assert found_doc["verification_status"] == VerificationStatus.VERIFIED
    assert found_doc["verification_source"] == "NBA"

    # Test GET /api/institute/documents/{id}/extraction returns verification section
    resp_ext = client.get(f"/api/institute/documents/{doc.id}/extraction")
    assert resp_ext.status_code == 200
    ext_data = resp_ext.json()
    assert ext_data["verification"] is not None
    ver_sec = ext_data["verification"]
    assert ver_sec["status"] == VerificationStatus.VERIFIED
    assert ver_sec["source_name"] == "NBA"
    assert ver_sec["is_simulated"] is True
    assert len(ver_sec["all_comparisons"]) >= 1

    # Test POST /api/institute/documents/{id}/verify endpoint
    resp_ver = client.post(f"/api/institute/documents/{doc.id}/verify")
    assert resp_ver.status_code == 200
    ver_out = resp_ver.json()
    assert ver_out["status"] == VerificationStatus.VERIFIED
    assert ver_out["source_name"] == "NBA"


def test_explainer_root_cause_and_bilingual_templates():
    # 1. Simulate findings from MISMATCH_DETECTED and SOURCE_UNAVAILABLE
    finding_mismatch = ValidationFinding(
        rule_code="DOC_VERIF_MISMATCH",
        rule_title="Fire NOC Issuing Authority Verification",
        severity="MAJOR",
        status="NEEDS_REVIEW",
        reason="External verification for 'FIRE_NOC' detected mismatched statutory records via Fire Dept.",
        evidence_json=[{
            "document": "FIRE_NOC",
            "document_type": "FIRE_NOC",
            "verification_status": "MISMATCH_DETECTED",
            "source_name": "Fire Dept",
        }],
        suggested_action="Review mismatched certificate fields against authority registers or conduct manual scrutiny.",
    )

    finding_unavail = ValidationFinding(
        rule_code="DOC_VERIF_UNAVAIL",
        rule_title="Municipal NOC Authority Verification",
        severity="MAJOR",
        status="NEEDS_REVIEW",
        reason="External issuing authority source (Municipal Corporation) for 'MUNICIPAL_NOC' is currently unavailable. Routed to manual scrutiny.",
        evidence_json=[{
            "document": "MUNICIPAL_NOC",
            "document_type": "MUNICIPAL_NOC",
            "verification_status": "SOURCE_UNAVAILABLE",
            "source_name": "Municipal Corporation",
        }],
        suggested_action="Refer to admin verification queue for manual scrutiny by committee.",
    )

    # 2. Test RootCauseAnalyzer classifies both as VERIFICATION_FAILED
    cause_1 = RootCauseAnalyzer.classify_finding(finding_mismatch)
    cause_2 = RootCauseAnalyzer.classify_finding(finding_unavail)
    assert cause_1 == "VERIFICATION_FAILED"
    assert cause_2 == "VERIFICATION_FAILED"

    root_causes = RootCauseAnalyzer.analyze_findings([finding_mismatch, finding_unavail])
    assert len(root_causes) >= 1
    for rc in root_causes:
        assert rc.cause_code == "VERIFICATION_FAILED"
        # Headline must be worded as "needs verification"
        assert "needs verification" in rc.headline.lower()
        # Suggested action must be "Official confirmation required"
        assert "Official confirmation required" in rc.ordered_suggested_actions

    # 3. Test English Narrator
    exp_en = ExplainerNarrator.generate_template_explanation(
        root_causes=root_causes,
        application_id="APP-TEST-2026",
        institute_name="Coimbatore Institute",
        lang="en",
    )
    assert len(exp_en["reasons"]) >= 1
    reason_en = exp_en["reasons"][0]["explanation"]
    assert "needs verification" in reason_en
    assert "Official confirmation required" in reason_en
    assert exp_en["how_to_fix"][0]["step"] == "Official confirmation required"

    # Strictly verify NO prohibited words appear
    full_en_text = (exp_en["headline"] + " " + exp_en["plain_summary"] + " " + reason_en).lower()
    for pw in PROHIBITED_WORDS:
        assert pw not in full_en_text

    # 4. Test Hindi Narrator
    exp_hi = ExplainerNarrator.generate_template_explanation(
        root_causes=root_causes,
        application_id="APP-TEST-2026",
        institute_name="Coimbatore Institute",
        lang="hi",
    )
    assert len(exp_hi["reasons"]) >= 1
    reason_hi = exp_hi["reasons"][0]["explanation"]
    assert "आधिकारिक सत्यापन आवश्यक है" in reason_hi
    assert "आधिकारिक पुष्टि आवश्यक है" in reason_hi


def test_validation_summary_pdf_contains_verification_section(db_session: Session, stage4_fixture: dict):
    inst = stage4_fixture["inst"]

    # Create application
    app_rec = Application(
        institute_id=inst.id,
        application_id="APP-PDF-STAGE4",
        category="EOA",
        academic_year="2026-27",
        programme="ENGINEERING_AND_TECHNOLOGY",
        status="SUBMITTED",
    )
    db_session.add(app_rec)
    db_session.commit()
    db_session.refresh(app_rec)

    # Attach document
    doc = Document(
        institute_id=inst.id,
        application_id=app_rec.id,
        document_type_code="FIRE_NOC",
        original_filename="fire_noc_stage4.pdf",
        stored_filename="fire_noc_stage4.pdf",
        file_path="/tmp/fake_fire.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="1111111111111111111111111111111111111111111111111111111111111111",
        status="Uploaded",
        ocr_status="DONE",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    # Add verification result
    ver_res = VerificationResult(
        document_id=doc.id,
        status=VerificationStatus.VERIFIED,
        source_name="Fire Dept Statutory Registry",
        source_ref="FSNOC-2026",
        checked_at=datetime.now(timezone.utc),
        details_json={"message": "Verified against Fire Dept register"},
    )
    db_session.add(ver_res)
    db_session.commit()

    # Generate PDF report
    rep = ReportService.generate_report(
        db=db_session,
        institute_id=inst.id,
        report_type="Validation Summary",
        report_format="PDF",
        date_range="Current Academic Year",
        application_id=app_rec.application_id,
    )

    assert rep is not None
    assert os.path.exists(rep.file_path)

    # Inspect PDF text
    pdf_doc = pymupdf.open(rep.file_path)
    full_pdf_text = " ".join([page.get_text() for page in pdf_doc])
    pdf_doc.close()

    assert "Statutory Document Verification Scrutiny" in full_pdf_text
    assert "FIRE_NOC" in full_pdf_text
    assert "VERIFIED" in full_pdf_text
    assert "Fire Dept" in full_pdf_text


def test_demo_stage4_script_runs_end_to_end():
    # Execute demo_stage4 and confirm it runs without exception
    run_stage4_demo()
