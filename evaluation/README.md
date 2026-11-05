# Verifact Evaluation Harness

The `/evaluation` module provides a reproducible, honest benchmarking suite for musculoskeletal radiograph triage.

> [!IMPORTANT]
> **Dataset Task Distinction**:
> - **MURA**: Stanford ML dataset evaluated strictly for **abnormality detection** (upper extremity: wrist, hand, forearm, elbow, shoulder, humerus, finger). Results are labeled abnormality detection, never fracture detection.
> - **FracAtlas**: Evaluated for **fracture detection** (bone fractures vs non-fractured bones).

---

## 1. Datasets to Download & Where to Put Them

### A. Stanford MURA v1.1 (Abnormality Detection)
1. **Source**: Download from Stanford Machine Learning Group ([MURA Competition](https://stanfordmlgroup.github.io/competitions/mura/)).
2. **Directory Placement**:
   Place the extracted archive in:
   ```text
   evaluation/data/MURA-v1.1/
   ├── valid/
   │   ├── XR_WRIST/
   │   ├── XR_HAND/
   │   ├── XR_FOREARM/
   │   └── ...
   ├── valid_image_paths.csv
   └── valid_labeled_studies.csv
   ```
3. **Environment Variable**:
   ```bash
   export MURA_DATASET_PATH="evaluation/data/MURA-v1.1"
   # Or on Windows PowerShell:
   $env:MURA_DATASET_PATH="evaluation\data\MURA-v1.1"
   ```

### B. FracAtlas (Fracture Detection)
1. **Source**: Download from Figshare ([FracAtlas Dataset](https://figshare.com/articles/dataset/FracAtlas_A_Dataset_for_Fracture_Classification_Localization_and_Segmentation/22363012)).
2. **Directory Placement**:
   Place the extracted folder in:
   ```text
   evaluation/data/FracAtlas/
   ├── dataset.csv
   └── images/
       ├── Fractured/
       └── Non_fractured/
   ```
3. **Environment Variable**:
   ```bash
   export FRACATLAS_DATASET_PATH="evaluation/data/FracAtlas"
   # Or on Windows PowerShell:
   $env:FRACATLAS_DATASET_PATH="evaluation\data\FracAtlas"
   ```

---

## 2. Fixed Reproducible Subset Manifests

To ensure that different models, LLM providers, and CNN checkpoints are compared on identical images, evaluation runs sample a fixed, seeded subset (~200–300 upper-extremity images) saved to disk in:
- `evaluation/manifests/mura_valid_subset_250.json`
- `evaluation/manifests/fracatlas_subset_250.json`

If the manifest does not exist on the first run, it is deterministically generated using seed `42` and saved.

---

## 3. Running the Benchmark

### Dry Run (Mock Mode — No Downloads Required)
To verify the full runner, confusion matrix, AUROC, ECE calibration, and report generation in seconds without downloading datasets:
```bash
python evaluation/runner.py --dataset mock --provider mock --n-samples 20
```

### Offline Enhancement Baseline
Evaluates the offline enhancement pipeline (checks fallback rate and honesty banners):
```bash
python evaluation/runner.py --dataset mock --provider offline --n-samples 20
```

### Live Provider Evaluation (Requires Dataset and API Keys in `.env`)
```bash
# Evaluate Google Gemini Flash on FracAtlas fracture detection
python evaluation/runner.py --dataset fracatlas --provider gemini --n-samples 250

# Evaluate Groq Llama Vision on MURA abnormality detection
python evaluation/runner.py --dataset mura --provider groq --n-samples 250
```

---

## 4. Output Metrics & Results

Each run writes:
1. **Detailed JSON**: `evaluation/results/<dataset>_<provider>_<timestamp>.json` with per-sample predictions, ground truths, latency, and calibration statistics.
2. **Summary Markdown**: `evaluation/results/summary.md` with:
   - Sensitivity (Recall)
   - Specificity
   - Precision (PPV)
   - Negative Predictive Value (NPV)
   - F1 Score
   - AUROC (Area Under the Receiver Operating Characteristic)
   - Expected Calibration Error (ECE)
   - Brier Score
   - Latency (Mean, p50, p95 in ms)
   - Fallback Rate
