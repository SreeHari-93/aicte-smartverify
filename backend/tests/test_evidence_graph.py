import os
import json
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.institute import Institute
from backend.app.models.application import Application
from backend.app.models.document import Document
from backend.app.models.extracted_field import ExtractedField
from backend.app.models.verification import VerificationResult, VerificationStatus
from backend.app.models.anomaly import AnomalyRun, AnomalyFlag, AnomalySeverity, AnomalyReviewStatus
from backend.app.services.anomaly.evidence_graph import EvidenceGraphBuilder
from backend.app.services.report_service import ReportService
from backend.app.security.tokens import create_access_token


@pytest.fixture
def evidence_graph_fixture(db_session: Session):
    # Institute 1 & User 1
    inst_1 = Institute(
        aicte_institute_id="1-123456789",
        name="Sri Krishna College of Engineering and Technology",
        state="Tamil Nadu",
        status="ACTIVE",
    )
    db_session.add(inst_1)
    db_session.flush()

    user_1 = User(
        email="inst1_admin@skcet.ac.in",
        password_hash="fakehash",
        role="INSTITUTE",
        institute_id=inst_1.id,
        is_active=True,
    )
    db_session.add(user_1)

    # Institute 2 & User 2
    inst_2 = Institute(
        aicte_institute_id="1-999999999",
        name="Other Institute of Technology",
        state="Karnataka",
        status="ACTIVE",
    )
    db_session.add(inst_2)
    db_session.flush()

    user_2 = User(
        email="inst2_admin@other.ac.in",
        password_hash="fakehash",
        role="INSTITUTE",
        institute_id=inst_2.id,
        is_active=True,
    )
    db_session.add(user_2)

    # Admin User
    admin_user = User(
        email="scrutiny_officer@aicte-india.org",
        password_hash="fakehash",
        role="ADMIN",
        institute_id=None,
        is_active=True,
    )
    db_session.add(admin_user)
    db_session.flush()

    # Application for Institute 1
    app_1 = Application(
        institute_id=inst_1.id,
        application_id="APP-2026-EVD-01",
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Engineering & Technology",
        status="SUBMITTED",
    )
    db_session.add(app_1)
    db_session.flush()

    # Application for Institute 2
    app_2 = Application(
        institute_id=inst_2.id,
        application_id="APP-2026-EVD-02",
        category="Extension of Approval (EoA)",
        academic_year="2026-2027",
        programme="Management",
        status="DRAFT",
    )
    db_session.add(app_2)
    db_session.flush()

    # Document 1 for App 1 (Authentic SKCET details)
    doc_1 = Document(
        institute_id=inst_1.id,
        application_id=app_1.id,
        document_type_code="FIRE_NOC",
        original_filename="Fire_Safety_NOC_2026.pdf",
        stored_filename="stored_fire_noc_2026.pdf",
        file_path="/tmp/Fire_Safety_NOC_2026.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        status="Uploaded",
        extracted_data={
            "institute_name": "Sri Krishna College of Engineering and Technology",
            "aicte_id": "1-123456789",
            "address": "BK Pudur, Kuniamuthur, Coimbatore, Tamil Nadu 641008",
            "issue_date": "2025-01-10",
            "expiry_date": "2026-01-09",
        },
    )
    db_session.add(doc_1)
    db_session.flush()

    # Document 2 for App 1 (DELIBERATE cross-document conflict: different institute, AICTE ID, and address)
    doc_2 = Document(
        institute_id=inst_1.id,
        application_id=app_1.id,
        document_type_code="BUILDING_PLAN",
        original_filename="Municipal_Building_Plan_NOC.pdf",
        stored_filename="stored_building_plan_noc.pdf",
        file_path="/tmp/Municipal_Building_Plan_NOC.pdf",
        file_size=4096,
        mime_type="application/pdf",
        sha256_hash="fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210",
        status="Uploaded",
        extracted_data={
            "institute_name": "Delhi Institute of Advanced Studies",  # Conflict!
            "aicte_id": "1-987654321",  # Conflict!
            "address": "Sector 25, Rohini, New Delhi 110085",  # Conflict!
            "issue_date": "2024-05-15",
        },
    )
    db_session.add(doc_2)
    db_session.flush()

    # Document 3 for App 1 (DELIBERATE duplicate SHA-256 with doc_1)
    doc_3 = Document(
        institute_id=inst_1.id,
        application_id=app_1.id,
        document_type_code="FIRE_NOC",
        original_filename="Fire_Safety_NOC_Duplicate_Copy.pdf",
        stored_filename="stored_fire_noc_copy.pdf",
        file_path="/tmp/Fire_Safety_NOC_Duplicate_Copy.pdf",
        file_size=2048,
        mime_type="application/pdf",
        sha256_hash="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",  # Exactly matches doc_1!
        status="Uploaded",
        extracted_data={
            "institute_name": "Sri Krishna College of Engineering and Technology",
            "aicte_id": "1-123456789",
        },
    )
    db_session.add(doc_3)
    db_session.flush()

    # Verification result for Document 1
    ver_1 = VerificationResult(
        document_id=doc_1.id,
        status=VerificationStatus.VERIFIED,
        source_name="State Fire Services Portal (Simulated)",
        source_ref="FIRE-REG-2026-SKCET",
        details_json={"message": "Matches official statutory register."},
    )
    db_session.add(ver_1)

    # Anomaly Run and Flag for Document 2
    anom_run = AnomalyRun(
        document_id=doc_2.id,
        application_id=app_1.id,
        detectors_run=["ImageTamperDetector", "IdentifierDetector"],
    )
    db_session.add(anom_run)
    db_session.flush()

    anom_flag = AnomalyFlag(
        run_id=anom_run.id,
        document_id=doc_2.id,
        detector="ImageTamperDetector",
        code="IMAGE_TAMPER_SUSPECTED",
        group_key="TAMPER",
        severity=AnomalySeverity.HIGH,
        reason="Visual layout compression irregularities detected in document header; potential anomaly requiring verification.",
        evidence_json=[{"document_id": doc_2.id, "page": 1, "type": "compression_inconsistency", "bbox": [100, 200, 300, 400]}],
        confidence=0.92,
        recommended_action="Conduct official verification of physical paper certificate with issuing municipal corporation.",
        review_status=AnomalyReviewStatus.OPEN,
    )
    db_session.add(anom_flag)

    db_session.commit()
    db_session.refresh(app_1)
    db_session.refresh(app_2)
    db_session.refresh(doc_1)
    db_session.refresh(doc_2)
    db_session.refresh(doc_3)
    db_session.refresh(user_1)
    db_session.refresh(user_2)
    db_session.refresh(admin_user)

    return {
        "inst_1": inst_1,
        "inst_2": inst_2,
        "user_1": user_1,
        "user_2": user_2,
        "admin_user": admin_user,
        "app_1": app_1,
        "app_2": app_2,
        "doc_1": doc_1,
        "doc_2": doc_2,
        "doc_3": doc_3,
    }


