"""
Base Adapter Interface for AICTE External System Integrations.

All adapters in this package simulate connectivity to legacy AICTE systems
(e.g., Central Application Processing Portal, National Institute Database).
Every adapter is explicitly flagged as SIMULATED, read-only or strictly
sandboxed, and enforces role-based access checks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class BaseIntegrationAdapter(ABC):
    """
    Abstract interface for AICTE legacy integration adapters.
    """

    def __init__(self, name: str, adapter_type: str, is_simulated: bool = True):
        self.name = name
        self.adapter_type = adapter_type
        self.is_simulated = is_simulated
        self.last_sync: Optional[datetime] = None
        self.last_sync_status: str = "IDLE"
        self.last_sync_message: str = "Ready for simulation synchronization"

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verify connectivity to external AICTE endpoint or simulated service."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return adapter configuration, capabilities, and simulation metadata."""
        pass

