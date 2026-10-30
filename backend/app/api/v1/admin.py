from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.rule import Rule, RuleVersion, RuleSet, RuleChangeRequest
from backend.app.models.document_type import DocumentType
from backend.app.models.application_category import ApplicationCategory
from backend.app.models.checklist_item import ChecklistItem
from backend.app.models.audit_log import AuditLog
from backend.app.services.audit_service import AuditService
from backend.app.services.rule_engine.schemas import RuleDefinition
from backend.app.services.rule_engine.engine import RuleEngine
from backend.app.config import settings
from backend.app.api.deps import require_role
from backend.app.schemas.admin import (
    DocumentTypeCreate,
    DocumentTypeUpdate,
    DocumentTypeOut,
    ApplicationCategoryCreate,
    ApplicationCategoryUpdate,
    ApplicationCategoryOut,
    ChecklistItemCreate,
    ChecklistItemUpdate,
    ChecklistItemOut,
    ChecklistReorderIn,
    RuleCreate,
    RuleUpdate,
    RuleCloneIn,
    RuleOut,
    RuleDetailOut,
    RuleVersionOut,
    RuleSetPublishRequest,
    RuleSetOut,
    RuleSimulationRequest,
    RuleSimulationResponse,
    DefinitionValidationRequest,
    DefinitionValidationResponse,
    ExportBundle,
    ImportBundle,
)

router = APIRouter(prefix="/admin", tags=["admin"])

require_admin = require_role(["ADMIN"])
require_admin_or_reviewer = require_role(["ADMIN", "REVIEWER"])


def _rule_to_dict(rule: Rule) -> Dict[str, Any]:
    return {
        "id": rule.id,
        "code": rule.code,
        "title": rule.title,
        "description": rule.description,
        "handbook_ref": rule.handbook_ref,
        "rule_type": rule.rule_type,
        "severity": rule.severity,
        "mandatory": rule.mandatory,
        "applies_to_categories": rule.applies_to_categories,
        "definition": rule.definition,
        "ai_checks": rule.ai_checks,
        "evidence_required": rule.evidence_required,
        "suggested_action": rule.suggested_action,
        "status": rule.status,
        "current_version": rule.current_version,
        "is_active": rule.is_active,
    }


# =====================================================================
# 1. Document Types CRUD
# =====================================================================

