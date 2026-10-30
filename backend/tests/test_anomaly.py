import os
import pytest
from datetime import datetime, date, timedelta, timezone
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.verification import (
    VerificationResult,
    VerificationStatus,
    MockRegisterEntry,
)
from backend.app.models.anomaly import (
    AnomalyRun,
    AnomalyFlag,
    AnomalySeverity,
    AnomalyReviewStatus,
)
from backend.app.models.audit_log import AuditLog
from backend.app.security.password import hash_password
from backend.app.security.tokens import create_access_token
from backend.app.services.anomaly.seed import generate_all_samples
from backend.app.services.anomaly.service import AnomalyService
from backend.app.services.anomaly.detectors.base import DetectionContext
from backend.app.services.anomaly.detectors import (
    DuplicateDetector,
    MetadataDetector,
    DateAnomalyDetector,
    IdentifierDetector,
    ImageTamperDetector,
    VerificationConflictDetector,
)
from backend.app.services.validation.runner import ValidationRunner


@pytest.fixture
def anomaly_fixture(db_session: Session):
    # 1. Clean anomaly tables
    db_session.query(AnomalyFlag).delete()
    db_session.query(AnomalyRun).delete()
    db_session.query(VerificationResult).delete()
    db_session.query(MockRegisterEntry).delete()
    db_session.query(Document).delete()
    db_session.query(Application).delete()
    db_session.commit()

    # 2. Setup Institute A
    inst_a = Institute(
        aicte_institute_id="INST_ALPHA_99",
        name="Alpha Engineering Institute",
        state="Maharashtra",
        status="ACTIVE",
    )
    db_session.add(inst_a)

    # 3. Setup Institute B
    inst_b = Institute(
        aicte_institute_id="INST_BETA_88",
        name="Beta Technology Campus",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst_b)
    db_session.commit()
    db_session.refresh(inst_a)
    db_session.refresh(inst_b)

    # 4. Setup Users
    user_a = User(
        email="alpha_inst@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst_a.id,
        is_active=True,
    )
    user_b = User(
        email="beta_inst@aicte.edu.in",
        password_hash=hash_password("Pass@123"),
        role=UserRole.INSTITUTE,
        institute_id=inst_b.id,
        is_active=True,
    )
    admin_user = User(
        email="scrutiny_admin@aicte-india.org",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add_all([user_a, user_b, admin_user])
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)
    db_session.refresh(admin_user)

    # 5. Setup Applications
    app_a = Application(
        institute_id=inst_a.id,
        application_id="APP-2026-ALPHA-01",
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="ENGINEERING_AND_TECHNOLOGY",
        status="SUBMITTED",
    )
    app_b = Application(
        institute_id=inst_b.id,
        application_id="APP-2026-BETA-02",
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="ENGINEERING_AND_TECHNOLOGY",
        status="SUBMITTED",
    )
    db_session.add_all([app_a, app_b])
    db_session.commit()
    db_session.refresh(app_a)
    db_session.refresh(app_b)

    # 6. Ensure Document Types
    dt_nba = db_session.query(DocumentType).filter(DocumentType.code == "NBA_TEST").first()
    if not dt_nba:
        dt_nba = DocumentType(
            code="NBA_TEST",
            name="NBA Accreditation Test",
            default_validity_months=36,
            extraction_schema=[{"key": "certificate_number", "pattern": r"^NBA-\d{4}-[A-Z0-9-]+$"}],
        )
        db_session.add(dt_nba)
        db_session.commit()

    samples = generate_all_samples()

    return {
        "inst_a": inst_a,
        "inst_b": inst_b,
        "user_a": user_a,
        "user_b": user_b,
        "admin": admin_user,
        "app_a": app_a,
        "app_b": app_b,
        "dt_nba": dt_nba,
        "samples": samples,
    }


