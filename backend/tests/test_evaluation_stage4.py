import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.models.user import User, UserRole
from backend.app.models.alert_event import AlertEvent
from backend.app.models.audit_log import AuditLog
from backend.app.models.workflow import ApplicationWorkflow
from backend.app.security.tokens import create_access_token


def test_evaluation_stage4_institute_user_forbidden(client: TestClient, db_session: Session):
    """Verify an institute user receives 403 Forbidden on evaluation endpoints."""
    inst_user = db_session.query(User).filter(User.email == "eval_inst_test@aicte.edu.in").first()
    if not inst_user:
        inst_user = User(
            email="eval_inst_test@aicte.edu.in",
            password_hash="pwd",
            role=UserRole.INSTITUTE,
            is_active=True
        )
        db_session.add(inst_user)
        db_session.commit()
        db_session.refresh(inst_user)

    role_str = inst_user.role.value if hasattr(inst_user.role, "value") else str(inst_user.role)
    token = create_access_token(inst_user.id, role_str)
    headers = {"Authorization": f"Bearer {token}"}

    res_get = client.get("/api/evaluation/synthetic-scenarios", headers=headers)
    assert res_get.status_code == 403

    res_post = client.post("/api/evaluation/trigger-scenarios", headers=headers)
    assert res_post.status_code == 403


def test_evaluation_re_run_and_count_isolation(client: TestClient, db_session: Session):
    """
    Verify:
    1. Re-run returns a new run with a later timestamp.
    2. A re-run does not change counts of alerts, audit entries, or workflows.
    """
    admin_user = db_session.query(User).filter(User.email == "eval_admin_test@aicte.gov.in").first()
    if not admin_user:
        admin_user = User(
            email="eval_admin_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    admin_role = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    token = create_access_token(admin_user.id, admin_role)
    headers = {"Authorization": f"Bearer {token}"}

    # Record baseline counts of real operational tables
    alerts_count_before = db_session.query(AlertEvent).count()
    audits_count_before = db_session.query(AuditLog).count()
    workflows_count_before = db_session.query(ApplicationWorkflow).count()

    # Initial synchronous run
    res1 = client.post("/api/evaluation/trigger-scenarios?sync=true", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "evaluated_at" in data1
    assert "overall_accuracy" in data1
    assert len(data1["scenarios"]) == 8

    # Second synchronous re-run
    res2 = client.post("/api/evaluation/trigger-scenarios?sync=true", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert "evaluated_at" in data2
    assert data2["id"] >= data1["id"]
    assert data2["evaluated_at"] >= data1["evaluated_at"]

    # Check previous_run in data2 references data1
    assert data2.get("previous_run") is not None
    assert "dimension_scores" in data2["previous_run"]

    # Verify counts of alerts, audit entries, and workflows remain identical (isolated and honest)
    alerts_count_after = db_session.query(AlertEvent).count()
    audits_count_after = db_session.query(AuditLog).count()
    workflows_count_after = db_session.query(ApplicationWorkflow).count()

    assert alerts_count_after == alerts_count_before
    assert audits_count_after == audits_count_before
    assert workflows_count_after == workflows_count_before


def test_evaluation_deliberately_wrong_expectation_fails_dimension(client: TestClient, db_session: Session):
    """
    Verify:
    A deliberately wrong expectation produces a failed dimension with failure reason and lower score.
    """
    admin_user = db_session.query(User).filter(User.email == "eval_admin_test@aicte.gov.in").first()
    if not admin_user:
        admin_user = User(
            email="eval_admin_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    admin_role = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    token = create_access_token(admin_user.id, admin_role)
    headers = {"Authorization": f"Bearer {token}"}

    # Re-run with injected wrong routing expectation
    res = client.post("/api/evaluation/trigger-scenarios?sync=true&fail_dimension=routing", headers=headers)
    assert res.status_code == 200
    data = res.json()

    routing_dim = next((s for s in data["scenarios"] if "routing" in s["dimension"].lower()), None)
    assert routing_dim is not None
    assert routing_dim["status"] == "FAILED"
    assert routing_dim["score"] < 95.0
    assert routing_dim["failure_reason"] is not None
    assert "routed to" in routing_dim["failure_reason"].lower() or "expected" in routing_dim["failure_reason"].lower()
    assert data["overall_accuracy"] < 100.0


def test_evaluation_prevent_double_runs(client: TestClient, db_session: Session):
    """Verify that when a run is active, subsequent trigger requests return active run instead of duplicate run."""
    admin_user = db_session.query(User).filter(User.email == "eval_admin_test@aicte.gov.in").first()
    if not admin_user:
        admin_user = User(
            email="eval_admin_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    admin_role = admin_user.role.value if hasattr(admin_user.role, "value") else str(admin_user.role)
    token = create_access_token(admin_user.id, admin_role)
    headers = {"Authorization": f"Bearer {token}"}

    # Start an asynchronous run
    res1 = client.post("/api/evaluation/trigger-scenarios", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "RUNNING"
    run_id_1 = data1.get("run_id") or data1.get("active_run", {}).get("id")

    # Immediate second call must detect active run and return RUNNING with the same run_id
    res2 = client.post("/api/evaluation/trigger-scenarios", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "RUNNING"
    run_id_2 = data2.get("run_id") or data2.get("active_run", {}).get("id")
    assert run_id_1 == run_id_2