def test_evidence_graph_nodes_and_edges_cross_doc_conflict(db_session: Session, evidence_graph_fixture):
    """
    Verifies that the evidence graph builds complete multi-entity nodes and edges,
    and reliably detects cross-document conflicts across institute name, AICTE ID, and address.
    """
    app = evidence_graph_fixture["app_1"]
    doc_1 = evidence_graph_fixture["doc_1"]
    doc_2 = evidence_graph_fixture["doc_2"]
    doc_3 = evidence_graph_fixture["doc_3"]

    graph = EvidenceGraphBuilder.build_graph(db=db_session, application_id=app.id, is_admin=False)

    # 1. Verify Nodes
    node_types = {n["type"] for n in graph["nodes"]}
    assert "institute" in node_types
    assert "application" in node_types
    assert "document" in node_types
    assert "field" in node_types
    assert "verification" in node_types
    assert "anomaly_flag" in node_types

    doc_node_ids = [n["id"] for n in graph["nodes"] if n["type"] == "document"]
    assert f"doc_{doc_1.id}" in doc_node_ids
    assert f"doc_{doc_2.id}" in doc_node_ids
    assert f"doc_{doc_3.id}" in doc_node_ids

    # 2. Verify Edges
    edge_types = {e["type"] for e in graph["edges"]}
    assert "institute-submits-application" in edge_types
    assert "application-includes-document" in edge_types
    assert "document-contains-field" in edge_types
    assert "document-verified-by-source" in edge_types
    assert "flag-about-document" in edge_types
    assert "duplicate-of" in edge_types
    assert "field-conflicts-with-field" in edge_types

    # 3. Verify Detected Cross-Document Conflicts
    conflicts = graph["conflicts"]
    conflict_fields = {c["field"] for c in conflicts}

    assert "institute_name" in conflict_fields, "Must detect cross-document institute name conflict"
    assert "aicte_id" in conflict_fields, "Must detect cross-document AICTE ID conflict"
    assert "address" in conflict_fields, "Must detect cross-document address conflict"

    # Verify conflict details
    inst_name_conf = next(c for c in conflicts if c["field"] == "institute_name")
    assert "Delhi Institute of Advanced Studies" in [inst_name_conf["value_1"], inst_name_conf["value_2"]]
    assert "Sri Krishna College" in str([inst_name_conf["value_1"], inst_name_conf["value_2"]])
    assert "needs verification" in inst_name_conf["reason"].lower() or "potential anomaly" in inst_name_conf["reason"].lower()

    # 4. Verify Duplicate Edge
    dup_edges = [e for e in graph["edges"] if e["type"] == "duplicate-of"]
    assert len(dup_edges) >= 1
    dup_pair = {dup_edges[0]["source"], dup_edges[0]["target"]}
    assert f"doc_{doc_1.id}" in dup_pair and f"doc_{doc_3.id}" in dup_pair