def test_each_detector_flags_target_and_not_clean(db_session: Session, anomaly_fixture):
    """
    Each detector flags its specific anomaly sample and does NOT flag the clean sample.
    """
    inst = anomaly_fixture["inst_a"]
    samples = anomaly_fixture["samples"]

    # 1. Clean Sample Context
    clean_doc = Document(
        id=7001,
        institute_id=inst.id,
        original_filename="clean_sample.pdf",
        stored_filename="clean_sample_7001.pdf",
        file_path=samples["clean"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="unique_clean_sha_123",
        extracted_data={
            "certificate_number": "NBA-2024-SKCET-001",
            "issue_date": "2026-10-28",
            "expiry_date": "2029-10-27",
            "institute_name": inst.name,
            "aicte_institute_id": inst.aicte_institute_id,
        },
    )
    ctx_clean = DetectionContext(
        db=db_session,
        document=clean_doc,
        doc_type=anomaly_fixture["dt_nba"],
        extracted_fields=clean_doc.extracted_data,
    )

    # Clean document should produce ZERO flags on date, metadata, tamper, and identifier
    assert len(DateAnomalyDetector().detect(ctx_clean)) == 0
    assert len(MetadataDetector().detect(ctx_clean)) == 0
    assert len(ImageTamperDetector().detect(ctx_clean)) == 0
    assert len(IdentifierDetector().detect(ctx_clean)) == 0

    # 2. Date Anomaly Detector
    date_doc = Document(
        id=7002,
        institute_id=inst.id,
        original_filename="edited_date_sample.pdf",
        stored_filename="date_sample_7002.pdf",
        file_path=samples["edited_date"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="date_sha_456",
        extracted_data={
            "issue_date": "2027-01-10",
            "expiry_date": "2025-06-30",
        },
    )
    ctx_date = DetectionContext(db=db_session, document=date_doc, extracted_fields=date_doc.extracted_data)
    date_flags = DateAnomalyDetector().detect(ctx_date)
    date_codes = [f.code for f in date_flags]
    assert "DATE_ISSUE_AFTER_EXPIRY" in date_codes
    assert "DATE_FUTURE_ISSUE" in date_codes

    # 3. Duplicate Detector
    dup_doc = Document(
        id=7003,
        institute_id=inst.id,
        original_filename="duplicate_sample.pdf",
        stored_filename="dup_sample_7003.pdf",
        file_path=samples["duplicate"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash=clean_doc.sha256_hash,  # Identical hash to clean_doc
    )
    db_session.add(clean_doc)
    db_session.commit()
    ctx_dup = DetectionContext(db=db_session, document=dup_doc)
    dup_flags = DuplicateDetector().detect(ctx_dup)
    assert any(f.code == "EXACT_HASH_DUPLICATE" and f.severity == "HIGH" for f in dup_flags)

    # 4. Metadata Detector
    meta_doc = Document(
        id=7004,
        institute_id=inst.id,
        original_filename="suspicious_metadata_sample.pdf",
        stored_filename="meta_sample_7004.pdf",
        file_path=samples["suspicious_metadata"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="meta_sha_789",
        extracted_data={"issue_date": "2021-03-01"},
    )
    ctx_meta = DetectionContext(db=db_session, document=meta_doc, extracted_fields=meta_doc.extracted_data)
    meta_flags = MetadataDetector().detect(ctx_meta)
    meta_codes = [f.code for f in meta_flags]
    assert "METADATA_SUSPICIOUS_PRODUCER" in meta_codes
    assert "METADATA_CREATION_POSTDATES_ISSUE" in meta_codes

    # 5. Image Tamper Detector
    tamper_doc = Document(
        id=7005,
        institute_id=inst.id,
        original_filename="tampered_stamp_sample.pdf",
        stored_filename="tamper_sample_7005.pdf",
        file_path=samples["tampered_stamp"],
        file_size=32000,
        mime_type="application/pdf",
        sha256_hash="tamper_sha_101",
        extracted_data={},
    )
    ctx_tamper = DetectionContext(db=db_session, document=tamper_doc)
    tamper_flags = ImageTamperDetector().detect(ctx_tamper)
    assert len(tamper_flags) >= 1
    assert tamper_flags[0].code == "IMAGE_TAMPER_SUSPECTED"
    assert tamper_flags[0].overlay_image_path is not None
    assert os.path.exists(tamper_flags[0].overlay_image_path)

    # 6. Verification Conflict Detector
    conflict_doc = Document(
        id=7006,
        institute_id=inst.id,
        original_filename="conflict.pdf",
        stored_filename="conflict_sample_7006.pdf",
        file_path=samples["clean"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="conflict_sha_102",
        extracted_data={},
    )
    db_session.add(conflict_doc)
    db_session.commit()

    ver_res = VerificationResult(
        document_id=conflict_doc.id,
        status=VerificationStatus.MISMATCH_DETECTED,
        source_name="NBA Authority Register",
        details_json={"mismatched_fields": [{"field": "institute_name", "submitted": "A", "official": "B"}]},
    )
    db_session.add(ver_res)
    db_session.commit()

    ctx_conflict = DetectionContext(db=db_session, document=conflict_doc)
    conflict_flags = VerificationConflictDetector().detect(ctx_conflict)
    assert any(f.code == "VERIFICATION_CONFLICT_MISMATCH" and f.severity == "HIGH" for f in conflict_flags)

    # 7. Identifier Detector
    id_doc = Document(
        id=7007,
        institute_id=inst.id,
        original_filename="id_test.pdf",
        stored_filename="id_sample_7007.pdf",
        file_path=samples["clean"],
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="id_sha_103",
        extracted_data={"certificate_number": "INVALID-FORMAT-99"},
    )
    ctx_id = DetectionContext(
        db=db_session,
        document=id_doc,
        doc_type=anomaly_fixture["dt_nba"],
        extracted_fields=id_doc.extracted_data,
    )
    id_flags = IdentifierDetector().detect(ctx_id)
    assert any(f.code == "IDENTIFIER_PATTERN_MISMATCH" for f in id_flags)


def test_clean_demo_documents_false_positive_guard(db_session: Session, anomaly_fixture):
    """
    Ensures that standard clean demo documents (e.g. DEMO-READY certificates)
    do not trigger false-positive HIGH severity or tamper flags.
    """
    inst = anomaly_fixture["inst_a"]
    demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../demo_data"))

    ready_files = [
        f for f in os.listdir(demo_dir)
        if f.startswith("DEMO-READY") and f.endswith(".pdf")
    ]
    assert len(ready_files) >= 5, "DEMO-READY files must exist in demo_data"

    tamper_detector = ImageTamperDetector()
    date_detector = DateAnomalyDetector()

    for fname in ready_files[:4]:
        fpath = os.path.join(demo_dir, fname)
        doc = Document(
            institute_id=inst.id,
            original_filename=fname,
            file_path=fpath,
            sha256_hash=f"hash_{fname}",
            extracted_data={
                "issue_date": "2026-10-28",
                "expiry_date": "2029-10-27",
            },
        )
        ctx = DetectionContext(db=db_session, document=doc, extracted_fields=doc.extracted_data)

        # Tamper detector should not trigger on clean documents
        tamper_flags = tamper_detector.detect(ctx)
        assert len(tamper_flags) == 0, f"False positive tamper detected on {fname}"

        # Date detector should not trigger on valid dates
        date_flags = date_detector.detect(ctx)
        high_date_flags = [f for f in date_flags if f.severity == AnomalySeverity.HIGH]
        assert len(high_date_flags) == 0, f"False positive date anomaly on {fname}"


def test_institute_isolation_on_anomaly_endpoints(client, anomaly_fixture, db_session: Session):
    """
    Institute A cannot access or scan Institute B's documents or applications.
    Institute responses omit internal confidence scores.
    """
    user_a = anomaly_fixture["user_a"]
    user_b = anomaly_fixture["user_b"]
    app_b = anomaly_fixture["app_b"]
    samples = anomaly_fixture["samples"]

    # Register document for Institute B
    doc_b = Document(
        institute_id=anomaly_fixture["inst_b"].id,
        application_id=app_b.id,
        original_filename="doc_b.pdf",
        stored_filename="doc_b_stored.pdf",
        file_path=samples["clean"],
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="doc_b_sha_unique",
        status="Uploaded",
    )
    db_session.add(doc_b)
    db_session.commit()
    db_session.refresh(doc_b)

    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    client.cookies.set("aicte_access_token", token_a)

    # 1. Institute A attempts to scan Application B -> 403 Forbidden
    res_scan = client.post(f"/api/institute/applications/{app_b.id}/anomaly-scan")
    assert res_scan.status_code == 403

    # 2. Institute A attempts to get anomalies for Document B -> 403 Forbidden
    res_get = client.get(f"/api/institute/documents/{doc_b.id}/anomalies")
    assert res_get.status_code == 403

    # 3. Institute B accesses Document B anomalies -> 200 OK & confidence score is omitted
    token_b = create_access_token(user_id=user_b.id, role=user_b.role)
    client.cookies.set("aicte_access_token", token_b)

    # Trigger scan by owner
    scan_b = client.post(f"/api/institute/applications/{app_b.id}/anomaly-scan")
    assert scan_b.status_code == 200
    scan_data = scan_b.json()
    assert "flags" in scan_data
    for flag_item in scan_data["flags"]:
        assert "confidence" not in flag_item, "Internal confidence score must NOT be exposed to institute"

    res_doc_b = client.get(f"/api/institute/documents/{doc_b.id}/anomalies")
    assert res_doc_b.status_code == 200
    doc_flags = res_doc_b.json()
    for f in doc_flags:
        assert "confidence" not in f, "Confidence score must be omitted from institute document view"


def test_admin_review_requires_note_and_logs_audit(client, anomaly_fixture, db_session: Session):
    """
    Administrative review of an anomaly flag requires a mandatory note and writes an AuditLog event.
    """
    admin = anomaly_fixture["admin"]
    inst = anomaly_fixture["inst_a"]
    samples = anomaly_fixture["samples"]

    # Register document and flag
    doc = Document(
        institute_id=inst.id,
        original_filename="review_test.pdf",
        stored_filename="review_test_stored.pdf",
        file_path=samples["edited_date"],
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="rev_doc_hash",
        status="Uploaded",
        extracted_data={"issue_date": "2027-01-10", "expiry_date": "2025-06-30"},
    )
    db_session.add(doc)
    db_session.commit()

    run, flags = AnomalyService.scan_document(db=db_session, document_id=doc.id)
    assert len(flags) >= 1
    target_flag = flags[0]

    admin_token = create_access_token(user_id=admin.id, role=admin.role)
    client.cookies.set("aicte_access_token", admin_token)

    # 1. Attempt review with empty note -> 422 Unprocessable Entity
    empty_res = client.post(
        f"/api/admin/anomalies/{target_flag.id}/review",
        json={"status": AnomalyReviewStatus.CONFIRMED_OK, "note": ""},
    )
    assert empty_res.status_code == 422

    # 2. Attempt review with note shorter than 3 chars -> 422
    short_res = client.post(
        f"/api/admin/anomalies/{target_flag.id}/review",
        json={"status": AnomalyReviewStatus.CONFIRMED_OK, "note": "ok"},
    )
    assert short_res.status_code == 422

    # 3. Valid review with proper rationale
    valid_res = client.post(
        f"/api/admin/anomalies/{target_flag.id}/review",
        json={
            "status": AnomalyReviewStatus.NEEDS_ACTION,
            "note": "Verified with Fire Department register; certificate dates are inconsistent. Re-submission required.",
        },
    )
    assert valid_res.status_code == 200
    updated = valid_res.json()
    assert updated["review_status"] == AnomalyReviewStatus.NEEDS_ACTION
    assert updated["review_note"] == "Verified with Fire Department register; certificate dates are inconsistent. Re-submission required."
    assert updated["reviewed_by"] == admin.id

    # 4. Check AuditLog entry
    audit_entry = (
        db_session.query(AuditLog)
        .filter(AuditLog.action == "ANOMALY_FLAG_REVIEWED", AuditLog.user_id == admin.id)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_entry is not None
    assert str(target_flag.id) in audit_entry.reason


def test_validation_runner_anomaly_findings_mapping(anomaly_fixture, db_session: Session):
    """
    Feeds anomaly flags into ValidationRunner:
    - Severity mapped: HIGH -> MAJOR, MEDIUM -> MINOR, LOW/INFO -> ADVISORY
    - Status is strictly NEEDS_REVIEW, NEVER FAIL.
    """
    inst = anomaly_fixture["inst_a"]
    app = anomaly_fixture["app_a"]
    samples = anomaly_fixture["samples"]

    doc = Document(
        institute_id=inst.id,
        application_id=app.id,
        original_filename="val_runner_test.pdf",
        stored_filename="val_runner_stored.pdf",
        file_path=samples["edited_date"],
        file_size=1024,
        mime_type="application/pdf",
        sha256_hash="val_runner_hash",
        status="Uploaded",
        extracted_data={"issue_date": "2027-01-10", "expiry_date": "2025-06-30"},
    )
    db_session.add(doc)
    db_session.commit()

    # Run anomaly detection
    run, flags = AnomalyService.scan_document(db=db_session, document_id=doc.id)
    assert len(flags) >= 1

    # Run validation
    val_run = ValidationRunner.run_validation(db=db_session, application_id=app.id)

    # Locate anomaly findings in validation run
    anomaly_findings = [
        f for f in val_run.findings
        if f.rule_code and f.rule_code.startswith("ANOMALY_")
    ]
    assert len(anomaly_findings) >= 1

    for af in anomaly_findings:
        # Crucial invariant: Anomaly findings must always be NEEDS_REVIEW, never FAIL
        assert af.status == "NEEDS_REVIEW", f"Expected NEEDS_REVIEW status, got {af.status}"
        assert af.severity in ["MAJOR", "MINOR", "ADVISORY"]


def test_strict_wording_no_forbidden_words(db_session: Session, anomaly_fixture):
    """
    STRICT WORDING CHECK:
    Outputs are preliminary indicators requiring human verification.
    NEVER use 'forgery', 'fraud', or 'misconduct'.
    ALWAYS use 'needs verification' and 'potential anomaly'.
    """
    forbidden_words = ["forgery", "fraud", "misconduct"]
    inst = anomaly_fixture["inst_a"]
    samples = anomaly_fixture["samples"]

    # Run anomaly scan across all sample types
    for key, path in samples.items():
        doc = Document(
            institute_id=inst.id,
            original_filename=f"wording_{key}.pdf",
            file_path=path,
            sha256_hash=f"wording_hash_{key}",
            extracted_data={
                "issue_date": "2027-01-10",
                "expiry_date": "2025-06-30",
                "certificate_number": "NBA-INVALID-99",
            },
        )
        ctx = DetectionContext(db=db_session, document=doc, extracted_fields=doc.extracted_data)

        detectors = [
            DuplicateDetector(),
            MetadataDetector(),
            DateAnomalyDetector(),
            IdentifierDetector(),
            ImageTamperDetector(),
            VerificationConflictDetector(),
        ]

        for det in detectors:
            flags = det.detect(ctx)
            for f in flags:
                text_to_check = f"{f.reason} {f.recommended_action} {f.code}".lower()
                for forbidden in forbidden_words:
                    assert forbidden not in text_to_check, (
                        f"Forbidden word '{forbidden}' found in detector {det.name} flag {f.code}: '{text_to_check}'"
                    )
                # Reason must include standard terminology
                assert "verification" in f.reason.lower() or "anomaly" in f.reason.lower(), (
                    f"Flag reason must use 'needs verification' or 'potential anomaly': {f.reason}"
                )
