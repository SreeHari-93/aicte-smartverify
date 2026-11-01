import logging
import re
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.alert_event import AlertEvent
from backend.app.models.notification_rule import NotificationRule
from backend.app.models.escalation import EscalationMatrix, EscalationRecord
from backend.app.models.scheduler_log import SchedulerRunLog
from backend.app.models.system_setting import SystemSetting
from backend.app.models.email_outbox import EmailOutbox
from backend.app.models.notification import Notification
from backend.app.models.workflow import ApplicationWorkflow
from backend.app.models.evc import EvcRecord
from backend.app.models.undertaking import Undertaking
from backend.app.models.document_validity import DocumentValidityRecord
from backend.app.models.institute import Institute
from backend.app.models.user import User
from backend.app.services.audit_service import AuditService

logger = logging.getLogger("aicte.scheduler")

def to_utc_datetime(dt):
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    if isinstance(dt, date):
        return datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
    return dt


MANDATORY_REMINDER_SUFFIX = "\n\nThis is a system reminder. Decisions remain with the competent authority."
FORBIDDEN_WORDS = ["forgery", "fraud", "misconduct"]


def assert_no_prohibited_words(text: str) -> None:
    """Strictly assert no prohibited inflammatory terminology exists in statutory messages."""
    lower_text = text.lower()
    for word in FORBIDDEN_WORDS:
        if re.search(r'\b' + re.escape(word) + r'\b', lower_text):
            raise ValueError(f"Prohibited word detected: '{word}' is strictly disallowed in statutory notifications.")


def sanitize_message(text: str) -> str:
    """Ensure message does not contain forbidden words and ends with the mandatory system reminder suffix."""
    assert_no_prohibited_words(text)
    if not text.rstrip().endswith("Decisions remain with the competent authority."):
        text = text.rstrip() + MANDATORY_REMINDER_SUFFIX
    return text


# --- Demo Clock Support ---

def get_effective_time(db: Session) -> datetime:
    """Return simulated demo clock time if active, otherwise true current UTC time."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == "demo_clock").first()
    if setting and setting.value:
        try:
            dt = datetime.fromisoformat(setting.value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            logger.warning(f"Failed to parse demo_clock '{setting.value}': {e}")
    return datetime.now(timezone.utc)


def set_demo_clock(db: Session, sim_time: datetime | str, user_id: Optional[int] = None, role: Optional[str] = None) -> datetime:
    """Set demo clock simulated date/time."""
    if isinstance(sim_time, str):
        dt = datetime.fromisoformat(sim_time)
    else:
        dt = sim_time
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    setting = db.query(SystemSetting).filter(SystemSetting.key == "demo_clock").first()
    iso_val = dt.isoformat()
    if not setting:
        setting = SystemSetting(key="demo_clock", value=iso_val, description="Simulated system clock for demonstration")
        db.add(setting)
    else:
        setting.value = iso_val
    db.commit()

    AuditService.log(
        db=db,
        action="DEMO_CLOCK_UPDATED",
        user_id=user_id,
        role=role or "ADMIN",
        details={"simulated_time": iso_val},
        reason="Demonstration simulated clock updated by administrator"
    )
    return dt


def reset_demo_clock(db: Session, user_id: Optional[int] = None, role: Optional[str] = None) -> None:
    """Clear demo clock setting to return to real system time."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == "demo_clock").first()
    if setting:
        db.delete(setting)
        db.commit()

    AuditService.log(
        db=db,
        action="DEMO_CLOCK_RESET",
        user_id=user_id,
        role=role or "ADMIN",
        details={"action": "reverted_to_realtime"},
        reason="Demonstration simulated clock reset to real wall clock time"
    )


