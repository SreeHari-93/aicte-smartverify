# AICTE SmartVerify AI — Step 1: Secure Authentication Core

AICTE SmartVerify AI is an AI-powered validation platform built for the **All India Council for Technical Education (AICTE)**. This repository houses **Step 1: Secure Login & Authentication Backend**, establishing the identity foundation, RBAC, tamper-proof audit logging, and anti-abuse safeguards for future verification modules.

---

## 📸 Visual Design & Layout

- **Desktop (1440px)**: Full-viewport background featuring the AICTE headquarters (`inst1.jpg`). The AICTE logo, English title, and Hindi text (*अखिल भारतीय तकनीकी शिक्षा परिषद*) are native to the image at the top-left and kept completely unobscured. A 440px card floats on the right over the sky and trees.
- **Mobile (390px)**: The image acts as a 38vh top banner preserving the council header, while the card sits below with a -24px overlap.
- **Human Touches**: Thin 4px Tricolour strip (Saffron, White, Green) at the top, official copyright footer, and a *"Secured by SmartVerify AI"* badge.

---

## 🛠 Tech Stack

- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, React Hook Form, Zod, Axios, Lucide React.
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (with SQLite fallback for local development), Argon2id (`argon2-cffi`), PyJWT, Pillow (`PIL`).
- **DevOps**: Docker, Docker Compose, Nginx.

---

## 🚀 Quickstart

### Option A: Run with Docker Compose (PostgreSQL + Backend + Frontend)

Ensure Docker Desktop is running:

```bash
docker-compose up --build
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **PostgreSQL**: `localhost:5432`

---

### Option B: Run Locally (Fast SQLite Dev Mode)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create & activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Alembic database migrations
alembic -c alembic.ini upgrade head

# Seed synthetic test data
python -m backend.app.scripts.seed

# Start FastAPI server
uvicorn backend.app.main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install npm packages
npm install

# Start Vite development server
npm run dev
```

