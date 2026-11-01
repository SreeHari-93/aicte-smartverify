import os
import shutil
import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from fastapi import HTTPException, UploadFile, Request

from backend.app.models.document_validity import DocumentValidityRecord, ValidityStatus
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.certificate import Certificate
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.user import User, UserRole
from backend.app.services.alert_service import create_alert_event
from backend.app.services.audit_service import AuditService


UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "renewals")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ValidityService:
    @classmethod
    def sync_documents_to_validity_register(cls, db: Session) -> None:
        """
        Scan uploaded documents and existing certificates to populate the validity register.
        Extracts expiry dates and lease fields where present.
        """
        now = datetime.now(timezone.utc)
        today = date.today()

        # 1. Sync from Certificate table if not yet in DocumentValidityRecord
        certs = db.query(Certificate).all()
        for c in certs:
            existing = db.query(DocumentValidityRecord).filter(
                or_(
                    DocumentValidityRecord.certificate_number == c.certificate_id,
                    and_(
                        DocumentValidityRecord.institute_id == c.institute_id,
                        DocumentValidityRecord.document_name == c.name,
                    ),
                )
            ).first()
            if not existing:
                is_lease = "lease" in (c.name or "").lower() or "land" in (c.name or "").lower()
                rec = DocumentValidityRecord(
                    document_id=c.document_id,
                    institute_id=c.institute_id,
                    application_id=None,
                    document_type_code="CERTIFICATE",
                    document_name=c.name,
                    certificate_number=c.certificate_id,
                    issuing_authority="State Statutory Authority",
                    issue_date=c.issue_date,
                    expiry_date=c.expiry_date,
                    status=ValidityStatus.VALID,
                    days_left=(c.expiry_date - today).days if c.expiry_date else 0,
                    expiring_soon_window_days=60,
                    is_lease=is_lease,
                    lessor="Government Land Administration" if is_lease else None,
                    lessee=c.institute.name if c.institute and is_lease else None,
                    lease_start=c.issue_date if is_lease else None,
                    lease_end=c.expiry_date if is_lease else None,
                    property_address=f"Campus Survey No. 44/2, {c.institute.state if c.institute else 'Tamil Nadu'}" if is_lease else None,
                    created_at=now,
                    updated_at=now,
                )
                rec.status, rec.days_left = rec.compute_status(today)
                db.add(rec)

        # 2. Sync from Documents table where extracted_data has expiry_date
        docs = db.query(Document).filter(Document.extracted_data.isnot(None)).all()
        for d in docs:
            ext = d.extracted_data or {}
            exp_str = ext.get("expiry_date")
            if not exp_str and d.document_type and d.document_type.has_expiry:
                # Fallback to default validity
                exp_date = today + timedelta(days=d.document_type.default_validity_months * 30)
            elif exp_str:
                try:
                    exp_date = datetime.strptime(str(exp_str)[:10], "%Y-%m-%d").date()
                except Exception:
                    exp_date = today + timedelta(days=365)
            else:
                continue

            existing = db.query(DocumentValidityRecord).filter(
                DocumentValidityRecord.document_id == d.id
            ).first()
            if not existing:
                code = d.document_type_code or "DOC"
                is_lease = code in ["LAND_DOC", "LAND_DOCUMENTS", "BUILDING_PLAN", "DEED_CONV"] or "lease" in d.original_filename.lower()
                window = 60
                if d.document_type and d.document_type.default_validity_months:
                    window = min(90, max(30, d.document_type.default_validity_months * 5))

                doc_name = d.document_type.name if d.document_type else d.original_filename
                rec = DocumentValidityRecord(
                    document_id=d.id,
                    institute_id=d.institute_id,
                    application_id=d.application_id,
                    document_type_code=code,
                    document_name=doc_name,
                    certificate_number=ext.get("certificate_number") or f"DOC-{d.id:04d}",
                    issuing_authority=ext.get("issuing_authority") or (d.document_type.issuing_authority if d.document_type else "Statutory Body"),
                    issue_date=today - timedelta(days=180),
                    expiry_date=exp_date,
                    status=ValidityStatus.VALID,
                    days_left=(exp_date - today).days,
                    expiring_soon_window_days=window,
                    is_lease=is_lease,
                    lessor=ext.get("lessor") or ("District Collector / Revenue Officer" if is_lease else None),
                    lessee=ext.get("lessee") or (d.institute.name if d.institute and is_lease else None),
                    lease_start=today - timedelta(days=1825) if is_lease else None,
                    lease_end=exp_date if is_lease else None,
                    property_address=ext.get("property_address") or (f"Survey Plot #108, Main Campus, {d.institute.state if d.institute else ''}" if is_lease else None),
                    created_at=now,
                    updated_at=now,
                )
                rec.status, rec.days_left = rec.compute_status(today)
                db.add(rec)

        db.commit()

    @classmethod
    def register_or_update_document_validity(cls, db: Session, doc: Document) -> Optional[DocumentValidityRecord]:
        """
        Automatically creates or updates a DocumentValidityRecord whenever a document upload
        yields an expiry date (or has a default validity period).
        """
        ext = doc.extracted_data or {}
        exp_str = ext.get("expiry_date")
        today = date.today()
        exp_date = None
        if exp_str:
            try:
                exp_date = datetime.strptime(str(exp_str)[:10], "%Y-%m-%d").date()
            except Exception:
                pass
        if not exp_date and doc.document_type and doc.document_type.has_expiry:
            months = doc.document_type.default_validity_months or 12
            exp_date = today + timedelta(days=months * 30)

        if not exp_date:
            return None

        # Look for existing record by document_id or (institute_id + document_type_code)
        rec = db.query(DocumentValidityRecord).filter(
            or_(
                DocumentValidityRecord.document_id == doc.id,
                and_(
                    DocumentValidityRecord.institute_id == doc.institute_id,
                    DocumentValidityRecord.document_type_code == (doc.document_type_code or "DOC"),
                )
            )
        ).first()

        code = doc.document_type_code or "DOC"
        is_lease = code in ["LAND_DOC", "LAND_DOCUMENTS", "BUILDING_PLAN", "DEED_CONV"] or "lease" in doc.original_filename.lower()
        now = datetime.now(timezone.utc)
        doc_name = doc.document_type.name if doc.document_type else doc.original_filename

        if not rec:
            rec = DocumentValidityRecord(
                document_id=doc.id,
                institute_id=doc.institute_id,
                application_id=doc.application_id,
                document_type_code=code,
                document_name=doc_name,
                certificate_number=ext.get("certificate_number") or f"DOC-{doc.id:04d}",
                issuing_authority=ext.get("issuing_authority") or (doc.document_type.issuing_authority if doc.document_type else "Statutory Authority"),
                issue_date=today - timedelta(days=180),
                expiry_date=exp_date,
                status=ValidityStatus.VALID,
                days_left=(exp_date - today).days,
                expiring_soon_window_days=30,
                is_lease=is_lease,
                lessor=ext.get("lessor") or ("District Revenue Administration" if is_lease else None),
                lessee=ext.get("lessee") or (doc.institute.name if doc.institute and is_lease else None),
                lease_start=today - timedelta(days=1825) if is_lease else None,
                lease_end=exp_date if is_lease else None,
                property_address=ext.get("property_address") or (f"Campus Plot #44/2, {doc.institute.state if doc.institute else ''}" if is_lease else None),
                created_at=now,
                updated_at=now,
            )
            db.add(rec)
        else:
            rec.document_id = doc.id
            rec.expiry_date = exp_date
            rec.updated_at = now
            if ext.get("certificate_number"):
                rec.certificate_number = ext["certificate_number"]

        rec.status, rec.days_left = rec.compute_status(today)
        db.commit()
        db.refresh(rec)
        return rec

    @classmethod
    def list_records(
        cls,
        db: Session,
        user: User,
        region: Optional[str] = None,
        institute_id: Optional[int] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        is_lease: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[DocumentValidityRecord]:
        cls.sync_documents_to_validity_register(db)

        query = db.query(DocumentValidityRecord).order_by(DocumentValidityRecord.expiry_date.asc())

        # Institute isolation
        if user.role == UserRole.INSTITUTE:
            query = query.filter(DocumentValidityRecord.institute_id == user.institute_id)
        elif institute_id:
            query = query.filter(DocumentValidityRecord.institute_id == institute_id)

        effective_region = region if isinstance(region, str) else None
        if user.role == UserRole.REGIONAL_OFFICER and user.region:
            effective_region = user.region

        if effective_region and effective_region.upper() != "ALL":
            reg_norm = effective_region.lower().replace("ern", "")
            region_states = {
                "south": ["tamil nadu", "karnataka", "kerala", "andhra", "telangana"],
                "north": ["delhi", "rajasthan", "punjab", "haryana", "uttar pradesh"],
                "west": ["maharashtra", "gujarat", "goa"],
                "east": ["bengal", "odisha", "bihar", "assam"],
                "central": ["madhya pradesh", "chhattisgarh"],
            }
            state_list = region_states.get(reg_norm, [effective_region])
            query = query.join(Institute, DocumentValidityRecord.institute_id == Institute.id)
            query = query.filter(or_(*[Institute.state.ilike(f"%{st}%") for st in state_list]))

        if document_type and document_type != "ALL":
            query = query.filter(DocumentValidityRecord.document_type_code == document_type)
        if status and status != "ALL":
            query = query.filter(DocumentValidityRecord.status == status)
        if is_lease is not None:
            query = query.filter(DocumentValidityRecord.is_lease == is_lease)

        records = query.all()
        today = date.today()

        # Update dynamic status and alert events
        for r in records:
            old_status = r.status
            new_status, days = r.compute_status(today)
            r.days_left = days
            if r.status not in [ValidityStatus.RENEWAL_SUBMITTED, ValidityStatus.RENEWED]:
                r.status = new_status

            # Trigger alert events on condition changes
            if r.status == ValidityStatus.EXPIRING_SOON and old_status != ValidityStatus.EXPIRING_SOON:
                create_alert_event(
                    db,
                    "DOC_EXPIRING_SOON",
                    str(r.id),
                    "INSTITUTE",
                    r.expiry_date,
                    -(r.expiring_soon_window_days or 60),
                    details={"doc_name": r.document_name, "days_left": r.days_left},
                )
            elif r.status == ValidityStatus.EXPIRED and old_status != ValidityStatus.EXPIRED:
                create_alert_event(
                    db,
                    "DOC_EXPIRED",
                    str(r.id),
                    "REGIONAL_OFFICER",
                    r.expiry_date,
                    0,
                    details={"doc_name": r.document_name, "overdue_days": abs(r.days_left or 0)},
                )

        db.commit()

        if search:
            s = search.lower()
            records = [
                r for r in records
                if s in (r.document_name or "").lower()
                or s in (r.certificate_number or "").lower()
                or s in (r.document_type_code or "").lower()
                or (r.institute and s in (r.institute.name or "").lower())
            ]

        return records

    @classmethod
    def submit_renewal(
        cls,
        db: Session,
        record_id: int,
        renewal_file: UploadFile,
        new_issue_date: date,
        new_expiry_date: date,
        user: User,
        request: Optional[Request] = None,
    ) -> DocumentValidityRecord:
        rec = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == record_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Monitored document record not found.")

        # Institute isolation check
        if user.role == UserRole.INSTITUTE and rec.institute_id != user.institute_id:
            raise HTTPException(status_code=403, detail="Cannot renew document for another institution.")

        now = datetime.now(timezone.utc)
        stored_name = f"renewal_{rec.id}_{uuid.uuid4().hex[:8]}_{renewal_file.filename}"
        target_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(renewal_file.file, buffer)

        # Create Document record for the renewal file
        doc = Document(
            institute_id=rec.institute_id,
            application_id=rec.application_id,
            document_type_code=rec.document_type_code,
            original_filename=renewal_file.filename,
            stored_filename=stored_name,
            file_path=target_path,
            file_size=os.path.getsize(target_path),
            mime_type=renewal_file.content_type or "application/pdf",
            sha256_hash="ren_" + uuid.uuid4().hex,
            status="Uploaded",
            created_at=now,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        # Link renewal document to old monitored document record
        rec.renewal_document_id = doc.id
        rec.renewal_status = "PENDING"
        rec.renewal_submitted_at = now
        rec.status = ValidityStatus.RENEWAL_SUBMITTED
        rec.updated_at = now
        # Store requested dates in renewal details
        if rec.is_lease:
            rec.lease_start = new_issue_date
            rec.lease_end = new_expiry_date
        db.commit()
        db.refresh(rec)

        create_alert_event(
            db,
            "RENEWAL_SUBMITTED",
            str(rec.id),
            "REGIONAL_OFFICER",
            new_expiry_date,
            0,
            details={"document_name": rec.document_name, "renewal_file": renewal_file.filename},
        )

        AuditService.log(
            db=db,
            action="DOCUMENT_RENEWAL_SUBMITTED",
            user_id=user.id,
            role=user.role,
            reason=f"Uploaded renewal document for {rec.document_name}: {renewal_file.filename}",
            details={"validity_id": rec.id, "renewal_document_id": doc.id},
            request=request,
        )

        return rec

    @classmethod
    def decide_renewal(
        cls,
        db: Session,
        record_id: int,
        action: str,  # ACCEPT | REJECT
        reason: str,
        new_expiry_date: Optional[date],
        user: User,
        request: Optional[Request] = None,
    ) -> DocumentValidityRecord:
        if user.role == UserRole.INSTITUTE:
            raise HTTPException(status_code=403, detail="Institutes cannot approve or reject renewal submissions.")

        if not reason or not reason.strip():
            raise HTTPException(status_code=400, detail="Mandatory reason is required for renewal determination.")

        rec = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == record_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Validity record not found.")

        act = action.upper()
        now = datetime.now(timezone.utc)
        today = date.today()

        if act == "ACCEPT":
            rec.renewal_status = "ACCEPTED"
            if new_expiry_date:
                rec.expiry_date = new_expiry_date
            elif not rec.expiry_date or rec.expiry_date <= today:
                rec.expiry_date = today + timedelta(days=365)
            rec.status = ValidityStatus.RENEWED
            rec.days_left = (rec.expiry_date - today).days
        elif act == "REJECT":
            rec.renewal_status = "REJECTED"
            rec.status, rec.days_left = rec.compute_status(today)
        else:
            raise HTTPException(status_code=400, detail="Action must be ACCEPT or REJECT.")

        rec.renewal_decision_reason = reason.strip()
        rec.renewal_decided_by_id = user.id
        rec.renewal_decided_at = now
        rec.updated_at = now
        db.commit()
        db.refresh(rec)

        AuditService.log(
            db=db,
            action=f"DOCUMENT_RENEWAL_{act}",
            user_id=user.id,
            role=user.role,
            reason=reason.strip(),
            details={"validity_id": rec.id, "decision": act, "new_expiry": str(rec.expiry_date)},
            request=request,
        )

        if act == "ACCEPT":
            from backend.app.services.scheduler_service import auto_close_escalations
            auto_close_escalations(db, f"DOC-{rec.id}", "Document renewal accepted")

        return rec

    @classmethod
    def update_lease_fields(
        cls,
        db: Session,
        record_id: int,
        lessor: Optional[str],
        lessee: Optional[str],
        lease_start: Optional[date],
        lease_end: Optional[date],
        property_address: Optional[str],
        user: User,
        request: Optional[Request] = None,
    ) -> DocumentValidityRecord:
        rec = db.query(DocumentValidityRecord).filter(DocumentValidityRecord.id == record_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Validity record not found.")

        rec.is_lease = True
        if lessor is not None:
            rec.lessor = lessor
        if lessee is not None:
            rec.lessee = lessee
        if lease_start is not None:
            rec.lease_start = lease_start
        if lease_end is not None:
            rec.lease_end = lease_end
            rec.expiry_date = lease_end
        if property_address is not None:
            rec.property_address = property_address

        rec.status, rec.days_left = rec.compute_status(date.today())
        rec.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(rec)

        AuditService.log(
            db=db,
            action="LEASE_DETAILS_UPDATED",
            user_id=user.id,
            role=user.role,
            reason="Updated statutory lease registration details",
            details={"validity_id": rec.id, "property_address": property_address},
            request=request,
        )

        return rec

