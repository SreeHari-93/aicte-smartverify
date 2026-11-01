import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.api.deps import get_current_user
from backend.app.services.evaluation_service import EvaluationService

logger = logging.getLogger("aicte.evaluation_api")
router = APIRouter(prefix="/evaluation", tags=["System Evaluation"])


@router.get("/synthetic-scenarios")
def get_synthetic_evaluation(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get evaluation results on scripted synthetic scenarios:
    Workflow routing accuracy, deadline calculation accuracy, alert timeliness using demo clock,
    duplicate-alert rate, escalation correctness, audit completeness, return & resubmit cycle,
    and late renewal escalation level 3. Includes active progress and runs history.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val not in ["ADMIN", "BUREAU_OFFICER"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrative officers can access system evaluation metrics."
        )

    return EvaluationService.get_evaluation_summary(db)


@router.get("/status")
def get_evaluation_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Poll live progress and status of active or latest evaluation run."""
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val not in ["ADMIN", "BUREAU_OFFICER"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrative officers can access evaluation status."
        )

    return EvaluationService.get_evaluation_summary(db)


@router.post("/trigger-scenarios")
def trigger_synthetic_evaluation(
    sync: bool = Query(False, description="Whether to execute synchronously (useful for test suites)"),
    fail_dimension: Optional[str] = Query(None, description="Optional dimension to deliberately inject failure for testing"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-run statutory synthetic scenarios in an isolated, safe manner.
    Does NOT mutate real alerts, workflows, undertakings, audit entries, or notifications.
    Prevents double runs by returning active run status if one is already in progress.
    """
    role_val = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role_val not in ["ADMIN", "BUREAU_OFFICER"]:
        raise HTTPException(
            status_code=403,
            detail="Only administrative officers can run system evaluation."
        )

    return EvaluationService.start_or_execute_run(db, sync=sync, fail_dimension=fail_dimension)
