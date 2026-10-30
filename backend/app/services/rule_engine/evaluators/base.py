from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    status: str  # PASS | FAIL | WARNING | NEEDS_REVIEW | NOT_APPLICABLE
    reason: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_action: Optional[str] = None


class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, definition: Dict[str, Any], context: Any) -> EvaluationResult:
        pass


class EvaluatorRegistry:
    _evaluators: Dict[str, BaseEvaluator] = {}

    @classmethod
    def register(cls, rule_type: str):
        def decorator(evaluator_cls: Type[BaseEvaluator]):
            cls._evaluators[rule_type.upper()] = evaluator_cls()
            return evaluator_cls
        return decorator

    @classmethod
    def get(cls, rule_type: str) -> Optional[BaseEvaluator]:
        return cls._evaluators.get(rule_type.upper())

    @classmethod
    def list_supported_types(cls) -> List[str]:
        return list(cls._evaluators.keys())

