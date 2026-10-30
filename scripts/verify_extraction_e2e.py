import os
import sys
import time
from datetime import date, datetime
import httpx
import fitz

sys.path.insert(0, ".")

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.institute import Institute
from backend.app.models.document import Document
from backend.app.models.verification import MockRegisterEntry
from backend.app.security.tokens import create_access_token

BASE_URL = "http://127.0.0.1:8000"
TASK_LOG_PATH = r"C:\Users\lenovo\.gemini\antigravity\brain\6cf39195-eee5-4fd7-9d8b-8854a97b95b0\.system_generated\tasks\task-1881.log"

def main():
    print("=" * 70)
    print("AICTE SmartVerify AI - End-to-End Extraction Verification")
    print("=" * 70)

    # 1. Connect & Prepare SKCET User and Token
    db = SessionLocal()
    inst = db.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
    assert inst is not None, "Institute SKCET01 not found"
    user = db.query(User).filter(User.institute_id == inst.id).first()
    assert user is not None, "User for SKCET01 not found"

    # Ensure mock register entry exists so verification passes cleanly
    mock = db.query(MockRegisterEntry).filter(MockRegisterEntry.certificate_number == "FSNOC-SKCET-2026-VAL").first()
    if not mock:
        mock = MockRegisterEntry(
            authority="fire_dept",
            certificate_number="FSNOC-SKCET-2026-VAL",
            institute_name="Sri Krishna College of Engineering and Technology",
            issue_date="2026-07-02",
            expiry_date="2027-07-02",
            status="VALID",
            data_json={
                "building_name": "Sri Krishna College of Engineering and Technology",
                "address": "Kuniamuthur, Coimbatore, Tamil Nadu 641008",
                "aicte_id": "SKCET01",
            },
        )
        db.add(mock)
        db.commit()
        print("[MOCK REGISTER] Created entry for FSNOC-SKCET-2026-VAL")
    else:
        print("[MOCK REGISTER] Entry for FSNOC-SKCET-2026-VAL confirmed")

    token = create_access_token(user_id=user.id, role=user.role)
    headers = {"Authorization": f"Bearer {token}"}
    client = httpx.Client(base_url=BASE_URL, headers=headers, timeout=20.0)

    # 2. Step 2: Delete old documents named "01_fire_noc_VALID.pdf" and "03_occupancy_EXPIRING_SOON.pdf"
    target_filenames = ["01_fire_noc_VALID.pdf", "03_occupancy_EXPIRING_SOON.pdf"]
    old_docs = (
        db.query(Document)
        .filter(Document.institute_id == inst.id, Document.original_filename.in_(target_filenames))
        .all()
    )
    print(f"\n[STEP 2] Deleting {len(old_docs)} old target documents for {inst.name}...")
    for d in old_docs:
        del_resp = client.delete(f"/api/institute/documents/{d.id}")
        print(f"  DELETE /api/institute/documents/{d.id} ({d.original_filename}): Status {del_resp.status_code} - {del_resp.json().get('message')}")
        assert del_resp.status_code == 200, f"Failed to delete document {d.id}: {del_resp.text}"

    db.close()

    # 3. Step 3: Create & upload fresh Fire NOC PDF
    print("\n[STEP 3] Generating fresh Fire NOC PDF...")
    doc_pdf = fitz.open()
    page = doc_pdf.new_page(width=595, height=842)

    # Insert Title and the 7 required lines
    page.insert_text(fitz.Point(50, 60), "Fire & Life Safety No Objection Certificate", fontsize=15, fontname="helv", color=(0.1, 0.2, 0.5))
    lines = [
        "Certificate Number: FSNOC-SKCET-2026-VAL",
        "Issued To: Sri Krishna College of Engineering and Technology",
        "Building Name: Sri Krishna College of Engineering and Technology",
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008",
        "AICTE Institute ID: SKCET01",
        "Date of Issue: 02-07-2026",
        "Valid Upto: 02-07-2027",
    ]
    y = 110
    for line in lines:
        page.insert_text(fitz.Point(50, y), line, fontsize=11, fontname="helv")
        y += 28

    pdf_bytes = doc_pdf.tobytes()
    doc_pdf.close()

    filename = "01_fire_noc_VALID.pdf"
    print(f"Uploading '{filename}' ({len(pdf_bytes)} bytes) to /api/institute/documents...")

    files = {"file": (filename, pdf_bytes, "application/pdf")}
    data = {"document_type_code": "FIRE_NOC", "application_id": "113"}

    upload_start = time.time()
    upload_resp = client.post("/api/institute/documents", data=data, files=files)
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.status_code} {upload_resp.text}"
    uploaded_doc = upload_resp.json()
    new_doc_id = uploaded_doc["id"]
    print(f"Uploaded successfully! Document ID: {new_doc_id}, Status: {uploaded_doc.get('status')}")

    # 4. Step 4: Wait until OCR, extraction, and verification finish
    print(f"\n[STEP 4] Waiting for document #{new_doc_id} pipeline to complete...")
    max_wait = 20
    poll_interval = 1.0
    elapsed = 0.0

    extraction_data = None
    verification_data = None
    final_doc_status = None

    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed = time.time() - upload_start

        # Check document status
        d_resp = client.get("/api/institute/documents")
        if d_resp.status_code == 200:
            doc_items = d_resp.json()
            matching = next((item for item in doc_items if item["id"] == new_doc_id), None)
            if matching:
                final_doc_status = matching.get("status")
                ocr_st = matching.get("ocr_status")
                if ocr_st in ["DONE", "COMPLETED"]:
                    print(f"  Pipeline completed in {elapsed:.2f}s! (OCR: {ocr_st}, Document Status: {final_doc_status})")
                    break

    # Fetch extraction details
    ext_resp = client.get(f"/api/institute/documents/{new_doc_id}/extraction")
    assert ext_resp.status_code == 200, f"Failed to get extraction: {ext_resp.text}"
    extraction_data = ext_resp.json()

    # Fetch verification details
    ver_resp = client.get(f"/api/institute/documents/{new_doc_id}/verification")
    assert ver_resp.status_code == 200, f"Failed to get verification: {ver_resp.text}"
    verification_data = ver_resp.json()

    # Print results as requested
    print("\n" + "=" * 70)
    print("PIPELINE EXECUTION RESULTS:")
    print("=" * 70)

    # 1. Classification type and score
    cls_info = extraction_data.get("classification") or {}
    pred_type = cls_info.get("predicted_type")
    score = cls_info.get("score", 0.0)
    print(f"1. Classification:")
    print(f"   • Type : {pred_type}")
    print(f"   • Score: {score:.2%}")

    # 2. Every extracted field with value and confidence
    fields = extraction_data.get("fields") or []
    print(f"\n2. Extracted Fields ({len(fields)} fields):")
    field_dict = {}
    for f in fields:
        field_dict[f["key"]] = f
        val = f.get("value")
        norm = f.get("normalized_value")
        conf = f.get("confidence", 0.0)
        print(f"   • {f['key']:18}: {val!r:45} (norm: {norm!r:15}, conf: {conf:.2f})")

    # 3. Expiry date and days left
    exp_date = extraction_data.get("expiry_date")
    iss_date = extraction_data.get("issue_date")
    days_left = extraction_data.get("days_remaining")
    is_exp = extraction_data.get("is_expired")
    print(f"\n3. Dates & Validity:")
    print(f"   • Issue Date : {iss_date}")
    print(f"   • Expiry Date: {exp_date}")
    print(f"   • Days Left  : {days_left} (as of today)")
    print(f"   • Is Expired : {is_exp}")

    # 4. Verification status and field-by-field comparison
    ver_status = verification_data.get("status")
    print(f"\n4. Verification Status & Comparisons:")
    print(f"   • Status     : {ver_status}")
    print(f"   • Source     : {verification_data.get('source_name')}")
    print(f"   • Matched    : {verification_data.get('matched_fields')}")
    print(f"   • Mismatched : {verification_data.get('mismatched_fields')}")
    details = verification_data.get("details") or {}
    comparisons = details.get("all_comparisons") or []
    if comparisons:
        print("   • Field-by-Field Comparisons:")
        for cmp in comparisons:
            matched_sym = "MATCH" if cmp.get("matched") else "MISMATCH"
            print(f"     [{matched_sym}] {cmp.get('field'):18} => Submitted: {cmp.get('submitted')!r} | Official: {cmp.get('official')!r}")

    # 5. Job log lines for this document
    print(f"\n5. Server Job Log Lines for Document #{new_doc_id}:")
    if os.path.exists(TASK_LOG_PATH):
        with open(TASK_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            log_lines = f.readlines()
        doc_logs = [line.strip() for line in log_lines if f"#{new_doc_id}" in line or f"Document {new_doc_id}" in line or f"doc_id={new_doc_id}" in line]
        if doc_logs:
            for l in doc_logs:
                print(f"   {l}")
        else:
            print("   (No direct lines with document ID, showing last 10 lines of task log:)")
            for l in log_lines[-10:]:
                print(f"   {l.strip()}")
    else:
        print("   (Task log file not found at expected path)")

    # 5. Step 5: Pass criteria validation
    print("\n" + "=" * 70)
    print("PASS CRITERIA VERIFICATION:")
    print("=" * 70)

    # Criterion 1: valid_upto = 2027-07-02
    valid_upto_norm = field_dict.get("valid_upto", {}).get("normalized_value")
    c1 = (valid_upto_norm == "2027-07-02" or exp_date == "2027-07-02")
    print(f"  [1] valid_upto = 2027-07-02             : {'PASS' if c1 else 'FAIL'} (valid_upto norm={valid_upto_norm}, exp_date={exp_date})")

    # Criterion 2: issue_date = 2026-07-02
    issue_date_norm = field_dict.get("issue_date", {}).get("normalized_value")
    c2 = (issue_date_norm == "2026-07-02" or iss_date == "2026-07-02")
    print(f"  [2] issue_date = 2026-07-02             : {'PASS' if c2 else 'FAIL'} (issue_date norm={issue_date_norm}, iss_date={iss_date})")

    # Criterion 3: building_name and institute_name = Sri Krishna College of Engineering and Technology (not "Name")
    bld = field_dict.get("building_name", {}).get("value", "")
    inst_name = field_dict.get("institute_name", {}).get("value", "")
    expected_name = "Sri Krishna College of Engineering and Technology"
    c3 = (bld == expected_name and inst_name == expected_name)
    print(f"  [3] building_name & institute_name full  : {'PASS' if c3 else 'FAIL'} (building='{bld}', institute='{inst_name}')")

    # Criterion 4: at least 6 fields extracted
    c4 = len(fields) >= 6
    print(f"  [4] at least 6 fields extracted ({len(fields)} >= 6): {'PASS' if c4 else 'FAIL'}")

    # Criterion 5: classification score at least 80%
    c5 = score >= 0.80
    print(f"  [5] classification score >= 80% ({score:.2%} >= 80%): {'PASS' if c5 else 'FAIL'}")

    # Criterion 6: document status not "Expired"
    c6 = (final_doc_status != "Expired" and not is_exp)
    print(f"  [6] document status not 'Expired'       : {'PASS' if c6 else 'FAIL'} (status='{final_doc_status}', is_exp={is_exp})")

    all_passed = c1 and c2 and c3 and c4 and c5 and c6
    print("=" * 70)
    if all_passed:
        print("ALL PASS CRITERIA SATISFIED SUCCESSFULLY!")
    else:
        print("SOME CRITERIA FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()

