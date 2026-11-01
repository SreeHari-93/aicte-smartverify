import pytest
from datetime import datetime, timezone, timedelta, date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app as fastapi_app
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.workflow import ApplicationWorkflow, WorkflowTemplate
from backend.app.models.evc import EvcRecord
from backend.app.models.undertaking import Undertaking
from backend.app.models.document_validity import DocumentValidityRecord
from backend.app.models.escalation import EscalationRecord
from backend.app.services.consolidated_report_service import (
    ConsolidatedReportService,
    normalize_region,
    CANONICAL_REGIONS,
)
from backend.app.security.tokens import create_access_token


def test_normalize_region_canonical_mapping():
    """Verify normalize_region maps variants to canonical regions and ALL to None."""
    assert normalize_region("South") == "Southern"
    assert normalize_region("Southern") == "Southern"
    assert normalize_region("South Region") == "Southern"
    assert normalize_region("SR") == "Southern"
    assert normalize_region("Tamil Nadu") == "Southern"

    assert normalize_region("North") == "Northern"
    assert normalize_region("Northern") == "Northern"
    assert normalize_region("North Region") == "Northern"
    assert normalize_region("NR") == "Northern"
    assert normalize_region("Delhi") == "Northern"

    assert normalize_region("West") == "Western"
    assert normalize_region("Western") == "Western"
    assert normalize_region("Maharashtra") == "Western"

    assert normalize_region("East") == "Eastern"
    assert normalize_region("Eastern") == "Eastern"

    assert normalize_region("Central") == "Central"
    assert normalize_region("South-Western") == "South-Western"
    assert normalize_region("South Western") == "South-Western"

    assert normalize_region("ALL") is None
    assert normalize_region("all") is None
    assert normalize_region("National") is None
    assert normalize_region(None) is None
    assert normalize_region("") is None


