import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.api.deps import get_current_user, require_role
from backend.app.models.user import User, UserRole
from backend.app.integrations import app_feed_adapter, institute_record_adapter

logger = logging.getLogger("aicte_integrations_router")

router = APIRouter(prefix="/integrations", tags=["External Integrations (Simulated)"])


@router.get("/status")
def get_integrations_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get connectivity status, last sync timestamp, and capabilities
    for all simulated AICTE legacy system adapters.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.REGIONAL_OFFICER, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Unauthorized to access integrations console.")

    return {
        "status": "OPERATIONAL",
        "is_simulated": True,
        "adapters": [
            {
                "name": app_feed_adapter.name,
                "type": app_feed_adapter.adapter_type,
                "is_simulated": True,
                "health": app_feed_adapter.health_check(),
                "metadata": app_feed_adapter.get_metadata(),
            },
            {
                "name": institute_record_adapter.name,
                "type": institute_record_adapter.adapter_type,
                "is_simulated": True,
                "health": institute_record_adapter.health_check(),
                "metadata": institute_record_adapter.get_metadata(),
            },
        ],
        "queried_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/sync-feed")
def trigger_simulated_feed_sync(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger automated synchronization from simulated external application feed.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Only Central Administrators can trigger external feed synchronization.")

    feed_records = app_feed_adapter.get_simulated_feed_items()
    result = app_feed_adapter.process_records(
        db=db,
        records=feed_records,
        operator_user_id=current_user.id,
        operator_role=current_user.role,
    )
    return result


@router.post("/import-feed")
async def import_applications_from_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import applications from an uploaded JSON or CSV file feed.
    Duplicates are skipped idempotently.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.BUREAU_OFFICER]:
        raise HTTPException(status_code=403, detail="Only Administrators can import application feed files.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Feed file exceeds 10MB maximum limit.")

    records = app_feed_adapter.parse_file_content(contents, file.filename or "feed.json")
    result = app_feed_adapter.process_records(
        db=db,
        records=records,
        operator_user_id=current_user.id,
        operator_role=current_user.role,
    )
    return result


@router.get("/institutes/{institute_id}/profile")
def get_external_institute_profile(
    institute_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Fetch external master record and historical multi-year approval decisions
    for an institution via the simulated InstituteRecordAdapter.
    """
    if current_user.role == UserRole.INSTITUTE and current_user.institute_id != institute_id:
        raise HTTPException(status_code=403, detail="Access denied to external records of another institution.")

    profile = institute_record_adapter.fetch_institute_profile(
        db=db,
        institute_id=institute_id,
        operator_user_id=current_user.id,
        operator_role=current_user.role,
    )
    return profile

