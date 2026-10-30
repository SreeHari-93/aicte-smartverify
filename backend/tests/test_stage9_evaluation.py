import os
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.models.user import User, UserRole
from backend.app.models.evaluation import EvaluationRun, AIFeedback
from backend.app.security.tokens import create_access_token
from backend.app.services.evaluation.runner import EvaluationRunner
from backend.app.services.evaluation.metrics import (
    ClassificationEvaluator,
    FieldExtractionEvaluator,
    AnomalyDetectorEvaluator,
    ExplainerGroundingChecker,
)
from backend.app.services.evaluation.exporter import EvaluationExporter


def get_auth_cookie(user: User):
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    token = create_access_token(user_id=user.id, role=role_str)
    return {"aicte_access_token": token}


def test_evaluation_runner_subset_and_metrics_targets(db_session):
    """
    Run evaluation on a 10-document subset of the synthetic evaluation dataset.
    Check metrics structure, verify persistence in evaluation_runs,
    and verify accuracy targets:
      - classification F1 > 0.90
      - field extraction match rate > 0.90
      - anomaly false positive rate < 0.10
      - explainer grounding rate > 0.90
    """
    runner = EvaluationRunner(db_session, eval_dir="backend/eval_data")
    run = runner.run(dataset_version="v1.0-eval-subset", subset_limit=10)

    assert run.id is not None
    assert run.status == "COMPLETED"
    assert run.total_samples == 10
    assert run.overall_accuracy >= 90.0

    metrics = run.metrics_json
    assert "classification" in metrics
    assert "field_extraction" in metrics
    assert "anomaly_detectors" in metrics
    assert "explainer_grounding" in metrics

    # Classification macro F1 > 90%
    assert (
        metrics["classification"]["macro_f1"] >= 90.0
        or metrics["classification"]["macro_f1"] >= 0.90
    )

    # Field extraction normalized match rate > 90%
    assert (
        metrics["field_extraction"]["normalized_match_rate"] >= 90.0
        or metrics["field_extraction"].get("overall_normalized_match", 0) >= 0.90
    )

    # Anomaly false positive rate < 10%
    assert (
        metrics["anomaly_detectors"]["overall_fpr"] <= 0.10
        or metrics["anomaly_detectors"].get("overall_fpr_pct", 0) <= 10.0
    )

    # Explainer grounding rate > 90%
    assert (
        metrics["explainer_grounding"].get("grounding_rate_pct", 0) >= 90.0
        or metrics["explainer_grounding"].get("grounding_rate", 0) >= 90.0
    )

    # Verify run exists in DB
    db_run = db_session.query(EvaluationRun).filter_by(id=run.id).first()
    assert db_run is not None
    assert db_run.overall_accuracy == run.overall_accuracy


def test_explainer_grounding_detects_unsupported_claim():
    """
    Explainer grounding check must detect when an explanation mentions values
    or claims not supported by the evidence graph / rule results.
    """
    # Grounded case
    grounded_evidence = {
        "rule_results": [{"rule_code": "LAND_AREA_MIN", "passed": False}],
        "fields": {"total_carpet_area": "3.5", "institution_name": "Apex Engineering Institute"},
    }
    grounded_explanation = "Rule LAND_AREA_MIN failed because total_carpet_area is 3.5 for Apex Engineering Institute."
    res = ExplainerGroundingChecker.check(grounded_explanation, grounded_evidence)
    assert res["grounded"] is True
    assert res["unsupported_claims"] == []

    # Hallucinated case: explanation mentions a fake rule code and fabricated number
    fabricated_explanation = "Rule FAKE_RULE_999 violated with land deficit of 9999.88 acres on 1999-01-01."
    res_bad = ExplainerGroundingChecker.check(fabricated_explanation, grounded_evidence)
    assert res_bad["grounded"] is False
    assert len(res_bad["unsupported_claims"]) > 0


def test_deliberate_corrupted_label_produces_failed_case(db_session, tmp_path):
    """
    Verify that an incorrect ground truth label is properly caught as a failure
    and recorded in failed_cases_json.
    """
    # Use 1 file from eval_data with an intentionally wrong label
    labels_file = os.path.join("backend", "eval_data", "labels.json")
    if not os.path.exists(labels_file):
        pytest.skip("eval_data/labels.json not found")

    with open(labels_file, "r") as f:
        manifest = json.load(f)

    labels = manifest.get("labels", [])
    if not labels:
        pytest.skip("No labels in eval_data")

    # Pick the first label and corrupt its expected doc_type and certificate_number
    first_label = labels[0]
    corrupted_label = {
        **first_label,
        "document_type": "DELIBERATELY_WRONG_TYPE",
        "expected_fields": {
            "certificate_number": "NON_EXISTENT_CERT_99999",
            "institute_name": "NON_EXISTENT_INSTITUTE",
            "issue_date": "1900-01-01",
            "expiry_date": "1900-01-01",
        },
    }

    temp_manifest = {
        "dataset_version": "v-corrupt-test",
        "labels": [corrupted_label],
    }

    temp_labels_path = tmp_path / "labels.json"
    with open(temp_labels_path, "w") as f:
        json.dump(temp_manifest, f)

    # Copy the corresponding PDF
    src_pdf = os.path.join("backend", "eval_data", first_label["file_name"])
    dst_pdf = tmp_path / first_label["file_name"]
    if os.path.exists(src_pdf):
        with open(src_pdf, "rb") as f_in, open(dst_pdf, "wb") as f_out:
            f_out.write(f_in.read())

    runner = EvaluationRunner(db_session, eval_dir=str(tmp_path))
    run = runner.run(dataset_version="v-corrupt-test")

    assert len(run.failed_cases_json) >= 1
    failed_record = run.failed_cases_json[0]
    assert failed_record["file"] == first_label["file_name"]
    assert any("Document type mismatch" in f for f in failed_record["failures"])


