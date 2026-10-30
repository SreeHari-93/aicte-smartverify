from backend.app.services.anomaly.detectors.base import BaseDetector, DetectorRegistry, DetectionContext
from backend.app.services.anomaly.detectors.duplicate_detector import DuplicateDetector
from backend.app.services.anomaly.detectors.metadata_detector import MetadataDetector
from backend.app.services.anomaly.detectors.date_anomaly_detector import DateAnomalyDetector
from backend.app.services.anomaly.detectors.identifier_detector import IdentifierDetector
from backend.app.services.anomaly.detectors.image_tamper_detector import ImageTamperDetector
from backend.app.services.anomaly.detectors.verification_conflict_detector import VerificationConflictDetector

# Initialize and register all 6 standard detectors
_all_detectors = [
    DuplicateDetector(),
    MetadataDetector(),
    DateAnomalyDetector(),
    IdentifierDetector(),
    ImageTamperDetector(),
    VerificationConflictDetector(),
]

DetectorRegistry.clear()
for d in _all_detectors:
    DetectorRegistry.register(d)

__all__ = [
    "BaseDetector",
    "DetectorRegistry",
    "DetectionContext",
    "DuplicateDetector",
    "MetadataDetector",
    "DateAnomalyDetector",
    "IdentifierDetector",
    "ImageTamperDetector",
    "VerificationConflictDetector",
]

