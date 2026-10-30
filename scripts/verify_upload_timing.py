import os
import sys
import time
import httpx
import pymupdf as fitz

# Ensure workspace root in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.security.tokens import create_access_token
from backend.app.database import SessionLocal
from backend.app.models.user import User

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("=" * 70)
    print("AICTE SmartVerify AI — Document Pipeline & Timing Verification")
    print("=" * 70)

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1. Ensure server is up
    print("1. Waiting for backend server at", BASE_URL)
    server_ready = False
    for attempt in range(20):
        try:
            r = client.get("/api/docs")
            if r.status_code == 200:
                server_ready = True
                print("   -> Backend server is healthy and responding.")
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not server_ready:
        print("ERROR: Backend server did not respond in time.")
        sys.exit(1)

    # 2. Generate auth token for Sri Krishna College user
    db = SessionLocal()
    user = db.query(User).filter(User.email == "skcet@aicte.edu.in").first()
    if not user:
        user = db.query(User).filter(User.role == "INSTITUTE").first()
    user_id = user.id
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    db.close()

    token = create_access_token(user_id=user_id, role=user_role)
    headers = {"Authorization": f"Bearer {token}"}
    print(f"2. Authenticated as user #{user_id} ({user.email})")

    # 3. Create a small valid text PDF
    pdf_filename = "test_live_fire_noc.pdf"
    doc_fitz = fitz.open()
    page = doc_fitz.new_page(width=595, height=842)
    sample_text = (
        "GOVERNMENT OF TAMIL NADU\n"
        "FIRE AND RESCUE SERVICES DEPARTMENT\n\n"
        "NO OBJECTION CERTIFICATE / FIRE SAFETY CLEARANCE\n\n"
        "Certificate Number: NOC-FIRE-2026-SKCET-001\n"
        "Institution Name: Sri Krishna College of Engineering and Technology\n"
        "Address: Kuniamuthur, Coimbatore, Tamil Nadu 641008\n"
        "Issue Date: 2026-01-10\n"
        "Expiry Date: 2027-01-09\n"
        "Statutory Status: APPROVED AND COMPLIANT\n"
    )
    page.insert_text((72, 100), sample_text, fontsize=12)
    pdf_bytes = doc_fitz.write()
    doc_fitz.close()
    file_size = len(pdf_bytes)
    print(f"3. Generated small text PDF '{pdf_filename}' ({file_size} bytes)")

    # 4. Upload document and measure timing
    print("4. Uploading document to /api/institute/documents ...")
    t0 = time.time()
    files = {"file": (pdf_filename, pdf_bytes, "application/pdf")}
    data = {"document_type_code": "FIRE_NOC"}

    upload_resp = client.post("/api/institute/documents", headers=headers, files=files, data=data)
    if upload_resp.status_code not in (200, 201):
        print(f"ERROR: Upload failed: {upload_resp.status_code} - {upload_resp.text}")
        sys.exit(1)

    upload_data = upload_resp.json()
    doc_id = upload_data["id"]
    t_upload = time.time() - t0
    print(f"   -> Upload acknowledged in {t_upload:.3f}s. Document ID: #{doc_id}")
    print(f"   -> Initial OCR Status: {upload_data.get('ocr_status')}")

    # 5. Poll for OCR status DONE and verification status leaving PENDING
    print("5. Monitoring background processing pipeline...")
    ocr_done_time = None
    verification_done_time = None
    final_ver_status = None
    final_ocr_status = None
    final_ver_source = None
    max_wait = 15.0

    while (time.time() - t0) < max_wait:
        elapsed = time.time() - t0
        try:
            doc_r = client.get("/api/institute/documents", headers=headers)
            if doc_r.status_code == 200:
                docs = doc_r.json()
                matching = next((d for d in docs if d["id"] == doc_id), None)
                if matching:
                    current_ocr = matching.get("ocr_status")
                    final_ocr_status = current_ocr
                    if current_ocr == "DONE" and ocr_done_time is None:
                        ocr_done_time = elapsed
                        print(f"   [{elapsed:.2f}s] OCR Status: DONE (Completed in {ocr_done_time:.2f}s)")

                    ver_st = matching.get("verification_status")
                    final_ver_source = matching.get("verification_source")
                    if ver_st and ver_st not in ("VERIFICATION_PENDING", "Pending") and verification_done_time is None:
                        verification_done_time = elapsed
                        final_ver_status = ver_st
                        print(f"   [{elapsed:.2f}s] Verification Status: {ver_st} (Source: {final_ver_source}) (Done in {verification_done_time:.2f}s)")
        except Exception as poll_err:
            print("   Polling warning:", poll_err)

        if ocr_done_time is not None and verification_done_time is not None:
            break

        time.sleep(0.2)

    total_time = time.time() - t0
    print("-" * 70)
    print("TIMING RESULTS:")
    print(f"   - Total elapsed time:               {total_time:.3f} seconds")
    print(f"   - Upload acknowledgement:           {t_upload:.3f} seconds")
    print(f"   - OCR status became Completed (DONE): {ocr_done_time:.3f}s" if ocr_done_time else "   - OCR status: TIMEOUT / NOT COMPLETED")
    print(f"   - Verification left Pending:        {verification_done_time:.3f}s (Final: {final_ver_status})" if verification_done_time else "   - Verification: TIMEOUT / STILL PENDING")
    print(f"   - Final Verification Status:        {final_ver_status}")
    print(f"   - Verification Source:              {final_ver_source}")
    print("-" * 70)

    # Detailed verification checks
    ver_detail_resp = client.get(f"/api/institute/documents/{doc_id}/verification", headers=headers)
    if ver_detail_resp.status_code == 200:
        ver_info = ver_detail_resp.json()
        print("VERIFICATION DETAILS:")
        print(f"   - Checked At: {ver_info.get('checked_at')}")
        print(f"   - Source Name: {ver_info.get('source_name')} ({'Simulated' if ver_info.get('is_simulated') else 'Official'})")
        print(f"   - Status: {ver_info.get('status')}")
        print(f"   - Mismatches: {len(ver_info.get('mismatched_fields') or [])}")
        print(f"   - Matches: {len(ver_info.get('matched_fields') or [])}")
        for mf in (ver_info.get('matched_fields') or []):
            print(f"       * {mf.get('field')}: {mf.get('submitted')} == {mf.get('official')}")

    success = (ocr_done_time is not None and verification_done_time is not None and total_time < 15.0)
    if success:
        print("\nSUCCESS: Document OCR completed and verification left Pending within 15 seconds!")
        sys.exit(0)
    else:
        print("\nFAILURE: Processing did not complete within 15 seconds.")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
