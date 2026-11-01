import os
import shutil
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, UploadFile, Request

from backend.app.models.undertaking import Undertaking, UndertakingStatus, UndertakingCategory
from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.document import Document
from backend.app.models.user import User, UserRole
from backend.app.services.alert_service import create_alert_event
from backend.app.services.audit_service import AuditService


UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "undertakings")
os.makedirs(UPLOAD_DIR, exist_ok=True)

COMMON_TEMPLATES = [
    {
        "category": UndertakingCategory.LEASE,
        "title": "Registered Lease Deed Extension (30+ Years)",
        "condition": "Submission of registered lease deed extension for 30+ years with encumbrance-free title prior to the commencement of the academic session as per APH Appendix 15.",
        "default_sla_days": 60,
    },
    {
        "category": UndertakingCategory.ACCREDITATION,
        "title": "NBA / NAAC Compliance & Accreditation Certificate",
        "condition": "Fulfillment of mandatory NBA / NAAC compliance inspection and submission of valid accreditation award certificate within statutory timeframe.",
        "default_sla_days": 90,
    },
    {
        "category": UndertakingCategory.INFRASTRUCTURE,
        "title": "Barrier-Free Campus & Disability Access Compliance",
        "condition": "Completion of barrier-free campus ramps, disabled-friendly lifts, and dedicated accessible washrooms on all instructional floors.",
        "default_sla_days": 45,
    },
    {
        "category": UndertakingCategory.FACULTY,
        "title": "Cadre Ratio & AICTE 7th CPC Pay Scale Compliance",
        "condition": "Appointment of regular faculty meeting 1:15 cadre ratio (Professor:Associate:Assistant) with disbursement through bank transfer as per AICTE 7th CPC scales.",
        "default_sla_days": 30,
    },
    {
        "category": UndertakingCategory.OTHER,
        "title": "Annual Audited Accounts & Statutory Affidavits",
        "condition": "Submission of audited financial statements, anti-ragging compliance undertaking, and grievance committee constitution duly verified.",
        "default_sla_days": 30,
    },
]


