from backend.app.services.verification.adapters.base import VerificationAdapter, AdapterRegistry
from backend.app.services.verification.adapters.manual_adapter import ManualVerificationAdapter
from backend.app.services.verification.adapters.qr_adapter import QRVerificationAdapter
from backend.app.services.verification.adapters.digital_signature_adapter import DigitalSignatureAdapter
from backend.app.services.verification.adapters.api_adapter import APIVerificationAdapter

__all__ = [
    "VerificationAdapter",
    "AdapterRegistry",
    "ManualVerificationAdapter",
    "QRVerificationAdapter",
    "DigitalSignatureAdapter",
    "APIVerificationAdapter",
]

