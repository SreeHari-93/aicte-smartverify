# AICTE PS 26262 Statutory Clause Coverage Matrix & Verification Proof

**Problem Statement PS 26262:** *Institutional Approval Workflow Automation, Multi-Tier SLA Escalations, Expert Visit Committee (EVC) Governance, Post-Approval Undertakings, and Document Validity Lifecycle Management.*

This document provides complete traceability mapping every statutory clause of PS 26262 (Sections A through F, key requirements, expected outcomes, and prototype criteria) to its implementing screen, API route, database tables, and automated test suite.

---

## 1. Statutory Invariant Mandate
> **Statutory Rule:** All decisions regarding approvals, rejections, committee formations, and deficiency reviews strictly remain with authorized AICTE officials. The system **never auto-approves or auto-rejects** any application under any circumstance; it strictly computes SLA timers, flags deficiencies, schedules visits, issues timely reminders, and escalates overdue milestones.

---

## 2. Clause-by-Clause Traceability Matrix

### Section A: Institutional Application & Checklist Submission
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **A.1 Multi-Category Application** | Technical institutions submit applications by selecting category (New Institute, EoA, Intake, Supernumerary, Appeal/Hearing, Surprise Inspection) with academic year, programme, intake details, and mandatory documents. Automatically determines statutory template and initial stage SLA. | `/institute/applications` (`ApplicationsPage.tsx`) | `POST /api/workflow/application/submit` | `applications`, `application_workflows`, `workflow_templates`, `workflow_template_stages` | `backend/tests/test_workflow.py::test_application_submission_creates_workflow` | **VERIFIED** |
| **A.2 Document Taxonomy & Checklist Validation** | Category-specific mandatory document checklists with strict taxonomy mapping (Land Documents, Building Plan, Fire NOC, AICTE Approval, NAAC/NBA Cert, etc.). | `/institute/documents` & `/admin/rules?tab=checklists` (`AdminChecklistsPage.tsx`) | `GET /api/v1/checklists`, `GET /api/v1/document-types` | `document_types`, `checklists`, `checklist_items`, `documents` | `backend/tests/test_workflow.py` | **VERIFIED** |

---

### Section B: Workflow Automation & 4 Statutory Templates
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **B.1 Four Configurable DB Templates** | Four standard procedural templates (`ONLY_SCRUTINY`, `SCRUTINY_EVC`, `EVC_SAC_SHC`, `ONLY_EVC`) stored in database with sequential stages, responsible roles, and editable SLA days. | `/admin/rules?tab=slas` (`WorkflowTimelinesManager.tsx`) | `GET /api/workflow/templates`, `PUT /api/workflow/templates/{tid}/stages/{sid}` | `workflow_templates`, `workflow_template_stages` | `backend/tests/test_workflow.py::test_workflow_templates_exist` | **VERIFIED** |
| **B.2 Multi-Role Stage Execution** | Stage advancement, return with mandatory deficiency justification, officer reassignment, and hold/resume operations. Only competent authority records final decision. Zero auto-decision invariant. | `/admin/workflow` (`AdminWorkflowPage.tsx`, `WorkflowDetailDrawer.tsx`) | `POST /api/workflow/application/{id}/advance`, `/return`, `/hold`, `/resume`, `/reassign`, `/decision` | `application_workflows`, `workflow_history`, `audit_logs` | `backend/tests/test_workflow.py::test_zero_auto_decision_invariant`, `test_workflow_state_transitions` | **VERIFIED** |
| **B.3 Return & Resubmit Deficiency Cycle** | When an officer returns an application for deficiency, institute receives itemized deficiency reasons and can submit clarification with optional files. Resubmission restarts stage SLA clock with full audit trail. | `/institute/applications` (`ApplicationsPage.tsx` modal) | `POST /api/workflow/application/{id}/resubmit` | `application_workflows`, `workflow_history`, `audit_logs`, `notifications` | `backend/tests/test_workflow.py::test_return_and_resubmit_workflow_cycle` | **VERIFIED** |
| **B.4 Plain-Language Case Summary** | Dynamic plain-language case summary synthesising application category, current stage, days remaining or overdue, assigned officer, and recent actions. | `/admin/workflow` & `/admin/applications` (`WorkflowDetailDrawer.tsx`) | `GET /api/workflow/application/{id}` | `application_workflows`, `applications` | `backend/tests/test_workflow.py::test_case_summary_generation` | **VERIFIED** |
| **B.5 Workload & Stage Bottleneck Analytics** | Average days spent per stage compared against SLA limit, identifying delays and operational bottlenecks; officer case counts. | `/admin/workflow` (`AdminWorkflowPage.tsx`) | `GET /api/workflow/dashboard` | `application_workflows`, `workflow_history` | `backend/tests/test_workflow.py::test_workflow_dashboard_metrics` | **VERIFIED** |

---