Visit [http://localhost:5173](http://localhost:5173).

---

## 🔑 Synthetic Test Accounts (Pre-Seeded)

| Role | Tab | User / Identifier | AICTE Institute ID | Password | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Institute** | Institute | `skcet@aicte.edu.in` | `SKCET01` | `Institute@123` | **Sri Krishna College of Eng & Tech** (108 apps, 24 certs, 11 courses) |
| **Institute** | Institute | `del0101@aicte.edu.in` | `DEL0101` | `Institute@123` | Delhi Institute of Advanced Technology |
| **Institute** | Institute | `mah0202@aicte.edu.in` | `MAH0202` | `Institute@123` | Maharashtra College of Engineering |
| **Institute** | Institute | `kar0303@aicte.edu.in` | `KAR0303` | `Institute@123` | Karnataka Technical University |
| **Admin** | Admin | `admin@aicte-india.org` | *N/A* | `Admin@2026!` | Central AICTE Administrator |
| **Reviewer**| Admin | `reviewer@aicte-india.org` | *N/A* | `Reviewer@2026!`| Document Scrutiny Reviewer |

---

## 📡 API Reference

### Authentication (Step 1)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/auth/captcha` | Generates distorted image captcha (SHA-256 stored, 2-min TTL) | No |
| `POST` | `/api/auth/login` | Authenticates user (Argon2id, Captcha check, Lockout & Rate limit) | No |
| `POST` | `/api/auth/logout` | Revokes server-side refresh token & clears HttpOnly cookies | Yes |
| `POST` | `/api/auth/refresh` | Rotates refresh token & issues fresh access token | Cookie |
| `GET` | `/api/auth/me` | Fetches authenticated user and affiliated institute details | Yes (JWT) |
| `POST` | `/api/auth/register` | Registration onboarding stub with strict password policy | No |
| `GET` | `/api/health` | Service health status | No |

### Institute Portal (Step 2A)
| Method | Endpoint | Description | Scoped / Auth |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/institute/dashboard` | Institute stats (filed, approved, pending, rejected), NIRF rank & courses | Yes (INSTITUTE) |
| `GET` | `/api/institute/certificates` | Paginated certificate expiry tracker with computed statuses & stats | Yes (INSTITUTE) |
| `GET` | `/api/institute/certificates/upcoming` | Soonest upcoming expiries sorted relative to today's date | Yes (INSTITUTE) |
| `POST` | `/api/institute/certificates/{id}/renew` | Submits certificate renewal request with new validity dates | Yes (INSTITUTE) |
| `GET` | `/api/institute/applications` | List institutional applications & summary chips (Draft, Submitted, etc.) | Yes (INSTITUTE) |
| `POST` | `/api/institute/applications` | Creates new draft application under specified category | Yes (INSTITUTE) |
| `GET` | `/api/institute/rules` | Searchable AICTE Approval Process Handbook checklist rules | Yes (INSTITUTE) |
| `POST` | `/api/institute/documents` | Multipart file upload with magic byte verification & SHA-256 hashing | Yes (INSTITUTE) |
| `GET` | `/api/institute/documents` | Lists uploaded institutional documents archive | Yes (INSTITUTE) |
| `GET` | `/api/institute/documents/{id}/download` | Downloads or previews authentic uploaded document | Yes (INSTITUTE) |
| `DELETE` | `/api/institute/documents/{id}` | Permanently deletes document record and off-root file | Yes (INSTITUTE) |
| `GET` | `/api/institute/validation/{app_id}` | AI scrutiny validation checklist report with sample synthetic rows | Yes (INSTITUTE) |
| `GET` | `/api/institute/complaints` | Lists lodged grievance tickets and status | Yes (INSTITUTE) |
| `POST` | `/api/institute/complaints` | Lodges new grievance ticket with category and details | Yes (INSTITUTE) |
| `POST` | `/api/institute/reports/generate` | Generates real PDF/CSV regulatory report files using ReportLab | Yes (INSTITUTE) |
| `GET` | `/api/institute/reports` | Lists generated reports with download links | Yes (INSTITUTE) |
| `GET` | `/api/institute/reports/{id}/download`| Downloads compiled PDF/CSV report file | Yes (INSTITUTE) |
| `GET` | `/api/institute/notifications` | Returns certificate expiry notifications & unread counter | Yes (INSTITUTE) |
| `PATCH`| `/api/institute/notifications/{id}/read` | Marks notification as read | Yes (INSTITUTE) |
| `PATCH`| `/api/institute/notifications/read-all` | Marks all notifications as read | Yes (INSTITUTE) |

---

## 🔒 Security Architecture Highlights

1. **Argon2id Password Hashing**: State-of-the-art memory-hard hashing with timing attack prevention via constant-time dummy verification.
2. **Server-Side Dynamic Captcha**: Rendered using Pillow with geometric distortion, noise lines, and random rotation. Stored solely as a SHA-256 digest with single-use consumption.
3. **Double-Layered Abuse Prevention**:
   - Sliding-window rate limiter: 5 attempts/minute per IP and per account.
   - Account Lockout: Automatically locks account for 15 minutes after 5 consecutive failures.
4. **Token Security**:
   - Access Token: 15-minute JWT in `HttpOnly`, `SameSite=Strict` cookie.
   - Refresh Token: 7-day cryptographically random token stored hashed in DB with rotation.
   - CSRF Defense: Double-submit cookie verification on mutating endpoints.
5. **Append-Only Audit Trail**: Every authentication action (`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `CAPTCHA_FAILURE`, `ACCOUNT_LOCKOUT`, `LOGOUT`, etc.) is recorded immutably in `audit_logs`.

---

## 🧪 Running Pytest Tests

The backend includes a comprehensive test suite (37 tests) covering security, portal, the declarative rule engine, and admin APIs:

```bash
backend\venv\Scripts\pytest -v backend\tests
```

Suite covers:
- `test_captcha_generation`
- `test_captcha_verification_success`
- `test_captcha_reuse_fails` (one-time use)
- `test_captcha_expiry` (2-minute TTL)
- `test_account_lockout_after_five_failed_attempts` (15-min lockout & countdown response)
- `test_successful_institute_login` & `test_successful_admin_login`
- `test_wrong_role_login_rejection`
- `test_get_me_authenticated`
- `test_logout_revokes_session`
- `test_ip_rate_limiting` (429 responses after 5 attempts/min)
- `test_safe_path_resolver_safety` (sandbox containment, rejection of `__class__`/globals)
- `test_safe_comparator_operations` (regex length guard, date comparison, fuzzy matching)
- `test_evaluator_document_required` (presence, expiration check, min validity days)
- `test_evaluator_field_required` (presence, null checks)
- `test_evaluator_validity_period` (reference date, buffer days)
- `test_evaluator_cross_field_match` (fuzzy threshold, exact string matches)
- `test_evaluator_numeric_threshold` (comparison operators, metrics)
- `test_evaluator_count_at_least` (filtering, conditions on collections)
- `test_evaluator_composite` (nested boolean trees: all, any, not)
- `test_nesting_depth_validation` (rejection of condition trees exceeding depth 6)
- `test_rbac_admin_routes` (403 for unauthorized institute users)
- `test_document_type_crud` (catalog management)
- `test_category_and_checklist_crud` (dynamic checklist mapping)
- `test_rule_crud_optimistic_locking_and_versioning` (409 on version conflict, snapshot history)
- `test_rule_simulation_and_validation` (offline condition dry-runs)
- `test_ruleset_publish_and_rollback` (snapshot freezing and restoration)

