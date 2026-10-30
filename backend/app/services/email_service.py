import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.email_outbox import EmailOutbox


class EmailService:
    @classmethod
    def send_email(
        cls,
        db: Session,
        recipient: str,
        subject: str,
        body: str,
    ) -> EmailOutbox:
        """
        Sends an email or logs it into the email_outbox table.
        If SMTP is not configured or transmission fails, marks it 'queued (SMTP not configured)'
        and does not fail.
        """
        smtp_host = os.environ.get("SMTP_HOST")
        smtp_port = os.environ.get("SMTP_PORT")
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASSWORD")
        smtp_from = os.environ.get("SMTP_FROM", "noreply@aicte-india.org")

        outbox_entry = EmailOutbox(
            recipient=recipient,
            subject=subject,
            body=body,
            status="queued (SMTP not configured)",
            sent_at=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
        )

        if smtp_host and smtp_port:
            try:
                port = int(smtp_port)
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = smtp_from
                msg["To"] = recipient

                part = MIMEText(body, "html" if "<html" in body.lower() else "plain")
                msg.attach(part)

                with smtplib.SMTP(smtp_host, port, timeout=10) as server:
                    if port == 587:
                        server.starttls()
                    if smtp_user and smtp_pass:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(smtp_from, [recipient], msg.as_string())

                outbox_entry.status = "sent"
                outbox_entry.sent_at = datetime.now(timezone.utc)
            except Exception as e:
                outbox_entry.status = "queued (SMTP not configured)"
                outbox_entry.error_message = f"SMTP transmission error: {str(e)}"
        else:
            outbox_entry.status = "queued (SMTP not configured)"

        db.add(outbox_entry)
        db.commit()
        db.refresh(outbox_entry)
        return outbox_entry