### Section C: Expert Visit Committee (EVC) Management
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **C.1 Automated Enqueueing & Deadlines** | Cases entering EVC stage automatically enter EVC queue with shorter scheduling (3d) & completion (5d) deadlines for new institutions vs standard (7d & 10d). Configurable in DB. | `/admin/evc` (`AdminEvcPage.tsx`) | `GET /api/evc/queue` | `evc_visits`, `application_workflows`, `system_settings` | `backend/tests/test_stage3.py::test_evc_creation_and_scheduling` | **VERIFIED** |
| **C.2 Committee Scheduling & Conflict Detection** | Assign committee members, proposed visit date, with automated validation alerting if any assigned committee member already has a visit scheduled on that date. | `/admin/evc` (`AdminEvcPage.tsx`) | `POST /api/evc/schedule`, `GET /api/evc/member-schedule-check` | `evc_visits`, `evc_committee_members` | `backend/tests/test_stage3.py::test_evc_creation_and_scheduling` | **VERIFIED** |
| **C.3 Visit Completion & Workflow Advancement** | Committee uploads physical inspection report, records recommendations, and completes visit. Completing visit automatically advances workflow to SAC / Decision stage via `WorkflowService`. | `/admin/evc` (`AdminEvcPage.tsx`) | `POST /api/evc/{id}/complete` | `evc_visits`, `application_workflows`, `audit_logs` | `backend/tests/test_stage3.py::test_evc_completion_advances_workflow` | **VERIFIED** |

---

### Section D: Undertakings & Document Validity Lifecycle
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **D.1 Undertakings Management** | Officials issue conditional undertakings across 5 statutory categories (Lease, Accreditation, Infrastructure, Faculty, Other). Institute uploads evidence; officer verifies (Accept, Request More, Reject). | `/admin/undertakings` & `/institute/undertakings` (`AdminUndertakingsPage.tsx`, `InstituteUndertakingsPage.tsx`) | `GET /api/undertakings`, `POST /api/undertakings`, `POST /api/undertakings/{id}/submit-evidence`, `/review` | `undertakings`, `undertaking_evidence`, `audit_logs` | `backend/tests/test_stage3.py::test_undertaking_lifecycle` | **VERIFIED** |
| **D.2 Document Validity & Expiry Timeline** | Tracks validity dates for statutory instruments (Fire NOC, Occupancy, Land Lease, Affiliation). Classifies status (VALID, EXPIRING_SOON, EXPIRED), displays timeline, supports renewal submission and review. | `/admin/validity` & `/institute/validity` (`AdminDocumentValidityPage.tsx`, `InstituteDocumentValidityPage.tsx`) | `GET /api/validity/summary`, `POST /api/validity/{id}/renew`, `/review` | `document_validities`, `validity_renewal_requests`, `audit_logs` | `backend/tests/test_stage3.py::test_document_validity_lifecycle` | **VERIFIED** |

---

### Section E: Alerts, Multi-Tier Escalation & Communications
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **E.1 Notification Rules Engine & Offsets** | Configurable alert rules for 11 statutory event types (Stage due soon/overdue, EVC pending/overdue, Undertakings due/overdue, Document expiring/expired). Specific offsets (e.g. T-30, 15, 7, 1; T-90, 60, 30, 7). | `/admin/alerts` & `/admin/rules?tab=alert_rules` (`AdminAlertsPage.tsx`, `AdminRulesPage.tsx`) | `GET /api/alerts/rules`, `PUT /api/alerts/rules/{id}`, `POST /api/alerts/scan` | `notification_rules`, `alert_events`, `email_outbox`, `notifications` | `backend/tests/test_stage4.py::test_alert_rules_and_scheduler_scan` | **VERIFIED** |
| **E.2 Multi-Tier Escalation Matrix (Levels 1 to 3)** | Escalation matrix mapping overdue thresholds to designated official roles (Level 1: Regional Officer at >=3d, Level 2: Bureau Officer at >=7d, Level 3: Bureau Officer/Admin at >=14d). Records who was notified and when; auto-closes on case resolution. | `/admin/alerts` (`AdminAlertsPage.tsx`) | `GET /api/alerts/escalations`, `GET /api/alerts/matrix`, `PUT /api/alerts/matrix/{id}` | `escalation_matrix`, `escalation_records` | `backend/tests/test_stage4.py::test_escalation_matrix_trigger` | **VERIFIED** |
| **E.3 Standardised Communications with Legal Disclaimer** | Pre-seeded statutory communication templates (Deficiency Notice, Clarification Request, EVC Intimation, Undertaking Reminder, Renewal Notice, Escalation Notice). Dispatches in-app notification, queues email, and generates PDF letter with mandatory disclaimer: *"This is a system reminder. Decisions remain with the competent authority."* | `/admin/rules?tab=communications` (`AdminRulesPage.tsx`) | `GET /api/workflow/communications/templates`, `POST /api/workflow/communications/generate`, `GET /api/workflow/communications/letter/{wf_id}/{code}` | `communication_templates`, `email_outbox`, `notifications`, `audit_logs` | `backend/tests/test_workflow.py::test_standardised_communications_and_disclaimer` | **VERIFIED** |
| **E.4 Demo Simulated Clock** | Interactive fast-forward demo clock allowing simulated time jumps to evaluate notifications and escalations on synthetic scenarios. | `/admin/alerts` (`AdminAlertsPage.tsx`) | `POST /api/alerts/demo-clock`, `DELETE /api/alerts/demo-clock` | Memory state / Scheduler reference time | `backend/tests/test_stage4.py::test_alert_rules_and_scheduler_scan` | **VERIFIED** |

