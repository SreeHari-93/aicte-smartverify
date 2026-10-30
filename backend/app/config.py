import os
from typing import List, Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AICTE SmartVerify AI"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Database
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./aicte.db"
    
    # JWT & Auth
    SECRET_KEY: str = "aicte-smartverify-super-secret-key-change-in-production-2026-xyz"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Security Policies
    CAPTCHA_EXPIRE_SECONDS: int = 120  # 2 minutes
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    RATE_LIMIT_PER_MINUTE: int = 5
    
    # Governance & Approval Workflow
    RULES_REQUIRE_APPROVAL: bool = False

    # Pipeline & AI Extraction
    EXTRACTION_LLM_ENABLED: bool = False
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.4
    GEMINI_API_KEY: str = ""

    # Validation Engine Settings
    VALIDATION_MAJOR_FAIL_THRESHOLD: int = 2
    SEVERITY_DEDUCTION_WEIGHTS: Dict[str, float] = {
        "BLOCKER": 40.0,
        "MAJOR": 15.0,
        "MINOR": 5.0,
        "ADVISORY": 0.0,
    }

    # Explainer & LLM Settings
    ANTHROPIC_API_KEY: str = ""
    EXPLAINER_MODEL: str = "claude-3-7-sonnet-20250219"
    EXPLAINER_TIMEOUT_SECONDS: int = 20
    EXPLAINER_CIRCUIT_BREAKER_FAILURES: int = 3

    # Anomaly Detection Engine Settings
    ANOMALY_STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../storage/anomalies"))
    ANOMALY_DUPLICATE_PHASH_THRESHOLD: int = 3
    ANOMALY_DUPLICATE_TEXT_SIMILARITY_THRESHOLD: float = 0.85
    ANOMALY_SUSPICIOUS_PRODUCERS: List[str] = [
        "photoshop", "canva", "gimp", "sejda", "pdfescape", 
        "illustrator", "inkscape", "ilovepdf", "smallpdf", "nitro",
        "foxit phantom", "pdf architect"
    ]
    ANOMALY_DATE_MAX_VALIDITY_MONTHS_RATIO: float = 2.0
    ANOMALY_ELA_SCALE: float = 15.0
    ANOMALY_ELA_QUALITY: int = 90
    ANOMALY_ELA_DIFF_THRESHOLD: float = 28.0
    ANOMALY_COPY_MOVE_MIN_MATCHES: int = 40
    ANOMALY_COPY_MOVE_MIN_DISTANCE: float = 40.0
    ANOMALY_TEXT_BASELINE_VAR_THRESHOLD: float = 12.0

    # Cookies
    COOKIE_SECURE: bool = False  # Set to True in HTTPS production
    COOKIE_SAMESITE: str = "lax"  # "strict" or "lax"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

