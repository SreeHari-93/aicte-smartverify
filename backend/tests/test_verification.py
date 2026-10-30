import os
import time
import json
import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session

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
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.demo_data import create_synthetic_pdf, DemoDataSeeder
from backend.app.services.document_pipeline.seed_catalog import seed_catalog_document_types
from backend.app.services.verification import (
    VerificationService,
    VerificationComparator,
    circuit_breaker,
    CircuitBreakerOpenException,
    SourceUnavailableException,
)
from backend.app.services.rule_engine.context import EvaluationContext
from backend.app.services.rule_engine.evaluators.external_verification import ExternalVerificationEvaluator
from backend.app.services.validation.runner import ValidationRunner


@pytest.fixture
def verification_test_fixture(db_session: Session):
    # Reset circuit breaker
    circuit_breaker.reset()

    # 1. Clear verification & demo tables and seed DocumentTypes
    db_session.query(VerificationResult).delete()
    db_session.query(MockRegisterEntry).delete()
    db_session.query(AuthoritySource).delete()
    db_session.query(Document).delete()
    db_session.commit()
    seed_catalog_document_types(db_session)

    # 2. Setup Institute 1 (Alpha Tech)
    inst1 = Institute(
        aicte_institute_id="INST_ALPHA_01",
        name="Alpha Institute of Technology",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst1)
    db_session.commit()
    db_session.refresh(inst1)

    user1 = User(
        email="alpha_inst@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst1.id,
        is_active=True,
    )
    db_session.add(user1)

    # 3. Setup Institute 2 (Beta Tech)
    inst2 = Institute(
        aicte_institute_id="INST_BETA_02",
        name="Beta College of Engineering",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst2)
    db_session.commit()
    db_session.refresh(inst2)

    user2 = User(
        email="beta_inst@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst2.id,
        is_active=True,
    )
    db_session.add(user2)

    # 4. Setup Admin User
    admin = User(
        email="super_admin@aicte-india.org",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)
    db_session.refresh(admin)

    # 5. Seed Authority Sources
    auth_nba = AuthoritySource(
        name="NBA",
        base_url="/mock-authorities/NBA/verify",
        auth_type="API_KEY",
        enabled=True,
        env_secret_key="NBA_API_KEY",
    )
    auth_fire = AuthoritySource(
        name="FIRE_DEPT",
        base_url="/mock-authorities/FIRE_DEPT/verify",
        auth_type="NONE",
        enabled=True,
    )
    db_session.add_all([auth_nba, auth_fire])
    db_session.commit()

    # 6. Seed Mock Register Entries
    today = date.today()
    reg_valid = MockRegisterEntry(
        authority="NBA",
        certificate_number="NBA-ALPHA-VALID",
        institute_name="Alpha Institute of Technology",
        issue_date=(today - timedelta(days=60)).isoformat(),
        expiry_date=(today + timedelta(days=365)).isoformat(),
        status="VALID",
        data_json={"tier": "Tier-1", "programme": "Computer Engineering"},
    )
    reg_mismatch = MockRegisterEntry(
        authority="NBA",
        certificate_number="NBA-ALPHA-MISMATCH",
        institute_name="Completely Different University",
        issue_date=(today - timedelta(days=60)).isoformat(),
        expiry_date=(today + timedelta(days=365)).isoformat(),
        status="VALID",
        data_json={"tier": "Tier-2"},
    )
    reg_expired = MockRegisterEntry(
        authority="NBA",
        certificate_number="NBA-ALPHA-EXPIRED",
        institute_name="Alpha Institute of Technology",
        issue_date=(today - timedelta(days=500)).isoformat(),
        expiry_date=(today - timedelta(days=45)).isoformat(),
        status="EXPIRED",
        data_json={"expired": True},
    )
    db_session.add_all([reg_valid, reg_mismatch, reg_expired])
    db_session.commit()

    # Auth tokens
    token1 = create_access_token(user_id=user1.id, role="INSTITUTE")
    token2 = create_access_token(user_id=user2.id, role="INSTITUTE")
    admin_token = create_access_token(user_id=admin.id, role="ADMIN")

    return {
        "inst1": inst1,
        "inst2": inst2,
        "user1": user1,
        "user2": user2,
        "admin": admin,
        "token1": token1,
        "token2": token2,
        "admin_token": admin_token,
        "auth_nba": auth_nba,
        "auth_fire": auth_fire,
        "today": today,
    }


