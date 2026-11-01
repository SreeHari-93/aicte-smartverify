import os
import shutil
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, UploadFile, Request

from backend.app.models.evc import EvcRecord, EvcStatus
from backend.app.models.workflow import ApplicationWorkflow
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.user import User, UserRole
from backend.app.services.alert_service import create_alert_event
from backend.app.services.audit_service import AuditService
from backend.app.services.workflow_service import WorkflowService


UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "evc_reports")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class EvcService:
    @classmethod
    def ensure_evc_record(cls, db: Session, workflow: ApplicationWorkflow) -> EvcRecord:
        """
        When a workflow reaches the EVC stage, automatically create an EVC record
        and place it in the EVC queue. Shorter deadlines apply for new institutions.
        """
        existing = db.query(EvcRecord).filter(EvcRecord.workflow_id == workflow.id).first()
        if existing:
            return existing

        app = workflow.application
        cat_upper = (app.category or "").upper() if app else ""
        is_new = "NEW" in cat_upper or "SETTING UP" in cat_upper or "START" in cat_upper

        now = datetime.now(timezone.utc)
        # Configurable deadlines from database settings (shorter for new institutions)
        sched_days = 5 if is_new else 10
        comp_days = 10 if is_new else 20

        from backend.app.models.system_setting import SystemSetting
        sched_key = "evc_scheduling_days_new" if is_new else "evc_scheduling_days_standard"
        comp_key = "evc_completion_days_new" if is_new else "evc_completion_days_standard"
        s_sched = db.query(SystemSetting).filter(SystemSetting.key == sched_key).first()
        if s_sched and s_sched.value:
            try:
                sched_days = int(s_sched.value)
            except ValueError:
                pass
        s_comp = db.query(SystemSetting).filter(SystemSetting.key == comp_key).first()
        if s_comp and s_comp.value:
            try:
                comp_days = int(s_comp.value)
            except ValueError:
                pass

        scheduling_deadline = now + timedelta(days=sched_days)
        completion_deadline = now + timedelta(days=comp_days)

        evc = EvcRecord(
            application_id=workflow.application_id,
            workflow_id=workflow.id,
            is_new_institution=is_new,
            committee_members=[],
            status=EvcStatus.PENDING_SCHEDULING,
            scheduling_deadline=scheduling_deadline,
            completion_deadline=completion_deadline,
            created_at=now,
            updated_at=now,
        )
        db.add(evc)
        db.commit()
        db.refresh(evc)

        # Trigger alert for scheduling pending
        create_alert_event(
            db,
            "EVC_PENDING_SCHEDULING",
            str(app.application_id if app else workflow.application_id),
            "REGIONAL_OFFICER",
            scheduling_deadline,
            0,
            details={"is_new_institution": is_new, "sla_days": sched_days},
        )

        return evc

    @classmethod
    def check_member_conflict(
        cls,
        db: Session,
        evc_id: Optional[int],
        visit_date: datetime,
        committee_members: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Check if any selected committee member already has an EVC visit scheduled on this date.
        """
        target_day = visit_date.date() if isinstance(visit_date, datetime) else visit_date

        query = db.query(EvcRecord).filter(
            EvcRecord.status.in_([EvcStatus.SCHEDULED, EvcStatus.RESCHEDULED]),
            EvcRecord.confirmed_date.isnot(None),
        )
        if evc_id:
            query = query.filter(EvcRecord.id != evc_id)

        scheduled_visits = query.all()

        for visit in scheduled_visits:
            if not visit.confirmed_date:
                continue
            visit_day = visit.confirmed_date.date()
            if visit_day == target_day:
                existing_members = visit.committee_members or []
                for em in existing_members:
                    em_email = (em.get("email") or "").strip().lower()
                    em_name = (em.get("name") or "").strip().lower()
                    for nm in committee_members:
                        nm_email = (nm.get("email") or "").strip().lower()
                        nm_name = (nm.get("name") or "").strip().lower()
                        if (nm_email and nm_email == em_email) or (nm_name and nm_name == em_name):
                            other_app = visit.application.application_id if visit.application else f"#{visit.application_id}"
                            return {
                                "has_conflict": True,
                                "member_name": nm.get("name"),
                                "member_email": nm.get("email"),
                                "conflicting_application": other_app,
                                "date": str(target_day),
                                "warning_message": f"Conflict Warning: Member {nm.get('name')} is already scheduled for an EVC visit on {target_day} for Application {other_app}.",
                            }
        return None

    @classmethod
    def schedule_evc(
        cls,
        db: Session,
        evc_id: int,
        proposed_date: datetime,
        confirmed_date: datetime,
        committee_members: List[Dict[str, Any]],
        user: User,
        remarks: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Dict[str, Any]:
        """
        Schedule or reschedule an EVC inspection.
        Returns the updated record along with any conflict warnings.
        """
        evc = db.query(EvcRecord).filter(EvcRecord.id == evc_id).first()
        if not evc:
            raise HTTPException(status_code=404, detail="EVC record not found.")

        # Check for conflicts
        conflict = cls.check_member_conflict(db, evc.id, confirmed_date, committee_members)

        old_status = evc.status
        new_status = EvcStatus.RESCHEDULED if old_status == EvcStatus.SCHEDULED else EvcStatus.SCHEDULED

        evc.proposed_date = proposed_date
        evc.confirmed_date = confirmed_date
        evc.committee_members = committee_members
        evc.status = new_status
        if remarks:
            evc.remarks = remarks
        evc.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(evc)

        app_code = evc.application.application_id if evc.application else str(evc.application_id)

        # Trigger visit approaching alert events (7 days and 2 days before visit)
        create_alert_event(
            db,
            "VISIT_APPROACHING",
            app_code,
            "COMMITTEE_MEMBER",
            confirmed_date,
            -7,
            details={"visit_date": str(confirmed_date), "members": [m.get("name") for m in committee_members]},
        )
        create_alert_event(
            db,
            "VISIT_APPROACHING",
            app_code,
            "COMMITTEE_MEMBER",
            confirmed_date,
            -2,
            details={"visit_date": str(confirmed_date), "members": [m.get("name") for m in committee_members]},
        )

        AuditService.log(
            db=db,
            action="EVC_SCHEDULED",
            user_id=user.id,
            role=user.role,
            reason=remarks or f"Scheduled EVC visit for {confirmed_date.strftime('%Y-%m-%d')}",
            details={
                "evc_id": evc.id,
                "application_id": evc.application_id,
                "confirmed_date": str(confirmed_date),
                "member_count": len(committee_members),
                "conflict_detected": bool(conflict),
            },
            request=request,
        )

        return {
            "evc": evc,
            "conflict_warning": conflict["warning_message"] if conflict else None,
        }

    @classmethod
    def complete_evc_visit(
        cls,
        db: Session,
        evc_id: int,
        report_file: Optional[UploadFile],
        remarks: str,
        user: User,
        request: Optional[Request] = None,
    ) -> EvcRecord:
        """
        Complete EVC visit, upload report, and auto-advance workflow to next stage.
        """
        if not remarks or not remarks.strip():
            raise HTTPException(status_code=400, detail="Remarks / inspection summary is mandatory to complete EVC visit.")

        evc = db.query(EvcRecord).filter(EvcRecord.id == evc_id).first()
        if not evc:
            raise HTTPException(status_code=404, detail="EVC record not found.")

        now = datetime.now(timezone.utc)

        # Save uploaded report file if provided
        if report_file:
            stored_name = f"evc_report_{evc.id}_{uuid.uuid4().hex[:8]}_{report_file.filename}"
            target_path = os.path.join(UPLOAD_DIR, stored_name)
            with open(target_path, "wb") as buffer:
                shutil.copyfileobj(report_file.file, buffer)

            # Register document in database
            doc = Document(
                institute_id=evc.application.institute_id if evc.application else 1,
                application_id=evc.application_id,
                document_type_code="EVC_REPORT",
                original_filename=report_file.filename,
                stored_filename=stored_name,
                file_path=target_path,
                file_size=os.path.getsize(target_path),
                mime_type=report_file.content_type or "application/pdf",
                sha256_hash="evc_" + uuid.uuid4().hex,
                status="Verified",
                created_at=now,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            evc.report_file_path = target_path
            evc.report_original_filename = report_file.filename
            evc.report_document_id = doc.id
            evc.report_uploaded_at = now

        evc.status = EvcStatus.COMPLETED
        evc.remarks = remarks
        evc.updated_at = now
        db.commit()
        db.refresh(evc)

        app_code = evc.application.application_id if evc.application else str(evc.application_id)

        # Alert event: report pending cleared / submitted
        create_alert_event(
            db,
            "REPORT_SUBMITTED",
            app_code,
            "REGIONAL_OFFICER",
            now,
            0,
            details={"evc_id": evc.id, "report": evc.report_original_filename},
        )

        AuditService.log(
            db=db,
            action="EVC_COMPLETED",
            user_id=user.id,
            role=user.role,
            reason=f"EVC visit completed: {remarks[:100]}",
            details={
                "evc_id": evc.id,
                "application_id": evc.application_id,
                "report_file": evc.report_original_filename,
            },
            request=request,
        )

        from backend.app.services.scheduler_service import auto_close_escalations
        auto_close_escalations(db, evc.case_id, "EVC inspection visit completed")

        # Auto-advance workflow through workflow_service
        if evc.workflow and evc.workflow.status != "COMPLETED":
            try:
                advance_reason = f"EVC physical inspection completed on {evc.confirmed_date.strftime('%Y-%m-%d') if evc.confirmed_date else 'schedule'}. Inspection report submitted. Remarks: {remarks}"
                WorkflowService.complete_stage(
                    db=db,
                    workflow=evc.workflow,
                    user=user,
                    reason=advance_reason,
                    notes=f"EVC Report: {evc.report_original_filename or 'Uploaded on file'}",
                    request=request,
                )
            except Exception as e:
                # If stage is already at decision or cannot advance, log note
                print(f"Workflow auto-advance note: {e}")

        return evc

    @classmethod
    def list_queue(
        cls,
        db: Session,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EvcRecord]:
        query = db.query(EvcRecord).order_by(desc(EvcRecord.created_at))
        if status and status != "ALL":
            query = query.filter(EvcRecord.status == status)
        if search:
            s = f"%{search}%"
            query = query.join(Application).filter(
                or_(Application.application_id.ilike(s), Application.category.ilike(s))
            )
        return query.offset(offset).limit(limit).all()

    @classmethod
    def list_upcoming_visits(cls, db: Session, limit: int = 20) -> List[EvcRecord]:
        now = datetime.now(timezone.utc)
        return (
            db.query(EvcRecord)
            .filter(
                EvcRecord.status.in_([EvcStatus.SCHEDULED, EvcStatus.RESCHEDULED]),
                EvcRecord.confirmed_date >= now - timedelta(days=1),
            )
            .order_by(EvcRecord.confirmed_date.asc())
            .limit(limit)
            .all()
        )

