import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.alert_event import AlertEvent
from backend.app.models.notification_rule import NotificationRule
from backend.app.models.escalation import EscalationMatrix, EscalationRecord
from backend.app.models.scheduler_log import SchedulerRunLog
from backend.app.api.deps import get_current_user
from backend.app.services.scheduler_service import (
    get_effective_time,
    set_demo_clock,
    reset_demo_clock,
    is_demo_clock_active,
    run_notification_scan,
    seed_rules_and_escalations_if_empty,
    assert_no_prohibited_words,
    sanitize_message,
)
from backend.app.services.audit_service import AuditService

logger = logging.getLogger("aicte.alerts_api")
router = APIRouter(tags=["Alerts & Escalations"])


def derive_case_type(event_type: str, case_id: str, details: Optional[Dict[str, Any]] = None) -> str:
    et = (event_type or "").upper()
    cid = str(case_id or "").upper()
    if any(k in et for k in ["EVC", "VISIT"]):
        return "EVC"
    if "UNDERTAKING" in et or cid.startswith("UT-"):
        return "UNDERTAKING"
    if any(k in et for k in ["DOCUMENT", "VALIDITY", "RENEWAL", "LEASE"]) or cid.startswith("DOC-"):
        return "DOCUMENT_VALIDITY"
    if any(k in et for k in ["STAGE", "APPLICATION", "WORKFLOW"]) or cid.startswith("APP-"):
        return "APPLICATION"
    return "APPLICATION"


# --- Schemas ---

class RuleUpdateSchema(BaseModel):
    title: Optional[str] = None
    offsets_days: Optional[List[int]] = None
    recipient_role: Optional[str] = None
    channel: Optional[str] = None
    message_template: Optional[str] = None
    is_enabled: Optional[bool] = None


class EscalationMatrixUpdateSchema(BaseModel):
    level: Optional[int] = None
    days_overdue: Optional[int] = None
    designated_role: Optional[str] = None
    is_enabled: Optional[bool] = None


class DemoClockSchema(BaseModel):
    simulated_date: str = Field(..., description="ISO 8601 string, e.g. '2026-11-15T10:00:00Z'")


# --- Alert Feed & Center Endpoints ---

