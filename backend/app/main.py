import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.institute import router as institute_router
from backend.app.api.v1.admin import router as admin_router
from backend.app.api.v1.mock_authorities import router as mock_authorities_router
from backend.app.services.notification_service import check_and_create_certificate_notifications
from backend.app.services.document_pipeline.recovery import recover_stuck_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aicte_smartverify")

# Initialize database schema
Base.metadata.create_all(bind=engine)

# Scheduler for daily certificate expiry checks
scheduler = BackgroundScheduler()


def run_scheduled_expiry_check():
    db = SessionLocal()
    try:
        check_and_create_certificate_notifications(db)
    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] Expiry check failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Recover any stuck documents from previous runs
    db = SessionLocal()
    try:
        recover_stuck_documents(db, max_age_minutes=2)
    except Exception as e:
        logger.error(f"[STARTUP ERROR] Stuck document recovery failed: {e}", exc_info=True)
    finally:
        db.close()

    # Start background scheduler
    scheduler.add_job(run_scheduled_expiry_check, 'interval', hours=24, id="daily_cert_check", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AICTE SmartVerify AI - Secure Authentication & Institute Validation Platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: https: blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline'; "
            "frame-ancestors 'none';"
        )
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount Routers (support both /api and /api/v1 prefixes)
app.include_router(auth_router, prefix="/api/auth")
app.include_router(auth_router, prefix="/api/v1/auth")

app.include_router(institute_router, prefix="/api")
app.include_router(institute_router, prefix="/api/v1")

app.include_router(admin_router, prefix="/api")
app.include_router(admin_router, prefix="/api/v1")

app.include_router(mock_authorities_router, prefix="/mock-authorities")
app.include_router(mock_authorities_router, prefix="/api/mock-authorities")


@app.get("/api/health", tags=["System"])
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
