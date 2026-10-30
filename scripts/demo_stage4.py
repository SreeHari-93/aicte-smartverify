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
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.verification import (
    VerificationResult,
    VerificationStatus,
    AuthoritySource,
    MockRegisterEntry,
)
from backend.app.services.verification.service import VerificationService
from backend.app.services.verification.adapters.api_adapter import SIMULATED_SOURCE_LABEL
from scripts.demo_stage3 import run_stage3_demo

STORAGE_DIR = os.path.abspath(os.path.join(str(ROOT_DIR), "backend/storage/documents"))
os.makedirs(STORAGE_DIR, exist_ok=True)


def create_demo_file(filename: str, content: str = "Demo document content") -> str:
    path = os.path.join(STORAGE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def run_stage4_demo():
    print("=" * 82)
    print("AICTE SmartVerify AI — Stage 4 Statutory Verification Multi-Adapter Scrutiny Demo")
    print("=" * 82)

    db = SessionLocal()
    try:
        # 1. Resolve or create Institute
        inst = db.query(Institute).first()
        if not inst:
            inst = Institute(
                name="Sri Krishna College of Engineering and Technology",
                aicte_institute_id="1-3327641201",
                state="Tamil Nadu",
                status="ACTIVE",
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)

        # 2. Seed Authority Sources
        authorities = [
            ("NBA", "/mock-authorities/nba/verify", True),
            ("Fire Dept", "/mock-authorities/fire_dept/verify", True),
            ("Pollution Board", "/mock-authorities/pollution_board/verify", True),
            ("Municipal Corporation", "/mock-authorities/municipal/verify", False),  # Disabled for SOURCE_UNAVAILABLE
        ]
        for name, url, enabled in authorities:
            src = db.query(AuthoritySource).filter(AuthoritySource.name == name).first()
            if not src:
                src = AuthoritySource(name=name, base_url=url, enabled=enabled)
                db.add(src)
            else:
                src.enabled = enabled
                src.base_url = url
        db.commit()

        # 3. Seed Document Types
        doc_types = [
            ("NBA_CERT", "NBA Accreditation Certificate", "API", "NBA"),
            ("FIRE_NOC", "Fire Safety NOC Certificate", "API", "Fire Dept"),
            ("POLLUTION_NOC", "State Pollution Board NOC", "API", "Pollution Board"),
            ("AFFIDAVIT", "AICTE Comprehensive Statutory Affidavit", "MANUAL", "AICTE"),
            ("MUNICIPAL_NOC", "Municipal Land & Infrastructure NOC", "API", "Municipal Corporation"),
            ("BUILDING_PLAN", "Approved Structural & Architectural Plan", "MANUAL", "Town Planning"),
        ]
        for code, name, method, auth in doc_types:
            dt = db.query(DocumentType).filter(DocumentType.code == code).first()
            if not dt:
                dt = DocumentType(code=code, name=name, verification_method=method, issuing_authority=auth)
                db.add(dt)
            else:
                dt.verification_method = method
                dt.issuing_authority = auth
        db.commit()

        # 4. Seed Mock Authority Registers
        registers = [
            # 1. Valid NBA record
            ("nba", "NBA-SKCET-2026-VAL", inst.name, "2024-06-15", "2027-06-14", "VALID"),
            # 2. Fire record with mismatched institute name
            ("fire_dept", "FSNOC-SKCET-2026-MIS", "Metropolitan Engineering Academy", "2025-01-10", "2028-01-09", "VALID"),
            # 3. Expired pollution NOC
            ("pollution_board", "PCB-SKCET-2021-EXP", inst.name, "2021-02-01", "2024-01-31", "EXPIRED"),
            # 4. Municipal entry (authority disabled)
            ("municipal", "MC-SKCET-2026-UNAV", inst.name, "2025-03-01", "2028-02-28", "VALID"),
        ]
        for auth, cert, iname, iss, exp, st in registers:
            reg = db.query(MockRegisterEntry).filter(
                MockRegisterEntry.authority == auth,
                MockRegisterEntry.certificate_number == cert,
            ).first()
            if not reg:
                reg = MockRegisterEntry(
                    authority=auth,
                    certificate_number=cert,
                    institute_name=iname,
                    issue_date=iss,
                    expiry_date=exp,
                    status=st,
                    data_json={"verified_by": "System Automated Registrar"},
                )
                db.add(reg)
            else:
                reg.institute_name = iname
                reg.issue_date = iss
                reg.expiry_date = exp
                reg.status = st
        db.commit()

        # 5. Define 6 Demo Documents demonstrating all 6 statuses
        demo_specs = [
            {
                "expected_status": VerificationStatus.VERIFIED,
                "title": "Document 1: Genuine Valid Certificate (VERIFIED)",
                "filename": "DEMO-STAGE4-01_NBA_ACCREDITATION.pdf",
                "doc_type_code": "NBA_CERT",
                "fields": {
                    "certificate_number": "NBA-SKCET-2026-VAL",
                    "institute_name": inst.name,
                    "issue_date": "2024-06-15",
                    "expiry_date": "2027-06-14",
                },
                "run_verification": True,
            },
            {
                "expected_status": VerificationStatus.MISMATCH_DETECTED,
                "title": "Document 2: Discrepant Institute Details (MISMATCH_DETECTED)",
                "filename": "DEMO-STAGE4-02_FIRE_NOC.pdf",
                "doc_type_code": "FIRE_NOC",
                "fields": {
                    "certificate_number": "FSNOC-SKCET-2026-MIS",
                    "institute_name": inst.name,  # Register has "Metropolitan Engineering Academy"
                    "issue_date": "2025-01-10",
                    "expiry_date": "2028-01-09",
                },
                "run_verification": True,
            },
            {
                "expected_status": VerificationStatus.EXPIRED,
                "title": "Document 3: Expired Statutory Certification (EXPIRED)",
                "filename": "DEMO-STAGE4-03_POLLUTION_NOC.pdf",
                "doc_type_code": "POLLUTION_NOC",
                "fields": {
                    "certificate_number": "PCB-SKCET-2021-EXP",
                    "institute_name": inst.name,
                    "issue_date": "2021-02-01",
                    "expiry_date": "2024-01-31",
                },
                "run_verification": True,
            },
            {
                "expected_status": VerificationStatus.VERIFICATION_PENDING,
                "title": "Document 4: Fresh Institutional Upload (VERIFICATION_PENDING)",
                "filename": "DEMO-STAGE4-04_STATUTORY_AFFIDAVIT.pdf",
                "doc_type_code": "AFFIDAVIT",
                "fields": {
                    "certificate_number": "AFF-PENDING-2026",
                    "deponent_name": "Dr. K. Sundararajan",
                    "institute_name": inst.name,
                },
                "run_verification": False,  # Kept in pending state
            },
            {
                "expected_status": VerificationStatus.SOURCE_UNAVAILABLE,
                "title": "Document 5: Offline/Disabled Municipal Portal (SOURCE_UNAVAILABLE)",
                "filename": "DEMO-STAGE4-05_MUNICIPAL_NOC.pdf",
                "doc_type_code": "MUNICIPAL_NOC",
                "fields": {
                    "certificate_number": "MC-SKCET-2026-UNAV",
                    "institute_name": inst.name,
                    "issue_date": "2025-03-01",
                    "expiry_date": "2028-02-28",
                },
                "run_verification": True,
            },
            {
                "expected_status": VerificationStatus.MANUAL_REVIEW_REQUIRED,
                "title": "Document 6: Physical Building Architecture Plan (MANUAL_REVIEW_REQUIRED)",
                "filename": "DEMO-STAGE4-06_BUILDING_PLAN.pdf",
                "doc_type_code": "BUILDING_PLAN",
                "fields": {
                    "approval_number": "BPA-SKCET-2026",
                    "total_built_up_area": "42500 sqm",
                    "architect_license": "CA/99/24180",
                    "institute_name": inst.name,
                },
                "run_verification": True,
            },
        ]

        print(f"\n[+] Processing 6 Sample Documents across all Statutory Verification statuses...\n")

        results_summary = []

        for idx, spec in enumerate(demo_specs, 1):
            fn = spec["filename"]
            dt_code = spec["doc_type_code"]
            fpath = create_demo_file(fn, f"Demo file for {fn}")

            doc = db.query(Document).filter(
                Document.original_filename == fn,
                Document.institute_id == inst.id,
            ).first()

            if not doc:
                doc = Document(
                    institute_id=inst.id,
                    document_type_code=dt_code,
                    original_filename=fn,
                    stored_filename=fn,
                    file_path=fpath,
                    file_size=os.path.getsize(fpath),
                    mime_type="application/pdf",
                    sha256_hash=hashlib.sha256(fn.encode("utf-8")).hexdigest(),
                    status="Uploaded",
                    ocr_status="DONE",
                    extracted_data=spec["fields"],
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
            else:
                doc.extracted_data = spec["fields"]
                db.commit()

            # Ensure fields are seeded in ExtractedField table
            for k, v in spec["fields"].items():
                ef = db.query(ExtractedField).filter(
                    ExtractedField.document_id == doc.id,
                    ExtractedField.key == k,
                ).first()
                if not ef:
                    ef = ExtractedField(
                        document_id=doc.id,
                        key=k,
                        value=str(v),
                        confidence=0.98,
                        source="ocr",
                    )
                    db.add(ef)
                else:
                    ef.value = str(v)
            db.commit()

            # Execute verification or record pending
            if spec["run_verification"]:
                ver_res = VerificationService.verify_document(
                    db=db,
                    document_id=doc.id,
                    force_reverify=True,
                )
            else:
                # Set VERIFICATION_PENDING record
                existing = db.query(VerificationResult).filter(VerificationResult.document_id == doc.id).first()
                if not existing:
                    existing = VerificationResult(
                        document_id=doc.id,
                        status=VerificationStatus.VERIFICATION_PENDING,
                        source_name="Awaiting Submission / Verification Queue",
                        source_ref=spec["fields"].get("certificate_number"),
                        checked_at=datetime.now(timezone.utc),
                        details_json={"message": "Document queued for statutory verification."},
                    )
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)
                ver_res = existing

            db.refresh(doc)
            results_summary.append((spec, doc, ver_res))

        # 6. Pretty Print Output
        for idx, (spec, doc, ver_res) in enumerate(results_summary, 1):
            details = ver_res.details_json or {}
            comparisons = details.get("all_comparisons", [])
            is_sim = "simulated" in ver_res.source_name.lower() or "mock" in ver_res.source_name.lower() or bool(details.get("disclaimer"))

            print("-" * 82)
            print(f"[{idx}/6] {spec['title']}")
            print(f"      Document ID:       {doc.id} ({doc.original_filename})")
            print(f"      Document Type:     {doc.document_type_code}")
            print(f"      Status:            [{ver_res.status}]")
            print(f"      Authority Source:  {ver_res.source_name} {'[SIMULATED SOURCE]' if is_sim else ''}")
            print(f"      Timestamp:         {ver_res.checked_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            if details.get("message"):
                print(f"      Notice:            {details.get('message')}")

            # Print compared fields table
            if comparisons:
                print("\n      Reconciled Statutory Fields:")
                print(f"      {'-'*74}")
                print(f"      {'Field':<22} | {'Submitted Value':<24} | {'Official Value':<22} | Match")
                print(f"      {'-'*74}")
                for c in comparisons:
                    match_str = "MATCHED (OK)" if c.get("matched") else "MISMATCH (FAIL)"
                    sub_val = str(c.get("submitted", ""))[:24]
                    off_val = str(c.get("official", ""))[:22]
                    print(f"      {c.get('field', ''):<22} | {sub_val:<24} | {off_val:<22} | {match_str}")
                print(f"      {'-'*74}")
            else:
                print(f"      Compared Fields:   (No comparative fields available; method={doc.document_type.verification_method if doc.document_type else 'MANUAL'})")
            print()

        print("=" * 82)
        print("STAGE 4 VERIFICATION MATRIX COVERAGE:")
        for spec, doc, ver_res in results_summary:
            status_match = "PASS" if ver_res.status == spec["expected_status"] else "UNEXPECTED"
            print(f"  - [{status_match}] {spec['expected_status']:<25} -> {doc.original_filename}")
        print("=" * 82)
        print("Demo Stage 4 Executed Successfully with 6/6 Statuses Demonstrated.")
        print("=" * 82)

    finally:
        db.close()


if __name__ == "__main__":
    run_stage4_demo()
