from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


# -------------------------------------------------------------
# Document Types
# -------------------------------------------------------------

class ExtractionSchemaField(BaseModel):
    key: str
    label: str
    type: str  # text | date | number | id
    required: bool = False


class DocumentTypeBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    issuing_authority: Optional[str] = None
    accepted_formats: List[str] = Field(default_factory=lambda: ["PDF", "JPG", "PNG"])
    max_size_mb: int = 10
    has_expiry: bool = False
    default_validity_months: Optional[int] = None
    verification_method: str = "MANUAL"  # QR | API | PORTAL | DIGITAL_SIGNATURE | MANUAL
    authority_adapter: Optional[str] = None
    statutory_verification_applies: Optional[bool] = False
    extraction_schema: Optional[List[Dict[str, Any]]] = None
    keywords: Optional[List[str]] = None
    is_active: bool = True


class DocumentTypeCreate(DocumentTypeBase):
    pass


class DocumentTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    issuing_authority: Optional[str] = None
    accepted_formats: Optional[List[str]] = None
    max_size_mb: Optional[int] = None
    has_expiry: Optional[bool] = None
    default_validity_months: Optional[int] = None
    verification_method: Optional[str] = None
    authority_adapter: Optional[str] = None
    statutory_verification_applies: Optional[bool] = None
    extraction_schema: Optional[List[Dict[str, Any]]] = None
    keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None


class DocumentTypeOut(DocumentTypeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------
# Application Categories
# -------------------------------------------------------------

class ApplicationCategoryBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ApplicationCategoryCreate(ApplicationCategoryBase):
    pass


class ApplicationCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ApplicationCategoryOut(ApplicationCategoryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------
# Checklist Items
# -------------------------------------------------------------

class ChecklistItemBase(BaseModel):
    document_type_id: int
    ruleset_id: Optional[int] = None
    institute_type: Optional[str] = "ALL"
    min_count: int = 1
    is_mandatory: bool = True
    condition: Optional[Dict[str, Any]] = None
    min_validity_days_remaining: Optional[int] = None
    max_age_days: Optional[int] = None
    display_order: int = 0
    help_text: Optional[str] = None
    is_active: bool = True


class ChecklistItemCreate(ChecklistItemBase):
    pass


class ChecklistItemUpdate(BaseModel):
    document_type_id: Optional[int] = None
    ruleset_id: Optional[int] = None
    institute_type: Optional[str] = None
    min_count: Optional[int] = None
    is_mandatory: Optional[bool] = None
    condition: Optional[Dict[str, Any]] = None
    min_validity_days_remaining: Optional[int] = None
    max_age_days: Optional[int] = None
    display_order: Optional[int] = None
    help_text: Optional[str] = None
    is_active: Optional[bool] = None


class ChecklistItemOut(ChecklistItemBase):
    id: int
    category_id: int
    document_type: Optional[DocumentTypeOut] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChecklistReorderItem(BaseModel):
    item_id: int
    display_order: int


class ChecklistReorderIn(BaseModel):
    items: List[ChecklistReorderItem]


# -------------------------------------------------------------
# Rules & Versions
# -------------------------------------------------------------

class RuleVersionOut(BaseModel):
    id: int
    rule_id: int
    version_no: int
    change_note: Optional[str] = None
    snapshot: Dict[str, Any]
    changed_by: Optional[int] = None
    changed_at: datetime

    class Config:
        from_attributes = True


class RuleBase(BaseModel):
    code: str
    title: str
    description: Optional[str] = None
    handbook_ref: Optional[str] = None
    rule_type: str = "GENERAL"  # INFRASTRUCTURE | FACULTY | LAND | DOCUMENT | FINANCIAL | GENERAL
    severity: str = "MAJOR"     # BLOCKER | MAJOR | MINOR | ADVISORY
    mandatory: bool = True
    applies_to_categories: Optional[List[str]] = None
    definition: Optional[Dict[str, Any]] = None
    ai_checks: Optional[List[str]] = None
    evidence_required: Optional[List[str]] = None
    suggested_action: Optional[str] = None
    status: str = "DRAFT"       # DRAFT | PUBLISHED | ARCHIVED
    is_active: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    expected_version: int  # For optimistic locking
    change_note: Optional[str] = "Updated rule configuration"
    title: Optional[str] = None
    description: Optional[str] = None
    handbook_ref: Optional[str] = None
    rule_type: Optional[str] = None
    severity: Optional[str] = None
    mandatory: Optional[bool] = None
    applies_to_categories: Optional[List[str]] = None
    definition: Optional[Dict[str, Any]] = None
    ai_checks: Optional[List[str]] = None
    evidence_required: Optional[List[str]] = None
    suggested_action: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class RuleCloneIn(BaseModel):
    new_code: str
    new_title: Optional[str] = None


class RuleOut(RuleBase):
    id: int
    current_version: int = 1
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RuleDetailOut(RuleOut):
    versions: List[RuleVersionOut] = Field(default_factory=list)


# -------------------------------------------------------------
# RuleSets
# -------------------------------------------------------------

class RuleSetPublishRequest(BaseModel):
    name: str
    version_label: str


class RuleSetOut(BaseModel):
    id: int
    name: str
    version_label: str
    status: str
    rules_count: int = 0
    published_at: Optional[datetime] = None
    published_by: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------
# Simulation & Validation
# -------------------------------------------------------------

class RuleSimulationRequest(BaseModel):
    definition: Dict[str, Any]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    rule_meta: Optional[Dict[str, Any]] = None
    application_id: Optional[Union[int, str]] = None


class RuleSimulationResponse(BaseModel):
    passed: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    rule_code: str
    rule_title: str
    severity: str
    evaluated_context_summary: Optional[Dict[str, Any]] = None


class DefinitionValidationRequest(BaseModel):
    definition: Dict[str, Any]


class DefinitionValidationResponse(BaseModel):
    valid: bool
    message: str
    depth: int = 0
    errors: List[str] = Field(default_factory=list)


# -------------------------------------------------------------
# Audit Logs, Preview & Diff
# -------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    role: Optional[str] = None
    ip_address: Optional[str] = None
    action: str
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class PublishPreviewOut(BaseModel):
    active_ruleset_name: Optional[str] = None
    active_ruleset_version: Optional[str] = None
    current_active_rules_count: int
    new_rules: List[Dict[str, Any]]
    modified_rules: List[Dict[str, Any]]
    unchanged_rules_count: int
    total_rules_to_publish: int
    total_categories_count: int
    total_checklists_count: int
    total_document_types_count: int


class RuleDiffOut(BaseModel):
    rule_code: str
    version_1: int
    version_2: int
    differences: Dict[str, Dict[str, Any]]


class AdminApplicationOut(BaseModel):
    id: int
    application_id: str
    institute_id: int
    institute_name: Optional[str] = None
    category: str
    academic_year: str
    status: str
    filed_on: Optional[datetime] = None

    class Config:
        from_attributes = True


# -------------------------------------------------------------
# Export / Import Bundle
# -------------------------------------------------------------

class ExportBundle(BaseModel):
    version: str = "1.0"
    exported_at: str
    document_types: List[Dict[str, Any]]
    categories: List[Dict[str, Any]]
    checklists: List[Dict[str, Any]]
    rules: List[Dict[str, Any]]


class ImportBundle(BaseModel):
    document_types: Optional[List[Dict[str, Any]]] = None
    categories: Optional[List[Dict[str, Any]]] = None
    checklists: Optional[List[Dict[str, Any]]] = None
    rules: Optional[List[Dict[str, Any]]] = None
    overwrite_existing: bool = True

