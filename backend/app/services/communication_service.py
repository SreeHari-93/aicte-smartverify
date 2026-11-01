import os
import io
import base64
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.app.models.communication_template import CommunicationTemplate
from backend.app.models.workflow import ApplicationWorkflow
from backend.app.models.application import Application
from backend.app.models.institute import Institute
from backend.app.models.user import User, UserRole
from backend.app.models.email_outbox import EmailOutbox
from backend.app.models.notification import Notification
from backend.app.models.alert_event import AlertEvent
from backend.app.services.audit_service import AuditService
from backend.app.services.scheduler_service import sanitize_message, assert_no_prohibited_words

MANDATORY_DISCLAIMER = "This is a system reminder. Decisions remain with the competent authority."

SEED_TEMPLATES = [
    {
        "code": "DEFICIENCY_NOTICE",
        "name": "Deficiency Notice",
        "category": "WORKFLOW",
        "subject_template": "AICTE Notice of Deficiency: Application {application_code} - {institute}",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: AICTE Statutory Deficiency Notice for Application {application_code}\n\n"
            "Dear Sir/Madam,\n\n"
            "During statutory scrutiny of your application ({application_code}) at stage '{stage}', the competent authority has identified the following deficiency or missing compliance item:\n\n"
            "Deficiency Identified:\n"
            "{reason}\n\n"
            "You are hereby directed to rectify the deficiency and submit formal clarification through the AICTE Portal on or before {due_date}. Failure to rectify within the statutory SLA may lead to adverse procedural determination under the AICTE Approval Process Handbook (APH).\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
    {
        "code": "CLARIFICATION_REQUEST",
        "name": "Clarification Request",
        "category": "WORKFLOW",
        "subject_template": "Request for Statutory Clarification: Application {application_code} - {institute}",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: Request for Procedural Clarification on Application {application_code}\n\n"
            "Dear Sir/Madam,\n\n"
            "In reference to your application ({application_code}) currently undergoing evaluation in stage '{stage}', additional information is required:\n\n"
            "Points for Clarification:\n"
            "{reason}\n\n"
            "Please submit your formal response and supporting documentation through the portal by {due_date}.\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
    {
        "code": "EVC_SCHEDULING_INTIMATION",
        "name": "EVC Scheduling Intimation",
        "category": "EVC",
        "subject_template": "Intimation of Expert Visit Committee (EVC) Inspection: {institute} ({application_code})",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: Intimation of On-Site Inspection by Expert Visit Committee (EVC)\n\n"
            "Dear Sir/Madam,\n\n"
            "This is to intimate that an Expert Visit Committee (EVC) has been constituted for physical inspection of your campus for application ({application_code}). The inspection is scheduled with a completion deadline of {due_date}.\n\n"
            "Inspection Directives:\n"
            "{reason}\n\n"
            "Please ensure that all instructional areas, laboratories, safety installations, original land documents, and faculty service books are kept ready for verification.\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
    {
        "code": "UNDERTAKING_REMINDER",
        "name": "Undertaking Reminder",
        "category": "UNDERTAKING",
        "subject_template": "Statutory Compliance Reminder: Outstanding Undertaking for {application_code}",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: Reminder for Submission of Compliance Evidence against Undertaking\n\n"
            "Dear Sir/Madam,\n\n"
            "This is a formal reminder regarding the conditional undertaking recorded against your application ({application_code}).\n\n"
            "Condition Requiring Compliance:\n"
            "{reason}\n\n"
            "Statutory Due Date: {due_date}\n\n"
            "Please upload certified fulfillment evidence through the AICTE Undertakings portal before the deadline to prevent escalation.\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
    {
        "code": "DOCUMENT_RENEWAL_REQUEST",
        "name": "Document Renewal Request",
        "category": "VALIDITY",
        "subject_template": "AICTE Validity Notice: Document Renewal Required for {institute}",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: Statutory Document Validity Expiration / Renewal Directive\n\n"
            "Dear Sir/Madam,\n\n"
            "Our monitored validity records indicate that statutory clearance certificates (Fire Safety NOC, Land Lease, or Building Stability Certificate) associated with case {application_code} require renewal.\n\n"
            "Validity Details:\n"
            "{reason}\n\n"
            "Statutory Target Due Date: {due_date}\n\n"
            "Kindly execute the renewal with the appropriate government department and submit the renewed certificate through the Document Validity portal.\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
    {
        "code": "ESCALATION_NOTICE",
        "name": "Escalation Notice",
        "category": "ESCALATION",
        "subject_template": "Formal Supervisory Escalation Notice: Application {application_code} - {institute}",
        "body_template": (
            "To,\n"
            "The Head of the Institution,\n"
            "{institute}\n\n"
            "Subject: AICTE Supervisory Escalation Intimation\n\n"
            "Dear Sir/Madam,\n\n"
            "Please be informed that statutory deadlines pertaining to your case ({application_code}) in stage '{stage}' have exceeded permissible handbook SLA limits and have triggered supervisory escalation.\n\n"
            "Escalation Details:\n"
            "{reason}\n\n"
            "Target Deadline Exceeded: {due_date}\n\n"
            "Immediate compliance is required. The regional and bureau oversight authorities have been alerted.\n\n"
            "This is a system reminder. Decisions remain with the competent authority."
        ),
    },
]

LOGO_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/public/aicte-logo.png")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../frontend/dist/aicte-logo.png")),
]


class CommunicationService:

    @classmethod
    def seed_templates_if_empty(cls, db: Session):
        """Ensure the 6 standard statutory communication templates are seeded in the database."""
        for item in SEED_TEMPLATES:
            existing = db.query(CommunicationTemplate).filter(CommunicationTemplate.code == item["code"]).first()
            if not existing:
                t = CommunicationTemplate(
                    code=item["code"],
                    name=item["name"],
                    category=item["category"],
                    subject_template=item["subject_template"],
                    body_template=item["body_template"],
                    is_enabled=True,
                )
                db.add(t)
        db.commit()

    @classmethod
    def get_templates(cls, db: Session) -> List[CommunicationTemplate]:
        cls.seed_templates_if_empty(db)
        return db.query(CommunicationTemplate).order_by(CommunicationTemplate.id).all()

    @classmethod
    def update_template(
        cls,
        db: Session,
        template_id: int,
        name: Optional[str] = None,
        subject_template: Optional[str] = None,
        body_template: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> CommunicationTemplate:
        tmpl = db.query(CommunicationTemplate).filter(CommunicationTemplate.id == template_id).first()
        if not tmpl:
            raise HTTPException(status_code=404, detail="Communication template not found.")

        if name is not None:
            assert_no_prohibited_words(name)
            tmpl.name = name
        if subject_template is not None:
            assert_no_prohibited_words(subject_template)
            tmpl.subject_template = subject_template
        if body_template is not None:
            assert_no_prohibited_words(body_template)
            tmpl.body_template = body_template
        if is_enabled is not None:
            tmpl.is_enabled = is_enabled

        tmpl.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(tmpl)
        return tmpl

    @classmethod
    def render_communication(
        cls,
        template: CommunicationTemplate,
        context: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Render subject and body replacing placeholders safely."""
        subject = template.subject_template
        body = template.body_template

        for key, val in context.items():
            token = f"{{{key}}}"
            subject = subject.replace(token, str(val))
            body = body.replace(token, str(val))

        # Guarantee mandatory disclaimer is present at the end
        if MANDATORY_DISCLAIMER not in body:
            body = f"{body.rstrip()}\n\n{MANDATORY_DISCLAIMER}"

        subject = sanitize_message(subject)
        body = sanitize_message(body)
        return subject, body

    @classmethod
    def generate_pdf_letter(
        cls,
        subject: str,
        body: str,
        context: Dict[str, Any],
    ) -> bytes:
        """Generate official AICTE statutory communication letter in PDF format."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Find logo
        logo_img = None
        for path in LOGO_PATHS:
            if os.path.exists(path):
                logo_img = Image(path, width=54, height=54)
                break

        # Header block
        header_text = Paragraph(
            "<font size='13' color='#0B3C9D'><b>ALL INDIA COUNCIL FOR TECHNICAL EDUCATION</b></font><br/>"
            "<font size='9' color='#555555'>A Statutory Body Under Ministry of Education, Govt. of India</font><br/>"
            "<font size='8' color='#777777'>Nelson Mandela Marg, Vasant Kunj, New Delhi-110070 | www.aicte-india.org</font>",
            styles["Normal"],
        )

        if logo_img:
            header_table = Table([[logo_img, header_text]], colWidths=[65, 450])
            header_table.setStyle(
                TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ])
            )
            elements.append(header_table)
        else:
            elements.append(header_text)

        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0B3C9D"), spaceAfter=12))

        # Letter Ref & Date row
        app_code = context.get("application_code", "AICTE-2026")
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
        meta_table = Table(
            [[
                Paragraph(f"<b>Ref No:</b> AICTE/APH/2026/{app_code}", styles["Normal"]),
                Paragraph(f"<b>Date:</b> {now_str}", ParagraphStyle("Right", parent=styles["Normal"], alignment=2)),
            ]],
            colWidths=[260, 255],
        )
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # Subject line
        subj_style = ParagraphStyle(
            "SubjectStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#0F2A5C"),
            fontName="Helvetica-Bold",
        )
        elements.append(Paragraph(f"<u>{subject}</u>", subj_style))
        elements.append(Spacer(1, 12))

        # Body text (preserve linebreaks)
        body_style = ParagraphStyle(
            "LetterBody",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1A202C"),
        )
        for line in body.split("\n"):
            line_str = line.strip()
            if not line_str:
                elements.append(Spacer(1, 6))
            else:
                elements.append(Paragraph(line_str, body_style))

        elements.append(Spacer(1, 20))

        # Sign-off block
        signoff = Table(
            [[
                Paragraph("", styles["Normal"]),
                Paragraph(
                    "<b>For and on behalf of AICTE</b><br/>"
                    "Competent Authority / Scrutiny Division<br/>"
                    "<font size='8' color='#666'>SmartVerify Statutory Governance Portal</font>",
                    ParagraphStyle("Sign", parent=styles["Normal"], alignment=2, leading=12),
                ),
            ]],
            colWidths=[280, 235],
        )
        elements.append(signoff)

        # Footer Box
        elements.append(Spacer(1, 25))
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
            leading=10,
        )
        disc_table = Table(
            [[Paragraph(f"<i>{MANDATORY_DISCLAIMER}</i>", disclaimer_style)]],
            colWidths=[515],
        )
        disc_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elements.append(disc_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    @classmethod
    def generate_and_dispatch(
        cls,
        db: Session,
        user: User,
        template_code: str,
        workflow_id: int,
        reason: str,
        target_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generates letter from template, dispatches in-app notification + email_outbox,
        generates PDF letter, and records audit trail.
        """
        cls.seed_templates_if_empty(db)
        tmpl = db.query(CommunicationTemplate).filter(CommunicationTemplate.code == template_code).first()
        if not tmpl:
            raise HTTPException(status_code=404, detail=f"Communication template '{template_code}' not found.")

        wf = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.id == workflow_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Application workflow not found.")

        app = wf.application
        inst = app.institute if app else None
        inst_name = inst.name if inst else "Registered Technical Institute"
        app_code = app.application_id if app else f"APP-WF-{wf.id}"
        due_str = wf.due_date.strftime("%d/%m/%Y") if wf.due_date else "Immediate"

        context = {
            "institute": inst_name,
            "application_code": app_code,
            "stage": wf.current_stage_name,
            "due_date": due_str,
            "reason": reason.strip(),
            "case_id": app_code,
            "officer_name": user.email,
        }

        subject, body = cls.render_communication(tmpl, context)

        # 1. In-app Notification for the institute
        now = datetime.now(timezone.utc)
        if inst:
            notif = Notification(
                institute_id=inst.id,
                title=subject[:100],
                message=body[:280],
                type="STATUTORY_NOTICE",
                link="/institute/applications",
                is_read=False,
                created_at=now,
            )
            db.add(notif)

            # Alert event
            alert = AlertEvent(
                event_type="STAGE_DUE_SOON" if "REMINDER" in tmpl.code else "STAGE_OVERDUE" if "ESCALATION" in tmpl.code else "STAGE_DUE_SOON",
                case_id=app_code,
                recipient_role="INSTITUTE",
                institute_id=inst.id,
                due_date=wf.due_date,
                title=subject[:120],
                message=body,
                link="/institute/applications",
                created_at=now,
            )
            db.add(alert)

        # 2. Email Outbox record (queued when SMTP is not configured)
        resolved_email = target_email
        if not resolved_email and inst:
            inst_user = db.query(User).filter(User.institute_id == inst.id).first()
            if inst_user:
                resolved_email = inst_user.email
        if not resolved_email:
            resolved_email = "nodal_officer@institution.ac.in"

        outbox = EmailOutbox(
            recipient=resolved_email,
            subject=subject,
            body=body,
            status="queued (SMTP not configured)",
            created_at=now,
        )
        db.add(outbox)
        db.commit()

        # 3. Generate PDF letter
        pdf_bytes = cls.generate_pdf_letter(subject, body, context)
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        # 4. Audit Log
        AuditService.log(
            db=db,
            action="COMMUNICATION_DISPATCHED",
            user_id=user.id,
            role=user.role,
            reason=f"Generated statutory letter '{tmpl.name}' for {app_code}: {reason[:100]}",
            resource_type="application_workflow",
            resource_id=str(wf.id),
            details={
                "template_code": tmpl.code,
                "recipient": resolved_email,
                "outbox_id": outbox.id,
            },
        )

        return {
            "success": True,
            "template_name": tmpl.name,
            "template_code": tmpl.code,
            "subject": subject,
            "body": body,
            "recipient_email": resolved_email,
            "outbox_status": outbox.status,
            "email_status": outbox.status,
            "disclaimer": MANDATORY_DISCLAIMER,
            "pdf_base64": pdf_b64,
        }