@router.get("")
def list_alerts(
    event_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    case_id: Optional[str] = None,
    unread_only: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List alerts for the current user.
    Institutes see ONLY alerts for their institution.
    Officers/Admins see regulatory alerts filtered by jurisdiction or role.
    """
    seed_rules_and_escalations_if_empty(db)
    query = db.query(AlertEvent)

    # Institute Isolation
    if current_user.role == UserRole.INSTITUTE:
        if not current_user.institute_id:
            return {"items": [], "total": 0, "unread_count": 0}
        query = query.filter(AlertEvent.institute_id == current_user.institute_id)
    else:
        # Officer/Admin visibility
        if current_user.role == UserRole.REGIONAL_OFFICER:
            query = query.filter(
                (AlertEvent.recipient_role.in_(["REGIONAL_OFFICER", "OFFICER", "ALL"])) |
                (AlertEvent.recipient_user_id == current_user.id)
            )
        elif current_user.role == UserRole.BUREAU_OFFICER:
            query = query.filter(
                AlertEvent.recipient_role.in_(["BUREAU_OFFICER", "REGIONAL_OFFICER", "ADMIN", "ALL"])
            )
        elif current_user.role == UserRole.COMMITTEE_MEMBER:
            query = query.filter(
                (AlertEvent.recipient_role.in_(["COMMITTEE_MEMBER", "ALL"])) |
                (AlertEvent.recipient_user_id == current_user.id)
            )

    if event_type:
        query = query.filter(AlertEvent.event_type == event_type)
    if status_filter:
        query = query.filter(AlertEvent.status == status_filter)
    if case_id:
        query = query.filter(AlertEvent.case_id.ilike(f"%{case_id}%"))
    if unread_only:
        query = query.filter(AlertEvent.is_read == False)

    total = query.count()
    unread_count = query.filter(AlertEvent.is_read == False).count()

    alerts = query.order_by(desc(AlertEvent.created_at)).offset((page - 1) * limit).limit(limit).all()

    items = []
    for a in alerts:
        case_type = (a.details or {}).get("case_type") if isinstance(a.details, dict) else None
        if not case_type:
            case_type = derive_case_type(a.event_type, a.case_id, a.details)
        items.append({
            "id": a.id,
            "event_type": a.event_type,
            "case_id": a.case_id,
            "case_type": case_type,
            "recipient_role": a.recipient_role,
            "due_date": a.due_date.isoformat() if a.due_date else None,
            "offset_days": a.offset_days,
            "title": a.title or a.event_type.replace("_", " ").title(),
            "message": a.message,
            "link": a.link,
            "is_read": a.is_read,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "institute_id": a.institute_id,
            "details": a.details,
        })

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "limit": limit
    }


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Universal lightweight unread alerts count for the top bar bell icon."""
    query = db.query(AlertEvent).filter(AlertEvent.is_read == False)
    if current_user.role == UserRole.INSTITUTE:
        if not current_user.institute_id:
            return {"unread_count": 0}
        query = query.filter(AlertEvent.institute_id == current_user.institute_id)
    elif current_user.role == UserRole.REGIONAL_OFFICER:
        query = query.filter(
            (AlertEvent.recipient_role.in_(["REGIONAL_OFFICER", "OFFICER", "ALL"])) |
            (AlertEvent.recipient_user_id == current_user.id)
        )
    elif current_user.role == UserRole.COMMITTEE_MEMBER:
        query = query.filter(
            (AlertEvent.recipient_role.in_(["COMMITTEE_MEMBER", "ALL"])) |
            (AlertEvent.recipient_user_id == current_user.id)
        )
    return {"unread_count": query.count()}


@router.post("/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an individual alert as read."""
    alert = db.query(AlertEvent).filter(AlertEvent.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found.")
    if current_user.role == UserRole.INSTITUTE and alert.institute_id != current_user.institute_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    alert.is_read = True
    db.commit()
    return {"success": True, "alert_id": alert_id}


@router.post("/mark-all-read")
def mark_all_alerts_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all visible alerts as read for the user."""
    query = db.query(AlertEvent).filter(AlertEvent.is_read == False)
    if current_user.role == UserRole.INSTITUTE:
        query = query.filter(AlertEvent.institute_id == current_user.institute_id)
    elif current_user.role == UserRole.REGIONAL_OFFICER:
        query = query.filter(
            (AlertEvent.recipient_role.in_(["REGIONAL_OFFICER", "OFFICER", "ALL"])) |
            (AlertEvent.recipient_user_id == current_user.id)
        )
    elif current_user.role == UserRole.COMMITTEE_MEMBER:
        query = query.filter(
            (AlertEvent.recipient_role.in_(["COMMITTEE_MEMBER", "ALL"])) |
            (AlertEvent.recipient_user_id == current_user.id)
        )

    updated_count = query.update({"is_read": True}, synchronize_session=False)
    db.commit()
    return {"success": True, "marked_count": updated_count}


# --- Notification Rules Management ---

@router.get("/rules")
def list_notification_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List statutory notification rules. Seed if empty."""
    seed_rules_and_escalations_if_empty(db)
    rules = db.query(NotificationRule).order_by(NotificationRule.id).all()
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "title": r.title,
            "offsets_days": r.offsets_days,
            "recipient_role": r.recipient_role,
            "channel": r.channel,
            "message_template": r.message_template,
            "is_enabled": r.is_enabled,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rules
    ]


@router.put("/rules/{rule_id}")
def update_notification_rule(
    rule_id: int,
    payload: RuleUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update statutory notification rule. Prohibited words check strictly enforced."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Central Administrators can edit statutory alert rules.")

    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")

    if payload.title is not None:
        assert_no_prohibited_words(payload.title)
        rule.title = payload.title

    if payload.message_template is not None:
        assert_no_prohibited_words(payload.message_template)
        rule.message_template = payload.message_template

    if payload.offsets_days is not None:
        rule.offsets_days = sorted(list(set(payload.offsets_days)))

    if payload.recipient_role is not None:
        rule.recipient_role = payload.recipient_role

    if payload.channel is not None:
        rule.channel = payload.channel

    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled

    rule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rule)

    AuditService.log(
        db=db,
        action="NOTIFICATION_RULE_UPDATED",
        user_id=current_user.id,
        role=current_user.role,
        details={"rule_id": rule.id, "event_type": rule.event_type},
        reason=f"Notification rule {rule.event_type} updated by {current_user.email}"
    )

    return {"success": True, "rule_id": rule.id}


# --- Escalation Matrix Management ---

@router.get("/escalation-matrix")
def list_escalation_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List escalation matrix levels."""
    seed_rules_and_escalations_if_empty(db)
    matrix = db.query(EscalationMatrix).order_by(EscalationMatrix.event_type, EscalationMatrix.level).all()
    return [
        {
            "id": m.id,
            "event_type": m.event_type,
            "level": m.level,
            "days_overdue": m.days_overdue,
            "designated_role": m.designated_role,
            "is_enabled": m.is_enabled,
        }
        for m in matrix
    ]


@router.put("/escalation-matrix/{matrix_id}")
def update_escalation_matrix(
    matrix_id: int,
    payload: EscalationMatrixUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update escalation level settings."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Central Administrators can edit the escalation matrix.")

    m = db.query(EscalationMatrix).filter(EscalationMatrix.id == matrix_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Matrix level not found.")

    if payload.level is not None:
        m.level = payload.level
    if payload.days_overdue is not None:
        m.days_overdue = payload.days_overdue
    if payload.designated_role is not None:
        m.designated_role = payload.designated_role
    if payload.is_enabled is not None:
        m.is_enabled = payload.is_enabled

    m.updated_at = datetime.now(timezone.utc)
    db.commit()

    AuditService.log(
        db=db,
        action="ESCALATION_MATRIX_UPDATED",
        user_id=current_user.id,
        role=current_user.role,
        details={"matrix_id": m.id, "event_type": m.event_type, "level": m.level},
        reason=f"Escalation matrix {m.event_type} level {m.level} modified"
    )

    return {"success": True, "matrix_id": m.id}


@router.get("/escalations")
def list_escalation_records(
    status_filter: Optional[str] = None,
    case_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List escalation history records."""
    if current_user.role == UserRole.INSTITUTE:
        raise HTTPException(status_code=403, detail="Institutes do not have access to council escalation logs.")

    query = db.query(EscalationRecord)
    if status_filter:
        query = query.filter(EscalationRecord.status == status_filter)
    if case_type:
        query = query.filter(EscalationRecord.case_type == case_type)

    records = query.order_by(desc(EscalationRecord.created_at)).limit(limit).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "case_type": r.case_type,
            "event_type": r.event_type,
            "level": r.level,
            "notified_role": r.notified_role,
            "notified_user_email": r.notified_user_email,
            "days_overdue": r.days_overdue,
            "status": r.status,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


# --- Scheduler Runs & Demo Clock ---

@router.post("/scheduler/run")
def trigger_scheduler_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin-only manual trigger for the background scanner."""
    if current_user.role not in [UserRole.ADMIN, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Only administrative officers can trigger immediate scheduler scans.")

    log_entry = run_notification_scan(db)
    return {
        "success": True,
        "run_id": log_entry.id,
        "items_checked": log_entry.items_checked,
        "alerts_created": log_entry.alerts_created,
        "escalations_triggered": log_entry.escalations_triggered,
        "duration_ms": log_entry.duration_ms,
        "run_at": log_entry.run_at.isoformat() if log_entry.run_at else None,
    }


@router.get("/scheduler/logs")
def list_scheduler_logs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List scheduler scan execution logs."""
    logs = db.query(SchedulerRunLog).order_by(desc(SchedulerRunLog.run_at)).limit(limit).all()
    return [
        {
            "id": l.id,
            "run_at": l.run_at.isoformat() if l.run_at else None,
            "simulated_clock": l.simulated_clock.isoformat() if l.simulated_clock else None,
            "items_checked": l.items_checked,
            "alerts_created": l.alerts_created,
            "escalations_triggered": l.escalations_triggered,
            "status": l.status,
            "duration_ms": l.duration_ms,
            "details": l.details,
        }
        for l in logs
    ]


@router.get("/demo-clock")
def get_demo_clock_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check demo clock active status and simulated date."""
    is_active, sim_time = is_demo_clock_active(db)
    effective_time = get_effective_time(db)
    return {
        "is_active": is_active,
        "simulated_time": sim_time.isoformat() if sim_time else None,
        "effective_time": effective_time.isoformat(),
        "wall_clock": datetime.now(timezone.utc).isoformat()
    }


@router.post("/demo-clock")
def set_demo_clock_time(
    payload: DemoClockSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set simulated demo clock date (Admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Only administrative officers can set simulated demo clock.")

    dt = set_demo_clock(db, payload.simulated_date, user_id=current_user.id, role=current_user.role)
    return {
        "success": True,
        "simulated_time": dt.isoformat(),
        "message": f"Demonstration clock set to {dt.isoformat()}"
    }


@router.delete("/demo-clock")
def reset_demo_clock_time(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset demo clock to real wall clock time."""
    if current_user.role not in [UserRole.ADMIN, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Only administrative officers can reset simulated demo clock.")

    reset_demo_clock(db, user_id=current_user.id, role=current_user.role)
    return {
        "success": True,
        "message": "Demo clock reset to real system wall clock time."
    }
