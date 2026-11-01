# AICTE SmartVerify AI • PS 26262 Demo Walkthrough

This document outlines the concise step-by-step click path to demonstrate the statutory workflow, procedural escalation engine, background scheduler, demo clock, consolidated reporting, simulated external integrations, safeguards, and statutory evaluation benchmark suite.

---

## 1. Demo User Logins

All demo accounts are pre-seeded and idempotent via `python -m backend.app.scripts.seed_workflow_demo`:

| Role | Email | Password | Region / Scope |
| :--- | :--- | :--- | :--- |
| **ADMIN (Central Admin)** | `admin@aicte.gov.in` | `password123` | National Oversight & Safeguards |
| **REGIONAL_OFFICER (South)** | `ro.south@aicte.gov.in` | `password123` | Southern Regional Office (View-Only Rules) |
| **REGIONAL_OFFICER (North)** | `ro.north@aicte.gov.in` | `password123` | Northern Regional Office (View-Only Rules) |
| **BUREAU_OFFICER (Director)** | `bureau@aicte.gov.in` | `password123` | Approvals Bureau (Competent Authority) |
| **COMMITTEE_MEMBER (Expert)** | `evc.expert@aicte.gov.in` | `password123` | Expert Visit Committee (EVC) |
| **INSTITUTE (SKCET)** | `principal@skcet.ac.in` | `password123` | Sri Krishna College of Eng & Tech |
| **INSTITUTE (BITS Pilani)** | `director@bitspilani.ac.in` | `password123` | BITS Pilani Technical Campus |

---

## 2. Pre-Seeded Highlight Cases for PS 26262

The demo seed script (`backend/app/scripts/seed_workflow_demo.py`) pre-populates the required state:

1. **Returned Application with Deficiency Remarks:** `APP-2026-S05` (SKCET) returned with reason: *"Certified land registry deed endorsement lacks survey number seal. Please upload clarification and endorsed registry documents."*
2. **Overdue EVC Visit:** `APP-2026-N01` (BITS Pilani) status `PENDING_SCHEDULING`, 4 days overdue past the statutory scheduling deadline.
3. **Undertaking at Escalation Level 2:** `APP-2026-W02` (VJTI Mumbai) - 10 days overdue registered lease deed, escalated to **Bureau Officer (Level 2)**.
4. **Lease Expiring in < 30 Days:** `INST-SKCET` Registered Lease Deed expiring in **25 days** (`EXPIRING_SOON`).

---

## 3. Walkthrough Click Path

### Step 1: Login & Navigation
1. Navigate to `/login`.
2. Login with `admin@aicte.gov.in` / `password123`.
3. Notice the official AICTE header, top bar unread notifications bell, role badge, and full navigation sidebar.

### Step 2: Application Workflow Routing & Actions
1. Navigate to **Workflow** (`/admin/workflow`) or **Applications** (`/admin/applications`).
2. Review the SLA counters, stage funnel, ageing buckets, and regional distribution.
3. Click on any application (e.g. `APP-2026-S01`) to open the **Workflow Detail Drawer**:
   - View current statutory stage, responsible role, start date, and due date.
   - Click **Reassign Officer**: select an officer from the list, provide a mandatory reason, and confirm.
   - Click **Return / Revert**: provide a statutory deficiency reason, note the stage step-back and applicant notification.
   - Switch to the **Unified Audit Timeline** tab inside the drawer to view the complete chronological log (Workflow stage changes, EVC events, Undertakings, Alerts, and Escalations).
   - *Governance Note:* System never auto-approves or rejects; only competent authorities (`BUREAU_OFFICER` or `ADMIN`) can record final decisions.

### Step 3: Return & Resubmit Deficiency Cycle
1. Log out and log in as Technical Institution: `principal@skcet.ac.in` / `password123`.
2. Navigate to **My Applications** (`/institute/applications`).
3. Find application `APP-2026-S05` flagged with status pill **RETURNED (Deficiency Notice)**.
4. View the itemized deficiency note: *"Certified land registry deed endorsement lacks survey number seal..."*.
5. Click **Respond & Resubmit**:
   - Enter institute clarification comments.
   - Submit response.