---

## 🧠 Declarative Rule Engine (Backend Stage 1)

AICTE SmartVerify AI features a declarative, sandbox-safe rule engine with **zero code execution (`no eval / exec`)**, deterministic Pydantic discriminated union schemas, and maximum nesting depth enforcement ($\le 6$).

### 1. Supported Rule Types & Declarative JSON Examples

#### A. `DOCUMENT_REQUIRED`
Verifies that a mandatory institutional document has been uploaded and remains valid for at least `min_validity_days`.
```json
{
  "type": "DOCUMENT_REQUIRED",
  "document": "FIRE_NOC",
  "min_validity_days": 30
}
```

#### B. `FIELD_REQUIRED`
Verifies that a specified field in the application or institute profile is present and non-empty.
```json
{
  "type": "FIELD_REQUIRED",
  "field": "application.academic_year"
}
```

#### C. `VALIDITY_PERIOD`
Verifies that a certificate or document remains legally unexpired on a specific date (or relative to `"today"`), optionally enforcing extra buffer days.
```json
{
  "type": "VALIDITY_PERIOD",
  "document": "NBA_CERT",
  "must_be_valid_on": "today",
  "buffer_days": 60
}
```

#### D. `CROSS_FIELD_MATCH`
Cross-validates extracted text from an uploaded document against institutional database records, supporting exact or fuzzy string matching.
```json
{
  "type": "CROSS_FIELD_MATCH",
  "left": "institute.name",
  "right": "doc.AFFIDAVIT.deponent_name",
  "fuzzy": true,
  "threshold": 0.8
}
```

#### E. `NUMERIC_THRESHOLD`
Verifies numeric metrics against statutory AICTE thresholds (e.g. NIRF ranking, sanctioned student intake).
```json
{
  "type": "NUMERIC_THRESHOLD",
  "field": "institute.nirf_rank",
  "operator": "<=",
  "value": 100
}
```

#### F. `COUNT_AT_LEAST`
Ensures that a specified sub-collection (e.g., courses, faculty, complaints) contains at least $N$ items satisfying an optional condition.
```json
{
  "type": "COUNT_AT_LEAST",
  "collection": "courses",
  "field": "intake",
  "min_count": 2,
  "condition": { "operator": ">=", "value": 120 }
}
```

#### G. `EXTERNAL_VERIFICATION`
Validates certificate authenticity against third-party statutory registries (e.g., NAAC portal, NBA API, DigiLocker).
```json
{
  "type": "EXTERNAL_VERIFICATION",
  "document": "NAAC_CERT",
  "verification_service": "NAAC_PORTAL_API"
}
```

#### H. `INFRASTRUCTURE`
Verifies physical infrastructure space norms (e.g., instructional carpet area, student-to-PC ratios, leased line bandwidth).
```json
{
  "type": "INFRASTRUCTURE",
  "check_type": "COMPUTER_RATIO",
  "min_bandwidth_mbps": 100.0
}
```

#### I. `COMPOSITE` (`all`, `any`, `not`)
Combines multiple atomic conditions into a boolean tree up to 6 levels deep.
```json
{
  "type": "COMPOSITE",
  "operator": "all",
  "conditions": [
    {
      "type": "VALIDITY_PERIOD",
      "document": "FIRE_NOC",
      "must_be_valid_on": "today",
      "buffer_days": 30
    },
    {
      "type": "DOCUMENT_REQUIRED",
      "document": "BARRIER_FREE"
    }
  ]
}
```

---

## 📖 How an Admin Adds a New Document Requirement

Through the Admin APIs, an administrator can configure a new document requirement from scratch without touching any backend code or redeploying the application:

1. **Create the DocumentType**:
   Define code, accepted MIME formats, maximum size in MB, verification method (`QR`, `API`, `PORTAL`, `DIGITAL_SIGNATURE`, `MANUAL`), and the JSON extraction schema for OCR.
2. **Add to Application Category Checklist**:
   Map the new document type into an application category (e.g., `EOA`), setting whether it is mandatory, display order, and minimum validity days.
3. **Configure the Declarative Rule**:
   Create a new rule referencing the document type with its condition definition, severity (`BLOCKER`, `MAJOR`, `MINOR`, `ADVISORY`), and handbook reference.
4. **Simulate Condition Execution**:
   Call the `POST /api/v1/admin/rules/simulate` endpoint with mock context data to verify the logic passes and fails as intended.
