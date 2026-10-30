from abc import ABC, abstractmethod
from typing import Dict, Any, Type
from sqlalchemy.orm import Session
from backend.app.models.document import Document
from backend.app.services.verification.schemas import VerificationResultDTO


class VerificationAdapter(ABC):
    """
    Abstract Base Adapter for statutory document verification.
    """

    @abstractmethod
    def verify(
        self,
        document: Document,
        extracted_fields: Dict[str, Any],
        db: Session,
    ) -> VerificationResultDTO:
        """
        Executes verification and returns standard VerificationResultDTO.
        """
        pass


class AdapterRegistry:
    _registry: Dict[str, Type[VerificationAdapter]] = {}

    @classmethod
    def register(cls, method_name: str):
        def decorator(adapter_cls: Type[VerificationAdapter]):
            cls._registry[method_name.upper().strip()] = adapter_cls
            return adapter_cls
        return decorator

    @classmethod
    def get_adapter(cls, method_name: str) -> VerificationAdapter:
        norm = (method_name or "MANUAL").upper().strip()
        adapter_cls = cls._registry.get(norm)
        if not adapter_cls:
            adapter_cls = cls._registry.get("MANUAL")
        return adapter_cls()