@router.get("/document-types", response_model=List[DocumentTypeOut])
def list_document_types(
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    query = db.query(DocumentType)
    if is_active is not None:
        query = query.filter(DocumentType.is_active == is_active)
    if search:
        s = f"%{search}%"
        query = query.filter((DocumentType.code.ilike(s)) | (DocumentType.name.ilike(s)))
    return query.order_by(DocumentType.code).all()


@router.post("/document-types", response_model=DocumentTypeOut, status_code=status.HTTP_201_CREATED)
def create_document_type(
    payload: DocumentTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(DocumentType).filter(DocumentType.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DocumentType with code '{payload.code.upper()}' already exists.",
        )

    doc_type = DocumentType(
        code=payload.code.upper().strip(),
        name=payload.name.strip(),
        description=payload.description,
        issuing_authority=payload.issuing_authority,
        accepted_formats=payload.accepted_formats,
        max_size_mb=payload.max_size_mb,
        has_expiry=payload.has_expiry,
        default_validity_months=payload.default_validity_months,
        verification_method=payload.verification_method,
        extraction_schema=payload.extraction_schema,
        keywords=payload.keywords,
        is_active=payload.is_active,
    )
    db.add(doc_type)
    db.commit()
    db.refresh(doc_type)

    AuditService.log_event(
        db=db,
        action="CREATE_DOCUMENT_TYPE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Created document type {doc_type.code}",
        details={"after": {"code": doc_type.code, "name": doc_type.name}},
    )
    return doc_type


@router.get("/document-types/{code}", response_model=DocumentTypeOut)
def get_document_type(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    doc_type = db.query(DocumentType).filter(DocumentType.code == code.upper()).first()
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type not found.")
    return doc_type


@router.put("/document-types/{code}", response_model=DocumentTypeOut)
def update_document_type(
    code: str,
    payload: DocumentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    doc_type = db.query(DocumentType).filter(DocumentType.code == code.upper()).first()
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type not found.")

    before = {"code": doc_type.code, "name": doc_type.name, "is_active": doc_type.is_active}
    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(doc_type, field, val)

    db.commit()
    db.refresh(doc_type)

    AuditService.log_event(
        db=db,
        action="UPDATE_DOCUMENT_TYPE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Updated document type {doc_type.code}",
        details={"before": before, "after": update_data},
    )
    return doc_type


@router.delete("/document-types/{code}")
def delete_document_type(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    doc_type = db.query(DocumentType).filter(DocumentType.code == code.upper()).first()
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type not found.")

    doc_type.is_active = False
    db.commit()

    AuditService.log_event(
        db=db,
        action="DEACTIVATE_DOCUMENT_TYPE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Deactivated document type {doc_type.code}",
    )
    return {"message": f"Document type '{code}' deactivated successfully."}


# =====================================================================
# 2. Application Categories CRUD
# =====================================================================

@router.get("/categories", response_model=List[ApplicationCategoryOut])
def list_categories(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    query = db.query(ApplicationCategory)
    if is_active is not None:
        query = query.filter(ApplicationCategory.is_active == is_active)
    return query.order_by(ApplicationCategory.code).all()


@router.post("/categories", response_model=ApplicationCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: ApplicationCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(ApplicationCategory).filter(ApplicationCategory.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with code '{payload.code.upper()}' already exists.",
        )
    cat = ApplicationCategory(
        code=payload.code.upper().strip(),
        name=payload.name.strip(),
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)

    AuditService.log_event(
        db=db,
        action="CREATE_APPLICATION_CATEGORY",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Created category {cat.code}",
    )
    return cat


@router.get("/categories/{code}", response_model=ApplicationCategoryOut)
def get_category(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == code.upper()).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return cat


@router.put("/categories/{code}", response_model=ApplicationCategoryOut)
def update_category(
    code: str,
    payload: ApplicationCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == code.upper()).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(cat, field, val)

    db.commit()
    db.refresh(cat)
    return cat


# =====================================================================
# 3. Checklists CRUD
# =====================================================================

@router.get("/checklists/{category_code}", response_model=List[ChecklistItemOut])
def get_category_checklist(
    category_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == category_code.upper()).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    items = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.category_id == cat.id)
        .order_by(ChecklistItem.display_order.asc(), ChecklistItem.id.asc())
        .all()
    )
    return items


@router.post("/checklists/{category_code}/items", response_model=ChecklistItemOut, status_code=status.HTTP_201_CREATED)
def add_checklist_item(
    category_code: str,
    payload: ChecklistItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cat = db.query(ApplicationCategory).filter(ApplicationCategory.code == category_code.upper()).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    doc_type = db.query(DocumentType).filter(DocumentType.id == payload.document_type_id).first()
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document type not found.")

    item = ChecklistItem(
        category_id=cat.id,
        document_type_id=payload.document_type_id,
        is_mandatory=payload.is_mandatory,
        condition=payload.condition,
        min_validity_days_remaining=payload.min_validity_days_remaining,
        max_age_days=payload.max_age_days,
        display_order=payload.display_order,
        help_text=payload.help_text,
        is_active=payload.is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    AuditService.log_event(
        db=db,
        action="ADD_CHECKLIST_ITEM",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Added checklist item {item.id} for {cat.code}",
        details={"category": cat.code, "document_type": doc_type.code},
    )
    return item


@router.put("/checklists/{category_code}/items/{item_id}", response_model=ChecklistItemOut)
def update_checklist_item(
    category_code: str,
    item_id: int,
    payload: ChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found.")

    update_data = payload.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(item, field, val)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/checklists/{category_code}/items/{item_id}")
def delete_checklist_item(
    category_code: str,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found.")

    db.delete(item)
    db.commit()
    return {"message": "Checklist item deleted successfully."}


@router.post("/checklists/{category_code}/reorder")
def reorder_checklist_items(
    category_code: str,
    payload: ChecklistReorderIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    for item_order in payload.items:
        db.query(ChecklistItem).filter(ChecklistItem.id == item_order.item_id).update(
            {"display_order": item_order.display_order}
        )
    db.commit()
    return {"message": "Checklist items reordered successfully."}


# =====================================================================
# 4. Rules CRUD, Optimistic Concurrency, Simulation & Validation
# =====================================================================

@router.get("/rules", response_model=List[RuleOut])
def list_rules(
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    severity: Optional[str] = None,
    rule_type: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    query = db.query(Rule)
    if is_active is not None:
        query = query.filter(Rule.is_active == is_active)
    if status_filter:
        query = query.filter(Rule.status == status_filter.upper())
    if severity:
        query = query.filter(Rule.severity == severity.upper())
    if rule_type:
        query = query.filter(Rule.rule_type == rule_type.upper())
    if search:
        s = f"%{search}%"
        query = query.filter((Rule.rule_code.ilike(s)) | (Rule.title.ilike(s)) | (Rule.description.ilike(s)))

    rules = query.order_by(Rule.rule_code.asc()).all()
    if category:
        cat_upper = category.upper()
        rules = [
            r for r in rules
            if not r.applies_to_categories or cat_upper in r.applies_to_categories
        ]
    return rules


@router.post("/rules", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Check uniqueness
    rule_code = payload.code.strip()
    existing = db.query(Rule).filter(Rule.rule_code == rule_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule with code '{rule_code}' already exists.",
        )

    # Validate definition if provided
    if payload.definition:
        try:
            parsed = RuleDefinition.model_validate(payload.definition)
            depth = parsed.calculate_depth()
            if depth > 6:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Condition nesting depth {depth} exceeds max allowed limit of 6.",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid rule definition schema: {str(e)}",
            )

    rule = Rule(
        code=rule_code,
        rule_code=rule_code,
        category=payload.applies_to_categories[0] if payload.applies_to_categories else "General",
        title=payload.title.strip(),
        description=payload.description or "",
        handbook_ref=payload.handbook_ref or "",
        handbook_reference=payload.handbook_ref or "",
        rule_type=payload.rule_type.upper(),
        severity=payload.severity.upper(),
        mandatory=payload.mandatory,
        is_mandatory=payload.mandatory,
        applies_to_categories=payload.applies_to_categories or [],
        definition=payload.definition,
        ai_checks=payload.ai_checks or [],
        evidence_required=payload.evidence_required or [],
        suggested_action=payload.suggested_action,
        status=payload.status.upper() if payload.status else "DRAFT",
        current_version=1,
        is_active=payload.is_active,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    AuditService.log_event(
        db=db,
        action="CREATE_RULE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Created rule {rule.code}",
        details={"after": _rule_to_dict(rule)},
    )
    return rule


@router.get("/rules/{code}", response_model=RuleDetailOut)
def get_rule_detail(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    rule = db.query(Rule).filter(Rule.rule_code == code).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    versions = (
        db.query(RuleVersion)
        .filter(RuleVersion.rule_id == rule.id)
        .order_by(RuleVersion.version_no.desc())
        .all()
    )

    rule_dict = _rule_to_dict(rule)
    rule_dict["id"] = rule.id
    rule_dict["created_at"] = rule.created_at
    rule_dict["updated_at"] = rule.updated_at
    rule_dict["created_by"] = rule.created_by
    rule_dict["updated_by"] = rule.updated_by
    rule_dict["versions"] = versions
    return rule_dict


@router.put("/rules/{code}", response_model=RuleOut)
def update_rule(
    code: str,
    payload: RuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rule = db.query(Rule).filter(Rule.rule_code == code).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    # 1. Optimistic Concurrency Check
    if rule.current_version != payload.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Version conflict on rule '{code}': expected version {payload.expected_version}, "
                f"but current version is {rule.current_version}. Please refresh and reapply changes."
            ),
        )

    # 2. Validate definition if modified
    if payload.definition is not None:
        try:
            parsed = RuleDefinition.model_validate(payload.definition)
            depth = parsed.calculate_depth()
            if depth > 6:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Condition nesting depth {depth} exceeds max allowed limit of 6.",
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid rule definition schema: {str(e)}",
            )

    # 3. Snapshot prior version to RuleVersion table
    prior_state = _rule_to_dict(rule)
    version_record = RuleVersion(
        rule_id=rule.id,
        version_no=rule.current_version,
        change_note=payload.change_note or f"Updated to version {rule.current_version + 1}",
        snapshot=prior_state,
        changed_by=current_user.id,
        changed_at=datetime.utcnow(),
    )
    db.add(version_record)

    # 4. Apply updates
    fields_to_update = [
        "title", "description", "handbook_ref", "rule_type",
        "severity", "mandatory", "applies_to_categories",
        "definition", "ai_checks", "evidence_required",
        "suggested_action", "status", "is_active",
    ]
    for f in fields_to_update:
        val = getattr(payload, f)
        if val is not None:
            if f in ["rule_type", "severity", "status"] and isinstance(val, str):
                setattr(rule, f, val.upper())
            else:
                setattr(rule, f, val)

    rule.current_version += 1
    rule.updated_by = current_user.id
    if payload.handbook_ref is not None:
        rule.handbook_reference = payload.handbook_ref
    if payload.mandatory is not None:
        rule.is_mandatory = payload.mandatory

    db.commit()
    db.refresh(rule)

    # 5. Audit log with before/after state
    new_state = _rule_to_dict(rule)
    AuditService.log_event(
        db=db,
        action="UPDATE_RULE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Updated rule {rule.code} to version {rule.current_version}",
        details={"before": prior_state, "after": new_state},
    )

    return rule


@router.delete("/rules/{code}")
def deactivate_or_archive_rule(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rule = db.query(Rule).filter(Rule.rule_code == code).first()
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    prior_state = _rule_to_dict(rule)
    rule.is_active = False
    rule.status = "ARCHIVED"
    rule.updated_by = current_user.id
    db.commit()

    AuditService.log_event(
        db=db,
        action="ARCHIVE_RULE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Archived rule {rule.code}",
        details={"before": prior_state, "after": {"is_active": False, "status": "ARCHIVED"}},
    )
    return {"message": f"Rule '{code}' archived successfully."}


@router.post("/rules/{code}/clone", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def clone_rule(
    code: str,
    payload: RuleCloneIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    source = db.query(Rule).filter(Rule.rule_code == code).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source rule not found.")

    existing = db.query(Rule).filter(Rule.rule_code == payload.new_code.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target rule code '{payload.new_code.strip()}' already exists.",
        )

    cloned = Rule(
        code=payload.new_code.strip(),
        rule_code=payload.new_code.strip(),
        category=source.category,
        title=payload.new_title or f"Copy of {source.title}",
        description=source.description,
        handbook_ref=source.handbook_ref,
        handbook_reference=source.handbook_reference,
        rule_type=source.rule_type,
        severity=source.severity,
        mandatory=source.mandatory,
        is_mandatory=source.is_mandatory,
        applies_to_categories=source.applies_to_categories,
        definition=source.definition,
        ai_checks=source.ai_checks,
        evidence_required=source.evidence_required,
        suggested_action=source.suggested_action,
        status="DRAFT",
        current_version=1,
        is_active=True,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(cloned)
    db.commit()
    db.refresh(cloned)

    AuditService.log_event(
        db=db,
        action="CLONE_RULE",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Cloned rule {source.code} to {cloned.code}",
        details={"source_code": source.code, "cloned_code": cloned.code},
    )
    return cloned


@router.post("/rules/simulate", response_model=RuleSimulationResponse)
def simulate_rule(
    payload: RuleSimulationRequest,
    current_user: User = Depends(require_admin_or_reviewer),
):
    finding = RuleEngine.simulate(
        definition=payload.definition,
        context_data=payload.context,
        rule_meta=payload.rule_meta,
    )
    return RuleSimulationResponse(
        passed=finding.passed,
        message=finding.message,
        details=finding.details,
        rule_code=finding.rule_code,
        rule_title=finding.rule_title,
        severity=finding.severity,
    )


@router.post("/rules/validate-definition", response_model=DefinitionValidationResponse)
def validate_definition(
    payload: DefinitionValidationRequest,
    current_user: User = Depends(require_admin_or_reviewer),
):
    try:
        parsed = RuleDefinition.model_validate(payload.definition)
        depth = parsed.calculate_depth()
        if depth > 6:
            return DefinitionValidationResponse(
                valid=False,
                message=f"Condition nesting depth {depth} exceeds maximum limit of 6.",
                depth=depth,
                errors=["DepthExceeded"],
            )
        return DefinitionValidationResponse(
            valid=True,
            message="Rule definition is valid.",
            depth=depth,
            errors=[],
        )
    except Exception as e:
        return DefinitionValidationResponse(
            valid=False,
            message=str(e),
            depth=0,
            errors=[str(e)],
        )


# =====================================================================
# 5. RuleSet Publishing & Rollback
# =====================================================================

@router.get("/rulesets", response_model=List[RuleSetOut])
def list_rulesets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    rulesets = db.query(RuleSet).order_by(RuleSet.id.desc()).all()
    results = []
    for rs in rulesets:
        count = 0
        if rs.snapshot and isinstance(rs.snapshot, dict):
            count = len(rs.snapshot.get("rules", []))
        results.append(
            RuleSetOut(
                id=rs.id,
                name=rs.name,
                version_label=rs.version_label,
                status=rs.status,
                rules_count=count,
                published_at=rs.published_at,
                published_by=rs.published_by,
                created_at=rs.created_at,
            )
        )
    return results


@router.post("/rulesets/publish", response_model=RuleSetOut)
def publish_ruleset(
    payload: RuleSetPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Fetch all active published rules
    active_rules = db.query(Rule).filter(Rule.is_active == True, Rule.status == "PUBLISHED").all()
    if not active_rules:
        # If no published rules, allow draft rules to be marked published or published as is
        active_rules = db.query(Rule).filter(Rule.is_active == True).all()

    doc_types = db.query(DocumentType).filter(DocumentType.is_active == True).all()
    categories = db.query(ApplicationCategory).filter(ApplicationCategory.is_active == True).all()
    checklist_items = db.query(ChecklistItem).filter(ChecklistItem.is_active == True).all()

    snapshot = {
        "published_at": datetime.utcnow().isoformat() + "Z",
        "published_by": current_user.email,
        "rules": [_rule_to_dict(r) for r in active_rules],
        "document_types": [
            {
                "id": dt.id,
                "code": dt.code,
                "name": dt.name,
                "issuing_authority": dt.issuing_authority,
                "has_expiry": dt.has_expiry,
                "verification_method": dt.verification_method,
            }
            for dt in doc_types
        ],
        "categories": [{"id": c.id, "code": c.code, "name": c.name} for c in categories],
        "checklists": [
            {
                "id": ci.id,
                "category_id": ci.category_id,
                "document_type_id": ci.document_type_id,
                "is_mandatory": ci.is_mandatory,
                "display_order": ci.display_order,
            }
            for ci in checklist_items
        ],
    }

    # Archive previous active rulesets
    db.query(RuleSet).filter(RuleSet.status == "ACTIVE").update({"status": "ARCHIVED"})

    new_ruleset = RuleSet(
        name=payload.name.strip(),
        version_label=payload.version_label.strip(),
        status="ACTIVE",
        snapshot=snapshot,
        published_at=datetime.utcnow(),
        published_by=current_user.id,
    )
    db.add(new_ruleset)
    db.commit()
    db.refresh(new_ruleset)

    AuditService.log_event(
        db=db,
        action="PUBLISH_RULESET",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Published ruleset {new_ruleset.name} ({new_ruleset.version_label})",
        details={"name": new_ruleset.name, "version_label": new_ruleset.version_label, "rules_count": len(active_rules)},
    )

    return RuleSetOut(
        id=new_ruleset.id,
        name=new_ruleset.name,
        version_label=new_ruleset.version_label,
        status=new_ruleset.status,
        rules_count=len(active_rules),
        published_at=new_ruleset.published_at,
        published_by=new_ruleset.published_by,
        created_at=new_ruleset.created_at,
    )


@router.post("/rulesets/{ruleset_id}/rollback")
def rollback_to_ruleset(
    ruleset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    target_ruleset = db.query(RuleSet).filter(RuleSet.id == ruleset_id).first()
    if not target_ruleset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RuleSet not found.")

    snapshot = target_ruleset.snapshot or {}
    rules_snapshot = snapshot.get("rules", [])
    if not rules_snapshot:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RuleSet has empty snapshot.")

    # Mark other active rulesets archived
    db.query(RuleSet).filter(RuleSet.status == "ACTIVE").update({"status": "ARCHIVED"})
    target_ruleset.status = "ACTIVE"

    # Restore rules from snapshot
    restored_count = 0
    for r_data in rules_snapshot:
        code = r_data.get("code")
        rule = db.query(Rule).filter(Rule.code == code).first()
        if rule:
            rule.title = r_data.get("title", rule.title)
            rule.description = r_data.get("description", rule.description)
            rule.handbook_ref = r_data.get("handbook_ref", rule.handbook_ref)
            rule.rule_type = r_data.get("rule_type", rule.rule_type)
            rule.severity = r_data.get("severity", rule.severity)
            rule.mandatory = r_data.get("mandatory", rule.mandatory)
            rule.applies_to_categories = r_data.get("applies_to_categories", rule.applies_to_categories)
            rule.definition = r_data.get("definition", rule.definition)
            rule.suggested_action = r_data.get("suggested_action", rule.suggested_action)
            rule.status = r_data.get("status", "PUBLISHED")
            rule.is_active = True
            rule.current_version += 1
            rule.updated_by = current_user.id
            restored_count += 1

    db.commit()

    AuditService.log_event(
        db=db,
        action="ROLLBACK_RULESET",
        user_id=current_user.id,
        role=current_user.role,
        reason=f"Rolled back to ruleset {target_ruleset.name}",
        details={"name": target_ruleset.name, "restored_rules": restored_count},
    )

    return {
        "message": f"Successfully rolled back to RuleSet '{target_ruleset.name}' ({target_ruleset.version_label}).",
        "restored_rules": restored_count,
    }


# =====================================================================
# 6. Configuration Export & Import
# =====================================================================

@router.get("/export", response_model=ExportBundle)
def export_configuration(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer),
):
    doc_types = db.query(DocumentType).all()
    categories = db.query(ApplicationCategory).all()
    checklists = db.query(ChecklistItem).all()
    rules = db.query(Rule).all()

    return ExportBundle(
        version="1.0",
        exported_at=datetime.utcnow().isoformat() + "Z",
        document_types=[
            {
                "code": dt.code,
                "name": dt.name,
                "description": dt.description,
                "issuing_authority": dt.issuing_authority,
                "accepted_formats": dt.accepted_formats,
                "max_size_mb": dt.max_size_mb,
                "has_expiry": dt.has_expiry,
                "default_validity_months": dt.default_validity_months,
                "verification_method": dt.verification_method,
                "extraction_schema": dt.extraction_schema,
                "keywords": dt.keywords,
                "is_active": dt.is_active,
            }
            for dt in doc_types
        ],
        categories=[
            {
                "code": c.code,
                "name": c.name,
                "description": c.description,
                "is_active": c.is_active,
            }
            for c in categories
        ],
        checklists=[
            {
                "category_code": ci.category.code if ci.category else None,
                "document_type_code": ci.document_type.code if ci.document_type else None,
                "is_mandatory": ci.is_mandatory,
                "condition": ci.condition,
                "min_validity_days_remaining": ci.min_validity_days_remaining,
                "max_age_days": ci.max_age_days,
                "display_order": ci.display_order,
                "help_text": ci.help_text,
                "is_active": ci.is_active,
            }
            for ci in checklists
        ],
        rules=[_rule_to_dict(r) for r in rules],
    )


@router.post("/import")
def import_configuration(
    bundle: ImportBundle,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    imported_counts = {"document_types": 0, "categories": 0, "checklists": 0, "rules": 0}

    # 1. Document Types
    if bundle.document_types:
        for dt_data in bundle.document_types:
            code = dt_data.get("code", "").upper().strip()
            if not code:
                continue
            existing = db.query(DocumentType).filter(DocumentType.code == code).first()
            if existing and bundle.overwrite_existing:
                for k, v in dt_data.items():
                    setattr(existing, k, v)
                imported_counts["document_types"] += 1
            elif not existing:
                new_dt = DocumentType(**dt_data)
                db.add(new_dt)
                imported_counts["document_types"] += 1
        db.commit()

    # 2. Categories
    if bundle.categories:
        for cat_data in bundle.categories:
            code = cat_data.get("code", "").upper().strip()
            if not code:
                continue
            existing = db.query(ApplicationCategory).filter(ApplicationCategory.code == code).first()
            if existing and bundle.overwrite_existing:
                for k, v in cat_data.items():
                    setattr(existing, k, v)
                imported_counts["categories"] += 1
            elif not existing:
                new_cat = ApplicationCategory(**cat_data)
                db.add(new_cat)
                imported_counts["categories"] += 1
        db.commit()

    # 3. Rules
    if bundle.rules:
        for r_data in bundle.rules:
            code = r_data.get("code", "").strip()
            if not code:
                continue
            clean_data = {k: v for k, v in r_data.items() if k not in ["id", "created_at", "updated_at"]}
            existing = db.query(Rule).filter(Rule.code == code).first()
            if existing and bundle.overwrite_existing:
                for k, v in clean_data.items():
                    setattr(existing, k, v)
                existing.current_version += 1
                existing.updated_by = current_user.id
                imported_counts["rules"] += 1
            elif not existing:
                new_rule = Rule(**clean_data)
                new_rule.created_by = current_user.id
                new_rule.updated_by = current_user.id
                db.add(new_rule)
                imported_counts["rules"] += 1
        db.commit()

    AuditService.log_event(
        db=db,
        action="IMPORT_CONFIGURATION",
        user_id=current_user.id,
        role=current_user.role,
        reason="Imported configuration bundle",
        details=imported_counts,
    )

    return {"message": "Configuration bundle imported successfully.", "counts": imported_counts}
