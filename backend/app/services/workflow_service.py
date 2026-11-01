import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from fastapi import HTTPException, status, Request

from backend.app.models.user import User, UserRole
from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.validation_run import ValidationRun
from backend.app.models.notification import Notification
from backend.app.models.workflow import (
    WorkflowTemplate,
    WorkflowTemplateStage,
    ApplicationWorkflow,
    WorkflowHistory,
    WorkflowStatus,
    WorkflowAction,
)
from backend.app.services.audit_service import AuditService

logger = logging.getLogger("aicte_workflow")


class WorkflowService:
    @classmethod
    def get_templates(cls, db: Session) -> List[WorkflowTemplate]:
        """Fetch all templates with ordered stages"""
        return db.query(WorkflowTemplate).order_by(WorkflowTemplate.id).all()

    @classmethod
    def update_stage_sla(
        cls,
        db: Session,
        template_id: int,
        stage_id: int,
        sla_days: int,
        responsible_role: Optional[str] = None,
        user: Optional[User] = None,
        request: Optional[Request] = None,
    ) -> WorkflowTemplateStage:
        """Update SLA days and responsible role for a template stage"""
        stage = (
            db.query(WorkflowTemplateStage)
            .filter(
                WorkflowTemplateStage.template_id == template_id,
                WorkflowTemplateStage.id == stage_id,
            )
            .first()
        )
        if not stage:
            raise HTTPException(status_code=404, detail="Template stage not found.")

        old_sla = stage.sla_days
        old_role = stage.responsible_role

        if sla_days <= 0:
            raise HTTPException(status_code=400, detail="SLA days must be greater than zero.")

        stage.sla_days = sla_days
        if responsible_role:
            stage.responsible_role = responsible_role
        stage.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(stage)

        AuditService.log(
            db=db,
            action="WORKFLOW_STAGE_SLA_UPDATED",
            user_id=user.id if user else None,
            role=user.role if user else "ADMIN",
            reason=f"Updated SLA for {stage.stage_name}: {old_sla} -> {sla_days} days, role: {old_role} -> {stage.responsible_role}",
            resource_type="workflow_template_stage",
            resource_id=str(stage.id),
        )
        return stage

    @classmethod
    def choose_template_for_category(cls, db: Session, category: str) -> WorkflowTemplate:
        """Select default workflow template based on configurable database mapping or handbook heuristics"""
        import json
        from backend.app.models.system_setting import SystemSetting

        cat_str = (category or "").strip()
        # 1. Check database-configured category mapping
        setting = db.query(SystemSetting).filter(SystemSetting.key == "category_template_mapping").first()
        if setting and setting.value:
            try:
                mapping = json.loads(setting.value)
                for cat_key, tmpl_code in mapping.items():
                    if cat_key.lower() == cat_str.lower() or cat_key.lower() in cat_str.lower():
                        tmpl = db.query(WorkflowTemplate).filter(WorkflowTemplate.code == tmpl_code).first()
                        if tmpl:
                            return tmpl
            except Exception:
                pass

        # 2. Statutory handbook heuristics fallback
        cat_upper = cat_str.upper()
        if "APPEAL" in cat_upper or "HEARING" in cat_upper or "SAC" in cat_upper or "SHC" in cat_upper:
            code = "EVC_SAC_SHC"
        elif "NEW" in cat_upper or "SETTING UP" in cat_upper or "INTAKE" in cat_upper:
            code = "SCRUTINY_EVC"
        elif "SURPRISE" in cat_upper or "VERIFICATION" in cat_upper:
            code = "ONLY_EVC"
        else:
            code = "ONLY_SCRUTINY"

        template = db.query(WorkflowTemplate).filter(WorkflowTemplate.code == code).first()
        if not template:
            template = db.query(WorkflowTemplate).first()
        return template

    @classmethod
    def get_or_create_workflow(
        cls,
        db: Session,
        application: Application,
        template_code: Optional[str] = None,
        region: Optional[str] = None,
    ) -> ApplicationWorkflow:
        """Ensure an application has an active workflow instance"""
        wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.application_id == application.id).first()
        if wf:
            return wf

        if template_code:
            template = db.query(WorkflowTemplate).filter(WorkflowTemplate.code == template_code).first()
        else:
            template = cls.choose_template_for_category(db, application.category)

        if not template or not template.stages:
            # Fallback to any template that has stages configured
            for cand in db.query(WorkflowTemplate).all():
                if cand.stages:
                    template = cand
                    break

        if not template or not template.stages:
            raise HTTPException(status_code=500, detail="Workflow template configuration missing.")

        first_stage = template.stages[0]
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=first_stage.sla_days)

        # Determine region from institute state or override
        app_region = region
        if not app_region and application.institute:
            state = (application.institute.state or "").lower()
            if state in ["tamil nadu", "kerala", "karnataka", "andhra pradesh", "telangana", "pondicherry"]:
                app_region = "Southern"
            elif state in ["delhi", "punjab", "haryana", "uttar pradesh", "uttarakhand", "himachal pradesh", "jammu & kashmir"]:
                app_region = "Northern"
            elif state in ["maharashtra", "gujarat", "goa", "rajasthan"]:
                app_region = "Western"
            elif state in ["west bengal", "odisha", "bihar", "jharkhand", "assam"]:
                app_region = "Eastern"
            else:
                app_region = "Southern"
        if not app_region:
            app_region = "Southern"

        # Find matching officer for the role
        officer = (
            db.query(User)
            .filter(
                User.role == first_stage.responsible_role,
                or_(User.region == app_region, User.region.is_(None)),
            )
            .first()
        )
        if not officer:
            officer = db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.REVIEWER])).first()

        wf = ApplicationWorkflow(
            application_id=application.id,
            template_id=template.id,
            current_stage_id=first_stage.id,
            current_stage_sequence=first_stage.sequence,
            current_stage_name=first_stage.stage_name,
            assigned_officer_id=officer.id if officer else None,
            assigned_officer_name=officer.email if officer else "AICTE Desk",
            region=app_region,
            stage_start=now,
            due_date=due,
            status=WorkflowStatus.IN_PROGRESS,
        )
        db.add(wf)
        db.commit()
        db.refresh(wf)

        # Generate plain-language case summary
        summary = cls.generate_case_summary(db, wf)
        wf.case_summary = summary
        db.commit()
        db.refresh(wf)

        # If initial stage is EVC, automatically place into EVC queue
        if first_stage.stage_code == 'EVC' or 'EVC' in first_stage.stage_name.upper():
            from backend.app.services.evc_service import EvcService
            EvcService.ensure_evc_record(db, wf)

        return wf

    @classmethod
    def generate_case_summary(cls, db: Session, workflow: ApplicationWorkflow) -> str:
        """
        Generate a concise, plain-language statutory case summary.
        Grounded strictly on application attributes and validation findings.
        """
        app = workflow.application
        inst_name = app.institute.name if app.institute else "Registered Institution"
        category = app.category or "Approval"
        stage_name = workflow.current_stage_name
        due = workflow.due_date if workflow.due_date.tzinfo else workflow.due_date.replace(tzinfo=timezone.utc)
        sla_days_left = (due - datetime.now(timezone.utc)).days

        # Check latest validation run if present
        vrun = (
            db.query(ValidationRun)
            .filter(ValidationRun.application_id == app.id)
            .order_by(desc(ValidationRun.id))
            .first()
        )

        findings_note = "All mandatory baseline compliance items are satisfied."
        if vrun and vrun.findings:
            blockers = sum(1 for f in vrun.findings if getattr(f, "severity", "") == "BLOCKER")
            warnings = sum(1 for f in vrun.findings if getattr(f, "severity", "") == "WARNING")
            if blockers > 0:
                findings_note = f"Automated engine identified {blockers} blocking statutory compliance deficiencies requiring official review."
            elif warnings > 0:
                findings_note = f"Automated engine identified {warnings} minor advisories; no hard blockers found."

        time_note = f"SLA due in {sla_days_left} days." if sla_days_left >= 0 else f"SLA is overdue by {abs(sla_days_left)} days."

        summary = (
            f"Case #{app.application_id}: {inst_name} applied under category '{category}' in the {workflow.region} Region. "
            f"Currently progressing through stage '{stage_name}'. {findings_note} {time_note} "
            f"Regulatory recommendations are prepared for the reviewing officer."
        )
        return summary

    @classmethod
    def complete_stage(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        reason: str,
        notes: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """
        Complete current stage and auto-advance to next stage.
        If on the final decision stage, rejects auto-advance (final decision must be explicitly recorded).
        Mandatory reason is strictly required.
        """
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to complete stage.")

        # Ensure user has authority (not institute)
        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot execute workflow stage transitions.")

        current_stage = workflow.current_stage
        if current_stage and current_stage.is_final_decision:
            raise HTTPException(
                status_code=400,
                detail="Current stage is the Final Decision stage. The competent authority must record a formal decision (Approve / Reject) rather than auto-advancing.",
            )

        # Look for next stage in template
        next_stage = (
            db.query(WorkflowTemplateStage)
            .filter(
                WorkflowTemplateStage.template_id == workflow.template_id,
                WorkflowTemplateStage.sequence == workflow.current_stage_sequence + 1,
            )
            .first()
        )

        if not next_stage:
            raise HTTPException(
                status_code=400,
                detail="No subsequent stage found in template. Final decision must be recorded.",
            )

        old_stage_name = workflow.current_stage_name
        now = datetime.now(timezone.utc)
        due = now + timedelta(days=next_stage.sla_days)

        # Find next officer
        officer = (
            db.query(User)
            .filter(
                User.role == next_stage.responsible_role,
                or_(User.region == workflow.region, User.region.is_(None)),
            )
            .first()
        )
        if not officer:
            officer = workflow.assigned_officer

        # Update workflow instance
        workflow.current_stage_id = next_stage.id
        workflow.current_stage_sequence = next_stage.sequence
        workflow.current_stage_name = next_stage.stage_name
        workflow.stage_start = now
        workflow.due_date = due
        workflow.status = WorkflowStatus.IN_PROGRESS
        if officer:
            workflow.assigned_officer_id = officer.id
            workflow.assigned_officer_name = officer.email

        # Update summary
        workflow.case_summary = cls.generate_case_summary(db, workflow)
        workflow.updated_at = now

        # Add history record
        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.COMPLETE_STAGE,
            from_stage=old_stage_name,
            to_stage=next_stage.stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
            details=notes.strip() if notes else None,
        )
        db.add(hist)

        # Audit log
        AuditService.log(
            db=db,
            action="WORKFLOW_COMPLETE_STAGE",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
            details={"from": old_stage_name, "to": next_stage.stage_name, "notes": notes},
        )

        db.commit()
        db.refresh(workflow)

        # If advanced to EVC stage, automatically place into EVC queue
        if next_stage.stage_code == 'EVC' or 'EVC' in next_stage.stage_name.upper():
            from backend.app.services.evc_service import EvcService
            EvcService.ensure_evc_record(db, workflow)

        return workflow

    @classmethod
    def return_workflow(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        reason: str,
        notes: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """
        Return/revert workflow back for clarification or revisions.
        Mandatory reason required.
        """
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to return case.")

        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot modify workflow status.")

        old_status = workflow.status
        workflow.status = WorkflowStatus.RETURNED
        now = datetime.now(timezone.utc)
        workflow.updated_at = now

        # Add history
        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.RETURN,
            from_stage=workflow.current_stage_name,
            to_stage=workflow.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
            details=notes.strip() if notes else None,
        )
        db.add(hist)

        AuditService.log(
            db=db,
            action="WORKFLOW_RETURN",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
            details={"previous_status": old_status, "stage": workflow.current_stage_name, "notes": notes},
        )

        db.commit()
        db.refresh(workflow)
        return workflow

    @classmethod
    def resubmit_application(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        response_text: str,
        document_ids: Optional[List[int]] = None,
        simulated_time: Optional[datetime] = None,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """
        Resubmit returned application with institute response and optional evidence.
        Puts application back to IN_PROGRESS at the returned stage, restarts stage clock,
        creates audit entry and notifies reviewing officer.
        """
        if not response_text or not response_text.strip():
            raise HTTPException(status_code=400, detail="Response text is mandatory to resubmit an application.")

        if user.role != UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Only institutions can resubmit applications.")

        if workflow.application.institute_id != user.institute_id:
            raise HTTPException(status_code=403, detail="Access denied. You can only resubmit your own institution's application.")

        if workflow.status != WorkflowStatus.RETURNED:
            raise HTTPException(
                status_code=400,
                detail=f"Application cannot be resubmitted because current status is '{workflow.status}'. Only RETURNED applications can be resubmitted.",
            )

        # Link optional uploaded documents
        if document_ids:
            from backend.app.models.document import Document
            db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.institute_id == user.institute_id
            ).update({"application_id": workflow.application_id}, synchronize_session=False)

        # Restart stage clock & set status back to IN_PROGRESS at current stage
        now = simulated_time or datetime.now(timezone.utc)
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.stage_start = now
        sla_days = workflow.current_stage.sla_days if workflow.current_stage else 7
        workflow.due_date = now + timedelta(days=sla_days)
        workflow.updated_at = now

        # Record WorkflowHistory
        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.RESUBMIT,
            from_stage=workflow.current_stage_name,
            to_stage=workflow.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=response_text.strip(),
            details="Institution responded to deficiency notice; stage clock restarted.",
        )
        db.add(hist)

        # Audit log
        AuditService.log(
            db=db,
            action="WORKFLOW_RESUBMIT",
            user_id=user.id,
            role=user.role,
            reason=response_text.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
            details={
                "stage": workflow.current_stage_name,
                "new_due_date": workflow.due_date.isoformat(),
                "document_ids": document_ids or [],
            },
        )

        # Notify assigned officer
        if workflow.assigned_officer_id:
            notif = Notification(
                institute_id=user.institute_id,
                title=f"Application Resubmitted: {workflow.application.application_id}",
                message=f"Institute responded: {response_text.strip()[:140]}. Stage clock restarted (Due: {workflow.due_date.strftime('%d/%m/%Y')}).",
                type="APPLICATION_RESUBMITTED",
                link="/admin/applications",
                is_read=False,
                created_at=now,
            )
            db.add(notif)

        db.commit()
        db.refresh(workflow)
        return workflow

    @classmethod
    def submit_new_application(
        cls,
        db: Session,
        user: User,
        category: str,
        academic_year: str = "2026-2027",
        programme: str = "Engineering & Technology",
        intake: Optional[int] = 60,
        intake_details: Optional[str] = None,
        document_ids: Optional[List[int]] = None,
        notes: Optional[str] = None,
        simulated_time: Optional[datetime] = None,
    ) -> Tuple[Application, ApplicationWorkflow]:
        """
        Formal institute application submission from My Applications.
        Creates application record, attaches checklist documents, creates workflow instance,
        sets first stage with due date, records history and audit log.
        """
        if user.role != UserRole.INSTITUTE or not user.institute_id:
            raise HTTPException(status_code=403, detail="Only registered institutions can submit applications.")

        import uuid
        app_ref = f"APP-2026-{uuid.uuid4().hex[:5].upper()}"
        now = simulated_time or datetime.now(timezone.utc)

        new_app = Application(
            institute_id=user.institute_id,
            application_id=app_ref,
            category=category,
            academic_year=academic_year,
            programme=programme,
            status="SUBMITTED",
            filed_on=now,
            created_at=now,
            updated_at=now,
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)

        # Attach checklist documents if provided
        if document_ids:
            from backend.app.models.document import Document
            db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.institute_id == user.institute_id,
            ).update({"application_id": new_app.id}, synchronize_session=False)
            db.commit()

        # Create workflow instance with first stage
        wf = cls.get_or_create_workflow(db, new_app)
        if simulated_time:
            wf.stage_start = now
            sla_days = wf.current_stage.sla_days if wf.current_stage else 7
            wf.due_date = now + timedelta(days=sla_days)
            db.commit()
            db.refresh(wf)

        # Record submit history
        hist = WorkflowHistory(
            workflow_id=wf.id,
            action=WorkflowAction.SUBMIT,
            from_stage=None,
            to_stage=wf.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=notes.strip() if notes else f"Application submitted under category '{category}'.",
            details=f"Intake: {intake or 60} seats | Documents attached: {len(document_ids or [])}",
        )
        db.add(hist)

        # Audit log
        AuditService.log(
            db=db,
            action="APPLICATION_SUBMITTED",
            user_id=user.id,
            role=user.role,
            reason=f"Application {app_ref} ({category}) submitted by institution.",
            resource_type="application",
            resource_id=str(new_app.id),
            details={
                "category": category,
                "programme": programme,
                "intake": intake,
                "first_stage": wf.current_stage_name,
                "due_date": wf.due_date.isoformat(),
            },
        )

        # In-app notification for institute
        notif = Notification(
            institute_id=user.institute_id,
            title=f"Application {app_ref} Submitted Successfully",
            message=f"Application under '{category}' submitted. Review stage '{wf.current_stage_name}' started (Target Due: {wf.due_date.strftime('%d/%m/%Y')}).",
            type="APPLICATION_SUBMITTED",
            link="/institute/applications",
            is_read=False,
            created_at=now,
        )
        db.add(notif)
        db.commit()
        db.refresh(wf)

        return new_app, wf

    @classmethod
    def reassign_officer(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        new_officer_id: int,
        reason: str,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """Reassign workflow instance to another officer with mandatory reason"""
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to reassign case.")

        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot reassign workflow cases.")

        new_officer = db.query(User).filter(User.id == new_officer_id).first()
        if not new_officer:
            raise HTTPException(status_code=404, detail="Target officer not found.")

        old_officer_name = workflow.assigned_officer_name
        workflow.assigned_officer_id = new_officer.id
        workflow.assigned_officer_name = new_officer.email
        now = datetime.now(timezone.utc)
        workflow.updated_at = now

        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.REASSIGN,
            from_stage=workflow.current_stage_name,
            to_stage=workflow.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
            details=f"Reassigned from {old_officer_name} to {new_officer.email}",
        )
        db.add(hist)

        AuditService.log(
            db=db,
            action="WORKFLOW_REASSIGN",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
            details={"previous_officer": old_officer_name, "new_officer": new_officer.email},
        )

        db.commit()
        db.refresh(workflow)
        return workflow

    @classmethod
    def hold_workflow(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        reason: str,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """Place workflow on hold pending external clarification or inquiries"""
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to hold case.")

        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot place workflow on hold.")

        workflow.status = WorkflowStatus.ON_HOLD
        now = datetime.now(timezone.utc)
        workflow.updated_at = now

        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.HOLD,
            from_stage=workflow.current_stage_name,
            to_stage=workflow.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
        )
        db.add(hist)

        AuditService.log(
            db=db,
            action="WORKFLOW_HOLD",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
        )

        db.commit()
        db.refresh(workflow)
        return workflow

    @classmethod
    def resume_workflow(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        reason: str,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """Resume on-hold workflow and recalculate SLA"""
        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to resume case.")

        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot resume workflow.")

        workflow.status = WorkflowStatus.IN_PROGRESS
        now = datetime.now(timezone.utc)
        # Extend SLA by current stage SLA days
        sla = workflow.current_stage.sla_days if workflow.current_stage else 7
        workflow.due_date = now + timedelta(days=sla)
        workflow.updated_at = now

        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.RESUME,
            from_stage=workflow.current_stage_name,
            to_stage=workflow.current_stage_name,
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
        )
        db.add(hist)

        AuditService.log(
            db=db,
            action="WORKFLOW_RESUME",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
        )

        db.commit()
        db.refresh(workflow)
        return workflow

    @classmethod
    def record_final_decision(
        cls,
        db: Session,
        workflow: ApplicationWorkflow,
        user: User,
        decision: str,
        reason: str,
        notes: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> ApplicationWorkflow:
        """
        Record final statutory decision.
        STRICT REQUIREMENT: Only the competent authority (BUREAU_OFFICER or ADMIN)
        can record this decision. The system never auto-approves or rejects.
        """
        if user.role not in [UserRole.BUREAU_OFFICER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only the competent authority role (Bureau Officer or Admin) can record the final decision.",
            )

        if decision not in ["APPROVED", "REJECTED"]:
            raise HTTPException(status_code=400, detail="Decision must be APPROVED or REJECTED.")

        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required to record final decision.")

        now = datetime.now(timezone.utc)
        workflow.final_decision = decision
        workflow.final_decision_notes = notes.strip() if notes else reason.strip()
        workflow.final_decision_by = f"{user.email} ({user.role})"
        workflow.final_decision_at = now
        workflow.status = WorkflowStatus.COMPLETED
        workflow.updated_at = now

        # Update parent Application
        app = workflow.application
        if app:
            app.status = decision
            app.updated_at = now

        # Add history
        hist = WorkflowHistory(
            workflow_id=workflow.id,
            action=WorkflowAction.RECORD_DECISION,
            from_stage=workflow.current_stage_name,
            to_stage=f"DECISION: {decision}",
            performed_by_id=user.id,
            performed_by_role=user.role,
            performed_by_name=user.email,
            reason=reason.strip(),
            details=notes.strip() if notes else None,
        )
        db.add(hist)

        AuditService.log(
            db=db,
            action=f"WORKFLOW_FINAL_{decision}",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            resource_type="application_workflow",
            resource_id=str(workflow.id),
            details={"decision": decision, "notes": notes},
        )

        db.commit()
        db.refresh(workflow)

        # Auto-close any active escalations for this application
        from backend.app.services.scheduler_service import auto_close_escalations
        auto_close_escalations(db, workflow.application_id, f"Final decision recorded: {decision}")

        return workflow

    @classmethod
    def get_dashboard_metrics(
        cls,
        db: Session,
        user: User,
        region_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Produce role-scoped dashboard metrics:
        counters, stage funnel, region table, officer workload, oldest 10 pending cases, ageing buckets.
        """
        query = db.query(ApplicationWorkflow)

        # Scoping based on user role
        if user.role == UserRole.COMMITTEE_MEMBER:
            query = query.filter(ApplicationWorkflow.assigned_officer_id == user.id)

        effective_region = region_filter
        if user.role == UserRole.REGIONAL_OFFICER and user.region:
            effective_region = user.region

        if effective_region and effective_region.upper() != "ALL":
            query = query.filter(ApplicationWorkflow.region == effective_region)

        all_workflows = query.all()
        now = datetime.now(timezone.utc)

        # Workflow & Statutory Module Counters
        total = len(all_workflows)
        in_progress = sum(1 for w in all_workflows if w.status == WorkflowStatus.IN_PROGRESS)
        returned = sum(1 for w in all_workflows if w.status == WorkflowStatus.RETURNED)
        on_hold = sum(1 for w in all_workflows if w.status == WorkflowStatus.ON_HOLD)
        completed = sum(1 for w in all_workflows if w.status == WorkflowStatus.COMPLETED)

        overdue = 0
        due_in_7_days = 0
        for w in all_workflows:
            if w.status != WorkflowStatus.COMPLETED:
                due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
                if now > due:
                    overdue += 1
                elif due <= now + timedelta(days=7):
                    due_in_7_days += 1

        # Additional Statutory Module Counters
        from backend.app.models.undertaking import Undertaking, UndertakingStatus
        from backend.app.models.document_validity import DocumentValidityRecord, ValidityStatus
        from backend.app.models.evc import EvcRecord, EvcStatus

        open_undertakings = db.query(Undertaking).filter(
            Undertaking.status.in_([
                UndertakingStatus.ACTIVE,
                UndertakingStatus.SUBMITTED,
                UndertakingStatus.UNDER_VERIFICATION,
                UndertakingStatus.OVERDUE,
                UndertakingStatus.ESCALATED,
            ])
        ).count()

        documents_expiring = db.query(DocumentValidityRecord).filter(
            DocumentValidityRecord.status.in_([
                ValidityStatus.EXPIRING_SOON,
                ValidityStatus.EXPIRED,
                ValidityStatus.RENEWAL_SUBMITTED,
            ])
        ).count()

        evc_pending = db.query(EvcRecord).filter(
            EvcRecord.status.in_([
                EvcStatus.PENDING_SCHEDULING,
                EvcStatus.SCHEDULED,
                EvcStatus.RESCHEDULED,
            ])
        ).count()

        # Stage funnel
        stage_counts: Dict[str, int] = {}
        for w in all_workflows:
            s_name = w.current_stage_name
            stage_counts[s_name] = stage_counts.get(s_name, 0) + 1

        stage_funnel = [{"stage": k, "count": v} for k, v in stage_counts.items()]

        # Region table
        region_map: Dict[str, Dict[str, Any]] = {}
        all_regions_query = db.query(ApplicationWorkflow).all()
        for w in all_regions_query:
            r = w.region or "Central"
            if r not in region_map:
                region_map[r] = {"region": r, "total": 0, "in_progress": 0, "returned": 0, "overdue": 0}
            region_map[r]["total"] += 1
            if w.status == WorkflowStatus.IN_PROGRESS:
                region_map[r]["in_progress"] += 1
            elif w.status == WorkflowStatus.RETURNED:
                region_map[r]["returned"] += 1

            due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
            if w.status != WorkflowStatus.COMPLETED and now > due:
                region_map[r]["overdue"] += 1

        region_table = list(region_map.values())

        # Officer workload: deduplicated by normalized email, admin accounts excluded, display names mapped
        OFFICER_DISPLAY_NAMES = {
            "ro.south": "Dr. R. S. Ramanathan",
            "ro.north": "Dr. Vikram Malhotra",
            "bureau": "Shri A. K. Verma",
            "reviewer": "Dr. Meenakshi Sundaram",
            "evc.expert": "Prof. K. Sundaram",
            "committee": "Prof. S. Ranganathan",
            "kulkarni.panel": "Dr. Arvind Kulkarni",
        }

        def normalize_reg(r: Optional[str]) -> str:
            if not r:
                return "National"
            r_lower = r.strip().lower()
            if "south" in r_lower:
                return "South"
            if "north" in r_lower:
                return "North"
            if "west" in r_lower:
                return "West"
            if "east" in r_lower:
                return "East"
            if "national" in r_lower or "central" in r_lower:
                return "National"
            return r.strip().title()

        def format_role_pill(role_val: Any) -> str:
            r_str = str(role_val.value if hasattr(role_val, "value") else role_val).upper()
            if r_str == "REGIONAL_OFFICER":
                return "Regional officer"
            if r_str == "BUREAU_OFFICER":
                return "Bureau officer"
            if r_str == "COMMITTEE_MEMBER":
                return "Committee member"
            if r_str == "REVIEWER":
                return "Reviewer"
            return r_str.replace("_", " ").title()

        # Query all officers with workflow roles (excluding ADMIN and INSTITUTE)
        officers = (
            db.query(User)
            .filter(User.role.in_([
                UserRole.REGIONAL_OFFICER,
                UserRole.BUREAU_OFFICER,
                UserRole.COMMITTEE_MEMBER,
                UserRole.REVIEWER,
            ]))
            .all()
        )

        officer_groups: Dict[str, Dict[str, Any]] = {}
        for off in officers:
            u_key = off.email.split("@")[0].lower()
            if u_key not in officer_groups:
                officer_groups[u_key] = {
                    "officer_id": off.id,
                    "name": OFFICER_DISPLAY_NAMES.get(u_key, u_key.replace(".", " ").title()),
                    "email": off.email,
                    "role": format_role_pill(off.role),
                    "region": normalize_reg(off.region),
                    "assigned_count": 0,
                    "overdue_count": 0,
                    "completed_count": 0,
                    "_emails": {off.email.lower()},
                    "_user_ids": {off.id},
                }
            else:
                # Merge duplicate user records, preferring gov.in email
                if "@aicte.gov.in" in off.email and "@aicte.gov.in" not in officer_groups[u_key]["email"]:
                    officer_groups[u_key]["email"] = off.email
                    officer_groups[u_key]["officer_id"] = off.id
                if off.region and officer_groups[u_key]["region"] == "National":
                    officer_groups[u_key]["region"] = normalize_reg(off.region)
                officer_groups[u_key]["_emails"].add(off.email.lower())
                officer_groups[u_key]["_user_ids"].add(off.id)

        for w in all_workflows:
            matched_group = None
            if w.assigned_officer_id:
                for g in officer_groups.values():
                    if w.assigned_officer_id in g["_user_ids"]:
                        matched_group = g
                        break
            if not matched_group and w.assigned_officer_name:
                w_off = w.assigned_officer_name.lower().strip()
                w_key = w_off.split("@")[0]
                if w_key in officer_groups:
                    matched_group = officer_groups[w_key]
                else:
                    for g in officer_groups.values():
                        if w_off in g["_emails"]:
                            matched_group = g
                            break

            if matched_group:
                if w.status == WorkflowStatus.COMPLETED:
                    matched_group["completed_count"] += 1
                else:
                    matched_group["assigned_count"] += 1
                    due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
                    if now > due:
                        matched_group["overdue_count"] += 1

        officer_workload = []
        for g in officer_groups.values():
            g.pop("_emails", None)
            g.pop("_user_ids", None)
            officer_workload.append(g)

        officer_workload.sort(key=lambda o: o["assigned_count"], reverse=True)

        # Oldest 10 pending cases
        pending = [w for w in all_workflows if w.status != WorkflowStatus.COMPLETED]
        pending.sort(key=lambda w: w.stage_start if w.stage_start else now)
        oldest_pending = []
        for w in pending[:10]:
            due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
            start = w.stage_start if w.stage_start.tzinfo else w.stage_start.replace(tzinfo=timezone.utc)
            age_days = (now - start).days
            is_overdue = now > due

            oldest_pending.append({
                "id": w.id,
                "application_id": w.application.application_id if w.application else "APP-0",
                "institute_name": w.application.institute.name if w.application and w.application.institute else "Unknown",
                "category": w.application.category if w.application else "Approval",
                "stage_name": w.current_stage_name,
                "region": w.region,
                "assigned_officer": w.assigned_officer_name,
                "age_days": max(0, age_days),
                "due_date": due.isoformat(),
                "status": w.status,
                "sla_badge": "OVERDUE" if is_overdue else ("DUE SOON" if (due - now).days <= 2 else "ON TRACK"),
            })

        # Ageing Buckets: 0-7, 8-15, 16-30, 30+
        buckets = {
            "0-7": {"bucket": "0-7 Days", "count": 0, "on_track": 0, "due_soon": 0, "overdue": 0},
            "8-15": {"bucket": "8-15 Days", "count": 0, "on_track": 0, "due_soon": 0, "overdue": 0},
            "16-30": {"bucket": "16-30 Days", "count": 0, "on_track": 0, "due_soon": 0, "overdue": 0},
            "30+": {"bucket": "30+ Days", "count": 0, "on_track": 0, "due_soon": 0, "overdue": 0},
        }

        for w in pending:
            start = w.stage_start if w.stage_start.tzinfo else w.stage_start.replace(tzinfo=timezone.utc)
            due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
            age = max(0, (now - start).days)

            if age <= 7:
                b_key = "0-7"
            elif age <= 15:
                b_key = "8-15"
            elif age <= 30:
                b_key = "16-30"
            else:
                b_key = "30+"

            buckets[b_key]["count"] += 1
            if now > due:
                buckets[b_key]["overdue"] += 1
            elif (due - now).days <= 2:
                buckets[b_key]["due_soon"] += 1
            else:
                buckets[b_key]["on_track"] += 1

        # Stage analytics, SLA variance, and bottleneck identification
        stage_analytics = []
        worst_overdue_stage = "None"
        max_overdues = -1

        all_stages = db.query(WorkflowTemplateStage).order_by(WorkflowTemplateStage.sequence).all()
        seen_stage_names = set()
        unique_stages = []
        for s in all_stages:
            if s.stage_name not in seen_stage_names:
                seen_stage_names.add(s.stage_name)
                unique_stages.append(s)

        for stg in unique_stages:
            stg_workflows = [w for w in all_workflows if w.current_stage_name == stg.stage_name and w.status != WorkflowStatus.COMPLETED]
            stg_count = len(stg_workflows)
            stg_overdue = 0
            total_days_spent = 0
            for w in stg_workflows:
                stg_start = w.stage_start if w.stage_start.tzinfo else w.stage_start.replace(tzinfo=timezone.utc)
                stg_due = w.due_date if w.due_date.tzinfo else w.due_date.replace(tzinfo=timezone.utc)
                days_spent = max(0, (now - stg_start).days)
                total_days_spent += days_spent
                if now > stg_due:
                    stg_overdue += 1

            avg_days = round(total_days_spent / stg_count, 1) if stg_count > 0 else 0.0
            sla_diff = round(avg_days - stg.sla_days, 1) if stg_count > 0 else 0.0

            if stg_overdue > max_overdues and stg_overdue > 0:
                max_overdues = stg_overdue
                worst_overdue_stage = stg.stage_name

            stage_analytics.append({
                "stage_id": stg.id,
                "stage_name": stg.stage_name,
                "responsible_role": stg.responsible_role,
                "sla_days": stg.sla_days,
                "active_cases": stg_count,
                "overdue_cases": stg_overdue,
                "avg_days_spent": avg_days,
                "sla_variance_days": sla_diff,
                "variance_days": sla_diff,
                "status": "BOTTLENECK" if (sla_diff > 0 or stg_overdue > 0) else "ON_TRACK",
            })

        # Committee Workload: active cases in committee stages (EVC/SAC/SHC) and EVC visits panel counts
        from backend.app.models.evc import EvcRecord, EvcStatus
        committee_members = db.query(User).filter(User.role == UserRole.COMMITTEE_MEMBER).all()
        cm_groups: Dict[str, Dict[str, Any]] = {}

        for cm in committee_members:
            u_key = cm.email.split("@")[0].lower()
            if u_key not in cm_groups:
                cm_groups[u_key] = {
                    "member_id": cm.id,
                    "name": OFFICER_DISPLAY_NAMES.get(u_key, u_key.replace(".", " ").title()),
                    "email": cm.email,
                    "role": format_role_pill(cm.role),
                    "region": normalize_reg(cm.region),
                    "active_cases": 0,
                    "scheduled_visits": 0,
                    "completed_visits": 0,
                    "visits_display": "0",
                    "_emails": {cm.email.lower()},
                    "_user_ids": {cm.id},
                }
            else:
                if "@aicte.gov.in" in cm.email and "@aicte.gov.in" not in cm_groups[u_key]["email"]:
                    cm_groups[u_key]["email"] = cm.email
                    cm_groups[u_key]["member_id"] = cm.id
                if cm.region and cm_groups[u_key]["region"] == "National":
                    cm_groups[u_key]["region"] = normalize_reg(cm.region)
                cm_groups[u_key]["_emails"].add(cm.email.lower())
                cm_groups[u_key]["_user_ids"].add(cm.id)

        # 1. Count active cases (workflows in EVC, SAC, or SHC stages assigned to that member)
        for w in all_workflows:
            if w.status == WorkflowStatus.COMPLETED:
                continue
            stage_upper = (w.current_stage_name or "").upper()
            if not any(k in stage_upper for k in ["EVC", "SAC", "SHC", "COMMITTEE", "VISIT", "EXPERT"]):
                continue

            for g in cm_groups.values():
                matched = False
                if w.assigned_officer_id and w.assigned_officer_id in g["_user_ids"]:
                    matched = True
                elif w.assigned_officer_name:
                    w_name = w.assigned_officer_name.lower().strip()
                    if w_name in g["_emails"] or w_name.split("@")[0] == g["email"].lower().split("@")[0]:
                        matched = True
                if matched:
                    g["active_cases"] += 1
                    break

        # 2. Count EVC visits (records listing member on panel)
        all_evcs = db.query(EvcRecord).all()
        for evc in all_evcs:
            m_list = evc.committee_members or []
            for g in cm_groups.values():
                on_panel = False
                for m in m_list:
                    if not isinstance(m, dict):
                        continue
                    m_email = str(m.get("email") or "").lower()
                    m_name = str(m.get("name") or "").lower()
                    if m_email and (m_email in g["_emails"] or m_email.split("@")[0] == g["email"].lower().split("@")[0]):
                        on_panel = True
                        break
                    if m_name and (g["name"].lower() in m_name or m_name in g["name"].lower()):
                        on_panel = True
                        break
                if on_panel:
                    if evc.status == EvcStatus.COMPLETED:
                        g["completed_visits"] += 1
                    else:
                        g["scheduled_visits"] += 1

        committee_workload = []
        for g in cm_groups.values():
            g.pop("_emails", None)
            g.pop("_user_ids", None)
            s_cnt = g["scheduled_visits"]
            c_cnt = g["completed_visits"]
            if s_cnt + c_cnt > 0:
                g["visits_display"] = f"{s_cnt} scheduled / {c_cnt} completed"
            else:
                g["visits_display"] = "0"
            committee_workload.append(g)

        committee_workload.sort(key=lambda c: (c["active_cases"], c["scheduled_visits"] + c["completed_visits"]), reverse=True)

        return {
            "counters": {
                "total": total,
                "in_progress": in_progress,
                "returned": returned,
                "on_hold": on_hold,
                "completed": completed,
                "overdue": overdue,
                "due_in_7_days": due_in_7_days,
                "open_undertakings": open_undertakings,
                "documents_expiring": documents_expiring,
                "evc_pending": evc_pending,
            },
            "stage_funnel": stage_funnel,
            "stage_analytics": stage_analytics,
            "worst_overdue_stage": worst_overdue_stage,
            "region_table": region_table,
            "officer_workload": officer_workload,
            "committee_workload": committee_workload,
            "oldest_pending": oldest_pending,
            "ageing_buckets": list(buckets.values()),
            "user_scope": {
                "role": user.role,
                "region": user.region,
                "effective_region": effective_region,
            },
        }