6. The application returns to the Scrutiny stage, resets its stage SLA clock, creates an in-app notification, and writes an immutable audit log entry.

### Step 4: EVC Physical Inspection & Conflict Check
1. Log in as Central Administrator: `admin@aicte.gov.in` / `password123`.
2. Navigate to **EVC** (`/admin/evc`).
3. Review the queue of applications awaiting physical inspection. Notice `APP-2026-N01` highlighted with an overdue scheduling badge.
4. Click **Schedule Visit**:
   - Select committee members (e.g., `Prof. S. Ranganathan`).
   - Pick a proposed date. If the member already has a visit scheduled on that date, an instant **Member Conflict Warning** is surfaced.
   - Confirm scheduling.
5. Click **Complete Visit** on a scheduled case:
   - Attach committee report PDF and enter remarks.
   - Confirming advances the workflow automatically to the subsequent stage via `WorkflowService` and auto-closes any open scheduling escalations.

### Step 5: Undertakings Compliance Register & Multi-Tier Escalations
1. Navigate to **Undertakings** (`/admin/undertakings`).
2. Filter by status (`ACTIVE`, `OVERDUE`, `ESCALATED`, `FULFILLED`).
3. Locate `APP-2026-W02` flagged as **ESCALATED (Level 2 - Bureau Officer)** due to 10 days overdue registered lease deed.
4. For an undertaking with submitted evidence, click **Verify Action**:
   - Select **Accept as fulfilled**, enter the official justification, and confirm.
   - Notice status updates to `FULFILLED` and active overdue escalation records auto-close.
5. Log in as an institute (`principal@skcet.ac.in`) and view `/institute/undertakings` to upload compliance evidence through the pipeline.

### Step 6: Document Validity & Lease Renewal (< 30 Days)
1. Navigate to **Document Validity** (`/admin/validity`).
2. Observe monitored documents, lease metadata (lessor, lessee, property address, lease duration), days left, and expiration pills.
3. Locate `INST-SKCET` Registered Lease Deed expiring in **25 days**, flagged in amber with an **EXPIRING SOON** badge.
4. For renewals submitted, click **Review Renewal** to Accept (with new expiry date) or Reject with a mandatory reason.
5. Institutes can submit renewals via `/institute/validity`.

### Step 7: Statutory Alert Rules & Escalation Matrix
1. Navigate to **Alerts** (`/admin/alerts`).
2. **Procedural Alerts Feed**: Filter by event type, status, or case ID. Click **Open case** to navigate directly to the linked case.
3. **Notification Rules Tab**:
   - Inspect the 11 pre-configured statutory event types.
   - Click **Edit** on any rule to modify day offsets (e.g., `30, 15, 7, 1, 0`), delivery channel (In-App or Email Outbox), or message template.
   - *Strict Invariant:* Prohibited words (`forgery`, `fraud`, `misconduct`) are rejected by schema validators; the mandatory disclaimer suffix is preserved on all automated notices.
4. **Escalation Matrix Tab**: View Level 1 (Regional Officer at 3d), Level 2 (Bureau Officer at 7d), and Level 3 (Admin at 14d) escalation thresholds.
5. **Escalation History Tab**: Audit log of active and auto-closed escalations.

### Step 8: Demonstration Clock (Simulated Date Testing)
1. On `/admin/alerts`, locate the **Demonstration Clock** banner.
2. Select a future date (e.g. `2026-11-20T10:00`) and click **Set Date**.
3. Notice the **DEMO CLOCK: 20-Nov-2026** badge illuminates in amber in the top bar across all pages.
4. Click **Run Scanner Now**:
   - Watch the scheduler scan workflows, EVC records, undertakings, and validity records against the simulated date.
   - The scanner idempotently creates new statutory reminders and escalates overdue undertakings to `ESCALATED`.
   - Running the scanner again demonstrates 0 duplicate alerts (Idempotency).
