import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import date


def normalize_string_value(val: Optional[str]) -> str:
    """Normalize string by stripping whitespace, punctuation, and lowercase."""
    if val is None:
        return ""
    s = str(val).lower().strip()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def normalize_date_value(val: Optional[str]) -> Optional[str]:
    """Normalize various date formats into standard ISO YYYY-MM-DD."""
    if not val:
        return None
    s = str(val).strip()
    # Try ISO direct
    try:
        d = date.fromisoformat(s[:10])
        return d.isoformat()
    except Exception:
        pass
    # Try DD-MM-YYYY or DD/MM/YYYY
    m = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b", s)
    if m:
        try:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            return d.isoformat()
        except Exception:
            pass
    return s.strip()


def compute_classification_metrics(
    true_labels: List[str],
    pred_labels: List[str],
    all_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes overall accuracy, per-class precision, recall, F1-score,
    macro averages, and confusion matrix.
    """
    if not true_labels:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "per_type": {},
            "confusion_matrix": {"classes": [], "matrix": []},
        }

    classes = sorted(list(set(true_labels + pred_labels + (all_classes or []))))
    class_to_idx = {c: i for i, c in enumerate(classes)}
    n_classes = len(classes)

    # Initialize confusion matrix [true_idx][pred_idx]
    matrix = [[0 for _ in range(n_classes)] for _ in range(n_classes)]
    total = len(true_labels)
    correct = 0

    for t, p in zip(true_labels, pred_labels):
        if t in class_to_idx and p in class_to_idx:
            matrix[class_to_idx[t]][class_to_idx[p]] += 1
            if t == p:
                correct += 1

    accuracy = round((correct / total) * 100.0, 2) if total > 0 else 0.0

    per_type = {}
    precisions = []
    recalls = []
    f1s = []

    for c in classes:
        idx = class_to_idx[c]
        tp = matrix[idx][idx]
        fp = sum(matrix[r][idx] for r in range(n_classes) if r != idx)
        fn = sum(matrix[idx][col] for col in range(n_classes) if col != idx)
        support = sum(matrix[idx][col] for col in range(n_classes))

        p = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if support == 0 else 0.0)
        r = (tp / (tp + fn)) if (tp + fn) > 0 else (1.0 if support == 0 else 0.0)
        f1 = (2 * p * r / (p + r)) if (p + r) > 0 else 0.0

        if support > 0:
            precisions.append(p)
            recalls.append(r)
            f1s.append(f1)

        per_type[c] = {
            "precision": round(p * 100.0, 1),
            "recall": round(r * 100.0, 1),
            "f1": round(f1 * 100.0, 1),
            "support": support,
        }

    macro_precision = round((sum(precisions) / len(precisions)) * 100.0, 2) if precisions else 0.0
    macro_recall = round((sum(recalls) / len(recalls)) * 100.0, 2) if recalls else 0.0
    macro_f1 = round((sum(f1s) / len(f1s)) * 100.0, 2) if f1s else 0.0

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "macro_f1_ratio": round(macro_f1 / 100.0, 4),
        "per_type": per_type,
        "confusion_matrix": {
            "classes": classes,
            "labels": classes,
            "matrix": matrix,
        },
    }


def compute_field_extraction_metrics(
    field_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes exact-match and normalized-match accuracy for extracted fields.
    Each item in field_results: { field: str, expected: str, actual: str }
    """
    if not field_results:
        return {
            "exact_match_rate": 0.0,
            "normalized_match_rate": 0.0,
            "total_fields_evaluated": 0,
            "per_field": {},
        }

    per_field_stats: Dict[str, Dict[str, int]] = {}
    total_exact = 0
    total_norm = 0
    total_evaluated = len(field_results)

    for item in field_results:
        f_name = item.get("field", "unknown")
        exp = str(item.get("expected") or "").strip()
        act = str(item.get("actual") or "").strip()

        if f_name not in per_field_stats:
            per_field_stats[f_name] = {"total": 0, "exact": 0, "norm": 0}

        per_field_stats[f_name]["total"] += 1

        # 1. Exact Match
        is_exact = (exp.lower() == act.lower())
        if is_exact:
            total_exact += 1
            per_field_stats[f_name]["exact"] += 1

        # 2. Normalized Match
        if "date" in f_name.lower():
            exp_d = normalize_date_value(exp)
            act_d = normalize_date_value(act)
            is_norm = (exp_d == act_d) if (exp_d and act_d) else is_exact
        else:
            exp_norm = normalize_string_value(exp)
            act_norm = normalize_string_value(act)
            is_norm = (exp_norm == act_norm) or (len(exp_norm) > 4 and exp_norm in act_norm) or (len(act_norm) > 4 and act_norm in exp_norm)

        if is_norm or is_exact:
            total_norm += 1
            per_field_stats[f_name]["norm"] += 1

    per_field = {}
    for f_name, stats in per_field_stats.items():
        cnt = stats["total"]
        per_field[f_name] = {
            "total": cnt,
            "exact_match_rate": round((stats["exact"] / cnt) * 100.0, 1) if cnt > 0 else 0.0,
            "normalized_match_rate": round((stats["norm"] / cnt) * 100.0, 1) if cnt > 0 else 0.0,
        }

    exact_pct = round((total_exact / total_evaluated) * 100.0, 2) if total_evaluated > 0 else 0.0
    norm_pct = round((total_norm / total_evaluated) * 100.0, 2) if total_evaluated > 0 else 0.0
    return {
        "exact_match_rate": exact_pct,
        "normalized_match_rate": norm_pct,
        "overall_exact_match": round(exact_pct / 100.0, 4),
        "overall_normalized_match": round(norm_pct / 100.0, 4),
        "total_fields_evaluated": total_evaluated,
        "per_field": per_field,
    }


def compute_anomaly_metrics(
    eval_cases: List[Dict[str, Any]],
    detectors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Computes precision, recall, and False Positive Rate (FPR) per anomaly detector
    and overall across detectors.
    eval_cases items: { file: str, expected_anomalies: List[str], detected_anomalies: List[str] }
    """
    if detectors is None:
        detectors = ["duplicate", "metadata", "date_inconsistency", "name_mismatch"]

    per_detector = {}
    total_tp = 0
    total_fp = 0
    total_tn = 0
    total_fn = 0

    for det in detectors:
        tp = 0
        fp = 0
        tn = 0
        fn = 0

        for case in eval_cases:
            has_expected = any(det in str(a).lower() for a in case.get("expected_anomalies", []))
            has_detected = any(det in str(a).lower() for a in case.get("detected_anomalies", []))

            if has_expected and has_detected:
                tp += 1
            elif not has_expected and has_detected:
                fp += 1
            elif has_expected and not has_detected:
                fn += 1
            else:
                tn += 1

        total_tp += tp
        total_fp += fp
        total_tn += tn
        total_fn += fn

        prec = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if (tp + fn) == 0 else 0.0)
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else (1.0 if (tp + fn) == 0 else 0.0)
        fpr = (fp / (fp + tn)) if (fp + tn) > 0 else 0.0

        per_detector[det] = {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "precision": round(prec * 100.0, 1),
            "recall": round(rec * 100.0, 1),
            "fpr": round(fpr * 100.0, 2),
        }

    overall_prec = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 1.0
    overall_fpr = (total_fp / (total_fp + total_tn)) if (total_fp + total_tn) > 0 else 0.0

    overall_prec_pct = round(overall_prec * 100.0, 1)
    overall_rec_pct = round(overall_rec * 100.0, 1)
    overall_fpr_pct = round(overall_fpr * 100.0, 2)

    return {
        "overall_precision": overall_prec_pct,
        "overall_recall": overall_rec_pct,
        "overall_fpr": round(overall_fpr, 4),
        "overall_fpr_pct": overall_fpr_pct,
        "per_detector": per_detector,
    }


def compute_explainer_grounding_metrics(
    evaluations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validates that statements generated by ExplainerNarrator strictly ground
    on rule results and evidence fields.
    Each item in evaluations: { explanation_text: str, evidence_tokens: List[str] }
    """
    total_statements = 0
    grounded_statements = 0
    violations = []

    for ev in evaluations:
        text = ev.get("explanation_text", "")
        evidence = [str(t).lower() for t in ev.get("evidence_tokens", []) if t]

        # Break into sentences/clauses
        clauses = [c.strip() for c in re.split(r"[.\n;]", text) if len(c.strip()) > 8]
        for c in clauses:
            total_statements += 1
            # Check numbers or IDs in the clause
            tokens = re.findall(r"\b[A-Z0-9_\-]{4,}\b", c)
            unsupported = []
            for tok in tokens:
                tok_l = tok.lower()
                # Skip generic common words or abbreviations
                if tok_l in {"aicte", "approval", "compliance", "process", "handbook", "summary", "rules", "status", "report"}:
                    continue
                # Check if token exists in evidence
                if not any(tok_l in ev_item for ev_item in evidence):
                    unsupported.append(tok)

            if unsupported:
                violations.append({
                    "clause": c[:100],
                    "unsupported_tokens": unsupported,
                })
            else:
                grounded_statements += 1

    grounding_rate = round((grounded_statements / max(total_statements, 1)) * 100.0, 2)
    return {
        "grounding_rate": grounding_rate,
        "grounding_rate_pct": grounding_rate,
        "total_statements_checked": total_statements,
        "statements_checked": total_statements,
        "grounded_statements": grounded_statements,
        "violations_count": len(violations),
        "violations": violations[:10],
        "unsupported_claims": [v["clause"] for v in violations],
    }


class ClassificationEvaluator:
    @staticmethod
    def evaluate(true_labels: List[str], pred_labels: List[str], all_classes: Optional[List[str]] = None) -> Dict[str, Any]:
        return compute_classification_metrics(true_labels, pred_labels, all_classes)


class FieldExtractionEvaluator:
    @staticmethod
    def evaluate(field_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return compute_field_extraction_metrics(field_results)


class AnomalyDetectorEvaluator:
    @staticmethod
    def evaluate(eval_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        return compute_anomaly_metrics(eval_cases)


class ExplainerGroundingChecker:
    @staticmethod
    def check(explanation_text: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check whether an explanation statement's rule codes and values are grounded in evidence.
        """
        # Collect tokens from evidence
        evidence_tokens = set()
        for k, v in evidence.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        for sub_k, sub_v in item.items():
                            evidence_tokens.add(str(sub_k).lower())
                            evidence_tokens.add(str(sub_v).lower())
                    else:
                        evidence_tokens.add(str(item).lower())
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    evidence_tokens.add(str(sub_k).lower())
                    evidence_tokens.add(str(sub_v).lower())
            else:
                evidence_tokens.add(str(k).lower())
                evidence_tokens.add(str(v).lower())

        # Check for capitalized rule codes or large numbers in explanation
        tokens = re.findall(r"\b[A-Z0-9_\.]{4,}\b", explanation_text)
        unsupported = []
        for tok in tokens:
            tok_l = tok.lower()
            if tok_l in {
                "aicte", "approval", "compliance", "process", "handbook",
                "summary", "rules", "status", "report", "because", "failed",
                "passed", "deficiency", "standard", "regulation"
            }:
                continue
            if not any(tok_l in ev or ev in tok_l for ev in evidence_tokens):
                unsupported.append(tok)

        is_grounded = len(unsupported) == 0
        return {
            "grounded": is_grounded,
            "unsupported_claims": unsupported,
            "grounding_rate": 100.0 if is_grounded else 0.0,
        }

