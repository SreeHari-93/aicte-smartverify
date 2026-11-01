from datetime import datetime, timezone, date
from typing import Optional, Any
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal
from backend.app.models.alert_event import AlertEvent


def create_alert_event(
    event_type_or_db: Any,
    case_id_or_event_type: str,
    recipient_role_or_case_id: str,
    due_date_or_recipient_role: Any,
    offset_days_or_due_date: Any = 0,
    offset_days: int = 0,
    details: Optional[dict] = None,
    db: Optional[Session] = None,
) -> AlertEvent:
    """
    Shared function required by Stage 3:
    create_alert_event(event_type, case_id, recipient_role, due_date, offset_days)
    or create_alert_event(db, event_type, case_id, recipient_role, due_date, offset_days, details=...)
    """
    should_close = False
    if isinstance(event_type_or_db, Session):
        session = event_type_or_db
        e_type = str(case_id_or_event_type)
        c_id = str(recipient_role_or_case_id)
        r_role = str(due_date_or_recipient_role)
        d_date = offset_days_or_due_date
        o_days = int(offset_days)
    else:
        if db is not None:
            session = db
        else:
            session = SessionLocal()
            should_close = True
        e_type = str(event_type_or_db)
        c_id = str(case_id_or_event_type)
        r_role = str(recipient_role_or_case_id)
        d_date = due_date_or_recipient_role
        o_days = int(offset_days_or_due_date) if offset_days_or_due_date is not None else 0

    if isinstance(d_date, date) and not isinstance(d_date, datetime):
        d_date = datetime.combine(d_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    elif isinstance(d_date, datetime) and d_date.tzinfo is None:
        d_date = d_date.replace(tzinfo=timezone.utc)

    existing = (
        session.query(AlertEvent)
        .filter(
            AlertEvent.event_type == e_type,
            AlertEvent.case_id == c_id,
            AlertEvent.offset_days == o_days,
        )
        .first()
    )
    if existing:
        if should_close:
            session.close()
        return existing

    event = AlertEvent(
        event_type=e_type,
        case_id=c_id,
        recipient_role=r_role,
        due_date=d_date,
        offset_days=o_days,
        details=details or {},
        status="PENDING",
        created_at=datetime.now(timezone.utc),
    )
    try:
        session.add(event)
        session.commit()
        session.refresh(event)
    except Exception:
        session.rollback()
        existing = (
            session.query(AlertEvent)
            .filter(
                AlertEvent.event_type == e_type,
                AlertEvent.case_id == c_id,
                AlertEvent.offset_days == o_days,
            )
            .first()
        )
        if existing:
            if should_close:
                session.close()
            return existing

    if should_close:
        session.close()

    return event