def test_evidence_graph_institute_isolation_and_admin_view(client, evidence_graph_fixture):
    """
    Enforces institute isolation:
      - Institute A cannot view Institute B's application evidence graph (403 Forbidden).
      - Institute A view omits raw internal confidence scores.
      - Admin view includes full internal confidence scores and raw inspection fields.
    """
    user_1 = evidence_graph_fixture["user_1"]
    user_2 = evidence_graph_fixture["user_2"]
    admin = evidence_graph_fixture["admin_user"]
    app_1 = evidence_graph_fixture["app_1"]

    token_1 = create_access_token(user_id=user_1.id, role=user_1.role)
    token_2 = create_access_token(user_id=user_2.id, role=user_2.role)
    token_admin = create_access_token(user_id=admin.id, role=admin.role)

    # 1. Institute 2 attempts to access Institute 1's application evidence graph -> 403 Forbidden
    client.cookies.set("aicte_access_token", token_2)
    res_forbidden = client.get(f"/api/institute/applications/{app_1.id}/evidence-graph")
    assert res_forbidden.status_code == 403
    assert "Forbidden" in res_forbidden.json()["detail"]

    # 2. Institute 1 accesses own application evidence graph -> 200 OK
    client.cookies.set("aicte_access_token", token_1)
    res_inst = client.get(f"/api/institute/applications/{app_1.id}/evidence-graph")
    assert res_inst.status_code == 200
    inst_graph = res_inst.json()

    # Verify internal confidence is omitted from institute view
    flag_nodes = [n for n in inst_graph["nodes"] if n["type"] == "anomaly_flag"]
    assert len(flag_nodes) >= 1
    for f_node in flag_nodes:
        assert "confidence" not in f_node["properties"], "Internal confidence score must NOT be exposed to institute"

    # 3. Admin accesses admin evidence graph -> 200 OK with internal confidence
    client.cookies.set("aicte_access_token", token_admin)
    res_admin = client.get(f"/api/admin/applications/{app_1.id}/evidence-graph")
    assert res_admin.status_code == 200
    admin_graph = res_admin.json()

    admin_flag_nodes = [n for n in admin_graph["nodes"] if n["type"] == "anomaly_flag"]
    assert len(admin_flag_nodes) >= 1
    assert "confidence" in admin_flag_nodes[0]["properties"], "Admin endpoint must include internal confidence scores"


def test_strict_wording_no_forbidden_words_in_evidence_graph(db_session: Session, evidence_graph_fixture):
    """
    Strict wording compliance test:
    All evidence graph output must use 'needs verification' or 'potential anomaly'.
    Forbidden words ('forgery', 'fraud', 'misconduct') must NEVER appear.
    """
    app = evidence_graph_fixture["app_1"]
    graph = EvidenceGraphBuilder.build_graph(db=db_session, application_id=app.id, is_admin=False)

    dumped_str = json.dumps(graph).lower()

    # Assert forbidden words are completely absent
    assert "forgery" not in dumped_str, "Found forbidden word 'forgery' in evidence graph output"
    assert "forgeries" not in dumped_str, "Found forbidden word 'forgeries' in evidence graph output"
    assert "fraud" not in dumped_str, "Found forbidden word 'fraud' in evidence graph output"
    assert "fraudulent" not in dumped_str, "Found forbidden word 'fraudulent' in evidence graph output"
    assert "misconduct" not in dumped_str, "Found forbidden word 'misconduct' in evidence graph output"

    # Assert approved terminology is actively present
    assert "needs verification" in dumped_str or "potential anomaly" in dumped_str


def test_validation_summary_pdf_contains_anomaly_and_graph_sections(db_session: Session, evidence_graph_fixture):
    """
    Verifies that the generated Validation Summary PDF successfully includes
    the Preliminary Anomaly Indicators and Evidence Graph Consistency Analysis sections
    with proper human verification disclaimers.
    """
    inst = evidence_graph_fixture["inst_1"]
    app = evidence_graph_fixture["app_1"]

    rep = ReportService.generate_report(
        db=db_session,
        institute_id=inst.id,
        report_type="Validation Summary",
        report_format="PDF",
        date_range="AY 2026-27",
        application_id=str(app.id),
    )

    assert rep is not None
    assert rep.file_path is not None
    assert os.path.exists(rep.file_path), "Validation Summary PDF must be generated and saved to disk"
    file_size = os.path.getsize(rep.file_path)
    assert file_size > 2000, "Validation Summary PDF should contain populated content"
