import os
from typing import List
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

