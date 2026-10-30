from typing import List, Optional, Union, Dict, Any, Literal
from pydantic import BaseModel, Field, RootModel, model_validator
from typing_extensions import Annotated


# Base for all rule definitions
class BaseRuleDef(BaseModel):
    class Config:
        extra = "allow"


class DocumentRequiredDef(BaseRuleDef):
    type: Literal["DOCUMENT_REQUIRED"]
    document: str = Field(..., description="Document type code, e.g. FIRE_NOC")
    min_validity_days: Optional[int] = Field(0, description="Minimum days from today before certificate expires")


class FieldRequiredDef(BaseRuleDef):
    type: Literal["FIELD_REQUIRED"]
    field: str = Field(..., description="Path to required field, e.g. application.intake_total")


class ValidityPeriodDef(BaseRuleDef):
    type: Literal["VALIDITY_PERIOD"]
    document: str = Field(..., description="Document type code, e.g. NBA_CERT")
    must_be_valid_on: str = Field("today", description="Date path or 'today', e.g. application.submission_date")
    buffer_days: Optional[int] = Field(0, description="Grace or required buffer days remaining")


class CrossFieldMatchDef(BaseRuleDef):
    type: Literal["CROSS_FIELD_MATCH"]
    left: str = Field(..., description="Path to left value, e.g. doc.AFFIDAVIT.institute_name")
    right: str = Field(..., description="Path to right value, e.g. institute.name")
    match: Optional[str] = "EXACT"
    fuzzy: Optional[bool] = False
    threshold: Optional[float] = Field(0.8, ge=0.0, le=1.0, description="Fuzzy match threshold between 0.0 and 1.0")


class NumericThresholdDef(BaseRuleDef):
    type: Literal["NUMERIC_THRESHOLD"]
    field: Optional[str] = None
    value: Optional[Union[str, float, int]] = None
    operator: Literal["==", "!=", ">", ">=", "<", "<="]
    target: Optional[float] = None

    @model_validator(mode="before")
    def normalize_fields(cls, data: Any):
        if isinstance(data, dict):
            # If 'field' is path and 'value' is numeric target
            if "field" in data and "value" in data and isinstance(data["value"], (int, float)):
                data["target"] = float(data["value"])
            elif "field" in data and "value" not in data:
                data["value"] = data["field"]
            elif "value" in data and "field" not in data and isinstance(data["value"], str):
                data["field"] = data["value"]
            elif "value" in data and isinstance(data["value"], (int, float)) and "target" not in data:
                data["target"] = float(data["value"])
        return data


class CountAtLeastDef(BaseRuleDef):
    type: Literal["COUNT_AT_LEAST"]
    source: Optional[str] = None
    collection: Optional[str] = None
    field: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    filter: Optional[Dict[str, Any]] = None
    min: Optional[int] = None
    min_count: Optional[int] = None

    @model_validator(mode="before")
    def normalize_count_fields(cls, data: Any):
        if isinstance(data, dict):
            if "collection" in data and "source" not in data:
                data["source"] = data["collection"]
            elif "source" in data and "collection" not in data:
                data["collection"] = data["source"]
            if "min_count" in data and "min" not in data:
                data["min"] = data["min_count"]
            elif "min" in data and "min_count" not in data:
                data["min_count"] = data["min"]
        return data


class ExternalVerificationDef(BaseRuleDef):
    type: Literal["EXTERNAL_VERIFICATION"]
    document: str = Field(..., description="Document type code, e.g. NBA_CERT")
    required_status: Optional[str] = "VERIFIED"
    verification_service: Optional[str] = None


class InfrastructureDef(BaseRuleDef):
    type: Literal["INFRASTRUCTURE"]
    check_type: Optional[str] = None
    metric: Optional[str] = None
    operator: Optional[Literal["==", "!=", ">", ">=", "<", "<="]] = None
    target: Optional[float] = None
    min_carpet_area_sqm: Optional[float] = None
    min_bandwidth_mbps: Optional[float] = None


