import os
import sys
from datetime import datetime, timezone, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.workflow import WorkflowTemplate, WorkflowTemplateStage, ApplicationWorkflow, WorkflowHistory, WorkflowStatus
from backend.app.models.evc import EvcRecord, EvcStatus
from backend.app.models.undertaking import Undertaking, UndertakingStatus
from backend.app.models.document_validity import DocumentValidityRecord, ValidityStatus
from backend.app.models.escalation import EscalationRecord
from backend.app.models.document import Document
from backend.app.models.alert_event import AlertEvent
from backend.app.security.password import hash_password
from backend.app.services.workflow_service import WorkflowService
from backend.app.services.scheduler_service import seed_rules_and_escalations_if_empty, run_notification_scan
from backend.app.services.audit_service import AuditService


def seed_workflow_demo_data(db: Session = None):
    should_close = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        should_close = True

    try:
        print("[DEMO SEED] Starting idempotent statutory workflow demo seeding...")
        now = datetime.now(timezone.utc)
        today = date.today()

        # -------------------------------------------------------------
        # 1. Statutory Workflow Templates Seeding
        # -------------------------------------------------------------
        WorkflowService.get_templates(db)

        # -------------------------------------------------------------
        # 2. Canonical Institutes Seeding & Duplicate Resolution
        # -------------------------------------------------------------
        # Step 2a: Ensure single canonical SKCET institute record
        skcet = db.query(Institute).filter(Institute.aicte_institute_id == "SKCET01").first()
        if not skcet:
            # Check if old INST-SKCET exists to rename
            old_skcet = db.query(Institute).filter(Institute.aicte_institute_id == "INST-SKCET").first()
            if old_skcet:
                old_skcet.aicte_institute_id = "SKCET01"
                old_skcet.name = "Sri Krishna College of Engineering and Technology"
                old_skcet.state = "Tamil Nadu"
                old_skcet.status = "ACTIVE"
                db.commit()
                db.refresh(old_skcet)
                skcet = old_skcet
            else:
                skcet = Institute(
                    aicte_institute_id="SKCET01",
                    name="Sri Krishna College of Engineering and Technology",
                    state="Tamil Nadu",
                    status="ACTIVE"
                )
                db.add(skcet)
                db.commit()
                db.refresh(skcet)

        # Step 2b: Migrate any orphaned INST-SKCET duplicate into SKCET01
        duplicate_skcet = db.query(Institute).filter(
            Institute.aicte_institute_id == "INST-SKCET",
            Institute.id != skcet.id
        ).first()
        if duplicate_skcet:
            dup_id = duplicate_skcet.id
            db.query(User).filter(User.institute_id == dup_id).update({"institute_id": skcet.id})
            db.query(Application).filter(Application.institute_id == dup_id).update({"institute_id": skcet.id})
            db.query(Undertaking).filter(Undertaking.institute_id == dup_id).update({"institute_id": skcet.id})
            db.query(DocumentValidityRecord).filter(DocumentValidityRecord.institute_id == dup_id).update({"institute_id": skcet.id})
            db.query(AlertEvent).filter(AlertEvent.institute_id == dup_id).update({"institute_id": skcet.id})
            db.query(Document).filter(Document.institute_id == dup_id).update({"institute_id": skcet.id})
            db.commit()
            db.delete(duplicate_skcet)
            db.commit()

        # Step 2c: Consolidate other institutes
        other_institutes_data = [
            {"code": "INST-BITS", "name": "Birla Institute of Technology and Science, Pilani", "state": "Rajasthan"},
            {"code": "INST-COEP", "name": "COEP Technological University Pune", "state": "Maharashtra"},
            {"code": "INST-RVCE", "name": "R.V. College of Engineering", "state": "Karnataka"},
            {"code": "DEL0101", "name": "Delhi Institute of Applied Technology", "state": "Delhi"},
            {"code": "INST-VJTI", "name": "Veermata Jijabai Technological Institute Mumbai", "state": "Maharashtra"},
        ]

        inst_map = {"SKCET01": skcet, "INST-SKCET": skcet}

        for idata in other_institutes_data:
            # Check duplicate INST-IITD -> DEL0101 migration
            if idata["code"] == "DEL0101":
                dup_delhi = db.query(Institute).filter(Institute.aicte_institute_id == "INST-IITD").first()
                target_delhi = db.query(Institute).filter(Institute.aicte_institute_id == "DEL0101").first()
                if dup_delhi and target_delhi and dup_delhi.id != target_delhi.id:
                    db.query(User).filter(User.institute_id == dup_delhi.id).update({"institute_id": target_delhi.id})
                    db.query(Application).filter(Application.institute_id == dup_delhi.id).update({"institute_id": target_delhi.id})
                    db.query(Undertaking).filter(Undertaking.institute_id == dup_delhi.id).update({"institute_id": target_delhi.id})
                    db.query(DocumentValidityRecord).filter(DocumentValidityRecord.institute_id == dup_delhi.id).update({"institute_id": target_delhi.id})
                    db.query(AlertEvent).filter(AlertEvent.institute_id == dup_delhi.id).update({"institute_id": target_delhi.id})
                    db.commit()
                    db.delete(dup_delhi)
                    db.commit()
                elif dup_delhi and not target_delhi:
                    dup_delhi.aicte_institute_id = "DEL0101"
                    db.commit()

            inst = db.query(Institute).filter(Institute.aicte_institute_id == idata["code"]).first()
            if not inst:
                inst = Institute(
                    aicte_institute_id=idata["code"],
                    name=idata["name"],
                    state=idata["state"],
                    status="ACTIVE"
                )
                db.add(inst)
                db.commit()
                db.refresh(inst)
            inst_map[idata["code"]] = inst

        # Legacy alias mapping
        inst_map["INST-IITD"] = inst_map["DEL0101"]

        # -------------------------------------------------------------
        # 3. Canonical Users Seeding (both SKCET logins resolve to SKCET01)
        # -------------------------------------------------------------
        demo_users = [
            {"email": "admin@aicte.gov.in", "role": UserRole.ADMIN, "region": "National", "inst": None, "pw": "password123"},
            {"email": "admin@aicte-india.org", "role": UserRole.ADMIN, "region": "National", "inst": None, "pw": "Admin@2026!"},
            {"email": "ro.south@aicte.gov.in", "role": UserRole.REGIONAL_OFFICER, "region": "South", "inst": None, "pw": "password123"},
            {"email": "ro.south@aicte-india.org", "role": UserRole.REGIONAL_OFFICER, "region": "Southern", "inst": None, "pw": "Officer@2026!"},
            {"email": "ro.north@aicte.gov.in", "role": UserRole.REGIONAL_OFFICER, "region": "North", "inst": None, "pw": "password123"},
            {"email": "ro.north@aicte-india.org", "role": UserRole.REGIONAL_OFFICER, "region": "Northern", "inst": None, "pw": "Officer@2026!"},
            {"email": "bureau@aicte.gov.in", "role": UserRole.BUREAU_OFFICER, "region": "National", "inst": None, "pw": "password123"},
            {"email": "bureau@aicte-india.org", "role": UserRole.BUREAU_OFFICER, "region": "National", "inst": None, "pw": "Bureau@2026!"},
            {"email": "evc.expert@aicte.gov.in", "role": UserRole.COMMITTEE_MEMBER, "region": "South", "inst": None, "pw": "password123"},
            {"email": "committee@aicte-india.org", "role": UserRole.COMMITTEE_MEMBER, "region": "National", "inst": None, "pw": "Member@2026!"},
            # SKCET users both resolving to single canonical SKCET institute
            {"email": "skcet@aicte.edu.in", "role": UserRole.INSTITUTE, "region": "South", "inst": skcet.id, "pw": "Institute@123"},
            {"email": "principal@skcet.ac.in", "role": UserRole.INSTITUTE, "region": "South", "inst": skcet.id, "pw": "password123"},
            # Other demo institute users
            {"email": "director@bitspilani.ac.in", "role": UserRole.INSTITUTE, "region": "North", "inst": inst_map["INST-BITS"].id, "pw": "password123"},
            {"email": "del0101@aicte.edu.in", "role": UserRole.INSTITUTE, "region": "North", "inst": inst_map["DEL0101"].id, "pw": "Institute@123"},
        ]

        user_map = {}
        for ud in demo_users:
            u = db.query(User).filter(User.email == ud["email"]).first()
            if not u:
                u = User(
                    email=ud["email"],
                    password_hash=hash_password(ud["pw"]),
                    role=ud["role"],
                    region=ud["region"],
                    institute_id=ud["inst"],
                    is_active=True
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            else:
                # Update institute_id if needed
                if ud["inst"] is not None and u.institute_id != ud["inst"]:
                    u.institute_id = ud["inst"]
                    db.commit()
            user_map[ud["email"]] = u

        # -------------------------------------------------------------
        # 4. Applications and Workflows Seeding (Linked to real institute IDs)
        # -------------------------------------------------------------
        templates = {t.code: t for t in db.query(WorkflowTemplate).all()}

        app_definitions = [
            # South Region - SKCET (linked to canonical SKCET01)
            ("APP-2026-S01", "SKCET01", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "IN_PROGRESS", 1, -4, "ro.south@aicte.gov.in"),  # Overdue
            ("APP-2026-S02", "SKCET01", "New Technical Institution", "SCRUTINY_EVC", "IN_PROGRESS", 2, 5, "ro.south@aicte.gov.in"),      # EVC stage
            ("APP-2026-S03", "INST-RVCE", "Increase in Intake", "SCRUTINY_EVC", "IN_PROGRESS", 1, 2, "ro.south@aicte.gov.in"),            # Due in 2 days
            ("APP-2026-S04", "SKCET01", "Appeal / SAC / SHC Review", "EVC_SAC_SHC", "IN_PROGRESS", 3, 10, "ro.south@aicte.gov.in"),
            ("APP-2026-S05", "INST-RVCE", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "RETURNED", 1, -2, "ro.south@aicte.gov.in"),
            ("APP-2026-S06", "SKCET01", "Increase in Intake", "SCRUTINY_EVC", "COMPLETED", 3, 0, "bureau@aicte.gov.in"),
            ("APP-2026-S07", "INST-RVCE", "Unannounced Surprise Verification", "ONLY_EVC", "IN_PROGRESS", 1, 5, "ro.south@aicte.gov.in"),

            # North Region
            ("APP-2026-N01", "INST-BITS", "New Technical Institution", "SCRUTINY_EVC", "IN_PROGRESS", 2, -3, "ro.north@aicte.gov.in"),    # Overdue EVC
            ("APP-2026-N02", "DEL0101", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "IN_PROGRESS", 1, 14, "ro.north@aicte.gov.in"),
            ("APP-2026-N03", "INST-BITS", "Increase in Intake", "SCRUTINY_EVC", "IN_PROGRESS", 1, 1, "ro.north@aicte.gov.in"),            # Due in 1 day
            ("APP-2026-N04", "DEL0101", "Appeal / SAC / SHC Review", "EVC_SAC_SHC", "IN_PROGRESS", 2, 8, "ro.north@aicte.gov.in"),
            ("APP-2026-N05", "INST-BITS", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "ON_HOLD", 1, -1, "ro.north@aicte.gov.in"),
            ("APP-2026-N06", "DEL0101", "Unannounced Surprise Verification", "ONLY_EVC", "COMPLETED", 2, 0, "bureau@aicte.gov.in"),
            ("APP-2026-N07", "INST-BITS", "Introduction of Supernumerary Seats", "ONLY_SCRUTINY", "IN_PROGRESS", 1, 11, "ro.north@aicte.gov.in"),

            # West Region
            ("APP-2026-W01", "INST-COEP", "New Technical Institution", "SCRUTINY_EVC", "IN_PROGRESS", 2, 12, "bureau@aicte.gov.in"),
            ("APP-2026-W02", "INST-VJTI", "Increase in Intake", "SCRUTINY_EVC", "IN_PROGRESS", 1, -8, "bureau@aicte.gov.in"),            # Overdue 8d
            ("APP-2026-W03", "INST-COEP", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "IN_PROGRESS", 2, 4, "bureau@aicte.gov.in"),
            ("APP-2026-W04", "INST-VJTI", "Appeal / SAC / SHC Review", "EVC_SAC_SHC", "IN_PROGRESS", 1, 15, "bureau@aicte.gov.in"),
            ("APP-2026-W05", "INST-COEP", "Unannounced Surprise Verification", "ONLY_EVC", "IN_PROGRESS", 1, -5, "bureau@aicte.gov.in"),
            ("APP-2026-W06", "INST-VJTI", "Extension of Approval (EoA)", "ONLY_SCRUTINY", "COMPLETED", 2, 0, "bureau@aicte.gov.in"),
        ]

        workflows_map = {}
        for app_id, inst_code, category, tmpl_code, status_str, seq, offset_due_days, officer_email in app_definitions:
            inst = inst_map[inst_code]
            tmpl = templates[tmpl_code]
            officer = user_map.get(officer_email)

            app = db.query(Application).filter(Application.application_id == app_id).first()
            if not app:
                app = Application(
                    application_id=app_id,
                    institute_id=inst.id,
                    category=category,
                    academic_year="2026-2027",
                    programme="Engineering & Technology",
                    status="SUBMITTED" if status_str != "COMPLETED" else "APPROVED",
                    created_at=now - timedelta(days=20)
                )
                db.add(app)
                db.commit()
                db.refresh(app)
            else:
                # Ensure correct institute_id
                if app.institute_id != inst.id:
                    app.institute_id = inst.id
                    db.commit()

            wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == app.id).first()
            stages = sorted(tmpl.stages, key=lambda s: s.sequence)
            current_stage = stages[min(seq - 1, len(stages) - 1)]
            due_dt = now + timedelta(days=offset_due_days) if offset_due_days != 0 else now - timedelta(days=5)

            if not wf:
                wf = ApplicationWorkflow(
                    application_id=app.id,
                    template_id=tmpl.id,
                    current_stage_id=current_stage.id,
                    current_stage_sequence=seq,
                    current_stage_name=current_stage.stage_name,
                    assigned_officer_id=officer.id if officer else None,
                    assigned_officer_name=officer.email if officer else None,
                    region=inst.state in ["Tamil Nadu", "Karnataka"] and "South" or (inst.state in ["Maharashtra"] and "West" or "North"),
                    stage_start=now - timedelta(days=10),
                    due_date=due_dt,
                    status=status_str,
                    created_at=now - timedelta(days=15)
                )
                if status_str == "RETURNED":
                    wf.return_reason = "Deficiency noted: Certified land registry deed endorsement lacks survey number seal. Please upload clarification and endorsed registry documents."
                if status_str == "COMPLETED":
                    wf.final_decision = "APPROVED"
                    wf.final_decision_notes = "Compliant with AICTE Approval Process Handbook (APH) 2026-27."
                    wf.final_decision_by = "bureau@aicte.gov.in (BUREAU_OFFICER)"
                    wf.final_decision_at = now - timedelta(days=1)
                db.add(wf)
                db.commit()
                db.refresh(wf)
            else:
                # Update due date and status
                wf.status = status_str
                wf.due_date = due_dt
                db.commit()

            workflows_map[app_id] = wf

        # -------------------------------------------------------------
        # 5. EVC Records Seeding (Linked to real institute IDs)
        # -------------------------------------------------------------
        evc_definitions = [
            {
                "case_id": "APP-2026-S02",
                "proposed": now + timedelta(days=5),
                "confirmed": now + timedelta(days=5),
                "status": EvcStatus.SCHEDULED,
                "sched_dead": now + timedelta(days=2),
                "members": [{"name": "Prof. S. Ranganathan", "role": "Chairman", "email": "evc.expert@aicte.gov.in"}]
            },
            {
                "case_id": "APP-2026-N01",
                "proposed": None,
                "confirmed": None,
                "status": EvcStatus.PENDING_SCHEDULING,
                "sched_dead": now - timedelta(days=4),  # Scheduling Overdue
                "members": []
            },
            {
                "case_id": "APP-2026-W01",
                "proposed": now + timedelta(days=12),
                "confirmed": None,
                "status": EvcStatus.PENDING_SCHEDULING,
                "sched_dead": now + timedelta(days=7),
                "members": []
            },
            {
                "case_id": "APP-2026-S07",
                "proposed": now - timedelta(days=3),
                "confirmed": now - timedelta(days=3),
                "status": EvcStatus.COMPLETED,
                "sched_dead": now - timedelta(days=10),
                "members": [{"name": "Prof. S. Ranganathan", "role": "Expert"}],
                "report_pending": True
            }
        ]

        for ed in evc_definitions:
            app_obj = db.query(Application).filter(Application.application_id == ed["case_id"]).first()
            if not app_obj:
                continue
            existing_evc = db.query(EvcRecord).filter(EvcRecord.application_id == app_obj.id).first()
            if not existing_evc:
                wf = workflows_map.get(ed["case_id"])
                evc = EvcRecord(
                    application_id=app_obj.id,
                    workflow_id=wf.id if wf else None,
                    status=ed["status"],
                    proposed_date=ed["proposed"],
                    confirmed_date=ed["confirmed"],
                    scheduling_deadline=ed["sched_dead"],
                    completion_deadline=ed["sched_dead"] + timedelta(days=15),
                    committee_members=ed["members"],
                    remarks="Inspection panel constitution verified by council"
                )
                db.add(evc)
                db.commit()
            else:
                existing_evc.status = ed["status"]
                existing_evc.confirmed_date = ed["confirmed"]
                existing_evc.proposed_date = ed["proposed"]
                db.commit()

        # -------------------------------------------------------------
        # 6. Statutory Undertakings Seeding (At least 4 for SKCET01 in different states)
        # -------------------------------------------------------------
        ut_definitions = [
            # SKCET01: 4 undertakings in active, due soon, overdue, submitted
            ("APP-2026-S04", "SKCET01", "accreditation", "Submission of updated NBA compliance report and peer team review schedule", now + timedelta(days=25), UndertakingStatus.ACTIVE, None),
            ("APP-2026-S01", "SKCET01", "infrastructure", "Fire and life safety equipment installation and NOC compliance audit", now + timedelta(days=3), UndertakingStatus.ACTIVE, None),  # Due in 3 days (due soon)
            ("APP-2026-S01", "SKCET01", "lease", "Registered 30-year lease deed endorsement for sports complex and amenities", now - timedelta(days=5), UndertakingStatus.OVERDUE, None),  # Overdue 5d
            ("APP-2026-S02", "SKCET01", "faculty", "Appointment of cadre-ratio compliant professors and assistant professors", now + timedelta(days=10), UndertakingStatus.SUBMITTED, "Faculty_Cadre_Appointment_Orders_SKCET.pdf"),

            # Other institutes
            ("APP-2026-N01", "INST-BITS", "faculty", "Recruitment of cadre-ratio compliant Associate Professors", now - timedelta(days=8), UndertakingStatus.OVERDUE, None),
            ("APP-2026-W02", "INST-VJTI", "lease", "Registration of 30-year registered lease deed", now - timedelta(days=10), UndertakingStatus.OVERDUE, None),
            ("APP-2026-S03", "INST-RVCE", "other", "Barrier-free environment ramp and lift compliance audit", now + timedelta(days=15), UndertakingStatus.ACTIVE, None),
            ("APP-2026-N03", "INST-BITS", "infrastructure", "High-voltage electrical inspectorate clearance", now + timedelta(days=30), UndertakingStatus.ACTIVE, None),
        ]

        for app_id, inst_code, cat, cond, due_dt, u_status, evidence_fn in ut_definitions:
            inst = inst_map[inst_code]
            app_obj = db.query(Application).filter(Application.application_id == app_id).first()
            if not app_obj:
                continue
            existing_ut = db.query(Undertaking).filter(
                Undertaking.application_id == app_obj.id,
                Undertaking.condition == cond
            ).first()
            if not existing_ut:
                ut = Undertaking(
                    institute_id=inst.id,
                    application_id=app_obj.id,
                    category=cat,
                    condition=cond,
                    due_date=due_dt,
                    status=u_status,
                    evidence_original_filename=evidence_fn,
                    created_at=now - timedelta(days=15)
                )
                db.add(ut)
                db.commit()
                db.refresh(ut)
            else:
                existing_ut.institute_id = inst.id
                existing_ut.status = u_status
                existing_ut.due_date = due_dt
                if evidence_fn:
                    existing_ut.evidence_original_filename = evidence_fn
                db.commit()

        # -------------------------------------------------------------
        # 7. Document Validity Records Seeding
        # (At least 12 records across 3 institutes/regions, at least 5 for SKCET01 across all 5 statuses)
        # -------------------------------------------------------------
        # Statuses: Valid, Expiring soon (under 30 days), Expired, Renewal submitted, Renewed
        doc_definitions = [
            # 1. SKCET01 (South) - Registered Lease Deed (Expiring soon: 22 days left)
            {
                "inst_code": "SKCET01",
                "doc_type": "Land / Registered Lease Deed",
                "name": "Land / Registered Lease Deed",
                "cert_no": "TN-CBE-LEASE-2016-0891",
                "authority": "Sub-Registrar Office, Kuniamuthur",
                "expiry": today + timedelta(days=22),
                "status": ValidityStatus.EXPIRING_SOON,
                "is_lease": True,
                "lessor": "Coimbatore Educational and Industrial Trust",
                "lessee": "Sri Krishna College of Engineering and Technology",
                "lease_start": today - timedelta(days=3650),
                "lease_end": today + timedelta(days=22),
                "address": "SF No. 124/1A, Sugunapuram, Kuniamuthur, Coimbatore, Tamil Nadu 641008",
                "renewal_submitted": None
            },
            # 2. SKCET01 (South) - Fire Safety NOC Certificate (Expired: 15 days ago)
            {
                "inst_code": "SKCET01",
                "doc_type": "Fire Safety NOC Certificate",
                "name": "Fire Safety Certificate / NOC",
                "cert_no": "TN-FRS-CBE-2025-4421",
                "authority": "Tamil Nadu Fire and Rescue Services Department",
                "expiry": today - timedelta(days=15),
                "status": ValidityStatus.EXPIRED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },
            # 3. SKCET01 (South) - Building Occupancy / Completion Certificate (Renewal submitted)
            {
                "inst_code": "SKCET01",
                "doc_type": "Building Occupancy / Completion Certificate",
                "name": "Building Occupancy / Completion Certificate",
                "cert_no": "DTCP-OCC-2020-0082",
                "authority": "Directorate of Town and Country Planning (DTCP), Tamil Nadu",
                "expiry": today + timedelta(days=18),
                "status": ValidityStatus.RENEWAL_SUBMITTED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": now - timedelta(days=3)
            },
            # 4. SKCET01 (South) - National Board of Accreditation (Valid: 365 days left)
            {
                "inst_code": "SKCET01",
                "doc_type": "National Board of Accreditation (NBA)",
                "name": "National Board of Accreditation (NBA Tier-1)",
                "cert_no": "NBA-ENGG-TN-2023-718",
                "authority": "National Board of Accreditation, New Delhi",
                "expiry": today + timedelta(days=365),
                "status": ValidityStatus.VALID,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },
            # 5. SKCET01 (South) - Consent to Operate / Pollution Control (Renewed)
            {
                "inst_code": "SKCET01",
                "doc_type": "Pollution Control Consent",
                "name": "Consent to Operate (Pollution Control)",
                "cert_no": "TNPCB-CTO-2026-9901",
                "authority": "Tamil Nadu Pollution Control Board (TNPCB)",
                "expiry": today + timedelta(days=730),
                "status": ValidityStatus.RENEWED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },

            # 6. BITS Pilani (North) - Registered Campus Land Lease (Valid)
            {
                "inst_code": "INST-BITS",
                "doc_type": "Registered Long-term Land Lease",
                "name": "Registered Long-term Campus Land Lease",
                "cert_no": "RAJ-PIL-LEASE-1995-110",
                "authority": "Revenue Authority, Jhunjhunu",
                "expiry": today + timedelta(days=90),
                "status": ValidityStatus.VALID,
                "is_lease": True,
                "lessor": "Pilani Education Trust",
                "lessee": "Birla Institute of Technology and Science, Pilani",
                "lease_start": today - timedelta(days=7300),
                "lease_end": today + timedelta(days=90),
                "address": "Vidya Vihar Campus, Pilani, Rajasthan 333031",
                "renewal_submitted": None
            },
            # 7. BITS Pilani (North) - Building Occupancy Certificate (Expired)
            {
                "inst_code": "INST-BITS",
                "doc_type": "Building Occupancy / Completion Certificate",
                "name": "Building Occupancy Certificate",
                "cert_no": "RAJ-BOC-2021-041",
                "authority": "Municipal Council, Pilani",
                "expiry": today - timedelta(days=5),
                "status": ValidityStatus.EXPIRED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },
            # 8. BITS Pilani (North) - Fire Safety NOC (Expiring soon)
            {
                "inst_code": "INST-BITS",
                "doc_type": "Fire Safety NOC Certificate",
                "name": "Fire Safety Clearance Certificate",
                "cert_no": "RAJ-FIRE-2025-103",
                "authority": "Rajasthan Fire Services",
                "expiry": today + timedelta(days=14),
                "status": ValidityStatus.EXPIRING_SOON,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },

            # 9. COEP Pune (West) - Environmental Clearance Certificate (Valid)
            {
                "inst_code": "INST-COEP",
                "doc_type": "Environmental Clearance Certificate",
                "name": "Environmental Clearance Certificate",
                "cert_no": "MAH-ENV-PUN-2024-88",
                "authority": "Maharashtra State Environment Impact Assessment Authority",
                "expiry": today + timedelta(days=120),
                "status": ValidityStatus.VALID,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },
            # 10. COEP Pune (West) - Municipal Corporation Lease (Renewal submitted)
            {
                "inst_code": "INST-COEP",
                "doc_type": "Municipal Corporation Lease Renewal",
                "name": "Municipal Corporation Campus Lease Agreement",
                "cert_no": "PMC-LEASE-1998-504",
                "authority": "Pune Municipal Corporation",
                "expiry": today + timedelta(days=20),
                "status": ValidityStatus.RENEWAL_SUBMITTED,
                "is_lease": True,
                "lessor": "Pune Municipal Corporation",
                "lessee": "COEP Technological University",
                "lease_start": today - timedelta(days=5475),
                "lease_end": today + timedelta(days=20),
                "address": "Wellesley Road, Shivajinagar, Pune, Maharashtra 411005",
                "renewal_submitted": now - timedelta(days=5)
            },

            # 11. VJTI Mumbai (West) - Fire Safety Inspection NOC (Expired)
            {
                "inst_code": "INST-VJTI",
                "doc_type": "Fire Safety NOC Certificate",
                "name": "Fire Safety Inspection NOC",
                "cert_no": "MCGM-FIRE-2025-781",
                "authority": "Brihanmumbai Municipal Corporation Fire Brigade",
                "expiry": today - timedelta(days=20),
                "status": ValidityStatus.EXPIRED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },
            # 12. VJTI Mumbai (West) - Pollution Control Consent (Renewed)
            {
                "inst_code": "INST-VJTI",
                "doc_type": "Pollution Control Consent",
                "name": "Maharashtra Pollution Control Board Consent",
                "cert_no": "MPCB-CTO-2026-302",
                "authority": "Maharashtra Pollution Control Board (MPCB)",
                "expiry": today + timedelta(days=500),
                "status": ValidityStatus.RENEWED,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },

            # 13. RVCE Bangalore (South) - National Board of Accreditation (Valid)
            {
                "inst_code": "INST-RVCE",
                "doc_type": "National Board of Accreditation (NBA)",
                "name": "National Board of Accreditation (NBA Tier-1)",
                "cert_no": "NBA-ENGG-KAR-2024-512",
                "authority": "National Board of Accreditation, New Delhi",
                "expiry": today + timedelta(days=240),
                "status": ValidityStatus.VALID,
                "is_lease": False,
                "lessor": None, "lessee": None, "lease_start": None, "lease_end": None, "address": None,
                "renewal_submitted": None
            },

            # 14. Delhi Institute (North) - DDA Land Lease Deed (Valid)
            {
                "inst_code": "DEL0101",
                "doc_type": "Registered Campus Lease Agreement",
                "name": "DDA Institutional Land Lease Deed",
                "cert_no": "DDA-INST-2002-991",
                "authority": "Delhi Development Authority (DDA)",
                "expiry": today + timedelta(days=300),
                "status": ValidityStatus.VALID,
                "is_lease": True,
                "lessor": "Delhi Development Authority",
                "lessee": "Delhi Institute of Applied Technology",
                "lease_start": today - timedelta(days=5000),
                "lease_end": today + timedelta(days=300),
                "address": "Sector 9, Institutional Area, Dwarka, New Delhi 110077",
                "renewal_submitted": None
            },
        ]

        for dd in doc_definitions:
            inst = inst_map[dd["inst_code"]]
            existing_doc = db.query(DocumentValidityRecord).filter(
                DocumentValidityRecord.institute_id == inst.id,
                DocumentValidityRecord.document_type_code == dd["doc_type"]
            ).first()

            days_left = (dd["expiry"] - today).days

            if not existing_doc:
                d_rec = DocumentValidityRecord(
                    institute_id=inst.id,
                    document_type_code=dd["doc_type"],
                    document_name=dd["name"],
                    certificate_number=dd["cert_no"],
                    issuing_authority=dd["authority"],
                    expiry_date=dd["expiry"],
                    issue_date=today - timedelta(days=365),
                    days_left=days_left,
                    status=dd["status"],
                    expiring_soon_window_days=30,
                    is_lease=dd["is_lease"],
                    lessor=dd["lessor"],
                    lessee=dd["lessee"],
                    lease_start=dd["lease_start"],
                    lease_end=dd["lease_end"],
                    property_address=dd["address"],
                    renewal_submitted_at=dd["renewal_submitted"],
                    created_at=now - timedelta(days=30),
                    updated_at=now
                )
                db.add(d_rec)
                db.commit()
            else:
                existing_doc.institute_id = inst.id
                existing_doc.document_name = dd["name"]
                existing_doc.certificate_number = dd["cert_no"]
                existing_doc.issuing_authority = dd["authority"]
                existing_doc.expiry_date = dd["expiry"]
                existing_doc.days_left = days_left
                existing_doc.status = dd["status"]
                existing_doc.is_lease = dd["is_lease"]
                existing_doc.lessor = dd["lessor"]
                existing_doc.lessee = dd["lessee"]
                existing_doc.lease_start = dd["lease_start"]
                existing_doc.lease_end = dd["lease_end"]
                existing_doc.property_address = dd["address"]
                existing_doc.renewal_submitted_at = dd["renewal_submitted"]
                existing_doc.updated_at = now
                db.commit()

        # -------------------------------------------------------------
        # 8. Seed Default Alert Rules & Escalation Matrix
        # -------------------------------------------------------------
        seed_rules_and_escalations_if_empty(db)

        # -------------------------------------------------------------
        # 9. Execute Scanner Pass to Populate Demo Alerts for SKCET01
        # -------------------------------------------------------------
        scan_log = run_notification_scan(db)
        print(f"[DEMO SEED] Scan completed: created {scan_log.alerts_created} alerts, {scan_log.escalations_triggered} escalations.")

        print("[DEMO SEED] Demo seeding successfully completed!")
        print("\n================ DEMO USER CREDENTIALS ================")
        print("Role                     Email                        Password")
        print("----------------------------------------------------------------")
        print("ADMIN                    admin@aicte.gov.in           password123")
        print("ADMIN                    admin@aicte-india.org        Admin@2026!")
        print("REGIONAL_OFFICER (South) ro.south@aicte.gov.in        password123")
        print("REGIONAL_OFFICER (North) ro.north@aicte.gov.in        password123")
        print("BUREAU_OFFICER           bureau@aicte.gov.in          password123")
        print("COMMITTEE_MEMBER         evc.expert@aicte.gov.in      password123")
        print("INSTITUTE (SKCET01)      skcet@aicte.edu.in           Institute@123")
        print("INSTITUTE (SKCET01)      principal@skcet.ac.in        password123")
        print("INSTITUTE (BITS)         director@bitspilani.ac.in    password123")
        print("INSTITUTE (Delhi)        del0101@aicte.edu.in         Institute@123")
        print("========================================================\n")

    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_workflow_demo_data()
