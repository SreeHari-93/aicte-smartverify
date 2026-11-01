import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal, get_db
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.institute import router as institute_router
from backend.app.api.v1.admin import router as admin_router
from backend.app.api.v1.workflow import router as workflow_router
from backend.app.api.v1.evc import router as evc_router
from backend.app.api.v1.undertakings import router as undertakings_router
from backend.app.api.v1.validity import router as validity_router
from backend.app.api.v1.alerts import router as alerts_router
from backend.app.api.v1.reports_stage4 import router as reports_stage4_router
from backend.app.api.v1.evaluation_stage4 import router as evaluation_stage4_router
from backend.app.api.v1.mock_authorities import router as mock_authorities_router
from backend.app.api.v1.integrations import router as integrations_router
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from backend.app.schemas.infrastructure import InfrastructureDetailOut, InfrastructureDetailUpdate
from backend.app.api.v1.institute import get_institute_application_infrastructure, update_institute_application_infrastructure, get_current_institute_user
from backend.app.models.user import User
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
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

    # Initial startup scan & seeding for statutory alerts and escalations
    db_scan = SessionLocal()
    try:
        from backend.app.services.scheduler_service import seed_rules_and_escalations_if_empty, run_notification_scan
        seed_rules_and_escalations_if_empty(db_scan)
        run_notification_scan(db_scan)
    except Exception as e:
        logger.error(f"[STARTUP ERROR] Initial notification scan failed: {e}", exc_info=True)
    finally:
        db_scan.close()

    # Start background scheduler (hourly statutory scans + daily cert checks)
    scheduler.add_job(run_scheduled_expiry_check, 'interval', hours=24, id="daily_cert_check", replace_existing=True)
    def run_hourly_notification_scan():
        db_job = SessionLocal()
        try:
            from backend.app.services.scheduler_service import run_notification_scan
            run_notification_scan(db_job)
        except Exception as e:
            logger.error(f"[SCHEDULER ERROR] Hourly notification scan failed: {e}")
        finally:
            db_job.close()
    scheduler.add_job(run_hourly_notification_scan, 'interval', hours=1, id="hourly_notification_scan", replace_existing=True)
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
            "connect-src 'self' http: https: ws: wss:; "
            "frame-ancestors 'none';"
        )
        if request.url.scheme == "https":
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

app.include_router(workflow_router, prefix="/api/workflow")
app.include_router(workflow_router, prefix="/api/v1/workflow")

app.include_router(evc_router, prefix="/api/evc")
app.include_router(evc_router, prefix="/api/v1/evc")

app.include_router(undertakings_router, prefix="/api/undertakings")
app.include_router(undertakings_router, prefix="/api/v1/undertakings")

app.include_router(validity_router, prefix="/api/validity")
app.include_router(validity_router, prefix="/api/v1/validity")

app.include_router(alerts_router, prefix="/api/alerts")
app.include_router(alerts_router, prefix="/api/v1/alerts")

app.include_router(reports_stage4_router, prefix="/api")
app.include_router(reports_stage4_router, prefix="/api/v1")

app.include_router(evaluation_stage4_router, prefix="/api")
app.include_router(evaluation_stage4_router, prefix="/api/v1")

app.include_router(mock_authorities_router, prefix="/mock-authorities")
app.include_router(mock_authorities_router, prefix="/api/mock-authorities")

app.include_router(integrations_router, prefix="/api")
app.include_router(integrations_router, prefix="/api/v1")


# Global Safeguard: No raw stack traces leaked in API errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[SAFEGUARD_ERROR] {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal regulatory processing error occurred. Please contact the AICTE system administrator."},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.get("/api/health", tags=["System"])
def healthcheck():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


# Direct alias for frontend institute infrastructure API calls
@app.get("/api/applications/{application_id}/infrastructure", response_model=InfrastructureDetailOut, include_in_schema=False)
def api_get_application_infra(
    application_id: str,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    return get_institute_application_infrastructure(application_id=application_id, user=user, db=db)


@app.put("/api/applications/{application_id}/infrastructure", response_model=InfrastructureDetailOut, include_in_schema=False)
def api_put_application_infra(
    application_id: str,
    payload: InfrastructureDetailUpdate,
    user: User = Depends(get_current_institute_user),
    db: Session = Depends(get_db),
):
    return update_institute_application_infrastructure(application_id=application_id, payload=payload, user=user, db=db)


# Aliases for docs & openapi
@app.get("/docs", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url="/api/docs")


@app.get("/openapi.json", include_in_schema=False)
def openapi_alias():
    return JSONResponse(content=app.openapi())


# Static Uploads Mount
uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads"))
if not os.path.exists(uploads_dir):
    uploads_dir = os.path.abspath(os.path.join(os.getcwd(), "uploads"))
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# Serve Built Frontend (SPA) & Static Files
frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if not os.path.exists(frontend_dist_dir):
    frontend_dist_dir = os.path.abspath(os.path.join(os.getcwd(), "frontend/dist"))

if os.path.exists(frontend_dist_dir):
    frontend_assets_dir = os.path.join(frontend_dist_dir, "assets")
    if os.path.exists(frontend_assets_dir):
        app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def serve_root():
        index_file = os.path.join(frontend_dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return JSONResponse(status_code=404, content={"detail": "index.html not found"})

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_or_static(full_path: str):
        # Do not catch API, uploads, mock-authorities or documentation routes
        if (
            full_path.startswith("api/")
            or full_path == "api"
            or full_path.startswith("uploads/")
            or full_path == "uploads"
            or full_path.startswith("mock-authorities/")
            or full_path == "mock-authorities"
        ):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        file_path = os.path.join(frontend_dist_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        index_file = os.path.join(frontend_dist_dir, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)

        return JSONResponse(status_code=404, content={"detail": "Not Found"})