# Forward reference for composite
RuleDefUnion = Annotated[
    Union[
        DocumentRequiredDef,
        FieldRequiredDef,
        ValidityPeriodDef,
        CrossFieldMatchDef,
        NumericThresholdDef,
        CountAtLeastDef,
        ExternalVerificationDef,
        InfrastructureDef,
        "CompositeDef",
    ],
    Field(discriminator="type"),
]


class CompositeDef(BaseRuleDef):
    type: Literal["COMPOSITE"]
    all: Optional[List[RuleDefUnion]] = None
    any: Optional[List[RuleDefUnion]] = None
    not_: Optional[RuleDefUnion] = Field(None, alias="not")
    operator: Optional[str] = None
    conditions: Optional[List[Any]] = None

    @model_validator(mode="before")
    def normalize_composite(cls, data: Any):
        if isinstance(data, dict):
            op = data.get("operator")
            conds = data.get("conditions")
            if op and conds:
                if op == "all" and "all" not in data:
                    data["all"] = conds
                elif op == "any" and "any" not in data:
                    data["any"] = conds
                elif op == "not" and "not" not in data and len(conds) > 0:
                    data["not"] = conds[0]
        return data

    @model_validator(mode="after")
    def check_at_least_one_branch(self):
        if not self.all and not self.any and not self.not_:
            raise ValueError("COMPOSITE rule must specify at least one of 'all', 'any', or 'not'.")
        return self


# Resolve forward references
CompositeDef.model_rebuild()


def calculate_depth(defn: Union[dict, BaseModel], current_depth: int = 1) -> int:
    """Calculate maximum nesting depth of a definition tree"""
    if current_depth > 6:
        raise ValueError("Rule definition nesting exceeds maximum allowed limit of 6.")

    if isinstance(defn, BaseModel):
        data = defn.model_dump(by_alias=True)
    elif isinstance(defn, dict):
        data = defn
    else:
        return current_depth

    if data.get("type") == "COMPOSITE":
        max_sub = current_depth
        sub_items = []
        if data.get("all"):
            sub_items.extend(data.get("all"))
        if data.get("any"):
            sub_items.extend(data.get("any"))
        if data.get("conditions"):
            sub_items.extend(data.get("conditions"))
        if data.get("not"):
            sub_items.append(data.get("not"))

        for child in sub_items:
            max_sub = max(max_sub, calculate_depth(child, current_depth + 1))
        return max_sub

    return current_depth


def validate_rule_definition(definition_data: dict) -> RuleDefUnion:
    """
    Validate a declarative JSON rule definition with Pydantic discriminated unions.
    Enforces maximum nesting depth of 6 and returns precise field validation errors.
    """
    if not isinstance(definition_data, dict):
        raise ValueError("Rule definition must be a JSON object dictionary.")

    # Check depth before parsing
    calculate_depth(definition_data, current_depth=1)

    rule_type = definition_data.get("type")
    if not rule_type:
        raise ValueError("Missing required 'type' field in rule definition.")

    type_mapping = {
        "DOCUMENT_REQUIRED": DocumentRequiredDef,
        "FIELD_REQUIRED": FieldRequiredDef,
        "VALIDITY_PERIOD": ValidityPeriodDef,
        "CROSS_FIELD_MATCH": CrossFieldMatchDef,
        "NUMERIC_THRESHOLD": NumericThresholdDef,
        "COUNT_AT_LEAST": CountAtLeastDef,
        "EXTERNAL_VERIFICATION": ExternalVerificationDef,
        "INFRASTRUCTURE": InfrastructureDef,
        "COMPOSITE": CompositeDef,
    }

    schema_cls = type_mapping.get(rule_type)
    if not schema_cls:
        raise ValueError(f"Unknown rule type '{rule_type}'. Valid types: {list(type_mapping.keys())}")

    return schema_cls.model_validate(definition_data)


class RuleDefinition(RootModel[RuleDefUnion]):
    @classmethod
    def model_validate(cls, obj: Any) -> "RuleDefinition":
        parsed = validate_rule_definition(obj)
        return cls(root=parsed)

    def calculate_depth(self) -> int:
        return calculate_depth(self.root, 1)
