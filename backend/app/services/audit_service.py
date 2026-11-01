from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from backend.app.models.audit_log import AuditLog


class AuditService:
    @staticmethod
    def extract_client_info(request: Request) -> tuple[str, str]:
        """Extract client IP and user agent with proxy awareness"""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        user_agent = request.headers.get("user-agent", "unknown")[:500]
        return ip, user_agent

    @staticmethod
    def log_event(
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """
        Append-only audit log entry creation with optional structured JSON details.
        Strictly no updates or deletes are permitted.
        """
        log_entry = AuditLog(
            user_id=user_id,
            role=role,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            reason=reason,
            details=details,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @classmethod
    def log(
        cls,
        db: Session,
        action: str,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[dict] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Alias for log_event with resource metadata and request inspection support"""
        if request is not None:
            try:
                extracted_ip, extracted_ua = cls.extract_client_info(request)
                ip_address = ip_address or extracted_ip
                user_agent = user_agent or extracted_ua
            except Exception:
                pass

        full_details = dict(details or {})
        if resource_type:
            full_details["resource_type"] = resource_type
        if resource_id:
            full_details["resource_id"] = resource_id
        return cls.log_event(
            db=db,
            action=action,
            user_id=user_id,
            role=role,
            ip_address=ip_address,
            user_agent=user_agent,
            reason=reason or (full_details.get("reason") if isinstance(full_details, dict) else None),
            details=full_details,
        )