def test_reports_applications_dropdown_admin_and_regional_guard(db_session: Session, client: TestClient):
    """
    Test /api/reports/applications:
    - Admin receives all applications or filtered by region.
    - Regional officer receives only their region.
    - Regional officer requesting another region receives 403 Forbidden.
    """

    # 1. Setup users and template
    tmpl = db_session.query(WorkflowTemplate).first()
    if not tmpl:
        tmpl = WorkflowTemplate(code="REP_TMPL", name="Report Test Template")
        db_session.add(tmpl)
        db_session.commit()

    inst_south = Institute(
        aicte_institute_id="INST-REP-S",
        name="Southern Academy of Tech",
        state="Tamil Nadu",
        status="ACTIVE"
    )
    inst_north = Institute(
        aicte_institute_id="INST-REP-N",
        name="Northern Polytechnic",
        state="Delhi",
        status="ACTIVE"
    )
    db_session.add(inst_south)
    db_session.add(inst_north)
    db_session.commit()

    app_s = Application(
        application_id="APP-2026-S01",
        institute_id=inst_south.id,
        academic_year="2026-2027",
        category="EoA",
        programme="Engineering",
        status="SUBMITTED"
    )
    app_n = Application(
        application_id="APP-2026-N01",
        institute_id=inst_north.id,
        academic_year="2026-2027",
        category="EoA",
        programme="Engineering",
        status="SUBMITTED"
    )
    db_session.add(app_s)
    db_session.add(app_n)
    db_session.commit()

    wf_s = ApplicationWorkflow(
        application_id=app_s.id,
        template_id=tmpl.id,
        current_stage_name="Scrutiny",
        region="South",
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        status="IN_PROGRESS"
    )
    wf_n = ApplicationWorkflow(
        application_id=app_n.id,
        template_id=tmpl.id,
        current_stage_name="EVC",
        region="Northern",
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        status="IN_PROGRESS"
    )
    db_session.add(wf_s)
    db_session.add(wf_n)

    admin_user = db_session.query(User).filter(User.email == "admin_reports_test@aicte.gov.in").first()
    if not admin_user:
        admin_user = User(
            email="admin_reports_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin_user)

    ro_south = db_session.query(User).filter(User.email == "ro_south_test@aicte.gov.in").first()
    if not ro_south:
        ro_south = User(
            email="ro_south_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.REGIONAL_OFFICER,
            region="South",
            is_active=True
        )
        db_session.add(ro_south)

    db_session.commit()
    db_session.refresh(admin_user)
    db_session.refresh(ro_south)

    admin_role = admin_user.role.value if hasattr(admin_user.role, 'value') else str(admin_user.role)
    ro_role = ro_south.role.value if hasattr(ro_south.role, 'value') else str(ro_south.role)

    admin_token = create_access_token(admin_user.id, admin_role)
    ro_token = create_access_token(ro_south.id, ro_role)

    # 2. Admin fetches all applications
    res = client.get(
        "/api/reports/applications",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    apps_data = res.json()
    assert isinstance(apps_data, list)
    assert len(apps_data) > 0
    first_item = apps_data[0]
    assert "application_id" in first_item
    assert "institute_name" in first_item
    assert "stage" in first_item
    assert "label" in first_item
    assert " · " in first_item["label"]

    # 3. Admin filters by Southern
    res_south = client.get(
        "/api/reports/applications?region=Southern",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_south.status_code == 200
    south_apps = res_south.json()
    for item in south_apps:
        assert item["region"] == "Southern"

    # 4. Regional Officer (South) fetches applications without region param -> gets Southern applications
    res_ro = client.get(
        "/api/reports/applications",
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert res_ro.status_code == 200
    ro_apps = res_ro.json()
    for item in ro_apps:
        assert item["region"] == "Southern"

    # 5. Regional Officer (South) explicitly requests Northern -> 403 Forbidden
    res_ro_forbidden = client.get(
        "/api/reports/applications?region=Northern",
        headers={"Authorization": f"Bearer {ro_token}"}
    )
    assert res_ro_forbidden.status_code == 403
    assert "assigned region" in res_ro_forbidden.json()["detail"].lower()


def test_consolidated_reports_region_filter_and_role_guard(db_session: Session, client: TestClient):
    """
    Test /api/reports/consolidated/export:
    - Admin can download reports for any region and national.
    - Regional officer locked to their region; requesting another returns 403.
    - Generated CSV includes jurisdiction header.
    """

    admin_user = db_session.query(User).filter(User.email == "admin_reports_test@aicte.gov.in").first()
    if not admin_user:
        admin_user = User(
            email="admin_reports_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin_user)

    ro_south = db_session.query(User).filter(User.email == "ro_south_test@aicte.gov.in").first()
    if not ro_south:
        ro_south = User(
            email="ro_south_test@aicte.gov.in",
            password_hash="pwd",
            role=UserRole.REGIONAL_OFFICER,
            region="South",
            is_active=True
        )
        db_session.add(ro_south)

    db_session.commit()
    db_session.refresh(admin_user)
    db_session.refresh(ro_south)

    admin_role = admin_user.role.value if hasattr(admin_user.role, 'value') else str(admin_user.role)
    ro_role = ro_south.role.value if hasattr(ro_south.role, 'value') else str(ro_south.role)

    admin_token = create_access_token(admin_user.id, admin_role)
    ro_token = create_access_token(ro_south.id, ro_role)

    # Test all 6 report types in CSV and PDF
    for r_type in [
        "application_pendency",
        "evc_status",
        "undertaking_compliance",
        "document_validity",
        "overdue_cases",
        "region_processing_performance"
    ]:
        # Admin export CSV with region=Southern
        res_csv = client.get(
            f"/api/reports/consolidated/export?report_type={r_type}&format=CSV&region=Southern",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        csv_text = res_csv.text
        assert "Southern" in csv_text or "No records" in csv_text

        # Admin export PDF with region=Southern
        res_pdf = client.get(
            f"/api/reports/consolidated/export?report_type={r_type}&format=PDF&region=Southern",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert res_pdf.status_code == 200
        assert "application/pdf" in res_pdf.headers["content-type"]
        assert len(res_pdf.content) > 1000

        # RO South requesting Northern -> 403 Forbidden
        res_ro_block = client.get(
            f"/api/reports/consolidated/export?report_type={r_type}&format=CSV&region=Northern",
            headers={"Authorization": f"Bearer {ro_token}"}
        )
        assert res_ro_block.status_code == 403

        # RO South requesting Southern -> 200 OK
        res_ro_ok = client.get(
            f"/api/reports/consolidated/export?report_type={r_type}&format=CSV&region=Southern",
            headers={"Authorization": f"Bearer {ro_token}"}
        )
        assert res_ro_ok.status_code == 200


def test_region_processing_performance_canonical_grouping(db_session: Session):
    """
    Test region_processing_performance groups by canonical regions without duplicates.
    """
    csv_out = ConsolidatedReportService.generate_csv(db_session, "region_processing_performance")
    assert "Southern Regional Office" in csv_out
    assert "Northern Regional Office" in csv_out
    assert "Western Regional Office" in csv_out
    assert "South Regional Office," not in csv_out
    assert "North Regional Office," not in csv_out
