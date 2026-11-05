"""
Evaluation Runner for Verifact.
Runs test manifests through specified vision providers / pipeline modes,
benchmarks latency, fallback rate, and clinical triage performance,
and records reproducible JSON results and Markdown summary tables.
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root and backend are on PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from evaluation.dataset_loaders import (
    DatasetItem,
    load_mura_dataset,
    load_fracatlas_dataset,
    create_or_load_subset_manifest,
    create_mock_test_dataset
)
from evaluation.metrics import compute_clinical_metrics


def run_pipeline_on_image(
    image_path: str,
    provider: str,
    body_part: str = "upper_extremity"
) -> Dict[str, Any]:
    """
    Invokes the pipeline on an image with latency and failure tracking.
    """
    start_time = time.perf_counter()
    status = "success"
    error_msg = None
    y_pred = None
    y_prob = None
    is_fallback = False

    try:
        if provider == "mock":
            # Deterministic mock provider for CI / offline validation
            import hashlib
            h = int(hashlib.md5(image_path.encode()).hexdigest(), 16)
            y_prob = (h % 100) / 100.0
            y_pred = 1 if y_prob >= 0.50 else 0
            time.sleep(0.01)  # Simulate 10ms processing
        else:
            # Import backend ML pipeline
            from app.services.ml_pipeline import _call_multimodal_vision, _clinical_offline_enhancement_engine
            
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            if provider == "offline":
                res = _clinical_offline_enhancement_engine(
                    image_bytes=image_bytes,
                    detected_body_part=body_part
                )
                is_fallback = True
                # In offline enhancement mode, no AI prediction is made
                y_pred = None
                y_prob = None
            else:
                res = _call_multimodal_vision(
                    image_bytes=image_bytes,
                    provider_override=provider,
                    detected_body_part=body_part
                )
                if not res.get("is_ai_analysis", True) or res.get("analysis_mode") == "offline_enhancement_only":
                    is_fallback = True
                
                det = res.get("fracture_detected")
                if det is not None:
                    y_pred = 1 if det is True else 0
                y_prob = res.get("confidence")

    except Exception as e:
        status = "failed"
        error_msg = str(e)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return {
        "status": status,
        "error": error_msg,
        "y_pred": y_pred,
        "y_prob": y_prob,
        "is_fallback": is_fallback,
        "latency_ms": elapsed_ms
    }


def evaluate_dataset(
    items: List[DatasetItem],
    provider: str,
    output_dir: str,
    dataset_name: str,
    save_individual_logs: bool = True
) -> Dict[str, Any]:
    """
    Evaluates a collection of dataset items against a provider.
    """
    print(f"\n=======================================================")
    print(f"Starting Verifact Evaluation: Dataset={dataset_name}, Provider={provider}")
    print(f"Total Samples to Evaluate: {len(items)}")
    print(f"=======================================================\n")

    y_true: List[int] = []
    y_pred: List[int] = []
    y_prob: List[float] = []
    latencies: List[float] = []
    failed_count = 0
    fallback_count = 0
    detailed_records: List[Dict[str, Any]] = []

    for idx, item in enumerate(items, start=1):
        if not os.path.exists(item.image_path):
            failed_count += 1
            print(f"[{idx}/{len(items)}] MISSING FILE: {item.image_path}")
            continue

        result = run_pipeline_on_image(
            image_path=item.image_path,
            provider=provider,
            body_part=item.body_part
        )

        latencies.append(result["latency_ms"])

        if result["status"] == "failed":
            failed_count += 1
            print(f"[{idx}/{len(items)}] FAILED: {result['error']}")
        else:
            if result["is_fallback"]:
                fallback_count += 1

            if result["y_pred"] is not None:
                y_true.append(item.ground_truth)
                y_pred.append(result["y_pred"])
                if result["y_prob"] is not None:
                    y_prob.append(float(result["y_prob"]))

            pred_str = str(result["y_pred"]) if result["y_pred"] is not None else "None (Offline)"
            prob_str = f"{result['y_prob']:.2f}" if result["y_prob"] is not None else "N/A"
            print(f"[{idx}/{len(items)}] GT={item.ground_truth} | Pred={pred_str} (Conf: {prob_str}) | {result['latency_ms']:.1f}ms")

        if save_individual_logs:
            detailed_records.append({
                "index": idx,
                "image_path": item.image_path,
                "ground_truth": item.ground_truth,
                "task": item.task,
                "body_part": item.body_part,
                **result
            })

    # Compute metrics
    # If no predictions were made (e.g. offline enhancement mode), compute honest empty stats
    if not y_true:
        metrics = {
            "sample_count": len(items),
            "evaluated_predictions": 0,
            "notice": "No AI predictions emitted (offline enhancement or all calls failed)",
            "latency": {
                "mean_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "p50_ms": None,
                "p95_ms": None
            },
            "failed_count": failed_count,
            "failure_rate": round(failed_count / len(items), 4) if items else 0.0,
            "fallback_count": fallback_count,
            "fallback_rate": round(fallback_count / len(items), 4) if items else 0.0,
        }
    else:
        metrics = compute_clinical_metrics(
            y_true=y_true,
            y_pred=y_pred,
            y_prob=y_prob if len(y_prob) == len(y_true) else None,
            latencies_ms=latencies,
            total_attempts=len(items),
            failed_count=failed_count,
            fallback_count=fallback_count
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    result_payload = {
        "benchmark_metadata": {
            "dataset": dataset_name,
            "provider": provider,
            "timestamp_utc": timestamp,
            "total_samples": len(items),
            "evaluated_samples": len(y_true),
        },
        "metrics": metrics,
        "sample_records": detailed_records if save_individual_logs else []
    }

    result_file = out_path / f"{dataset_name}_{provider}_{timestamp}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_payload, f, indent=2)

    print(f"\nSaved detailed evaluation JSON to: {result_file}")

    # Update summary markdown table
    update_markdown_summary(out_path / "summary.md", result_payload)

    return result_payload


def update_markdown_summary(summary_md_path: Path, result_payload: Dict[str, Any]):
    """
    Appends or creates a markdown summary table in results directory.
    """
    meta = result_payload["benchmark_metadata"]
    metrics = result_payload["metrics"]
    lat = metrics.get("latency", {})

    header = (
        "# Verifact Evaluation Benchmark Results\n\n"
        "| Timestamp (UTC) | Dataset | Provider | N | Sens (Recall) | Spec | Prec (PPV) | F1 | AUROC | ECE | Mean Latency | Fallback Rate |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )

    sens = f"{metrics.get('sensitivity_recall', 0.0):.3f}" if 'sensitivity_recall' in metrics else "N/A"
    spec = f"{metrics.get('specificity', 0.0):.3f}" if 'specificity' in metrics else "N/A"
    prec = f"{metrics.get('precision_ppv', 0.0):.3f}" if 'precision_ppv' in metrics else "N/A"
    f1 = f"{metrics.get('f1_score', 0.0):.3f}" if 'f1_score' in metrics else "N/A"
    auroc = f"{metrics.get('auroc'):.3f}" if metrics.get('auroc') is not None else "N/A"
    ece = f"{metrics.get('expected_calibration_error_ece'):.3f}" if metrics.get('expected_calibration_error_ece') is not None else "N/A"
    mean_lat = f"{lat.get('mean_ms', 0.0):.1f} ms" if lat.get('mean_ms') is not None else "N/A"
    fb_rate = f"{metrics.get('fallback_rate', 0.0) * 100:.1f}%"

    row = (
        f"| {meta['timestamp_utc']} | {meta['dataset']} | {meta['provider']} | {meta['total_samples']} | "
        f"{sens} | {spec} | {prec} | {f1} | {auroc} | {ece} | {mean_lat} | {fb_rate} |\n"
    )

    if not summary_md_path.exists():
        with open(summary_md_path, "w", encoding="utf-8") as f:
            f.write(header + row)
    else:
        with open(summary_md_path, "a", encoding="utf-8") as f:
            f.write(row)


def main():
    parser = argparse.ArgumentParser(description="Verifact Evaluation Benchmark Runner")
    parser.add_argument("--dataset", choices=["mura", "fracatlas", "mock"], default="mock",
                        help="Dataset to evaluate: 'mura', 'fracatlas', or 'mock'")
    parser.add_argument("--dataset-path", type=str, default=None,
                        help="Path to dataset root directory (or set DATASET_PATH env var)")
    parser.add_argument("--provider", type=str, default="mock",
                        help="Vision provider to test: 'gemini', 'groq', 'offline', or 'mock'")
    parser.add_argument("--manifest", type=str, default=None,
                        help="Path to custom JSON subset manifest")
    parser.add_argument("--n-samples", type=int, default=250,
                        help="Number of subset samples to evaluate (default: 250)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for subset selection (default: 42)")
    parser.add_argument("--output-dir", type=str, default="evaluation/results",
                        help="Output directory for results JSON and summary Markdown")
    args = parser.parse_args()

    output_dir = str(PROJECT_ROOT / args.output_dir) if not os.path.isabs(args.output_dir) else args.output_dir

    # Resolve items
    if args.manifest and os.path.exists(args.manifest):
        with open(args.manifest, "r", encoding="utf-8") as f:
            raw = json.load(f)
            items = [DatasetItem.from_dict(d) for d in raw]
    elif args.dataset == "mock":
        mock_dir = str(PROJECT_ROOT / "evaluation" / "mock_dataset")
        items = create_mock_test_dataset(mock_dir, num_samples=min(args.n_samples, 20))
    elif args.dataset == "mura":
        dataset_path = args.dataset_path or os.getenv("MURA_DATASET_PATH") or os.getenv("DATASET_PATH")
        if not dataset_path or not os.path.exists(dataset_path):
            print(f"ERROR: MURA dataset path not found. Please provide --dataset-path or set MURA_DATASET_PATH env var.")
            sys.exit(1)
        raw_items = load_mura_dataset(dataset_path, split="valid")
        manifest_path = str(PROJECT_ROOT / "evaluation" / "manifests" / "mura_valid_subset_250.json")
        items = create_or_load_subset_manifest(raw_items, manifest_path, n_samples=args.n_samples, seed=args.seed)
    elif args.dataset == "fracatlas":
        dataset_path = args.dataset_path or os.getenv("FRACATLAS_DATASET_PATH") or os.getenv("DATASET_PATH")
        if not dataset_path or not os.path.exists(dataset_path):
            print(f"ERROR: FracAtlas dataset path not found. Please provide --dataset-path or set FRACATLAS_DATASET_PATH env var.")
            sys.exit(1)
        raw_items = load_fracatlas_dataset(dataset_path)
        manifest_path = str(PROJECT_ROOT / "evaluation" / "manifests" / "fracatlas_subset_250.json")
        items = create_or_load_subset_manifest(raw_items, manifest_path, n_samples=args.n_samples, seed=args.seed)

    evaluate_dataset(
        items=items,
        provider=args.provider,
        output_dir=output_dir,
        dataset_name=args.dataset
    )


if __name__ == "__main__":
    main()
