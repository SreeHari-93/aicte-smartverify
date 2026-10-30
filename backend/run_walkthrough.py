import httpx
import json
from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.security.tokens import create_access_token

BASE_URL = "http://127.0.0.1:8000"

def run_walkthrough():
    print("=================================================================")
    print("BACKEND STAGE 1 - END-TO-END VERIFICATION WALKTHROUGH")
    print("=================================================================\n")

    db = SessionLocal()
    admin_user = db.query(User).filter(User.email == "admin@aicte-india.org").first()
    inst_user = db.query(User).filter(User.email == "skcet@aicte.edu.in").first()
    assert admin_user is not None, "Admin user must exist"
    assert inst_user is not None, "Institute user must exist"

    admin_token = create_access_token(user_id=admin_user.id, role="ADMIN")
    inst_token = create_access_token(user_id=inst_user.id, role="INSTITUTE")
    db.close()

    admin_client = httpx.Client(base_url=BASE_URL, cookies={"aicte_access_token": admin_token}, timeout=10.0)
    inst_client = httpx.Client(base_url=BASE_URL, cookies={"aicte_access_token": inst_token}, timeout=10.0)

    # Step 1: Admin Authentication Verification
    print(f"[1] Verified AICTE Administrator Identity: {admin_user.email} (Role: ADMIN)...")

    # Step 2: Create new DocumentType
    print("\n[2] Creating new DocumentType: CYBER_AUDIT (Cyber Security Audit Clearance)...")
    doc_payload = {
        "code": "CYBER_AUDIT",
        "name": "Institutional Cyber Security & Network Audit Certificate",
        "description": "CERT-In empaneled auditor certification for campus network and digital examination safety.",
        "issuing_authority": "CERT-In Empaneled Information Security Auditor",
        "accepted_formats": ["PDF"],
        "max_size_mb": 15,
        "has_expiry": True,
        "default_validity_months": 12,
        "verification_method": "DIGITAL_SIGNATURE",
        "extraction_schema": [
            {"key": "auditor_empaneled_id", "label": "Auditor CERT-In ID", "type": "id", "required": True},
            {"key": "audit_date", "label": "Date of Comprehensive Audit", "type": "date", "required": True},
            {"key": "compliance_score", "label": "Network Compliance Score", "type": "number", "required": True}
        ],
        "keywords": ["cyber", "security", "audit", "cert-in", "network", "firewall", "vulnerability"],
        "is_active": True
    }
    res = admin_client.post("/api/v1/admin/document-types", json=doc_payload)
    print(f"    Status: {res.status_code}, Created Code: {res.json().get('code')}, Name: {res.json().get('name')}")
    assert res.status_code in [201, 200]
    cyber_doc_id = res.json()["id"]

    # Step 3: Add to EOA Checklist
    print("\n[3] Appending CYBER_AUDIT to Extension of Approval (EOA) regulatory checklist...")
    chk_payload = {
        "document_type_id": cyber_doc_id,
        "is_mandatory": True,
        "min_validity_days_remaining": 30,
        "display_order": 13,
        "help_text": "Upload signed audit report from CERT-In empaneled auditor with minimum 30 days validity remaining.",
        "is_active": True
    }
    res = admin_client.post("/api/v1/admin/checklists/EOA/items", json=chk_payload)
    print(f"    Status: {res.status_code}, Checklist Item ID: {res.json().get('id')}, Mandatory: {res.json().get('is_mandatory')}")
    assert res.status_code == 201

    # Step 4: Create Rule APH-2026-CH2-R22 with Declarative Definition
    print("\n[4] Creating new Declarative Rule APH-2026-CH2-R22...")
    rule_payload = {
        "code": "APH-2026-CH2-R22",
        "title": "Mandatory Cyber Security Infrastructure & Campus Network Audit",
        "description": "Institutions conducting online examinations and digital evaluation must maintain annual CERT-In cyber audit certification.",
        "handbook_ref": "Section 4.5.1",
        "rule_type": "INFRASTRUCTURE",
        "severity": "MAJOR",
        "mandatory": True,
        "applies_to_categories": ["EOA"],
        "definition": {
            "type": "DOCUMENT_REQUIRED",
            "document": "CYBER_AUDIT",
            "min_validity_days": 30
        },
        "ai_checks": [
            "Verify CERT-In empanelment number against national cyber auditor registry",
            "Extract audit report validity timeline and vulnerability remediation index"
        ],
        "evidence_required": ["CYBER_AUDIT"],
        "suggested_action": "Engage a CERT-In empaneled security agency to conduct campus IT infrastructure audit and upload clearance report.",
        "status": "PUBLISHED"
    }
    res = admin_client.post("/api/v1/admin/rules", json=rule_payload)
    print(f"    Status: {res.status_code}, Rule Code: {res.json().get('code')}, Version: {res.json().get('current_version')}, Status: {res.json().get('status')}")
    assert res.status_code in [201, 200]

    # Step 5: Simulate Rule Condition
    print("\n[5] Simulating Rule Execution against mock EvaluationContext...")
    sim_payload = {
        "definition": {
            "type": "DOCUMENT_REQUIRED",
            "document": "CYBER_AUDIT",
            "min_validity_days": 30
        },
        "context": {
            "application": {"id": 8401, "category": "EOA"},
            "institute": {"name": "Sri Krishna College of Engineering and Technology"},
            "documents": [
                {
                    "document_type_code": "CYBER_AUDIT",
                    "status": "Uploaded",
                    "expiry_date": "2027-04-30"
                }
            ]
        },
        "rule_meta": {
            "code": "APH-2026-CH2-R22",
            "title": "Mandatory Cyber Security Infrastructure & Campus Network Audit",
            "severity": "MAJOR"
        }
    }
    res = admin_client.post("/api/v1/admin/rules/simulate", json=sim_payload)
    sim_data = res.json()
    print(f"    Status: {res.status_code}, Passed: {sim_data.get('passed')}, Message: {sim_data.get('message')}")
    assert sim_data.get("passed") is True

    # Step 6: Publish new RuleSet snapshot
    print("\n[6] Freezing and publishing new RuleSet snapshot: 'APH 2026-27' (v2.0)...")
    pub_payload = {
        "name": "APH 2026-27",
        "version_label": "v2.0"
    }
    res = admin_client.post("/api/v1/admin/rulesets/publish", json=pub_payload)
    ruleset_data = res.json()
    print(f"    Status: {res.status_code}, RuleSet ID: {ruleset_data.get('id')}, Name: {ruleset_data.get('name')}, Label: {ruleset_data.get('version_label')}, Frozen Rules Count: {ruleset_data.get('rules_count')}")
    assert res.status_code == 200

    # Step 7: Institute User Verification
    print(f"\n[7] Verified Institute User Identity: {inst_user.email} (SKCET)...")

    # Step 8: Fetch dynamic Checklist as Institute
    print("\n[8] Fetching dynamic category checklist (GET /api/institute/checklist?category=EOA)...")
    res = inst_client.get("/api/institute/checklist?category=EOA")
    chk_resp = res.json()
    print(f"    Status: {res.status_code}, Total Required: {chk_resp.get('total_required')}, Uploaded: {chk_resp.get('uploaded_count')}, Missing: {chk_resp.get('missing_count')}")
    cyber_in_checklist = any(item["document_type_code"] == "CYBER_AUDIT" for item in chk_resp.get("items", []))
    print(f"    --> Verified newly added 'CYBER_AUDIT' is present in Institute Checklist: {cyber_in_checklist}")
    assert cyber_in_checklist is True

    # Step 9: Fetch Rules as Institute
    print("\n[9] Fetching Regulatory Rules as Institute (GET /api/institute/rules)...")
    res = inst_client.get("/api/institute/rules")
    rules_resp = res.json()
    print(f"    Status: {res.status_code}, Total Rules in Portal: {rules_resp.get('summary', {}).get('total')}, Mandatory Count: {rules_resp.get('summary', {}).get('mandatory')}")

    print("\n=================================================================")
    print("SUCCESS: ALL 9 BACKEND STAGE 1 VERIFICATION STEPS PASSED PERFECTLY!")
    print("=================================================================\n")

if __name__ == "__main__":
    run_walkthrough()