# ==============================================================================
# 1. FIELD COMPARISON & FUZZY MATCH TESTS
# ==============================================================================

def test_comparator_exact_and_fuzzy_matches():
    """Tests certificate normalization and fuzzy institute name matching"""
    # 1. Normalized Certificate Numbers
    assert VerificationComparator.normalize_cert_number("FSNOC-2026/01-A") == "FSNOC202601A"
    assert VerificationComparator.normalize_cert_number("fsnoc-2026-01-a") == "FSNOC202601A"

    # 2. Fuzzy Institute Name Matching
    matched, score = VerificationComparator.fuzzy_institute_match(
        "Sri Krishna College of Engineering and Technology",
        "Sri Krishna College of Engineering & Technology",
    )
    assert matched is True
    assert score >= 0.85

    # Slight variation in legal suffix
    matched2, score2 = VerificationComparator.fuzzy_institute_match(
        "Alpha Institute of Technology",
        "Alpha Institute of Technology, Pune",
    )
    assert matched2 is True

    # Complete mismatch
    matched3, score3 = VerificationComparator.fuzzy_institute_match(
        "Alpha Institute of Technology",
        "Delta Global Engineering College",
    )
    assert matched3 is False
    assert score3 < 0.60


def test_comparator_mismatch_field_recording():
    """Verify submitted vs official values are recorded for every field comparison"""
    submitted = {
        "certificate_number": "FSNOC-999",
        "institute_name": "Alpha Institute of Technology",
        "issue_date": "2025-01-01",
        "expiry_date": "2026-01-01",
    }
    official = {
        "certificate_number": "FSNOC-999",
        "institute_name": "Different Engineering College",  # mismatch!
        "issue_date": "2025-01-01",
        "expiry_date": "2026-06-01",  # mismatch!
        "status": "VALID",
    }

    comp = VerificationComparator.compare(submitted, official, today=date(2025, 6, 1))

    assert "certificate_number" in comp["matched_fields"]
    assert "issue_date" in comp["matched_fields"]

    # Check mismatched_fields structure [{field, submitted, official}]
    mismatches = comp["mismatched_fields"]
    mismatch_dict = {m["field"]: m for m in mismatches}

    assert "institute_name" in mismatch_dict
    assert mismatch_dict["institute_name"]["submitted"] == "Alpha Institute of Technology"
    assert mismatch_dict["institute_name"]["official"] == "Different Engineering College"

    assert "expiry_date" in mismatch_dict
    assert mismatch_dict["expiry_date"]["submitted"] == "2026-01-01"
    assert mismatch_dict["expiry_date"]["official"] == "2026-06-01"

    # Check all_comparisons has complete history
    assert len(comp["all_comparisons"]) == 4


# ==============================================================================
# 2. VERIFICATION STATUSES TESTS
# ==============================================================================