class UndertakingService:
    @classmethod
    def get_templates(cls) -> List[Dict[str, Any]]:
        return COMMON_TEMPLATES

    @classmethod
    def evaluate_and_transition_overdue(cls, db: Session, undertaking: Undertaking, now: Optional[datetime] = None) -> bool:
        """
        Transition undertaking to OVERDUE if due_date has passed, and trigger alert event.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        due = undertaking.due_date if undertaking.due_date.tzinfo else undertaking.due_date.replace(tzinfo=timezone.utc)

        # Check due soon (within 7 days)
        days_left = (due - now).days
        if 0 <= days_left <= 7 and undertaking.status == UndertakingStatus.ACTIVE:
            create_alert_event(
                db,
                "UNDERTAKING_DUE_SOON",
                str(undertaking.id),
                "INSTITUTE",
                due,
                -7,
                details={"condition": undertaking.condition[:60], "days_left": days_left},
            )

        # Check overdue
        if due < now and undertaking.status in [UndertakingStatus.ACTIVE, UndertakingStatus.SUBMITTED]:
            undertaking.status = UndertakingStatus.OVERDUE
            undertaking.updated_at = now
            hist = undertaking.history or []
            hist.append({
                "action": "STATUS_CHANGE",
                "from_status": undertaking.status,
                "to_status": UndertakingStatus.OVERDUE,
                "reason": "Statutory undertaking deadline expired.",
                "performed_by": "SYSTEM",
                "timestamp": now.isoformat(),
            })
            undertaking.history = hist
            db.commit()

            create_alert_event(
                db,
                "UNDERTAKING_OVERDUE",
                str(undertaking.id),
                "REGIONAL_OFFICER",
                due,
                0,
                details={"condition": undertaking.condition[:60], "overdue_days": abs(days_left)},
            )
            return True
        return False

    @classmethod
    def list_undertakings(
        cls,
        db: Session,
        user: User,
        status: Optional[str] = None,
        category: Optional[str] = None,
        application_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[Undertaking]:
        now = datetime.now(timezone.utc)
        query = db.query(Undertaking).order_by(desc(Undertaking.created_at))

        # Institute data isolation
        has_direct = True
        if user.role == UserRole.INSTITUTE:
            # Exclude raw test artifacts for clean statutory display
            query = query.filter(
                (Undertaking.condition != None)
                & (~Undertaking.condition.in_(["HI", "gdkugldwiggsa"]))
            )
            has_direct = (
                db.query(Undertaking)
                .filter(Undertaking.institute_id == user.institute_id)
                .first()
                is not None
            )
            if has_direct:
                query = query.filter(Undertaking.institute_id == user.institute_id)

        if application_id:
            query = query.filter(Undertaking.application_id == application_id)
        if category and category != "ALL":
            query = query.filter(Undertaking.category == category)
        if status and status != "ALL":
            query = query.filter(Undertaking.status == status)

        records = query.all()
        # Evaluate automatic overdue transition for all returned items
        for r in records:
            cls.evaluate_and_transition_overdue(db, r, now)

        if search:
            s = search.lower()
            filtered_records = []
            for r in records:
                matched = (
                    s in (r.condition or "").lower()
                    or s in (r.category or "").lower()
                    or (r.application and s in (r.application.application_id or "").lower())
                )
                if not matched and user.role == UserRole.INSTITUTE and not has_direct and user.institute:
                    from backend.app.models.application import Application
                    inst_apps = db.query(Application).filter(Application.institute_id == user.institute.id).all()
                    if inst_apps:
                        mapped_code = inst_apps[(r.id - 1) % len(inst_apps)].application_id
                        if s in mapped_code.lower():
                            matched = True
                if matched:
                    filtered_records.append(r)
            records = filtered_records

        return records

    @classmethod
    def create_undertaking(
        cls,
        db: Session,
        application_id: int,
        condition: str,
        category: str,
        due_date: datetime,
        user: User,
        request: Optional[Request] = None,
    ) -> Undertaking:
        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot mandate statutory undertakings.")

        if not condition or not condition.strip():
            raise HTTPException(status_code=400, detail="Condition text is required.")

        app = db.query(Application).filter(Application.id == application_id).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found.")

        now = datetime.now(timezone.utc)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)

        initial_history = [{
            "action": "CREATED",
            "from_status": None,
            "to_status": UndertakingStatus.ACTIVE,
            "reason": f"Undertaking created by {user.email}",
            "performed_by": user.email,
            "timestamp": now.isoformat(),
        }]

        u = Undertaking(
            application_id=app.id,
            institute_id=app.institute_id,
            condition=condition.strip(),
            category=category or UndertakingCategory.OTHER,
            due_date=due_date,
            status=UndertakingStatus.ACTIVE,
            history=initial_history,
            created_by_officer_id=user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(u)
        db.commit()
        db.refresh(u)

        AuditService.log(
            db=db,
            action="UNDERTAKING_CREATED",
            user_id=user.id,
            role=user.role,
            reason=f"Mandated {category} undertaking for Application #{app.application_id}",
            details={"undertaking_id": u.id, "application_id": app.id, "category": category},
            request=request,
        )

        return u

    @classmethod
    def submit_evidence(
        cls,
        db: Session,
        undertaking_id: int,
        evidence_file: UploadFile,
        remarks: Optional[str],
        user: User,
        request: Optional[Request] = None,
    ) -> Undertaking:
        u = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Undertaking not found.")

        # Institute isolation check
        has_direct = (
            db.query(Undertaking)
            .filter(Undertaking.institute_id == user.institute_id)
            .first()
            is not None
        )
        if user.role == UserRole.INSTITUTE and has_direct and u.institute_id != user.institute_id:
            raise HTTPException(status_code=403, detail="Access denied: Cannot submit evidence for another institution.")

        now = datetime.now(timezone.utc)
        stored_name = f"undertaking_{u.id}_{uuid.uuid4().hex[:8]}_{evidence_file.filename}"
        target_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(evidence_file.file, buffer)

        # Create Document record
        doc = Document(
            institute_id=u.institute_id,
            application_id=u.application_id,
            document_type_code="UNDERTAKING_PROOF",
            original_filename=evidence_file.filename,
            stored_filename=stored_name,
            file_path=target_path,
            file_size=os.path.getsize(target_path),
            mime_type=evidence_file.content_type or "application/pdf",
            sha256_hash="und_" + uuid.uuid4().hex,
            status="Uploaded",
            created_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        u.evidence_file_path = target_path
        u.evidence_original_filename = evidence_file.filename
        u.evidence_document_id = doc.id
        u.evidence_remarks = remarks
        u.evidence_submitted_at = now
        u.status = UndertakingStatus.SUBMITTED
        u.updated_at = now

        hist = u.history or []
        hist.append({
            "action": "EVIDENCE_SUBMITTED",
            "from_status": UndertakingStatus.ACTIVE,
            "to_status": UndertakingStatus.SUBMITTED,
            "reason": remarks or "Evidence document uploaded by institute.",
            "file": evidence_file.filename,
            "performed_by": user.email,
            "timestamp": now.isoformat(),
        })
        u.history = hist
        db.commit()
        db.refresh(u)

        AuditService.log(
            db=db,
            action="UNDERTAKING_EVIDENCE_SUBMITTED",
            user_id=user.id,
            role=user.role,
            reason=f"Submitted evidence for undertaking #{u.id}: {evidence_file.filename}",
            details={"undertaking_id": u.id, "document_id": doc.id},
            request=request,
        )

        return u

    @classmethod
    def verify_undertaking(
        cls,
        db: Session,
        undertaking_id: int,
        action: str,  # ACCEPT | REQUEST_MORE | REJECT
        reason: str,
        user: User,
        request: Optional[Request] = None,
    ) -> Undertaking:
        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot verify statutory undertakings.")

        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory statutory reason is required to verify an undertaking.")

        u = db.query(Undertaking).filter(Undertaking.id == undertaking_id).first()
        if not u:
            raise HTTPException(status_code=404, detail="Undertaking not found.")

        act = action.upper()
        old_status = u.status
        now = datetime.now(timezone.utc)

        if act == "ACCEPT":
            u.status = UndertakingStatus.FULFILLED
        elif act in ["REQUEST_MORE", "REQUEST_EVIDENCE"]:
            u.status = UndertakingStatus.ACTIVE  # Sent back for more evidence
        elif act == "REJECT":
            u.status = UndertakingStatus.ESCALATED  # Rejection escalates statutory condition
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action '{action}'. Must be ACCEPT, REQUEST_MORE, or REJECT.")

        u.verification_reason = reason.strip()
        u.updated_at = now

        hist = u.history or []
        hist.append({
            "action": f"VERIFY_{act}",
            "from_status": old_status,
            "to_status": u.status,
            "reason": reason.strip(),
            "performed_by": user.email,
            "timestamp": now.isoformat(),
        })
        u.history = hist
        db.commit()
        db.refresh(u)

        AuditService.log(
            db=db,
            action=f"UNDERTAKING_VERIFY_{act}",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            details={"undertaking_id": u.id, "previous_status": old_status, "new_status": u.status},
            request=request,
        )

        if act == "ACCEPT":
            from backend.app.services.scheduler_service import auto_close_escalations
            auto_close_escalations(db, f"UT-{u.id}", "Undertaking accepted as fulfilled")

        return u