5. Click **Reset to Real Time** to revert back to wall clock time.

### Step 9: Consolidated Statutory Reports
1. Navigate to **Reports** (`/admin/reports`).
2. Select the **Regional Scope** (e.g. *All Regions*, *Southern Regional Office*, etc.).
3. Choose any of the 6 consolidated reports:
   - Application Pendency & Stage Ageing
   - EVC Physical Inspection Status
   - Statutory Undertakings Compliance Register
   - Monitored Document Validity & Lease Register
   - Overdue Cases & Statutory Escalations
   - Region-Wise Processing Performance Audit
4. Click **Official PDF** to stream the generated ReportLab document (includes two-pass page count, header rules, and statutory footer disclaimer).
5. Click **CSV** to download the raw tabular export.

### Step 10: Integrations Layer, Category Mappings & Safeguards
1. Navigate to **Rules & Timelines** (`/admin/rules`).
2. **Category Mappings Tab:**
   - Review and dynamically re-map application categories (`New Technical Institution`, `Extension of Approval (EoA)`, `Increase in Intake`, etc.) to any of the 4 statutory templates without code changes.
3. **Integrations Tab:**
   - View connectivity health of simulated external adapters (`ApplicationFeedAdapter` and `InstituteRecordAdapter`).
   - Click **Sync Simulated Feed Now** to ingest synthetic applications; verify duplicates are skipped idempotently.
   - Click **Import from File (JSON / CSV)** to import an external file feed.
4. **Safeguards & Retention Tab:**
   - Configure document retention period (default 1825 days / 5 years), audit log retention (2555 days / 7 years), maximum upload file size (25 MB), permitted file extensions, and statutory EVC deadlines.
   - All changes take effect dynamically and write audit log entries.

### Step 11: In-App Statutory Coverage Console
1. Navigate to **Coverage** (`/admin/coverage`).
2. View live operational database counters: Total Workflows, EVC Cases, Active Undertakings, Document Validity Records, Alert Events, and Audit Entries.
3. Review the complete interactive clause checklist mapping Sections A to F to screens, API routes, database models, and automated test proof.

### Step 12: AICTE System Evaluation & Benchmark Suite
1. Navigate to **Evaluation** (`/admin/evaluation`).
2. View the algorithmic benchmark dashboard showing 100% statutory adherence across all 8 procedural dimensions:
   - **Workflow Routing Accuracy** (100.0%)
   - **Deadline Calculation Accuracy** (100.0%)
   - **Alert Timeliness Using Demo Clock** (100.0%)
   - **Duplicate-Alert Rate** (0.0% - Idempotent)
   - **Escalation Correctness** (100.0%)
   - **Audit Completeness** (100.0%)
   - **Return & Resubmit Cycle Verification** (100.0%)
   - **Late Renewal Escalation Level 3** (100.0%)
3. Review the mandatory benchmark disclaimer: *"Measured on synthetic scenarios."*
4. Click **Re-Run Evaluation Scenarios** to re-verify the full benchmark suite live.

---

## 4. Statutory & Architectural Invariants Verified

- **Human Authority Invariant:** The system never auto-approves or auto-rejects; final decisions remain exclusively with the designated official role.
- **Language Policy:** Never uses inflammatory terms (`forgery`, `fraud`, `misconduct`). Every automated reminder terminates with:
  > *"This is a system reminder. Decisions remain with the competent authority."*
- **Idempotency:** Background scans are strictly idempotent; identical `(event_type, case_id, offset_days)` tuples produce zero duplicate alerts.
- **Data Isolation:** Institutes strictly access only their own alerts, applications, and documents.
- **Access Logging:** All case file and document views log actor, timestamp, IP, and resource identifiers.
- **UI Integrity:** AICTE brand colors (`#0B3C9D`, `#F58220`, `#E8650A`, cream `#FDF0DC`), official typography, and seal are preserved throughout.