def is_demo_clock_active(db: Session) -> Tuple[bool, Optional[datetime]]:
    setting = db.query(SystemSetting).filter(SystemSetting.key == "demo_clock").first()
    if setting and setting.value:
        try:
            dt = datetime.fromisoformat(setting.value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return True, dt
        except Exception:
            return False, None
    return False, None


# --- Seed Default Rules & Escalation Matrix ---

DEFAULT_NOTIFICATION_RULES = [
    {
        "event_type": "STAGE_DUE_SOON",
        "title": "Application Stage SLA Due Soon",
        "offsets_days": [7, 2],
        "recipient_role": "ASSIGNED_OFFICER",
        "channel": "BOTH",
        "message_template": "Stage \"{stage_name}\" for application {case_id} ({institute_name}) is due in {days_left} day(s) on {due_date}."
    },
    {
        "event_type": "STAGE_OVERDUE",
        "title": "Application Stage SLA Overdue",
        "offsets_days": [0],
        "recipient_role": "ASSIGNED_OFFICER",
        "channel": "BOTH",
        "message_template": "Stage \"{stage_name}\" for application {case_id} ({institute_name}) is OVERDUE by {days_overdue} day(s). Statutory SLA exceeded."
    },
    {
        "event_type": "EVC_PENDING_SCHEDULING",
        "title": "EVC Visit Pending Scheduling",
        "offsets_days": [7, 2],
        "recipient_role": "REGIONAL_OFFICER",
        "channel": "BOTH",
        "message_template": "Expert Visit Committee for {case_id} ({institute_name}) is awaiting scheduling. Target deadline is {due_date}."
    },
    {
        "event_type": "EVC_SCHEDULING_OVERDUE",
        "title": "EVC Scheduling Overdue",
        "offsets_days": [0],
        "recipient_role": "REGIONAL_OFFICER",
        "channel": "BOTH",
        "message_template": "Scheduling of EVC for {case_id} ({institute_name}) is overdue by {days_overdue} day(s). Urgent committee constitution required."
    },
    {
        "event_type": "VISIT_APPROACHING",
        "title": "Upcoming EVC Inspection Visit",
        "offsets_days": [7, 2],
        "recipient_role": "COMMITTEE_MEMBER",
        "channel": "BOTH",
        "message_template": "AICTE Expert Visit to {institute_name} ({case_id}) is scheduled in {days_left} day(s) on {visit_date}."
    },
    {
        "event_type": "VISIT_COMPLETED_REPORT_PENDING",
        "title": "EVC Inspection Report Submission Pending",
        "offsets_days": [3, 7],
        "recipient_role": "COMMITTEE_MEMBER",
        "channel": "BOTH",
        "message_template": "EVC inspection for {case_id} ({institute_name}) concluded on {visit_date}. Final committee report upload is pending ({days_overdue} day(s) elapsed)."
    },
    {
        "event_type": "UNDERTAKING_DUE_SOON",
        "title": "Statutory Undertaking Due Soon",
        "offsets_days": [30, 15, 7, 1],
        "recipient_role": "INSTITUTE",
        "channel": "BOTH",
        "message_template": "Statutory undertaking condition \"{condition}\" for {case_id} is due in {days_left} day(s) on {due_date}. Please upload compliance evidence."
    },
    {
        "event_type": "UNDERTAKING_OVERDUE",
        "title": "Statutory Undertaking Overdue",
        "offsets_days": [0],
        "recipient_role": "INSTITUTE",
        "channel": "BOTH",
        "message_template": "Statutory undertaking condition \"{condition}\" for {case_id} is OVERDUE by {days_overdue} day(s). Immediate compliance upload required."
    },
    {
        "event_type": "DOCUMENT_EXPIRING",
        "title": "Mandatory Document Expiry Notice",
        "offsets_days": [90, 60, 30, 7],
        "recipient_role": "INSTITUTE",
        "channel": "BOTH",
        "message_template": "Document \"{doc_name}\" for {institute_name} expires in {days_left} day(s) on {expiry_date}. Please submit renewal."
    },
    {
        "event_type": "DOCUMENT_EXPIRED",
        "title": "Mandatory Document Expired",
        "offsets_days": [0],
        "recipient_role": "INSTITUTE",
        "channel": "BOTH",
        "message_template": "Document \"{doc_name}\" for {institute_name} expired on {expiry_date} ({days_overdue} day(s) ago). Renewal submission required immediately."
    },
    {
        "event_type": "RENEWAL_PENDING",
        "title": "Document Renewal Verification Pending",
        "offsets_days": [7, 14],
        "recipient_role": "REGIONAL_OFFICER",
        "channel": "IN_APP",
        "message_template": "Submitted renewal for \"{doc_name}\" of {institute_name} has been pending official verification for {days_overdue} day(s)."
    }
]

DEFAULT_ESCALATION_LEVELS = [
    # (event_type, level, days_overdue, designated_role)
    ("STAGE_OVERDUE", 1, 3, "REGIONAL_OFFICER"),
    ("STAGE_OVERDUE", 2, 7, "BUREAU_OFFICER"),
    ("STAGE_OVERDUE", 3, 14, "ADMIN"),
    ("UNDERTAKING_OVERDUE", 1, 3, "REGIONAL_OFFICER"),
    ("UNDERTAKING_OVERDUE", 2, 7, "BUREAU_OFFICER"),
    ("UNDERTAKING_OVERDUE", 3, 14, "ADMIN"),
    ("EVC_SCHEDULING_OVERDUE", 1, 3, "BUREAU_OFFICER"),
    ("EVC_SCHEDULING_OVERDUE", 2, 7, "ADMIN"),
    ("DOCUMENT_EXPIRED", 1, 7, "REGIONAL_OFFICER"),
    ("DOCUMENT_EXPIRED", 2, 15, "BUREAU_OFFICER"),
    ("DOCUMENT_EXPIRED", 3, 30, "ADMIN"),
]


def seed_rules_and_escalations_if_empty(db: Session) -> None:
    """Ensure default statutory rules and escalation matrix levels exist."""
    existing_rules_count = db.query(NotificationRule).count()
    if existing_rules_count == 0:
        for r_data in DEFAULT_NOTIFICATION_RULES:
            rule = NotificationRule(
                event_type=r_data["event_type"],
                title=r_data["title"],
                offsets_days=r_data["offsets_days"],
                recipient_role=r_data["recipient_role"],
                channel=r_data["channel"],
                message_template=r_data["message_template"],
                is_enabled=True,
            )
            db.add(rule)
        db.commit()

    existing_matrix_count = db.query(EscalationMatrix).count()
    if existing_matrix_count == 0:
        for ev_type, lvl, days, role in DEFAULT_ESCALATION_LEVELS:
            mat = EscalationMatrix(
                event_type=ev_type,
                level=lvl,
                days_overdue=days,
                designated_role=role,
                is_enabled=True
            )
            db.add(mat)
        db.commit()


# --- Auto-close Escalations on Case Resolution ---

def auto_close_escalations(db: Session, case_id: str, resolved_reason: str = "Case resolved") -> int:
    """
    Close all active escalation records for the given case_id when the condition is resolved.
    Returns the count of closed escalations.
    """
    now = get_effective_time(db)
    active_records = db.query(EscalationRecord).filter(
        EscalationRecord.case_id == str(case_id),
        EscalationRecord.status == "ACTIVE"
    ).all()

    closed_count = 0
    for rec in active_records:
        rec.status = "AUTO_CLOSED"
        rec.resolved_at = now
        closed_count += 1

    if closed_count > 0:
        db.commit()
        AuditService.log(
            db=db,
            action="ESCALATION_AUTO_CLOSED",
            details={
                "case_id": case_id,
                "closed_count": closed_count,
                "reason": resolved_reason,
                "resolved_at": now.isoformat()
            },
            reason=f"Escalation auto-closed: {resolved_reason}"
        )
    return closed_count


# --- Idempotent Alert Delivery ---

def deliver_alert(
    db: Session,
    rule: NotificationRule,
    case_id: str,
    offset_days: int,
    due_date: Optional[datetime],
    template_vars: Dict[str, Any],
    institute_id: Optional[int] = None,
    recipient_email: Optional[str] = None,
    recipient_user_id: Optional[int] = None,
    link: Optional[str] = None
) -> Optional[AlertEvent]:
    """
    Idempotent alert creation: creates AlertEvent only if (event_type, case_id, offset_days) doesn't exist.
    Delivers to in-app alert_events, institute notifications (if institute), and email_outbox.
    """
    # 1. Idempotency Check
    existing = db.query(AlertEvent).filter(
        AlertEvent.event_type == rule.event_type,
        AlertEvent.case_id == str(case_id),
        AlertEvent.offset_days == int(offset_days)
    ).first()
    if existing:
        return None  # Already delivered for this offset

    # 2. Format message
    try:
        body = rule.message_template.format(**template_vars)
    except Exception as e:
        logger.error(f"Failed formatting template for {rule.event_type}: {e}")
        body = f"{rule.title} for {case_id}."

    # Validate against forbidden words and attach mandatory reminder suffix
    formatted_body = sanitize_message(body)

    title = rule.title
    assert_no_prohibited_words(title)

    # 3. Create AlertEvent
    alert = AlertEvent(
        event_type=rule.event_type,
        case_id=str(case_id),
        recipient_role=rule.recipient_role,
        due_date=due_date,
        offset_days=int(offset_days),
        details=template_vars,
        status="ACTIVE",
        title=title,
        message=formatted_body,
        link=link,
        is_read=False,
        institute_id=institute_id,
        recipient_user_id=recipient_user_id,
        created_at=get_effective_time(db)
    )
    db.add(alert)

    # 4. In-App Institute Notification (if institute recipient)
    if institute_id and rule.recipient_role in ("INSTITUTE", "ALL"):
        notif = Notification(
            institute_id=institute_id,
            title=title,
            message=formatted_body,
            type=rule.event_type,
            link=link or f"/institute/applications",
            is_read=False,
            created_at=get_effective_time(db)
        )
        db.add(notif)

    # 5. Email Outbox delivery if channel is EMAIL or BOTH
    if rule.channel in ("EMAIL", "BOTH"):
        target_email = recipient_email
        if not target_email and institute_id:
            inst = db.query(Institute).filter(Institute.id == institute_id).first()
            if inst:
                inst_user = db.query(User).filter(User.institute_id == inst.id).first()
                if inst_user and inst_user.email:
                    target_email = inst_user.email
                elif getattr(inst, "email", None):
                    target_email = getattr(inst, "email")
        if not target_email:
            target_email = f"{rule.recipient_role.lower()}@aicte.gov.in"

        email_entry = EmailOutbox(
            recipient=target_email,
            subject=f"[AICTE Alert] {title} - Ref: {case_id}",
            body=formatted_body,
            status="queued (SMTP not configured)",
            created_at=get_effective_time(db)
        )
        db.add(email_entry)

    db.commit()
    db.refresh(alert)

    # Audit log
    AuditService.log(
        db=db,
        action="ALERT_GENERATED",
        details={
            "alert_id": alert.id,
            "event_type": rule.event_type,
            "case_id": str(case_id),
            "offset_days": offset_days,
            "recipient_role": rule.recipient_role,
            "channel": rule.channel
        },
        reason=f"Statutory notification generated for {case_id} (offset {offset_days}d)"
    )

    return alert


# --- Full Scan Engine ---

def run_notification_scan(db: Session, simulated_time: Optional[datetime] = None) -> SchedulerRunLog:
    """
    Hourly/on-startup background scanner.
    Scans:
      - Application workflows (stages due soon & overdue)
      - EVC records (pending scheduling, scheduling overdue, visit approaching, report pending)
      - Undertakings (due soon, overdue, and level 1 escalation)
      - Document validity (expiring, expired, renewal pending)
    Idempotent and logs results in SchedulerRunLog.
    """
    start_wall_time = datetime.now(timezone.utc)
    seed_rules_and_escalations_if_empty(db)

    now = simulated_time or get_effective_time(db)
    simulated_clock = now if is_demo_clock_active(db)[0] or simulated_time else None

    # Load active rules map
    rules = {r.event_type: r for r in db.query(NotificationRule).filter(NotificationRule.is_enabled == True).all()}
    # Load escalation matrix map: event_type -> list of (level, days_overdue, designated_role) sorted by level
    matrix_records = db.query(EscalationMatrix).filter(EscalationMatrix.is_enabled == True).all()
    matrix_map: Dict[str, List[EscalationMatrix]] = {}
    for m in matrix_records:
        matrix_map.setdefault(m.event_type, []).append(m)
    for k in matrix_map:
        matrix_map[k].sort(key=lambda x: x.level)

    items_checked = 0
    alerts_created = 0
    escalations_triggered = 0

    # -------------------------------------------------------------
    # 1. SCAN APPLICATION WORKFLOWS
    # -------------------------------------------------------------
    workflows = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.status.in_(["IN_PROGRESS", "RETURNED"])
    ).all()

    for wf in workflows:
        items_checked += 1
        case_id = wf.application_id
        app_obj = wf.application
        inst_name = (app_obj.institute.name if app_obj and app_obj.institute else getattr(wf, 'institute_name', None)) or "Institution"
        inst_id = app_obj.institute_id if app_obj else getattr(wf, 'institute_id', None)
        stage_name = wf.current_stage_name or "Scrutiny"
        officer_email = wf.assigned_officer.email if wf.assigned_officer else None
        officer_id = wf.assigned_officer_id

        stage_due = getattr(wf, 'current_stage_due_date', None) or wf.due_date
        if not stage_due:
            continue
        stage_due = to_utc_datetime(stage_due)

        diff_seconds = (stage_due - now).total_seconds()
        days_left = int(diff_seconds // 86400)
        days_overdue = int(-diff_seconds // 86400) if diff_seconds < 0 else 0

        # Due soon check
        if diff_seconds > 0:
            rule = rules.get("STAGE_DUE_SOON")
            if rule and days_left in rule.offsets_days:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=days_left,
                    due_date=stage_due,
                    template_vars={
                        "stage_name": stage_name,
                        "case_id": case_id,
                        "institute_name": inst_name,
                        "days_left": days_left,
                        "due_date": stage_due.strftime("%d-%b-%Y")
                    },
                    institute_id=inst_id,
                    recipient_email=officer_email,
                    recipient_user_id=officer_id,
                    link=f"/admin/workflow"
                )
                if alert:
                    alerts_created += 1

        # Overdue check
        elif diff_seconds <= 0:
            rule = rules.get("STAGE_OVERDUE")
            if rule:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=0,
                    due_date=stage_due,
                    template_vars={
                        "stage_name": stage_name,
                        "case_id": case_id,
                        "institute_name": inst_name,
                        "days_overdue": max(1, days_overdue),
                        "due_date": stage_due.strftime("%d-%b-%Y")
                    },
                    institute_id=inst_id,
                    recipient_email=officer_email,
                    recipient_user_id=officer_id,
                    link=f"/admin/workflow"
                )
                if alert:
                    alerts_created += 1

            # Check escalations for STAGE_OVERDUE
            for esc in matrix_map.get("STAGE_OVERDUE", []):
                if days_overdue >= esc.days_overdue:
                    # Check if escalation record for this case & level already exists
                    existing_esc = db.query(EscalationRecord).filter(
                        EscalationRecord.case_id == case_id,
                        EscalationRecord.event_type == "STAGE_OVERDUE",
                        EscalationRecord.level == esc.level
                    ).first()
                    if not existing_esc:
                        esc_rec = EscalationRecord(
                            case_id=case_id,
                            case_type="workflow",
                            event_type="STAGE_OVERDUE",
                            level=esc.level,
                            notified_role=esc.designated_role,
                            notified_user_email=f"{esc.designated_role.lower()}@aicte.gov.in",
                            days_overdue=days_overdue,
                            status="ACTIVE",
                            created_at=now
                        )
                        db.add(esc_rec)
                        db.commit()
                        escalations_triggered += 1

                        AuditService.log(
                            db=db,
                            action="ESCALATION_TRIGGERED",
                            details={
                                "case_id": case_id,
                                "level": esc.level,
                                "event_type": "STAGE_OVERDUE",
                                "role": esc.designated_role,
                                "days_overdue": days_overdue
                            },
                            reason=f"Level {esc.level} escalation triggered for stage overdue: {case_id}"
                        )

    # -------------------------------------------------------------
    # 2. SCAN EVC RECORDS
    # -------------------------------------------------------------
    evc_records = db.query(EvcRecord).filter(
        EvcRecord.status.in_(["PENDING_SCHEDULING", "SCHEDULED", "RESCHEDULED", "COMPLETED"])
    ).all()

    for evc in evc_records:
        items_checked += 1
        case_id = evc.case_id
        inst_name = evc.institute_name or "Institution"
        inst_id = evc.institute_id

        # 2a. EVC PENDING SCHEDULING & SCHEDULING OVERDUE
        if evc.status in ("PENDING_SCHEDULING", "RESCHEDULED"):
            sched_deadline = evc.scheduling_deadline
            if sched_deadline:
                if sched_deadline.tzinfo is None:
                    sched_deadline = sched_deadline.replace(tzinfo=timezone.utc)
                diff = (sched_deadline - now).total_seconds()
                days_left = int(diff // 86400)
                days_overdue = int(-diff // 86400) if diff < 0 else 0

                if diff > 0:
                    rule = rules.get("EVC_PENDING_SCHEDULING")
                    if rule and days_left in rule.offsets_days:
                        alert = deliver_alert(
                            db=db,
                            rule=rule,
                            case_id=case_id,
                            offset_days=days_left,
                            due_date=sched_deadline,
                            template_vars={
                                "case_id": case_id,
                                "institute_name": inst_name,
                                "due_date": sched_deadline.strftime("%d-%b-%Y")
                            },
                            institute_id=inst_id,
                            link="/admin/evc"
                        )
                        if alert:
                            alerts_created += 1
                else:
                    rule = rules.get("EVC_SCHEDULING_OVERDUE")
                    if rule:
                        alert = deliver_alert(
                            db=db,
                            rule=rule,
                            case_id=case_id,
                            offset_days=0,
                            due_date=sched_deadline,
                            template_vars={
                                "case_id": case_id,
                                "institute_name": inst_name,
                                "days_overdue": max(1, days_overdue)
                            },
                            institute_id=inst_id,
                            link="/admin/evc"
                        )
                        if alert:
                            alerts_created += 1

                    # Check escalations
                    for esc in matrix_map.get("EVC_SCHEDULING_OVERDUE", []):
                        if days_overdue >= esc.days_overdue:
                            existing_esc = db.query(EscalationRecord).filter(
                                EscalationRecord.case_id == case_id,
                                EscalationRecord.event_type == "EVC_SCHEDULING_OVERDUE",
                                EscalationRecord.level == esc.level
                            ).first()
                            if not existing_esc:
                                esc_rec = EscalationRecord(
                                    case_id=case_id,
                                    case_type="evc",
                                    event_type="EVC_SCHEDULING_OVERDUE",
                                    level=esc.level,
                                    notified_role=esc.designated_role,
                                    notified_user_email=f"{esc.designated_role.lower()}@aicte.gov.in",
                                    days_overdue=days_overdue,
                                    status="ACTIVE",
                                    created_at=now
                                )
                                db.add(esc_rec)
                                db.commit()
                                escalations_triggered += 1

        # 2b. VISIT APPROACHING (SCHEDULED)
        elif evc.status == "SCHEDULED":
            visit_date = evc.confirmed_date or evc.proposed_date
            if visit_date:
                if visit_date.tzinfo is None:
                    visit_date = visit_date.replace(tzinfo=timezone.utc)
                diff = (visit_date - now).total_seconds()
                days_left = int(diff // 86400)
                if diff > 0:
                    rule = rules.get("VISIT_APPROACHING")
                    if rule and days_left in rule.offsets_days:
                        alert = deliver_alert(
                            db=db,
                            rule=rule,
                            case_id=case_id,
                            offset_days=days_left,
                            due_date=visit_date,
                            template_vars={
                                "case_id": case_id,
                                "institute_name": inst_name,
                                "days_left": days_left,
                                "visit_date": visit_date.strftime("%d-%b-%Y")
                            },
                            institute_id=inst_id,
                            link="/admin/evc"
                        )
                        if alert:
                            alerts_created += 1

        # 2c. VISIT COMPLETED REPORT PENDING
        elif evc.status == "COMPLETED" and not evc.report_file_path:
            completed_at = evc.completed_at or evc.confirmed_date or now
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            days_since = int((now - completed_at).total_seconds() // 86400)
            rule = rules.get("VISIT_COMPLETED_REPORT_PENDING")
            if rule and days_since in rule.offsets_days:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=days_since,
                    due_date=completed_at,
                    template_vars={
                        "case_id": case_id,
                        "institute_name": inst_name,
                        "visit_date": completed_at.strftime("%d-%b-%Y"),
                        "days_overdue": max(1, days_since)
                    },
                    institute_id=inst_id,
                    link="/admin/evc"
                )
                if alert:
                    alerts_created += 1

    # -------------------------------------------------------------
    # 3. SCAN UNDERTAKINGS
    # -------------------------------------------------------------
    undertakings = db.query(Undertaking).filter(
        Undertaking.status.in_(["ACTIVE", "SUBMITTED", "UNDER_VERIFICATION", "OVERDUE", "ESCALATED"])
    ).all()

    for ut in undertakings:
        items_checked += 1
        case_id = f"UT-{ut.id}"
        app_id = ut.application_id or f"APP-UT-{ut.id}"
        inst_id = ut.institute_id
        condition_title = ut.condition_title or ut.condition_description or "Statutory Compliance"

        due_date = ut.due_date
        if not due_date:
            continue
        due_date = to_utc_datetime(due_date)

        diff = (due_date - now).total_seconds()
        days_left = int(diff // 86400)
        days_overdue = int(-diff // 86400) if diff < 0 else 0

        # Due soon check (ACTIVE, SUBMITTED, UNDER_VERIFICATION)
        if diff > 0 and ut.status in ("ACTIVE", "SUBMITTED", "UNDER_VERIFICATION"):
            rule = rules.get("UNDERTAKING_DUE_SOON")
            if rule and days_left in rule.offsets_days:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=days_left,
                    due_date=due_date,
                    template_vars={
                        "condition": condition_title,
                        "case_id": f"{case_id} ({app_id})",
                        "days_left": days_left,
                        "due_date": due_date.strftime("%d-%b-%Y")
                    },
                    institute_id=inst_id,
                    link=f"/institute/undertakings"
                )
                if alert:
                    alerts_created += 1

        # Overdue transition & alert
        elif diff <= 0:
            if ut.status in ("ACTIVE", "SUBMITTED", "UNDER_VERIFICATION"):
                ut.status = "OVERDUE"
                db.commit()

            rule = rules.get("UNDERTAKING_OVERDUE")
            if rule:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=0,
                    due_date=due_date,
                    template_vars={
                        "condition": condition_title,
                        "case_id": f"{case_id} ({app_id})",
                        "days_overdue": max(1, days_overdue)
                    },
                    institute_id=inst_id,
                    link=f"/institute/undertakings"
                )
                if alert:
                    alerts_created += 1

            # Escalation Matrix checks for UNDERTAKING_OVERDUE
            for esc in matrix_map.get("UNDERTAKING_OVERDUE", []):
                if days_overdue >= esc.days_overdue:
                    existing_esc = db.query(EscalationRecord).filter(
                        EscalationRecord.case_id == case_id,
                        EscalationRecord.event_type == "UNDERTAKING_OVERDUE",
                        EscalationRecord.level == esc.level
                    ).first()
                    if not existing_esc:
                        esc_rec = EscalationRecord(
                            case_id=case_id,
                            case_type="undertaking",
                            event_type="UNDERTAKING_OVERDUE",
                            level=esc.level,
                            notified_role=esc.designated_role,
                            notified_user_email=f"{esc.designated_role.lower()}@aicte.gov.in",
                            days_overdue=days_overdue,
                            status="ACTIVE",
                            created_at=now
                        )
                        db.add(esc_rec)

                        # Level 1 escalation: Update undertaking status to ESCALATED
                        if esc.level == 1 and ut.status != "ESCALATED":
                            ut.status = "ESCALATED"

                        db.commit()
                        escalations_triggered += 1

                        AuditService.log(
                            db=db,
                            action="UNDERTAKING_ESCALATED" if esc.level == 1 else "ESCALATION_TRIGGERED",
                            details={
                                "case_id": case_id,
                                "undertaking_id": ut.id,
                                "level": esc.level,
                                "role": esc.designated_role,
                                "days_overdue": days_overdue
                            },
                            reason=f"Level {esc.level} statutory escalation for overdue undertaking {case_id}"
                        )

    # -------------------------------------------------------------
    # 4. SCAN MONITORED DOCUMENTS & VALIDITY
    # -------------------------------------------------------------
    validity_docs = db.query(DocumentValidityRecord).filter(
        DocumentValidityRecord.status != "RENEWED"
    ).all()

    for doc in validity_docs:
        items_checked += 1
        case_id = f"DOC-{doc.id}"
        inst_id = doc.institute_id
        inst_name = doc.institute.name if doc.institute else "Institution"
        doc_name = doc.document_type_code or "Statutory Document"

        exp_date = doc.expiry_date
        if not exp_date:
            continue
        exp_date = to_utc_datetime(exp_date)

        diff = (exp_date - now).total_seconds()
        days_left = int(diff // 86400)
        days_overdue = int(-diff // 86400) if diff < 0 else 0

        # Expiring soon
        if diff > 0:
            rule = rules.get("DOCUMENT_EXPIRING")
            if rule and days_left in rule.offsets_days:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=days_left,
                    due_date=exp_date,
                    template_vars={
                        "doc_name": doc_name,
                        "institute_name": inst_name,
                        "days_left": days_left,
                        "expiry_date": exp_date.strftime("%d-%b-%Y")
                    },
                    institute_id=inst_id,
                    link="/institute/validity"
                )
                if alert:
                    alerts_created += 1

        # Expired
        elif diff <= 0:
            if doc.status in ("VALID", "EXPIRING_SOON"):
                doc.status = "EXPIRED"
                db.commit()

            rule = rules.get("DOCUMENT_EXPIRED")
            if rule:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=0,
                    due_date=exp_date,
                    template_vars={
                        "doc_name": doc_name,
                        "institute_name": inst_name,
                        "expiry_date": exp_date.strftime("%d-%b-%Y"),
                        "days_overdue": max(1, days_overdue)
                    },
                    institute_id=inst_id,
                    link="/institute/validity"
                )
                if alert:
                    alerts_created += 1

            # Escalation Matrix check for DOCUMENT_EXPIRED
            for esc in matrix_map.get("DOCUMENT_EXPIRED", []):
                if days_overdue >= esc.days_overdue:
                    existing_esc = db.query(EscalationRecord).filter(
                        EscalationRecord.case_id == case_id,
                        EscalationRecord.event_type == "DOCUMENT_EXPIRED",
                        EscalationRecord.level == esc.level
                    ).first()
                    if not existing_esc:
                        esc_rec = EscalationRecord(
                            case_id=case_id,
                            case_type="validity",
                            event_type="DOCUMENT_EXPIRED",
                            level=esc.level,
                            notified_role=esc.designated_role,
                            notified_user_email=f"{esc.designated_role.lower()}@aicte.gov.in",
                            days_overdue=days_overdue,
                            status="ACTIVE",
                            created_at=now
                        )
                        db.add(esc_rec)
                        db.commit()
                        escalations_triggered += 1

        # Renewal pending check
        if doc.status == "RENEWAL_SUBMITTED" and doc.renewal_submitted_at:
            ren_sub = doc.renewal_submitted_at
            if ren_sub.tzinfo is None:
                ren_sub = ren_sub.replace(tzinfo=timezone.utc)
            pending_days = int((now - ren_sub).total_seconds() // 86400)
            rule = rules.get("RENEWAL_PENDING")
            if rule and pending_days in rule.offsets_days:
                alert = deliver_alert(
                    db=db,
                    rule=rule,
                    case_id=case_id,
                    offset_days=pending_days,
                    due_date=ren_sub,
                    template_vars={
                        "doc_name": doc_name,
                        "institute_name": inst_name,
                        "days_overdue": pending_days
                    },
                    institute_id=inst_id,
                    link="/admin/validity"
                )
                if alert:
                    alerts_created += 1

    # -------------------------------------------------------------
    # 5. LOG SCHEDULER EXECUTION
    # -------------------------------------------------------------
    duration_ms = int((datetime.now(timezone.utc) - start_wall_time).total_seconds() * 1000)
    log_entry = SchedulerRunLog(
        run_at=start_wall_time,
        simulated_clock=simulated_clock,
        items_checked=items_checked,
        alerts_created=alerts_created,
        escalations_triggered=escalations_triggered,
        status="SUCCESS",
        duration_ms=duration_ms,
        details={
            "workflows_checked": len(workflows),
            "evc_checked": len(evc_records),
            "undertakings_checked": len(undertakings),
            "documents_checked": len(validity_docs),
            "effective_time": now.isoformat()
        }
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    logger.info(
        f"[SCHEDULER SCAN COMPLETE] checked={items_checked}, alerts={alerts_created}, "
        f"escalations={escalations_triggered}, duration={duration_ms}ms"
    )
    return log_entry