5. **Freeze & Publish a New RuleSet Snapshot**:
   Publish a new `RuleSet` (e.g. `"APH 2026-27 v2.0"`). The system captures an immutable snapshot of all published rules, document types, and checklists.
6. **Instant Institute Portal Propagation**:
   The institute portal immediately shows the document on the required checklist (`GET /api/institute/checklist?category=EOA`) and displays the rule in the rules directory (`GET /api/institute/rules`).

---

## 💻 Full Curl Walkthrough

Execute the following commands sequentially against `http://127.0.0.1:8000`:

```bash
# 1. Login as AICTE Administrator
curl -s -c cookies.txt -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"identifier":"admin@aicte-india.org","password":"Admin@2026!","role":"ADMIN","captcha_id":"bypass","captcha_text":"bypass"}'

# 2. Create DocumentType: CYBER_AUDIT
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/admin/document-types \
  -H "Content-Type: application/json" \
  -d '{
    "code": "CYBER_AUDIT",
    "name": "Institutional Cyber Security & Network Audit Certificate",
    "description": "CERT-In empaneled auditor certification for campus network.",
    "issuing_authority": "CERT-In Empaneled Auditor",
    "accepted_formats": ["PDF"],
    "max_size_mb": 15,
    "has_expiry": true,
    "default_validity_months": 12,
    "verification_method": "DIGITAL_SIGNATURE",
    "extraction_schema": [
      {"key": "auditor_id", "label": "Auditor ID", "type": "id", "required": true},
      {"key": "audit_date", "label": "Audit Date", "type": "date", "required": true}
    ],
    "keywords": ["cyber", "security", "cert-in"]
  }'

# 3. Add to EOA Category Checklist
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/admin/checklists/EOA/items \
  -H "Content-Type: application/json" \
  -d '{
    "document_type_id": 15,
    "is_mandatory": true,
    "min_validity_days_remaining": 30,
    "display_order": 13,
    "help_text": "Upload signed audit report from CERT-In empaneled auditor."
  }'

# 4. Create Rule APH-2026-CH2-R22
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/admin/rules \
  -H "Content-Type: application/json" \
  -d '{
    "code": "APH-2026-CH2-R22",
    "title": "Mandatory Cyber Security Infrastructure & Campus Network Audit",
    "description": "Institutions must maintain annual CERT-In cyber audit certification.",
    "handbook_ref": "Section 4.5.1",
    "rule_type": "INFRASTRUCTURE",
    "severity": "MAJOR",
    "mandatory": true,
    "applies_to_categories": ["EOA"],
    "definition": {
      "type": "DOCUMENT_REQUIRED",
      "document": "CYBER_AUDIT",
      "min_validity_days": 30
    },
    "status": "PUBLISHED"
  }'

# 5. Simulate Rule Condition
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/admin/rules/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "definition": {
      "type": "DOCUMENT_REQUIRED",
      "document": "CYBER_AUDIT",
      "min_validity_days": 30
    },
    "context": {
      "application": {"category": "EOA"},
      "documents": [
        {"document_type_code": "CYBER_AUDIT", "status": "Uploaded", "expiry_date": "2027-04-30"}
      ]
    }
  }'

# 6. Publish New RuleSet Snapshot
curl -s -b cookies.txt -X POST http://127.0.0.1:8000/api/v1/admin/rulesets/publish \
  -H "Content-Type: application/json" \
  -d '{"name": "APH 2026-27", "version_label": "v2.0"}'

# 7. Fetch Checklist as Institute
curl -s -b inst_cookies.txt http://127.0.0.1:8000/api/institute/checklist?category=EOA
```

---

## 🔮 Stage 2 Preview: Document Pipeline with OCR

Backend Stage 1 directly provides the architectural foundation for Stage 2:
1. **Target Extraction Schemas (`DocumentType.extraction_schema`)**:
   Stage 2 OCR extractors (LayoutLM, Donut, Gemini Vision) will read each document type's extraction schema dynamically to locate and extract specified fields (e.g. `noc_number`, `valid_upto`, `built_up_area_sqm`, `ca_udin`, `deponent_name`).
2. **Automated Zero-Shot Document Classification (`DocumentType.keywords`)**:
   Unlabeled document uploads are classified automatically into matching `DocumentType.code` based on OCR extracted keywords and layout signatures.
3. **Structured Document Metadata (`Document.extracted_data`)**:
   Stage 2 persists OCR extracted key-value pairs directly into `Document.extracted_data` (JSON).
4. **Reproducible Validation Runs (`RuleSet.id`)**:
   When an institute submits an application, the validation pipeline links the exact `RuleSet.id` active at submission time, guaranteeing that future regulatory audits evaluate against the exact rules that were legally in force on that day.


