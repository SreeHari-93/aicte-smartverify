from datetime import date, datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.application import Application
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.rule import RuleSet


class FieldProblem(BaseModel):
    document_id: Optional[int] = None
    document_type: str
    page_no: int = 1
    field_key: str
    problem: str
    value: Optional[str] = None


class DuplicateWarning(BaseModel):
    document_id: int
    document_type: Optional[str] = None
    original_filename: str
    duplicate_with_id: int
    duplicate_type: Optional[str] = None
    duplicate_filename: str
    application_id: Optional[int] = None
    institute_id: int
    sha256_hash: str
    message: str


class ChecklistItemReadiness(BaseModel):
    checklist_item_id: int
    document_type_code: str
    document_type_name: str
    is_mandatory: bool
    status: str  # MISSING | UPLOADED | PROCESSING | EXPIRED | EXPIRING_SOON | INCOMPLETE_FIELDS | NEEDS_REVIEW | READY
    document_id: Optional[int] = None
    document_filename: Optional[str] = None
    min_validity_days_remaining: Optional[int] = None
    days_remaining: Optional[int] = None
    expiry_date: Optional[str] = None
    is_duplicate: bool = False
    duplicate_with_id: Optional[int] = None
    help_text: Optional[str] = None


class ApplicationReadinessResult(BaseModel):
    application_id: int
    application_number: str
    category: str
    ruleset_name: str = "APH 2026-27"
    ruleset_version: str = "v1.0"
    readiness_percentage: float = 0.0
    status: str = "INCOMPLETE"  # READY | INCOMPLETE
    total_items: int = 0
    ready_items: int = 0
    missing_items: List[str] = Field(default_factory=list)
    items: List[ChecklistItemReadiness] = Field(default_factory=list)
    field_problems: List[FieldProblem] = Field(default_factory=list)
    duplicates: List[DuplicateWarning] = Field(default_factory=list)


