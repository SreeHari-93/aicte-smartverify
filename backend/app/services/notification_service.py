from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models.certificate import Certificate
from backend.app.models.notification import Notification
from backend.app.models.institute import Institute
from backend.app.services.audit_service import AuditService


def check_and_create_certificate_notifications(db: Session, today: date = None) -> int:
    """
    Evaluates all certificates across institutes and creates expiry notifications.
    Triggered by daily APScheduler job or invoked manually in tests/admin runners.
    Returns: count of notifications created.
    """
    if today is None:
        today = date.today()

    certificates = db.query(Certificate).all()
    created_count = 0

    for cert in certificates:
        status, days = cert.compute_status(today)

        notification_title = None
        notification_msg = None
        n_type = None

        if days == 60:
            n_type = "CERT_EXPIRING_60"
            notification_title = f"Certificate Expiring Soon: {cert.name}"
            notification_msg = f"{cert.name} (ID: {cert.certificate_id}) will expire in exactly 60 days on {cert.expiry_date.strftime('%d-%m-%Y')}."
        elif days == 30:
            n_type = "CERT_EXPIRING_30"
            notification_title = f"Urgent: Certificate Expiring in 30 Days ({cert.name})"
            notification_msg = f"{cert.name} (ID: {cert.certificate_id}) is due for renewal on {cert.expiry_date.strftime('%d-%m-%Y')}. Please submit renewal documents."
        elif days == 7:
            n_type = "CERT_EXPIRING_7"
            notification_title = f"Critical Alert: {cert.name} expires in 7 Days"
            notification_msg = f"{cert.name} (ID: {cert.certificate_id}) expires next week ({cert.expiry_date.strftime('%d-%m-%Y')}). Initiate renewal immediately."
        elif days < 0:
            # Check if an expired notification was already sent today
            n_type = "CERT_EXPIRED"
            notification_title = f"Expired Certificate Notice: {cert.name}"
            notification_msg = f"{cert.name} (ID: {cert.certificate_id}) expired {abs(days)} day(s) ago on {cert.expiry_date.strftime('%d-%m-%Y')}."

        if n_type:
            # Avoid duplicate notification for same cert and type on the same day
            existing = (
                db.query(Notification)
                .filter(
                    Notification.institute_id == cert.institute_id,
                    Notification.type == n_type,
                    Notification.title == notification_title,
                )
                .first()
            )
            if not existing:
                notif = Notification(
                    institute_id=cert.institute_id,
                    title=notification_title,
                    message=notification_msg,
                    type=n_type,
                    link="/institute/certificates",
                    is_read=False,
                )
                db.add(notif)
                created_count += 1

    if created_count > 0:
        db.commit()
        AuditService.log_event(
            db=db,
            action="EXPIRY_NOTIFICATIONS_GENERATED",
            reason=f"Generated {created_count} certificate expiry notifications",
        )

    return created_count