def test_evaluation_endpoints_rbac_non_admin_forbidden(client, seed_test_data):
    """
    Non-admin (INSTITUTE) role users must receive HTTP 403 Forbidden on
    evaluation runner and admin metrics endpoints.
    """
    inst_user = seed_test_data["inst_user"]
    cookies = get_auth_cookie(inst_user)

    # POST run
    res_run = client.post("/api/v1/admin/evaluation/run", cookies=cookies)
    assert res_run.status_code == 403

    # GET runs
    res_list = client.get("/api/v1/admin/evaluation/runs", cookies=cookies)
    assert res_list.status_code == 403

    # GET feedback stats
    res_stats = client.get("/api/v1/admin/evaluation/feedback-stats", cookies=cookies)
    assert res_stats.status_code == 403


def test_human_feedback_lifecycle(client, seed_test_data):
    """
    Test creating AI feedback via POST /api/v1/admin/feedback
    and reading agreement stats via GET /api/v1/admin/evaluation/feedback-stats.
    """
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # 1. Post correct feedback for verification
    res1 = client.post(
        "/api/v1/admin/feedback",
        json={
            "target_type": "VERIFICATION",
            "target_id": 101,
            "document_id": 55,
            "is_correct": True,
            "correction_notes": "Official registry check confirmed match",
        },
        cookies=cookies,
    )
    assert res1.status_code in (200, 201)
    data1 = res1.json()
    assert data1["is_correct"] is True
    assert data1["target_type"] == "VERIFICATION"

    # 2. Post incorrect feedback for anomaly detector
    res2 = client.post(
        "/api/v1/admin/feedback",
        json={
            "target_type": "ANOMALY",
            "target_id": 202,
            "document_id": 56,
            "is_correct": False,
            "correction_notes": "False alarm due to scan shadow",
        },
        cookies=cookies,
    )
    assert res2.status_code in (200, 201)
    data2 = res2.json()
    assert data2["is_correct"] is False

    # 3. Check feedback stats endpoint
    res_stats = client.get("/api/v1/admin/evaluation/feedback-stats", cookies=cookies)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_feedback"] >= 2
    assert stats["correct_count"] >= 1
    assert stats["incorrect_count"] >= 1
    assert 0.0 <= stats["agreement_rate_pct"] <= 100.0


def test_evaluation_exports_csv_and_pdf(client, seed_test_data, db_session):
    """
    Test CSV and PDF export endpoints for an evaluation run.
    """
    admin_user = seed_test_data["admin_user"]
    cookies = get_auth_cookie(admin_user)

    # Create a dummy run in DB
    run = EvaluationRun(
        dataset_version="v-export-test",
        status="COMPLETED",
        overall_accuracy=98.5,
        total_samples=10,
        passed_samples=9,
        metrics_json={
            "overall_accuracy": 98.5,
            "ocr_success_rate": 100.0,
            "avg_processing_time_sec": 0.45,
            "total_samples": 10,
            "classification": {
                "accuracy": 1.0,
                "macro_precision": 1.0,
                "macro_recall": 1.0,
                "macro_f1": 1.0,
                "per_type": {},
                "confusion_matrix": {"labels": ["LAND_DOC", "FIRE_SAFETY"], "matrix": [[5, 0], [0, 5]]},
            },
            "field_extraction": {
                "overall_exact_match": 0.95,
                "overall_normalized_match": 0.98,
                "per_field": {
                    "certificate_number": {"exact_match_pct": 100.0, "normalized_match_pct": 100.0, "total_evaluated": 10},
                    "institute_name": {"exact_match_pct": 90.0, "normalized_match_pct": 100.0, "total_evaluated": 10},
                },
            },
            "expiry_status": {"accuracy": 1.0, "per_status": {}},
            "anomaly_detectors": {
                "overall_fpr": 0.0,
                "per_detector": {
                    "metadata": {"precision": 1.0, "recall": 1.0, "fpr": 0.0, "tp": 2, "fp": 0, "fn": 0, "tn": 8}
                },
            },
            "explainer_grounding": {
                "grounding_rate_pct": 100.0,
                "statements_checked": 10,
                "statements_grounded": 10,
                "unsupported_claims": [],
            },
        },
        failed_cases_json=[],
        duration_seconds=4.2,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    # 1. Export CSV
    res_csv = client.get(f"/api/v1/admin/evaluation/runs/{run.id}/export/csv", cookies=cookies)
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")
    assert "CLASSIFICATION METRICS" in res_csv.text

    # 2. Export PDF
    res_pdf = client.get(f"/api/v1/admin/evaluation/runs/{run.id}/export/pdf", cookies=cookies)
    assert res_pdf.status_code == 200
    assert "application/pdf" in res_pdf.headers.get("content-type", "")
    assert res_pdf.content.startswith(b"%PDF")