class ReadinessService:
    """
    Evaluates application readiness against the published RuleSet checklist.
    Computes checklist item statuses (MISSING, UPLOADED, PROCESSING, EXPIRED,
    EXPIRING_SOON, INCOMPLETE_FIELDS, NEEDS_REVIEW, READY), flags SHA-256 duplicate uploads,
    and isolates specific field issues.
    """

    @classmethod
    def evaluate_application(
        cls, db: Session, application: Application
    ) -> ApplicationReadinessResult:
        today = date.today()

        # 1. Resolve Application Category
        cat_code = (application.category or "EOA").upper().strip()
        # Handle variations like "Extension of Approval (EoA)"
        if "EOA" in cat_code or "EXTENSION" in cat_code:
            cat_code = "EOA"
        elif "NAME" in cat_code:
            cat_code = "CHANGE_OF_NAME"
        elif "INTAKE" in cat_code:
            cat_code = "INTAKE_CHANGE"
        elif "CLOSURE" in cat_code or "MERGER" in cat_code:
            cat_code = "CLOSURE_MERGER"

        category = (
            db.query(ApplicationCategory)
            .filter(ApplicationCategory.code == cat_code)
            .first()
        )
        if not category:
            category = db.query(ApplicationCategory).first()

        # 2. Retrieve Published RuleSet metadata if available
        ruleset = (
            db.query(RuleSet)
            .filter(RuleSet.status.in_(["PUBLISHED", "ACTIVE"]))
            .order_by(RuleSet.id.desc())
            .first()
        )
        rs_name = ruleset.name if ruleset else "APH 2026-27"
        rs_version = ruleset.version_label if ruleset else "v1.0"

        # 3. Retrieve Checklist Items for this category
        checklist_items = []
        if category:
            checklist_items = (
                db.query(ChecklistItem)
                .filter(
                    ChecklistItem.category_id == category.id,
                    ChecklistItem.is_active == True,
                )
                .order_by(ChecklistItem.display_order.asc())
                .all()
            )

        # Fallback if no checklist items found for category
        if not checklist_items:
            checklist_items = (
                db.query(ChecklistItem)
                .filter(ChecklistItem.is_active == True)
                .order_by(ChecklistItem.display_order.asc())
                .limit(6)
                .all()
            )

        # 4. Fetch all Documents for this Application and Institute
        app_docs = (
            db.query(Document)
            .filter(Document.application_id == application.id)
            .all()
        )
        inst_docs = (
            db.query(Document)
            .filter(Document.institute_id == application.institute_id)
            .all()
        )

        # 5. Check Duplicates across Application Documents
        duplicate_warnings: List[DuplicateWarning] = []
        app_doc_hashes = {d.id: d.sha256_hash for d in app_docs if d.sha256_hash}
        doc_duplicate_map: Dict[int, int] = {}

        for doc in app_docs:
            if not doc.sha256_hash:
                continue

            # Check if same hash exists in other documents
            dup = (
                db.query(Document)
                .filter(
                    Document.sha256_hash == doc.sha256_hash,
                    Document.id != doc.id,
                )
                .first()
            )
            if dup:
                doc_duplicate_map[doc.id] = dup.id
                duplicate_warnings.append(
                    DuplicateWarning(
                        document_id=doc.id,
                        document_type=doc.document_type_code,
                        original_filename=doc.original_filename,
                        duplicate_with_id=dup.id,
                        duplicate_type=dup.document_type_code,
                        duplicate_filename=dup.original_filename,
                        application_id=dup.application_id,
                        institute_id=dup.institute_id,
                        sha256_hash=doc.sha256_hash,
                        message=f"Preliminary Indicator: Document #{doc.id} ({doc.original_filename}) shares identical SHA-256 hash with Document #{dup.id} ({dup.original_filename}).",
                    )
                )

        # 6. Evaluate Each Checklist Item
        item_results: List[ChecklistItemReadiness] = []
        field_problems: List[FieldProblem] = []
        missing_item_names: List[str] = []

        mandatory_count = 0
        ready_mandatory_count = 0

        for ci in checklist_items:
            dt: DocumentType = ci.document_type
            if not dt:
                continue

            if ci.is_mandatory:
                mandatory_count += 1

            # Match document for this checklist item
            # Preference: 1) uploaded specifically under application, 2) uploaded under institute
            matched_doc = next(
                (d for d in app_docs if (d.document_type_id == dt.id or (d.document_type_code and d.document_type_code.upper() == dt.code.upper()))),
                None,
            )
            if not matched_doc:
                matched_doc = next(
                    (d for d in inst_docs if (d.document_type_id == dt.id or (d.document_type_code and d.document_type_code.upper() == dt.code.upper()))),
                    None,
                )

            # Determine State
            if not matched_doc:
                item_status = "MISSING"
                missing_item_names.append(dt.name)
                item_results.append(
                    ChecklistItemReadiness(
                        checklist_item_id=ci.id,
                        document_type_code=dt.code,
                        document_type_name=dt.name,
                        is_mandatory=ci.is_mandatory,
                        status=item_status,
                        document_id=None,
                        document_filename=None,
                        min_validity_days_remaining=ci.min_validity_days_remaining,
                        help_text=ci.help_text,
                    )
                )
                continue

            # Document uploaded -> evaluate OCR and content
            doc_id = matched_doc.id
            is_dup = doc_id in doc_duplicate_map
            dup_id = doc_duplicate_map.get(doc_id)

            ocr_st = (matched_doc.ocr_status or "PENDING").upper()
            ext_data = matched_doc.extracted_data or {}
            exp_date_str = ext_data.get("expiry_date")
            days_rem = ext_data.get("days_remaining")
            is_exp = ext_data.get("is_expired")

            if ocr_st == "PENDING":
                item_status = "UPLOADED"
            elif ocr_st == "PROCESSING":
                item_status = "PROCESSING"
            elif ocr_st in ["FAILED", "MANUAL"]:
                item_status = "NEEDS_REVIEW"
                field_problems.append(
                    FieldProblem(
                        document_id=doc_id,
                        document_type=dt.code,
                        page_no=1,
                        field_key="ocr",
                        problem=matched_doc.error_message or "OCR extraction flagged for manual verification",
                        value=ocr_st,
                    )
                )
            else:
                # OCR status == "DONE"
                item_status = "READY"

                # A. Expiry Check
                if is_exp is True or (days_rem is not None and days_rem < 0):
                    item_status = "EXPIRED"
                    field_problems.append(
                        FieldProblem(
                            document_id=doc_id,
                            document_type=dt.code,
                            page_no=1,
                            field_key="valid_upto",
                            problem=f"Certificate expired on {exp_date_str or 'past date'} ({abs(days_rem or 0)} days overdue)",
                            value=exp_date_str,
                        )
                    )
                elif days_rem is not None:
                    min_days = ci.min_validity_days_remaining or 30
                    if days_rem <= min_days:
                        item_status = "EXPIRING_SOON"
                        field_problems.append(
                            FieldProblem(
                                document_id=doc_id,
                                document_type=dt.code,
                                page_no=1,
                                field_key="valid_upto",
                                problem=f"Expiring soon: only {days_rem} days remaining (minimum required: {min_days} days)",
                                value=exp_date_str,
                            )
                        )

                # B. Incomplete Required Fields Check
                if item_status not in ["EXPIRED", "EXPIRING_SOON"]:
                    schema = dt.extraction_schema or []
                    extracted_fields = (
                        db.query(ExtractedField)
                        .filter(ExtractedField.document_id == doc_id)
                        .all()
                    )
                    fields_by_key = {f.key: f for f in extracted_fields}

                    for req_item in schema:
                        if req_item.get("required"):
                            f_key = req_item.get("key")
                            f_record = fields_by_key.get(f_key)
                            val = None
                            if f_record:
                                val = f_record.corrected_value or f_record.normalized_value or f_record.value

                            if not val or not str(val).strip():
                                item_status = "INCOMPLETE_FIELDS"
                                field_problems.append(
                                    FieldProblem(
                                        document_id=doc_id,
                                        document_type=dt.code,
                                        page_no=1,
                                        field_key=f_key,
                                        problem=f"Mandatory field '{req_item.get('label', f_key)}' was not detected in document",
                                        value=None,
                                    )
                                )

                # C. Needs Review / Mismatch Check
                if item_status == "READY":
                    cls_info = ext_data.get("classification") or {}
                    has_mismatch = (
                        bool(cls_info.get("mismatch_flag"))
                        or bool(matched_doc.classification and matched_doc.classification.mismatch_flag)
                    )
                    if has_mismatch:
                        item_status = "NEEDS_REVIEW"
                        warning_msg = (
                            cls_info.get("warning_message")
                            or (matched_doc.classification.warning_message if matched_doc.classification else None)
                            or "Document type mismatch warning"
                        )
                        pred_type = (
                            cls_info.get("predicted_type")
                            or (matched_doc.classification.predicted_type if matched_doc.classification else None)
                        )
                        field_problems.append(
                            FieldProblem(
                                document_id=doc_id,
                                document_type=dt.code,
                                page_no=1,
                                field_key="classification",
                                problem=warning_msg,
                                value=pred_type,
                            )
                        )
                    else:
                        unverified_review = any(
                            (f.needs_review and not f.verified_by_user)
                            for f in (matched_doc.extracted_fields or [])
                        )
                        if unverified_review:
                            item_status = "NEEDS_REVIEW"

            if item_status == "READY" and ci.is_mandatory:
                ready_mandatory_count += 1

            item_results.append(
                ChecklistItemReadiness(
                    checklist_item_id=ci.id,
                    document_type_code=dt.code,
                    document_type_name=dt.name,
                    is_mandatory=ci.is_mandatory,
                    status=item_status,
                    document_id=doc_id,
                    document_filename=matched_doc.original_filename,
                    min_validity_days_remaining=ci.min_validity_days_remaining,
                    days_remaining=days_rem,
                    expiry_date=exp_date_str,
                    is_duplicate=is_dup,
                    duplicate_with_id=dup_id,
                    help_text=ci.help_text,
                )
            )

        # 7. Compute Overall Readiness Percentage
        if mandatory_count > 0:
            readiness_pct = round((ready_mandatory_count / mandatory_count) * 100.0, 1)
        elif item_results:
            ready_all = sum(1 for i in item_results if i.status == "READY")
            readiness_pct = round((ready_all / len(item_results)) * 100.0, 1)
        else:
            readiness_pct = 100.0

        overall_status = "READY" if readiness_pct >= 100.0 else "INCOMPLETE"

        return ApplicationReadinessResult(
            application_id=application.id,
            application_number=application.application_id,
            category=category.name if category else application.category,
            ruleset_name=rs_name,
            ruleset_version=rs_version,
            readiness_percentage=readiness_pct,
            status=overall_status,
            total_items=len(item_results),
            ready_items=sum(1 for i in item_results if i.status == "READY"),
            missing_items=missing_item_names,
            items=item_results,
            field_problems=field_problems,
            duplicates=duplicate_warnings,
        )

    @classmethod
    def get_all_duplicates(cls, db: Session) -> List[DuplicateWarning]:
        """Finds all document duplicates across the entire system by SHA-256 hash"""
        # Find hashes appearing more than once
        dup_hashes = (
            db.query(Document.sha256_hash)
            .filter(Document.sha256_hash.isnot(None))
            .group_by(Document.sha256_hash)
            .having(func.count(Document.id) > 1)
            .all()
        )
        hash_list = [h[0] for h in dup_hashes]

        if not hash_list:
            return []

        docs = (
            db.query(Document)
            .filter(Document.sha256_hash.in_(hash_list))
            .order_by(Document.sha256_hash.asc(), Document.id.asc())
            .all()
        )

        duplicates: List[DuplicateWarning] = []
        by_hash: Dict[str, List[Document]] = {}
        for d in docs:
            by_hash.setdefault(d.sha256_hash, []).append(d)

        for h, doc_group in by_hash.items():
            first = doc_group[0]
            for other in doc_group[1:]:
                duplicates.append(
                    DuplicateWarning(
                        document_id=other.id,
                        document_type=other.document_type_code,
                        original_filename=other.original_filename,
                        duplicate_with_id=first.id,
                        duplicate_type=first.document_type_code,
                        duplicate_filename=first.original_filename,
                        application_id=other.application_id,
                        institute_id=other.institute_id,
                        sha256_hash=h,
                        message=f"Duplicate content detected: Document #{other.id} ({other.original_filename}) has same SHA-256 as Document #{first.id} ({first.original_filename})",
                    )
                )

        return duplicates