def test_status_verified(db_session, verification_test_fixture):
    """Document with matching records in official register resolves to VERIFIED"""
    inst1 = verification_test_fixture["inst1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="nba_cert.pdf",
        stored_filename="nba_cert_valid.pdf",
        file_path="nba_cert_valid.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="dummy_hash_valid",
        status="Uploaded",
        extracted_data={
            "accreditation_number": "NBA-ALPHA-VALID",
            "institute_name": inst1.name,
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
        },
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.VERIFIED
    assert doc.status == "Verified"
    assert "certificate_number" in ver_res.details_json.get("matched_fields", [])


def test_status_mismatch_detected(db_session, verification_test_fixture):
    """Document with mismatching institute resolves to MISMATCH_DETECTED"""
    inst1 = verification_test_fixture["inst1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="nba_cert_mismatch.pdf",
        stored_filename="nba_cert_mismatch.pdf",
        file_path="nba_cert_mismatch.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="dummy_hash_mismatch",
        status="Uploaded",
        extracted_data={
            "accreditation_number": "NBA-ALPHA-MISMATCH",
            "institute_name": inst1.name,  # Official register has "Completely Different University"
        },
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.MISMATCH_DETECTED
    assert doc.status == "Needs Attention"
    mismatches = ver_res.details_json.get("mismatched_fields", [])
    assert any(m["field"] == "institute_name" for m in mismatches)


def test_status_expired(db_session, verification_test_fixture):
    """Document with expired date in official register resolves to EXPIRED"""
    inst1 = verification_test_fixture["inst1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="nba_cert_expired.pdf",
        stored_filename="nba_cert_expired.pdf",
        file_path="nba_cert_expired.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="dummy_hash_expired",
        status="Uploaded",
        extracted_data={
            "accreditation_number": "NBA-ALPHA-EXPIRED",
            "institute_name": inst1.name,
        },
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.EXPIRED
    assert doc.status == "Needs Attention"


def test_status_manual_review_required(db_session, verification_test_fixture):
    """Document configured with MANUAL method (e.g. BUILDING_PLAN) resolves to MANUAL_REVIEW_REQUIRED"""
    inst1 = verification_test_fixture["inst1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="BUILDING_PLAN",
        original_filename="building_plan.pdf",
        stored_filename="building_plan.pdf",
        file_path="building_plan.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="dummy_hash_plan",
        status="Uploaded",
        extracted_data={"approval_number": "BPA-101"},
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.MANUAL_REVIEW_REQUIRED


# ==============================================================================
# 3. RETRY AND CIRCUIT BREAKER TESTS
# ==============================================================================

def test_retry_and_circuit_breaker(db_session, verification_test_fixture):
    """
    Simulated 503 errors trigger 3 retries with backoff.
    Upon reaching failure threshold, circuit breaker opens and immediately routes to SOURCE_UNAVAILABLE.
    """
    inst1 = verification_test_fixture["inst1"]

    # Configure a document with simulated error hook
    doc = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="nba_fail.pdf",
        stored_filename="nba_fail.pdf",
        file_path="nba_fail.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="dummy_hash_fail",
        status="Uploaded",
        extracted_data={
            "accreditation_number": "NBA-ALPHA-VALID",
            "_simulate_error": "503",  # triggers HTTP 503 on mock endpoint
        },
    )
    db_session.add(doc)
    db_session.commit()

    # Reset circuit breaker before test
    circuit_breaker.reset("NBA")
    assert circuit_breaker.get_state("NBA") == "CLOSED"

    # Attempt 1: 3 retries happen, fails -> records failure count = 1
    res1 = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert res1.status == VerificationStatus.SOURCE_UNAVAILABLE

    # Record 2 more failures to trip circuit breaker (threshold = 3)
    circuit_breaker.record_failure("NBA")
    circuit_breaker.record_failure("NBA")

    assert circuit_breaker.get_state("NBA") == "OPEN"

    # Call while circuit breaker is OPEN -> immediately returns SOURCE_UNAVAILABLE without calling source
    res_cb = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert res_cb.status == VerificationStatus.SOURCE_UNAVAILABLE
    assert "Circuit breaker is OPEN" in (res_cb.details_json.get("error") or "")

    # Reset circuit breaker
    circuit_breaker.reset("NBA")
    assert circuit_breaker.get_state("NBA") == "CLOSED"


# ==============================================================================
# 4. INSTITUTE ISOLATION TESTS
# ==============================================================================

def test_institute_isolation_endpoints(client, db_session, verification_test_fixture):
    """
    Institute A cannot verify or access verification details for Institute B's documents.
    Returns 403 Forbidden.
    """
    inst1 = verification_test_fixture["inst1"]
    inst2 = verification_test_fixture["inst2"]
    token1 = verification_test_fixture["token1"]
    token2 = verification_test_fixture["token2"]

    # Document belongs to Institute 1
    doc1 = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="alpha_private_doc.pdf",
        stored_filename="alpha_private_doc.pdf",
        file_path="alpha_private_doc.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="alpha_sha_123",
        status="Uploaded",
        extracted_data={"accreditation_number": "NBA-ALPHA-VALID"},
    )
    db_session.add(doc1)
    db_session.commit()

    # 1. Institute 2 attempts POST verify on Institute 1's document -> 403 Forbidden
    client.cookies.set("aicte_access_token", token2)
    res_post_forbidden = client.post(f"/api/institute/documents/{doc1.id}/verify")
    assert res_post_forbidden.status_code == 403
    assert "Forbidden" in res_post_forbidden.json()["detail"]

    # 2. Institute 2 attempts GET verification on Institute 1's document -> 403 Forbidden
    res_get_forbidden = client.get(f"/api/institute/documents/{doc1.id}/verification")
    assert res_get_forbidden.status_code == 403

    # 3. Institute 1 triggers POST verify on their OWN document -> 200 OK
    client.cookies.set("aicte_access_token", token1)
    res_post_owner = client.post(f"/api/institute/documents/{doc1.id}/verify")
    assert res_post_owner.status_code == 200
    data = res_post_owner.json()
    assert data["document_id"] == doc1.id
    assert data["status"] == "VERIFIED"

    # 4. Institute 1 retrieves GET verification -> 200 OK
    res_get_owner = client.get(f"/api/institute/documents/{doc1.id}/verification")
    assert res_get_owner.status_code == 200
    assert res_get_owner.json()["id"] == data["id"]


# ==============================================================================
# 5. MANUAL CONFIRMATION TESTS (REASON MANDATORY)
# ==============================================================================

def test_manual_confirm_requires_reason(client, db_session, verification_test_fixture):
    """
    POST /api/admin/verification/{id}/manual-confirm requires a non-empty reason.
    Missing or whitespace-only reason returns 422 Unprocessable Entity.
    """
    inst1 = verification_test_fixture["inst1"]
    admin_token = verification_test_fixture["admin_token"]
    user_token = verification_test_fixture["token1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="BUILDING_PLAN",
        original_filename="plan_review.pdf",
        stored_filename="plan_review.pdf",
        file_path="plan_review.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="plan_hash_999",
        status="Uploaded",
        extracted_data={"approval_number": "BPA-999"},
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.MANUAL_REVIEW_REQUIRED

    client.cookies.set("aicte_access_token", admin_token)

    # 1. Missing reason or empty string -> 422
    res_empty_reason = client.post(
        f"/api/admin/verification/{ver_res.id}/manual-confirm",
        json={"decision": "APPROVED", "reason": ""},
    )
    assert res_empty_reason.status_code == 422

    res_whitespace_reason = client.post(
        f"/api/admin/verification/{ver_res.id}/manual-confirm",
        json={"decision": "APPROVED", "reason": "    "},
    )
    assert res_whitespace_reason.status_code == 422

    # 2. Non-admin user attempts manual confirmation -> 403 Forbidden
    client.cookies.set("aicte_access_token", user_token)
    res_non_admin = client.post(
        f"/api/admin/verification/{ver_res.id}/manual-confirm",
        json={"decision": "APPROVED", "reason": "Valid reason provided by student"},
    )
    assert res_non_admin.status_code == 403

    # 3. Valid Admin Manual Confirmation with mandatory reason -> 200 OK
    client.cookies.set("aicte_access_token", admin_token)
    res_valid_confirm = client.post(
        f"/api/admin/verification/{ver_res.id}/manual-confirm",
        json={
            "decision": "APPROVED",
            "reason": "Physical blueprint verified and sealed by regional scrutiny officer Dr. Sharma.",
        },
    )
    assert res_valid_confirm.status_code == 200
    confirm_data = res_valid_confirm.json()
    assert confirm_data["status"] == "VERIFIED"
    assert confirm_data["manual_decision"] == "APPROVED"
    assert "Dr. Sharma" in confirm_data["manual_reason"]


# ==============================================================================
# 6. ADMIN QUEUE ENDPOINT TESTS
# ==============================================================================

def test_admin_verification_queue(client, db_session, verification_test_fixture):
    """GET /api/admin/verification/queue returns items needing review and supports status filtering"""
    inst1 = verification_test_fixture["inst1"]
    admin_token = verification_test_fixture["admin_token"]

    # Create 2 documents: one manual review, one unavailable
    doc1 = Document(
        institute_id=inst1.id,
        document_type_code="BUILDING_PLAN",
        original_filename="plan_queue.pdf",
        stored_filename="plan_queue.pdf",
        file_path="plan_queue.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_queue_1",
        status="Uploaded",
    )
    doc2 = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="nba_queue.pdf",
        stored_filename="nba_queue.pdf",
        file_path="nba_queue.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_queue_2",
        status="Uploaded",
    )
    db_session.add_all([doc1, doc2])
    db_session.commit()

    v1 = VerificationResult(
        document_id=doc1.id,
        status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
        source_name="MANUAL_INSPECTION",
        checked_at=datetime.now(timezone.utc),
        details_json={"message": "Needs committee inspection"},
    )
    v2 = VerificationResult(
        document_id=doc2.id,
        status=VerificationStatus.SOURCE_UNAVAILABLE,
        source_name="NBA",
        checked_at=datetime.now(timezone.utc),
        details_json={"message": "Source offline"},
    )
    db_session.add_all([v1, v2])
    db_session.commit()

    client.cookies.set("aicte_access_token", admin_token)

    # 1. Fetch entire scrutiny queue
    res_all = client.get("/api/admin/verification/queue")
    assert res_all.status_code == 200
    queue_items = res_all.json()
    assert len(queue_items) >= 2

    # 2. Filter by status: manual_review
    res_filtered = client.get("/api/admin/verification/queue?status=manual_review")
    assert res_filtered.status_code == 200
    filtered_items = res_filtered.json()
    assert all(item["status"] == "MANUAL_REVIEW_REQUIRED" for item in filtered_items)


# ==============================================================================
# 7. QR CODE ADAPTER WITH SYNTHETIC PDF
# ==============================================================================

def test_qr_adapter_synthetic_pdf(db_session, verification_test_fixture):
    """Synthetic PDF generated with embedded QR code is correctly scanned and verified"""
    inst1 = verification_test_fixture["inst1"]
    today = date.today()

    fields = {
        "noc_number": "FSNOC-TEST-QR-99",
        "institute_name": inst1.name,
        "issue_date": (today - timedelta(days=30)).isoformat(),
        "expiry_date": (today + timedelta(days=365)).isoformat(),
    }

    # Generate synthetic PDF with embedded QR code
    pdf_path = create_synthetic_pdf(
        filename="test_qr_cert.pdf",
        title="Fire Safety Certificate",
        doc_type_code="FIRE_NOC",
        fields=fields,
    )

    doc = Document(
        institute_id=inst1.id,
        document_type_code="FIRE_NOC",
        original_filename="test_qr_cert.pdf",
        stored_filename="test_qr_cert.pdf",
        file_path=pdf_path,
        file_size=os.path.getsize(pdf_path),
        mime_type="application/pdf",
        sha256_hash="qr_pdf_sha",
        status="Uploaded",
        extracted_data=fields,
    )
    db_session.add(doc)
    db_session.commit()

    ver_res = VerificationService.verify_document(db=db_session, document_id=doc.id)
    assert ver_res.status == VerificationStatus.VERIFIED
    assert ver_res.source_name == "EMBEDDED_QR_CODE"
    assert "certificate_number" in ver_res.details_json.get("matched_fields", [])


# ==============================================================================
# 8. EVALUATION CONTEXT & EXTERNAL VERIFICATION RULE ENGINE
# ==============================================================================

def test_evaluation_context_and_external_verification_rules(db_session, verification_test_fixture):
    """
    VerificationResult feeds into EvaluationContext.
    EXTERNAL_VERIFICATION rule passes on VERIFIED, flags NEEDS_REVIEW on MISMATCH or SOURCE_UNAVAILABLE.
    """
    inst1 = verification_test_fixture["inst1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="NAAC_CERT",
        original_filename="naac.pdf",
        stored_filename="naac.pdf",
        file_path="naac.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="naac_hash",
        status="Uploaded",
    )
    db_session.add(doc)
    db_session.commit()

    # 1. When status is VERIFIED -> PASS
    v_verified = VerificationResult(
        document_id=doc.id,
        status=VerificationStatus.VERIFIED,
        source_name="NAAC_PORTAL",
        checked_at=datetime.now(timezone.utc),
        details_json={},
    )
    db_session.add(v_verified)
    db_session.commit()

    context = EvaluationContext(
        documents=[{
            "id": doc.id,
            "document_type_code": "NAAC_CERT",
            "type": "NAAC_CERT",
            "status": "Verified",
            "verification": {"status": "VERIFIED", "source_name": "NAAC_PORTAL"},
        }],
        verification={str(doc.id): {"status": "VERIFIED", "source_name": "NAAC_PORTAL"}},
    )

    evaluator = ExternalVerificationEvaluator()
    rule_def = {"type": "EXTERNAL_VERIFICATION", "document": "NAAC_CERT", "required_status": "VERIFIED"}
    res_pass = evaluator.evaluate(rule_def, context)
    assert res_pass.status == "PASS"

    # 2. When status is MISMATCH_DETECTED -> NEEDS_REVIEW
    context_mismatch = EvaluationContext(
        documents=[{
            "id": doc.id,
            "document_type_code": "NAAC_CERT",
            "type": "NAAC_CERT",
            "status": "Needs Attention",
            "verification": {"status": "MISMATCH_DETECTED", "source_name": "NAAC_PORTAL"},
        }],
        verification={str(doc.id): {"status": "MISMATCH_DETECTED", "source_name": "NAAC_PORTAL"}},
    )
    res_mismatch = evaluator.evaluate(rule_def, context_mismatch)
    assert res_mismatch.status == "NEEDS_REVIEW"
    assert "mismatched" in res_mismatch.reason.lower()

    # 3. When status is SOURCE_UNAVAILABLE -> NEEDS_REVIEW
    context_unavail = EvaluationContext(
        documents=[{
            "id": doc.id,
            "document_type_code": "NAAC_CERT",
            "type": "NAAC_CERT",
            "status": "Needs Attention",
            "verification": {"status": "SOURCE_UNAVAILABLE", "source_name": "NAAC_PORTAL"},
        }],
        verification={str(doc.id): {"status": "SOURCE_UNAVAILABLE", "source_name": "NAAC_PORTAL"}},
    )
    res_unavail = evaluator.evaluate(rule_def, context_unavail)
    assert res_unavail.status == "NEEDS_REVIEW"
    assert "unavailable" in res_unavail.reason.lower()


# ==============================================================================
# 9. DIGITAL SIGNATURE ADAPTER & AUDIT LOGGING
# ==============================================================================

def test_digital_signature_adapter(db_session, verification_test_fixture):
    """Verifies statutory CA Audited Accounts using digital signature / UDIN check"""
    inst1 = verification_test_fixture["inst1"]

    # 1. Valid 18-character ICAI UDIN
    doc_valid = Document(
        institute_id=inst1.id,
        document_type_code="AUDIT_ACCOUNTS",
        original_filename="audit_signed.pdf",
        stored_filename="audit_signed.pdf",
        file_path="audit_signed.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_udin_valid",
        status="Uploaded",
        extracted_data={
            "ca_udin": "26088219AAAAAA1234",  # valid 18 char ICAI UDIN
            "institute_name": inst1.name,
        },
    )
    db_session.add(doc_valid)
    db_session.commit()

    ver_valid = VerificationService.verify_document(db=db_session, document_id=doc_valid.id)
    assert ver_valid.status == VerificationStatus.VERIFIED
    assert ver_valid.source_name == "DIGITAL_SIGNATURE_ENGINE"

    # 2. Unsigned / Missing signature
    doc_unsigned = Document(
        institute_id=inst1.id,
        document_type_code="AUDIT_ACCOUNTS",
        original_filename="audit_unsigned.pdf",
        stored_filename="audit_unsigned.pdf",
        file_path="audit_unsigned.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="hash_udin_unsigned",
        status="Uploaded",
        extracted_data={
            "ca_udin": "SHORT",  # invalid
            "institute_name": inst1.name,
        },
    )
    db_session.add(doc_unsigned)
    db_session.commit()

    ver_unsigned = VerificationService.verify_document(db=db_session, document_id=doc_unsigned.id)
    assert ver_unsigned.status == VerificationStatus.MISMATCH_DETECTED
    assert any(m["field"] == "digital_signature" for m in ver_unsigned.details_json.get("mismatched_fields", []))


def test_audit_log_recorded_on_verification(db_session, verification_test_fixture):
    """Every verification check logs an AuditLog entry with source, timestamp and result"""
    from backend.app.models.audit_log import AuditLog
    inst1 = verification_test_fixture["inst1"]
    user1 = verification_test_fixture["user1"]

    doc = Document(
        institute_id=inst1.id,
        document_type_code="NBA_CERT",
        original_filename="audit_logged_doc.pdf",
        stored_filename="audit_logged_doc.pdf",
        file_path="audit_logged_doc.pdf",
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="sha_audit_logged",
        status="Uploaded",
        extracted_data={"accreditation_number": "NBA-ALPHA-VALID"},
    )
    db_session.add(doc)
    db_session.commit()

    # Trigger verify
    ver_res = VerificationService.verify_document(
        db=db_session,
        document_id=doc.id,
        triggered_by=user1.id,
    )

    # Check AuditLog
    log_entry = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.action == "DOCUMENT_VERIFIED",
            AuditLog.user_id == user1.id,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log_entry is not None
    assert log_entry.details.get("verification_id") == ver_res.id
    assert log_entry.details.get("status") == ver_res.status
    assert log_entry.details.get("source_name") == ver_res.source_name
    assert log_entry.timestamp is not None