---

### Section F: Integrations, Safeguards & Evaluation Benchmarks
| Clause & Ref | Statutory Requirement | Frontend Screen / UI Component | Backend API Route | Database Tables | Automated Test Proof | Status |
|---|---|---|---|---|---|---|
| **F.1 Legacy AICTE Systems Integration Layer** | Pluggable integration interface with SIMULATED adapters (`ApplicationFeedAdapter` importing JSON/CSV feeds, skipping duplicates; `InstituteRecordAdapter` fetching institute master record and historical 2021-2025 approval decisions). Admin UI section under Rules & Timelines with status, last sync, and file import modal. Read-only and role-guarded. | `/admin/rules?tab=integrations` (`AdminRulesPage.tsx`) | `GET /api/integrations/status`, `POST /api/integrations/sync-feed`, `POST /api/integrations/import-feed`, `GET /api/integrations/institutes/{id}/profile` | `system_settings`, `applications`, `application_workflows`, `audit_logs` | `backend/tests/test_final_stage.py::test_integrations_simulated_adapters` | **VERIFIED** |
| **F.2 Statutory Safeguards & Access Auditing** | Access logging for views of case files and documents (who, what, when), configurable retention settings for documents and audit logs, upload size and type limits, sanitized API errors (no raw stack traces), and login rate limiting. | `/admin/rules?tab=safeguards` & `/admin/audit-log` | `GET /api/workflow/settings/safeguards`, `PUT /api/workflow/settings/safeguards`, `GET /api/workflow/application/{id}` | `system_settings`, `audit_logs` | `backend/tests/test_final_stage.py::test_safeguards_and_access_logging` | **VERIFIED** |
| **F.3 Dynamic Statutory Configurability** | Verify SLA days, alert offsets, escalation days & roles, EVC deadlines, expiring-soon windows, communication templates, and category-to-template mappings are editable from UI and take effect dynamically without code changes. | `/admin/rules` (all tabs) | `PUT /api/workflow/templates/{tid}/stages/{sid}`, `PUT /api/alerts/rules/{id}`, `PUT /api/workflow/category-mappings`, `PUT /api/workflow/settings/safeguards` | `workflow_template_stages`, `notification_rules`, `system_settings` | `backend/tests/test_final_stage.py::test_configurability_without_code_changes` | **VERIFIED** |
| **F.4 In-App Statutory Coverage Console** | Dedicated `/admin/coverage` page displaying live database metrics and the interactive clause checklist with verification status badges. | `/admin/coverage` (`AdminCoveragePage.tsx`) | `GET /api/workflow/coverage` | All operational tables | `backend/tests/test_final_stage.py::test_coverage_endpoint` | **VERIFIED** |
| **F.5 AICTE System Evaluation & Benchmark Suite** | Automated statutory benchmark suite evaluating 8 procedural dimensions: (1) Workflow routing accuracy, (2) Deadline calculation accuracy, (3) Alert timeliness using demo clock, (4) Duplicate-alert rate, (5) Escalation correctness, (6) Audit completeness, (7) Return & resubmit cycle verification, (8) Late renewal escalation Level 3. Accompanied by mandatory disclaimer: *"Measured on synthetic scenarios."* | `/admin/evaluation` (`AdminEvaluationPage.tsx`) | `GET /api/evaluation/synthetic-scenarios`, `POST /api/evaluation/trigger-scenarios` | `alert_events`, `escalation_records`, `audit_logs`, `workflow_templates` | `backend/tests/test_final_stage.py::test_evaluation_8_synthetic_scenarios` | **VERIFIED** |

---

## 3. Operational Logins for Evaluation & Verification

All statutory roles are pre-seeded and active:
- **Central Administrator**: `admin@aicte.gov.in` / `Admin@123`
- **Regional Officer (Southern Region)**: `regional.south@aicte.gov.in` / `Officer@123`
- **Bureau Officer (Approval Bureau)**: `bureau.officer@aicte.gov.in` / `Officer@123`
- **Committee Member (EVC Expert)**: `committee.member@aicte.gov.in` / `Member@123`
- **Technical Institution**: `institute@test.edu` / `Institute@123`

---

## 4. Test Verification Summary
All automated test suites are executed via pytest:
```bash
backend\venv\Scripts\python -m pytest backend/tests/test_workflow.py backend/tests/test_stage3.py backend/tests/test_stage4.py backend/tests/test_final_stage.py
```
Total Test Suites: **4 files, 100% Passing**.
Frontend Production Build: **`npm run build --prefix frontend` succeeds with 0 TypeScript/Vite errors**.

