import os
import sys
import hashlib
from datetime import datetime, date, timezone
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import SessionLocal
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.verification import VerificationResult, VerificationStatus
from backend.app.services.anomaly.seed import generate_all_samples
from backend.app.services.anomaly.service import AnomalyService
from backend.app.models.anomaly import AnomalyReviewStatus


def run_stage5_demo():
    print("=" * 86)
    print("AICTE SmartVerify AI — Stage 5 Multi-Detector Anomaly Engine & Preliminary Screening Demo")
    print("=" * 86)
    print("NOTICE: All detector outputs are PRELIMINARY INDICATORS requiring human verification,")
    print("never proof. Categorized under 'needs verification' and 'potential anomaly'.")
    print("=" * 86)

    # 1. Ensure synthetic test documents exist
    print("\n[STEP 1] Generating Synthetic Test Documents in backend/demo_data/anomaly/ ...")
    sample_paths = generate_all_samples()
    for name, p in sample_paths.items():
        print(f"  * {name.ljust(22)}: {os.path.basename(p)} ({os.path.getsize(p)} bytes)")

    db = SessionLocal()
    try:
        # Resolve demo Institute (Sri Krishna College)
        inst = db.query(Institute).filter(Institute.name.ilike("%Sri Krishna%")).first()
        if not inst:
            inst = Institute(
                name="Sri Krishna College of Engineering and Technology",
                aicte_institute_id="SKCET01",
                state="Tamil Nadu",
                status="Active",
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)

        # Resolve or create demo Application
        app = db.query(Application).filter(Application.institute_id == inst.id).first()
        if not app:
            app = Application(
                institute_id=inst.id,
                application_id="AICTE-APP-2026-SKCET",
                category="Extension of Approval (EoA)",
                academic_year="2026-2027",
                programme="ENGINEERING_AND_TECHNOLOGY",
                status="SUBMITTED",
            )
            db.add(app)
            db.commit()
            db.refresh(app)

        # Resolve Document Types
        dt_nba = db.query(DocumentType).filter(DocumentType.code == "NBA_ACCREDITATION").first()
        if not dt_nba:
            dt_nba = DocumentType(
                code="NBA_ACCREDITATION",
                name="NBA Accreditation",
                default_validity_months=36,
                extraction_schema=[{"key": "certificate_number", "pattern": r"^NBA-\d{4}-[A-Z0-9-]+$"}],
            )
            db.add(dt_nba)
        dt_fire = db.query(DocumentType).filter(DocumentType.code == "FIRE_SAFETY_NOC").first()
        if not dt_fire:
            dt_fire = DocumentType(
                code="FIRE_SAFETY_NOC",
                name="Fire Safety NOC",
                default_validity_months=12,
                extraction_schema=[{"key": "certificate_number", "pattern": r"^FIRE-[A-Z0-9-]+$"}],
            )
            db.add(dt_fire)
        db.commit()

        # Helper to register or update a test Document in DB
        def register_test_doc(filename, filepath, type_code, extracted_dict, sha_seed=None):
            with open(filepath, "rb") as f:
                content = f.read()
            real_hash = hashlib.sha256(content).hexdigest()
            doc_hash = sha_seed if sha_seed else real_hash

            doc = (
                db.query(Document)
                .filter(Document.original_filename == filename, Document.institute_id == inst.id)
                .first()
            )
            if not doc:
                doc = Document(
                    institute_id=inst.id,
                    application_id=app.id,
                    document_type_code=type_code,
                    original_filename=filename,
                    stored_filename=f"demo_stg5_{filename}",
                    file_path=filepath,
                    file_size=len(content),
                    mime_type="application/pdf",
                    sha256_hash=doc_hash,
                    status="Processing",
                    extracted_data=extracted_dict,
                )
                db.add(doc)
            else:
                doc.file_path = filepath
                doc.file_size = len(content)
                doc.sha256_hash = doc_hash
                doc.extracted_data = extracted_dict
            db.commit()
            db.refresh(doc)
            return doc

        print("\n[STEP 2] Running Anomaly Detection Lifecycle Across Test Scenarios ...\n")

        # -------------------------------------------------------------
        # Scenario 1: Clean Authentic Sample
        # -------------------------------------------------------------
        print("-" * 86)
        print("TEST DOCUMENT: 1. Clean Authentic Document")
        doc_clean = register_test_doc(
            "clean_sample.pdf",
            sample_paths["clean"],
            "NBA_ACCREDITATION",
            {
                "certificate_number": "NBA-2024-SKCET-001",
                "issue_date": "2026-10-28",
                "expiry_date": "2029-10-27",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "aicte_institute_id": "SKCET01",
            },
            sha_seed="unique_clean_sample_sha256_hash",
        )
        print(f"Filename: {doc_clean.original_filename} | Doc ID: #{doc_clean.id}")
        run_clean, flags_clean = AnomalyService.scan_document(db=db, document_id=doc_clean.id)
        # Filter duplicate flags against itself if re-running
        pure_clean_flags = [f for f in flags_clean if "duplicate" not in f.code.lower()]
        if not pure_clean_flags:
            print("  [OK] NO ANOMALIES DETECTED — Document passes preliminary automated screening.")
        else:
            for idx, flag in enumerate(pure_clean_flags, 1):
                print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code} -> {flag.reason}")

        # -------------------------------------------------------------
        # Scenario 2: Date Anomaly (Issue > Expiry & Future)
        # -------------------------------------------------------------
        print("\n" + "-" * 86)
        print("TEST DOCUMENT: 2. Date Anomaly (Issue > Expiry & Future)")
        doc_date = register_test_doc(
            "edited_date_sample.pdf",
            sample_paths["edited_date"],
            "FIRE_SAFETY_NOC",
            {
                "certificate_number": "FIRE-NOC-2026-99",
                "issue_date": "2027-01-10",
                "expiry_date": "2025-06-30",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "aicte_institute_id": "SKCET01",
            },
        )
        print(f"Filename: {doc_date.original_filename} | Doc ID: #{doc_date.id}")
        run_date, flags_date = AnomalyService.scan_document(db=db, document_id=doc_date.id)
        for idx, flag in enumerate(flags_date, 1):
            print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code}")
            print(f"    Confidence: {flag.confidence} | Reason: {flag.reason}")
            print(f"    Action: {flag.recommended_action}")

        # -------------------------------------------------------------
        # Scenario 3: Duplicate Sample (Exact Hash Duplicate)
        # -------------------------------------------------------------
        print("\n" + "-" * 86)
        print("TEST DOCUMENT: 3. Duplicate Document (Exact Hash Match)")
        doc_dup = register_test_doc(
            "duplicate_sample.pdf",
            sample_paths["duplicate"],
            "NBA_ACCREDITATION",
            {
                "certificate_number": "NBA-2024-SKCET-001",
                "issue_date": "2026-10-28",
                "expiry_date": "2029-10-27",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "aicte_institute_id": "SKCET01",
            },
            sha_seed=doc_clean.sha256_hash,
        )
        print(f"Filename: {doc_dup.original_filename} | Doc ID: #{doc_dup.id}")
        run_dup, flags_dup = AnomalyService.scan_document(db=db, document_id=doc_dup.id)
        for idx, flag in enumerate(flags_dup, 1):
            print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code}")
            print(f"    Reason: {flag.reason}")
            print(f"    Evidence: {flag.evidence_json}")

        # -------------------------------------------------------------
        # Scenario 4: Tampered Stamp (Visual Copy-Move Clustering)
        # -------------------------------------------------------------
        print("\n" + "-" * 86)
        print("TEST DOCUMENT: 4. Tampered Stamp (Visual Copy-Move Clustering)")
        doc_tamper = register_test_doc(
            "tampered_stamp_sample.pdf",
            sample_paths["tampered_stamp"],
            "BUILDING_PLAN",
            {
                "certificate_number": "DTCP-BLDG-2024-554",
                "issue_date": "2024-03-20",
                "expiry_date": "2029-03-19",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "aicte_institute_id": "SKCET01",
            },
        )
        print(f"Filename: {doc_tamper.original_filename} | Doc ID: #{doc_tamper.id}")
        run_tamper, flags_tamper = AnomalyService.scan_document(db=db, document_id=doc_tamper.id)
        for idx, flag in enumerate(flags_tamper, 1):
            print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code}")
            print(f"    Reason: {flag.reason}")
            print(f"    Evidence: {flag.evidence_json}")
            if flag.overlay_image_path:
                print(f"    Overlay PNG Rendered: {os.path.basename(flag.overlay_image_path)}")

        # -------------------------------------------------------------
        # Scenario 5: Suspicious Metadata (Photoshop / Canva Headers)
        # -------------------------------------------------------------
        print("\n" + "-" * 86)
        print("TEST DOCUMENT: 5. Suspicious Metadata (Photoshop / Canva Headers)")
        doc_meta = register_test_doc(
            "suspicious_metadata_sample.pdf",
            sample_paths["suspicious_metadata"],
            "LAND_DOCUMENTS",
            {
                "certificate_number": "LAND-REG-2021-008",
                "issue_date": "2021-03-01",
                "expiry_date": "2099-12-31",
                "institute_name": "Sri Krishna College of Engineering and Technology",
                "aicte_institute_id": "SKCET01",
            },
        )
        print(f"Filename: {doc_meta.original_filename} | Doc ID: #{doc_meta.id}")
        run_meta, flags_meta = AnomalyService.scan_document(db=db, document_id=doc_meta.id)
        for idx, flag in enumerate(flags_meta, 1):
            print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code}")
            print(f"    Reason: {flag.reason}")
            print(f"    Evidence: {flag.evidence_json}")

        # -------------------------------------------------------------
        # Scenario 6: Statutory Verification Conflict
        # -------------------------------------------------------------
        print("\n" + "-" * 86)
        print("TEST DOCUMENT: 6. Statutory Verification Conflict (Mismatch Detected)")
        doc_conflict = register_test_doc(
            "conflict_sample.pdf",
            sample_paths["edited_date"],
            "NBA_ACCREDITATION",
            {
                "certificate_number": "NBA-CONF-999",
                "issue_date": "2026-10-28",
                "expiry_date": "2029-10-27",
                "institute_name": "Sri Krishna College of Engineering and Technology",
            },
            sha_seed="unique_conflict_sha_seed",
        )
        existing_ver = db.query(VerificationResult).filter(VerificationResult.document_id == doc_conflict.id).first()
        if not existing_ver:
            existing_ver = VerificationResult(
                document_id=doc_conflict.id,
                status=VerificationStatus.MISMATCH_DETECTED,
                source_name="NBA Official Register (Simulated)",
                source_ref="NBA/REG/2026/099",
                details_json={
                    "mismatched_fields": [{"field": "institute_name", "submitted": "Sri Krishna College", "official": "Other Institute"}]
                },
            )
            db.add(existing_ver)
            db.commit()

        print(f"Filename: {doc_conflict.original_filename} | Doc ID: #{doc_conflict.id}")
        run_conflict, flags_conflict = AnomalyService.scan_document(db=db, document_id=doc_conflict.id)
        sample_flag_for_review = None
        for idx, flag in enumerate(flags_conflict, 1):
            if not sample_flag_for_review:
                sample_flag_for_review = flag
            print(f"  Flag #{idx}: [{flag.severity}] {flag.detector} :: {flag.code}")
            print(f"    Reason: {flag.reason}")
            print(f"    Evidence: {flag.evidence_json}")

        # Step 3: Admin Review Action Demonstration
        print("\n" + "=" * 86)
        print("[STEP 3] Demonstrating Administrative Review Workflow (Mandatory Note Audit Trail)")
        print("=" * 86)
        if sample_flag_for_review:
            print(f"Reviewing Anomaly Flag #{sample_flag_for_review.id} ({sample_flag_for_review.detector} / {sample_flag_for_review.code})")
            reviewed = AnomalyService.review_flag(
                db=db,
                flag_id=sample_flag_for_review.id,
                status=AnomalyReviewStatus.NEEDS_ACTION,
                note="Scrutiny committee verified date inconsistency with issuing authority; requested revised certificate.",
                reviewer_id=1,
            )
            print(f"  * Review Status Updated : {reviewed.review_status}")
            print(f"  * Review Note           : {reviewed.review_note}")
            print(f"  * Reviewed By User ID   : {reviewed.reviewed_by}")
            print(f"  * Reviewed At Timestamp : {reviewed.reviewed_at.isoformat()}")

        print("\n" + "=" * 86)
        print("Stage 5 Multi-Detector Anomaly Engine Demo Finished Successfully.")
        print("=" * 86)

    finally:
        db.close()


if __name__ == "__main__":
    run_stage5_demo()
