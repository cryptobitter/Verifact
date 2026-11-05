"""
Evaluation metrics computation module for Verifact triage pipelines.
Outputs clinical and statistical metrics: sensitivity, specificity, precision, NPV,
F1, AUROC, confusion matrix, calibration (ECE, Brier score), and latency percentiles.
"""

from typing import List, Dict, Any, Optional
import numpy as np


def compute_confusion_matrix(y_true: List[int], y_pred: List[int]) -> Dict[str, int]:
    """
    Computes standard 2x2 confusion matrix counts.
    y_true, y_pred: 1 (positive/abnormal/fracture) or 0 (negative/normal).
    """
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 1)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 1)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 0 and yp == 0)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == 1 and yp == 0)
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def compute_expected_calibration_error(
    y_true: List[int],
    y_prob: List[float],
    n_bins: int = 10
) -> float:
    """
    Computes Expected Calibration Error (ECE) with equal-width probability bins.
    """
    if not y_true or len(y_true) != len(y_prob):
        return 0.0

    y_t = np.array(y_true, dtype=float)
    y_p = np.array(y_prob, dtype=float)

    bin_boundaries = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    total_samples = len(y_t)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # Include upper boundary in last bin
        if i == n_bins - 1:
            in_bin = (y_p >= bin_lower) & (y_p <= bin_upper)
        else:
            in_bin = (y_p >= bin_lower) & (y_p < bin_upper)

        bin_count = np.sum(in_bin)
        if bin_count > 0:
            bin_acc = np.mean(y_t[in_bin])
            bin_conf = np.mean(y_p[in_bin])
            ece += (bin_count / total_samples) * abs(bin_acc - bin_conf)

    return float(round(ece, 4))


def compute_brier_score(y_true: List[int], y_prob: List[float]) -> float:
    """
    Computes Brier Score: mean squared error between probabilities and ground truth.
    """
    if not y_true or len(y_true) != len(y_prob):
        return 0.0
    y_t = np.array(y_true, dtype=float)
    y_p = np.array(y_prob, dtype=float)
    return float(round(float(np.mean((y_p - y_t) ** 2)), 4))


def compute_clinical_metrics(
    y_true: List[int],
    y_pred: List[int],
    y_prob: Optional[List[float]] = None,
    latencies_ms: Optional[List[float]] = None,
    total_attempts: Optional[int] = None,
    failed_count: int = 0,
    fallback_count: int = 0
) -> Dict[str, Any]:
    """
    Computes comprehensive clinical triage metrics.
    """
    cm = compute_confusion_matrix(y_true, y_pred)
    tp, fp, tn, fn = cm["tp"], cm["fp"], cm["tn"], cm["fn"]

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    f1 = (2 * precision * sensitivity) / (precision + sensitivity) if (precision + sensitivity) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0

    auroc = None
    if y_prob is not None and len(set(y_true)) > 1:
        try:
            from sklearn.metrics import roc_auc_score
            auroc = float(round(roc_auc_score(y_true, y_prob), 4))
        except Exception:
            auroc = None

    ece = compute_expected_calibration_error(y_true, y_prob) if y_prob else None
    brier = compute_brier_score(y_true, y_prob) if y_prob else None

    # Latency percentiles
    latency_stats = {
        "mean_ms": None,
        "p50_ms": None,
        "p95_ms": None,
    }
    if latencies_ms and len(latencies_ms) > 0:
        l_arr = np.array(latencies_ms, dtype=float)
        latency_stats = {
            "mean_ms": float(round(float(np.mean(l_arr)), 2)),
            "p50_ms": float(round(float(np.percentile(l_arr, 50)), 2)),
            "p95_ms": float(round(float(np.percentile(l_arr, 95)), 2)),
        }

    total = total_attempts if total_attempts and total_attempts > 0 else (len(y_true) + failed_count)
    failure_rate = round(failed_count / total, 4) if total > 0 else 0.0
    fallback_rate = round(fallback_count / total, 4) if total > 0 else 0.0

    return {
        "sample_count": len(y_true),
        "confusion_matrix": cm,
        "sensitivity_recall": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "precision_ppv": round(precision, 4),
        "npv": round(npv, 4),
        "f1_score": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "auroc": auroc,
        "expected_calibration_error_ece": ece,
        "brier_score": brier,
        "latency": latency_stats,
        "failed_count": failed_count,
        "failure_rate": failure_rate,
        "fallback_count": fallback_count,
        "fallback_rate": fallback_rate,
    }
