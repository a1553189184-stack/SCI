from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LABELS = [
    "Atelectasis",
    "Cardiomegaly",
    "Pleural Effusion",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Pneumonia",
    "No Finding",
]

MODEL_SPECS = {
    "DenseNet121": {
        "tag": "densenet121",
        "pred_prefix": "",
        "metric_prefix": "",
        "checkpoint": "models_large/hf_large_densenet121/best_densenet121.pt",
    },
    "ResNet50": {
        "tag": "resnet50",
        "pred_prefix": "resnet50_",
        "metric_prefix": "resnet50_",
        "checkpoint": "models_large/hf_large_resnet50/best_resnet50.pt",
    },
    "EfficientNet-B0": {
        "tag": "efficientnet_b0",
        "pred_prefix": "efficientnet_b0_",
        "metric_prefix": "efficientnet_b0_",
        "checkpoint": "models_large/hf_large_efficientnet_b0/best_efficientnet_b0.pt",
    },
}


def fmt(x: object, digits: int = 3) -> str:
    try:
        val = float(x)
    except Exception:
        return str(x)
    if not np.isfinite(val):
        return "NA"
    return f"{val:.{digits}f}"


def pct(x: object, digits: int = 1) -> str:
    try:
        val = float(x)
    except Exception:
        return str(x)
    if not np.isfinite(val):
        return "NA"
    return f"{100 * val:.{digits}f}%"


def ci_text(row: pd.Series, metric: str) -> str:
    value = row.get(metric, np.nan)
    lo = row.get(f"{metric}_ci_lower", np.nan)
    hi = row.get(f"{metric}_ci_upper", np.nan)
    if not (np.isfinite(value) and np.isfinite(lo) and np.isfinite(hi)):
        return "NA"
    return f"{value:.3f} ({lo:.3f}-{hi:.3f})"


def label_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["average"].astype(str).eq("label")].copy()


def macro_row(df: pd.DataFrame) -> pd.Series:
    sub = df[(df["average"].astype(str).eq("macro")) & (df["label"].astype(str).eq("macro"))]
    if sub.empty:
        raise ValueError("Macro row not found.")
    return sub.iloc[0]


def read_metrics(model: str, split: str) -> pd.DataFrame:
    prefix = MODEL_SPECS[model]["metric_prefix"]
    file_name = f"{prefix}{'internal_metrics' if split == 'internal' else 'external_metrics'}.csv"
    return pd.read_csv(ROOT / "tables_large" / file_name)


def read_predictions(model: str, split: str) -> pd.DataFrame:
    prefix = MODEL_SPECS[model]["pred_prefix"]
    file_name = f"{prefix}{'internal_test_predictions' if split == 'internal' else 'external_vindr_predictions'}.csv"
    return pd.read_csv(ROOT / "predictions_large" / file_name)


def label_prevalence_from_predictions(pred: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(pred)
    for label in LABELS:
        positives = int(pd.to_numeric(pred[f"true_{label}"], errors="coerce").fillna(0).sum())
        rows.append(
            {
                "label": label,
                "n": n,
                "positives": positives,
                "negatives": int(n - positives),
                "prevalence": positives / n if n else np.nan,
                "externally_evaluable": positives > 0 and positives < n,
            }
        )
    return pd.DataFrame(rows)


def metric_value(df: pd.DataFrame, label: str, metric: str) -> float:
    sub = df[(df["average"].astype(str).eq("label")) & (df["label"].astype(str).eq(label))]
    if sub.empty:
        return float("nan")
    return float(pd.to_numeric(sub.iloc[0].get(metric), errors="coerce"))


def macro_for_labels(metrics: pd.DataFrame, labels: list[str], metric: str) -> float:
    vals = [metric_value(metrics, label, metric) for label in labels]
    vals = np.array([v for v in vals if np.isfinite(v)], dtype=float)
    return float(vals.mean()) if len(vals) else float("nan")


def safe_auroc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(y_true, y_score))


def safe_auprc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float("nan")
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(y_true, y_score))


def macro_from_predictions(pred: pd.DataFrame, labels: list[str], metric: str) -> float:
    vals = []
    for label in labels:
        y_true = pred[f"true_{label}"].to_numpy(dtype=int)
        y_score = pred[f"prob_{label}"].to_numpy(dtype=float)
        val = safe_auroc(y_true, y_score) if metric == "auroc" else safe_auprc(y_true, y_score)
        if np.isfinite(val):
            vals.append(val)
    return float(np.mean(vals)) if vals else float("nan")


def _prepare_bootstrap_arrays(preds: dict[str, pd.DataFrame], common_patients: list[str], labels: list[str]) -> dict[str, dict[str, object]]:
    prepared: dict[str, dict[str, object]] = {}
    for model, df in preds.items():
        patient_series = df["patient_id"].astype(str)
        grouped_indices = patient_series.groupby(patient_series).indices
        patient_indices = [np.asarray(grouped_indices[str(patient)], dtype=int) for patient in common_patients]
        arrays = {}
        for label in labels:
            arrays[label] = {
                "true": df[f"true_{label}"].to_numpy(dtype=int),
                "prob": df[f"prob_{label}"].to_numpy(dtype=float),
            }
        prepared[model] = {"patient_indices": patient_indices, "arrays": arrays}
    return prepared


def _macro_from_arrays(prepared_model: dict[str, object], sampled_patient_indices: np.ndarray, labels: list[str], metric: str) -> float:
    patient_indices = prepared_model["patient_indices"]
    if len(sampled_patient_indices) == 0:
        return float("nan")
    row_idx = np.concatenate([patient_indices[int(i)] for i in sampled_patient_indices])
    arrays = prepared_model["arrays"]
    vals = []
    for label in labels:
        y_true = arrays[label]["true"][row_idx]
        y_score = arrays[label]["prob"][row_idx]
        val = safe_auroc(y_true, y_score) if metric == "auroc" else safe_auprc(y_true, y_score)
        if np.isfinite(val):
            vals.append(val)
    return float(np.mean(vals)) if vals else float("nan")


def bootstrap_paired_model_comparison(
    dataset_name: str,
    split: str,
    label_set_name: str,
    labels: list[str],
    n_bootstrap: int = 500,
    seed: int = 20260614,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    preds = {model: read_predictions(model, split) for model in MODEL_SPECS}
    patient_sets = [set(df["patient_id"].astype(str).unique()) for df in preds.values()]
    common_patients = sorted(set.intersection(*patient_sets))
    if not common_patients:
        return pd.DataFrame()

    prepared = _prepare_bootstrap_arrays(preds, common_patients, labels)
    model_pairs = [
        ("DenseNet121", "ResNet50"),
        ("DenseNet121", "EfficientNet-B0"),
        ("ResNet50", "EfficientNet-B0"),
    ]
    point_estimates = {
        model: {metric: macro_from_predictions(preds[model], labels, metric) for metric in ["auroc", "auprc"]}
        for model in MODEL_SPECS
    }
    rows = []
    n_patients = len(common_patients)
    for metric in ["auroc", "auprc"]:
        diffs = {pair: [] for pair in model_pairs}
        for _ in range(n_bootstrap):
            sampled = rng.integers(0, n_patients, size=n_patients)
            boot_metrics = {
                model: _macro_from_arrays(prepared[model], sampled, labels, metric)
                for model in MODEL_SPECS
            }
            for pair in model_pairs:
                a, b = pair
                if np.isfinite(boot_metrics[a]) and np.isfinite(boot_metrics[b]):
                    diffs[pair].append(boot_metrics[a] - boot_metrics[b])
        for a, b in model_pairs:
            diff_point = point_estimates[a][metric] - point_estimates[b][metric]
            arr = np.asarray(diffs[(a, b)], dtype=float)
            if len(arr):
                lo, hi = np.percentile(arr, [2.5, 97.5])
                excludes_zero = bool(lo > 0 or hi < 0)
            else:
                lo = hi = float("nan")
                excludes_zero = False
            rows.append(
                {
                    "dataset": dataset_name,
                    "label_set": label_set_name,
                    "metric": metric,
                    "model_a": a,
                    "model_b": b,
                    "model_a_macro": point_estimates[a][metric],
                    "model_b_macro": point_estimates[b][metric],
                    "difference_a_minus_b": diff_point,
                    "ci_lower": lo,
                    "ci_upper": hi,
                    "n_bootstrap": n_bootstrap,
                    "patient_level": True,
                    "ci_excludes_zero": excludes_zero,
                    "interpretation": "descriptive paired bootstrap; not a confirmatory superiority test",
                }
            )
    return pd.DataFrame(rows)


def save_table(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def make_table1() -> pd.DataFrame:
    split_stats = pd.read_csv(ROOT / "splits_large" / "hf_large_nih_split_statistics.csv")
    nih_meta = pd.read_csv(ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv")
    vindr_meta = pd.read_csv(ROOT / "metadata_large" / "hf_large_vindr_clean_metadata.csv")
    rows = [
        {
            "dataset": "NIH ChestX-ray14 public parquet subset",
            "role": "development",
            "split": "overall",
            "n_images": len(nih_meta),
            "n_patients": nih_meta["patient_id"].nunique(),
            "patient_level_split": "yes",
            "notes": "selected public subset; frontal AP/PA images retained",
        }
    ]
    for _, row in split_stats.iterrows():
        rows.append(
            {
                "dataset": "NIH ChestX-ray14 public parquet subset",
                "role": "development",
                "split": row["split"],
                "n_images": int(row["n_images"]),
                "n_patients": int(row["n_patients"]),
                "patient_level_split": "yes",
                "notes": "no patient overlap across NIH splits",
            }
        )
    rows.append(
        {
            "dataset": "VinDr-CXR/VinBigData-derived public PNG subset",
            "role": "independent external validation",
            "split": "external",
            "n_images": len(vindr_meta),
            "n_patients": vindr_meta["patient_id"].nunique(),
            "patient_level_split": "not applicable",
            "notes": "image-level identifiers used as patient identifiers in cached subset; no threshold tuning or calibration fitting",
        }
    )
    return pd.DataFrame(rows)


def make_table2(external_prev: pd.DataFrame) -> pd.DataFrame:
    role_map = {
        "Atelectasis": "primary; external-evaluable",
        "Cardiomegaly": "primary; external-evaluable",
        "Pleural Effusion": "primary; external-evaluable",
        "Pneumothorax": "primary; external-evaluable",
        "Consolidation": "primary; external-evaluable",
        "Edema": "primary internally; external unevaluable in cached subset",
        "Pneumonia": "sensitivity internally; external unevaluable in cached subset",
        "No Finding": "sensitivity/reference label; external-evaluable",
    }
    rows = []
    for label in LABELS:
        ext = external_prev[external_prev["label"].eq(label)].iloc[0]
        rows.append(
            {
                "harmonized_label": label,
                "nih_label_source": label,
                "vindr_label_source": label if int(ext["positives"]) > 0 else "not present as positive finding in analyzed cached subset",
                "analysis_role": role_map[label],
                "nih_coding": "1 positive, 0 negative/missing",
                "vindr_coding": "1 positive, 0 negative/missing",
                "external_positives_in_analyzed_subset": int(ext["positives"]),
                "external_evaluable_for_auc_pr": bool(ext["externally_evaluable"]),
                "caution": "AUROC/AUPRC are NA when the external subset has no positive cases" if not bool(ext["externally_evaluable"]) else "",
            }
        )
    return pd.DataFrame(rows)


def make_densenet_labelwise_table(internal_prev: pd.DataFrame, external_prev: pd.DataFrame) -> pd.DataFrame:
    internal = label_rows(read_metrics("DenseNet121", "internal"))
    external = label_rows(read_metrics("DenseNet121", "external"))
    threshold = pd.read_csv(ROOT / "tables_large" / "thresholds_from_val.csv")
    rows = []
    for label in LABELS:
        irow = internal[internal["label"].eq(label)].iloc[0]
        erow = external[external["label"].eq(label)].iloc[0]
        trow = threshold[threshold["label"].eq(label)].iloc[0]
        iprev = internal_prev[internal_prev["label"].eq(label)].iloc[0]
        eprev = external_prev[external_prev["label"].eq(label)].iloc[0]
        rows.append(
            {
                "label": label,
                "nih_internal_prevalence": iprev["prevalence"],
                "vindr_external_prevalence": eprev["prevalence"],
                "validation_threshold": trow["threshold"],
                "internal_auroc_95ci": ci_text(irow, "auroc"),
                "external_auroc_95ci": ci_text(erow, "auroc"),
                "internal_auprc_95ci": ci_text(irow, "auprc"),
                "external_auprc_95ci": ci_text(erow, "auprc"),
                "internal_f1_95ci": ci_text(irow, "f1"),
                "external_f1_95ci": ci_text(erow, "f1"),
                "internal_sensitivity_95ci": ci_text(irow, "sensitivity"),
                "external_sensitivity_95ci": ci_text(erow, "sensitivity"),
                "internal_specificity_95ci": ci_text(irow, "specificity"),
                "external_specificity_95ci": ci_text(erow, "specificity"),
                "external_analysis_status": "evaluable" if bool(eprev["externally_evaluable"]) else "not evaluable for discrimination",
            }
        )
    return pd.DataFrame(rows)


def make_model_macro_table(external_eval_labels: list[str]) -> pd.DataFrame:
    rows = []
    for model in MODEL_SPECS:
        internal = read_metrics(model, "internal")
        external = read_metrics(model, "external")
        i_macro = macro_row(internal)
        e_macro = macro_row(external)
        rows.append(
            {
                "model": model,
                "internal_all_labels_macro_auroc": i_macro["auroc"],
                "internal_all_labels_macro_auprc": i_macro["auprc"],
                "internal_external_evaluable_labels_macro_auroc": macro_for_labels(internal, external_eval_labels, "auroc"),
                "internal_external_evaluable_labels_macro_auprc": macro_for_labels(internal, external_eval_labels, "auprc"),
                "external_nonzero_prevalence_labels_macro_auroc": macro_for_labels(external, external_eval_labels, "auroc"),
                "external_nonzero_prevalence_labels_macro_auprc": macro_for_labels(external, external_eval_labels, "auprc"),
                "full_external_reported_macro_auroc_nan_skipped": e_macro["auroc"],
                "full_external_reported_macro_auprc_nan_skipped": e_macro["auprc"],
                "external_evaluable_label_set": "; ".join(external_eval_labels),
                "checkpoint_path": str(ROOT / MODEL_SPECS[model]["checkpoint"]),
            }
        )
    return pd.DataFrame(rows)


def make_calibration_table() -> pd.DataFrame:
    cal = pd.read_csv(ROOT / "tables_large" / "calibration_metrics.csv")
    rows = []
    for _, row in cal[(cal["average"].eq("macro")) & (cal["label"].eq("macro"))].iterrows():
        rows.append(
            {
                "dataset": row["dataset"],
                "calibration_method": row["method"],
                "fit_dataset": "NIH calibration split" if row["method"] != "uncalibrated" else "not fitted",
                "brier_score": row["brier"],
                "ece": row["ece"],
                "mce": row["mce"],
                "calibration_slope": row["slope"],
                "calibration_intercept": row["intercept"],
                "external_fitting_used": "no",
                "interpretation_note": "VinDr metrics evaluate transfer of NIH-fitted calibration only",
            }
        )
    return pd.DataFrame(rows)


def make_subgroup_table(external_eval_labels: list[str]) -> pd.DataFrame:
    from src.metrics import compute_metrics

    pred = read_predictions("DenseNet121", "internal")
    rows = []
    for variable in ["sex", "view_position"]:
        if variable not in pred.columns:
            continue
        for value, group in pred.groupby(variable, dropna=True):
            if len(group) < 20:
                continue
            metrics_all = compute_metrics(group, LABELS, f"NIH_internal_{variable}_{value}")
            metrics_eval = compute_metrics(group, external_eval_labels, f"NIH_internal_{variable}_{value}_external_evaluable")
            ma = macro_row(metrics_all)
            me = macro_row(metrics_eval)
            rows.append(
                {
                    "dataset": "NIH internal test",
                    "subgroup_variable": variable,
                    "subgroup": value,
                    "n_images": len(group),
                    "n_patients": group["patient_id"].nunique(),
                    "all_label_macro_auroc": ma["auroc"],
                    "all_label_macro_auprc": ma["auprc"],
                    "external_evaluable_label_macro_auroc": me["auroc"],
                    "external_evaluable_label_macro_auprc": me["auprc"],
                    "analysis_status": "descriptive; not powered for fairness inference",
                }
            )
    rows.append(
        {
            "dataset": "VinDr external",
            "subgroup_variable": "age/sex/view_position",
            "subgroup": "not analyzed",
            "n_images": len(read_predictions("DenseNet121", "external")),
            "n_patients": read_predictions("DenseNet121", "external")["patient_id"].nunique(),
            "all_label_macro_auroc": np.nan,
            "all_label_macro_auprc": np.nan,
            "external_evaluable_label_macro_auroc": np.nan,
            "external_evaluable_label_macro_auprc": np.nan,
            "analysis_status": "cached external subset lacks reliable age/sex metadata",
        }
    )
    return pd.DataFrame(rows)


def make_comparator_labelwise_table(model: str) -> pd.DataFrame:
    internal = label_rows(read_metrics(model, "internal"))
    external = label_rows(read_metrics(model, "external"))
    rows = []
    for label in LABELS:
        irow = internal[internal["label"].eq(label)].iloc[0]
        erow = external[external["label"].eq(label)].iloc[0]
        rows.append(
            {
                "model": model,
                "label": label,
                "internal_auroc_95ci": ci_text(irow, "auroc"),
                "external_auroc_95ci": ci_text(erow, "auroc"),
                "internal_auprc_95ci": ci_text(irow, "auprc"),
                "external_auprc_95ci": ci_text(erow, "auprc"),
                "internal_f1_95ci": ci_text(irow, "f1"),
                "external_f1_95ci": ci_text(erow, "f1"),
            }
        )
    return pd.DataFrame(rows)


def make_auprc_baseline_lift_table() -> pd.DataFrame:
    rows = []
    for model in MODEL_SPECS:
        for split, dataset_name in [("internal", "NIH internal test"), ("external", "VinDr external")]:
            pred = read_predictions(model, split)
            metrics = label_rows(read_metrics(model, split))
            for label in LABELS:
                y = pred[f"true_{label}"].to_numpy(dtype=int)
                prevalence = float(y.mean()) if len(y) else float("nan")
                auprc = metric_value(metrics, label, "auprc")
                rows.append(
                    {
                        "model": model,
                        "dataset": dataset_name,
                        "label": label,
                        "n": len(y),
                        "positives": int(y.sum()),
                        "auprc": auprc,
                        "auprc_baseline_prevalence": prevalence,
                        "auprc_absolute_gain": auprc - prevalence if np.isfinite(auprc) else np.nan,
                        "auprc_lift_over_prevalence": auprc / prevalence if np.isfinite(auprc) and prevalence > 0 else np.nan,
                        "status": "evaluable" if int(y.sum()) > 0 and int(y.sum()) < len(y) else "not evaluable",
                    }
                )
    return pd.DataFrame(rows)


def make_hyperparameter_table() -> pd.DataFrame:
    env = json.loads((ROOT / "outputs_large" / "training" / "hf_large_densenet121" / "environment_report.json").read_text(encoding="utf-8"))
    rows = [
        ("image_size", "224 x 224"),
        ("architecture_main", "DenseNet121"),
        ("architecture_comparators", "ResNet50; EfficientNet-B0"),
        ("pretraining", "ImageNet pretrained torchvision weights"),
        ("loss", "BCEWithLogitsLoss with positive class weights"),
        ("optimizer", "AdamW"),
        ("learning_rate", "0.0001"),
        ("weight_decay", "0.0001"),
        ("epochs", "5"),
        ("early_stopping_patience", "3"),
        ("monitor", "validation macro AUPRC"),
        ("train_batch_size", "24"),
        ("eval_batch_size", "48"),
        ("augmentation", "horizontal flip p=0.5; random rotation +/-7 degrees"),
        ("mixed_precision", "enabled when CUDA available"),
        ("threshold_selection", "per-label F1 maximization on NIH validation split only"),
        ("calibration_fit", "NIH calibration split only"),
        ("bootstrap_iterations", "500 patient-level resamples"),
        ("random_seed", "20260614"),
        ("python", env.get("python", "[TO BE FILLED]")),
        ("torch", env.get("torch", "[TO BE FILLED]")),
        ("cuda_available", str(env.get("cuda_available", "[TO BE FILLED]"))),
        ("torch_cuda", str(env.get("torch_cuda", "[TO BE FILLED]"))),
        ("gpu", env.get("gpu_name", "[TO BE FILLED]")),
    ]
    return pd.DataFrame(rows, columns=["parameter", "value"])


def make_reproducibility_table() -> pd.DataFrame:
    commands = [
        ("create environment", "python -m venv .venv && .venv\\Scripts\\python -m pip install -r environment\\requirements.txt"),
        ("prepare large cached public subset", ".venv\\Scripts\\python scripts\\prepare_hf_large.py"),
        ("train DenseNet121", ".venv\\Scripts\\python -m src.train --config configs\\hf_large.yaml"),
        ("evaluate internal", ".venv\\Scripts\\python -m src.evaluate_internal --config configs\\hf_large.yaml"),
        ("evaluate external", ".venv\\Scripts\\python -m src.evaluate_external --config configs\\hf_large.yaml"),
        ("fit calibration on NIH calibration split", ".venv\\Scripts\\python -m src.calibration --config configs\\hf_large.yaml"),
        ("generate Grad-CAM failure-mode panels", ".venv\\Scripts\\python -m src.gradcam --config configs\\hf_large.yaml"),
        ("generate manuscript assets", ".venv\\Scripts\\python scripts\\build_10_upgrade_assets.py"),
    ]
    return pd.DataFrame(commands, columns=["step", "command"])


def save_workflow_figure(out: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    fig, ax = plt.subplots(figsize=(10.8, 4.2), dpi=160)
    ax.axis("off")
    boxes = [
        ("NIH ChestX-ray14\n5,000 images\n3,795 patients", 0.05, 0.62, "#E8F1F2"),
        ("Patient-level split\ntrain / validation /\ncalibration / internal test", 0.27, 0.62, "#F4F1DE"),
        ("Train three CNNs\nDenseNet121 main\nResNet50, EfficientNet-B0", 0.49, 0.62, "#EAE4F2"),
        ("Thresholds chosen\non NIH validation only", 0.71, 0.62, "#FCE8D5"),
        ("NIH calibration split\nfit temperature, Platt,\nisotonic only", 0.27, 0.20, "#EAF5E4"),
        ("NIH internal test\nperformance, calibration,\nGrad-CAM++", 0.49, 0.20, "#EEF2FF"),
        ("VinDr external subset\n1,000 images\nno tuning or fitting", 0.71, 0.20, "#FDECEF"),
    ]
    for text, x, y, color in boxes:
        patch = FancyBboxPatch((x, y), 0.18, 0.22, boxstyle="round,pad=0.015,rounding_size=0.015", fc=color, ec="#374151", lw=0.8)
        ax.add_patch(patch)
        ax.text(x + 0.09, y + 0.11, text, ha="center", va="center", fontsize=8.3)
    arrows = [
        ((0.23, 0.73), (0.27, 0.73)),
        ((0.45, 0.73), (0.49, 0.73)),
        ((0.67, 0.73), (0.71, 0.73)),
        ((0.36, 0.62), (0.36, 0.42)),
        ((0.58, 0.62), (0.58, 0.42)),
        ((0.80, 0.62), (0.80, 0.42)),
        ((0.45, 0.31), (0.49, 0.31)),
        ((0.67, 0.31), (0.71, 0.31)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops=dict(arrowstyle="->", color="#374151", lw=1.0))
    ax.text(0.5, 0.05, "Analysis guardrails: no patient leakage across NIH splits; VinDr used only after model, threshold, and calibration choices were fixed.", ha="center", fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def save_figure2_densenet_ci(table3: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt

    y = np.arange(len(table3))
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 5.0), dpi=160, sharey=True)
    raw_internal = label_rows(read_metrics("DenseNet121", "internal")).set_index("label")
    raw_external = label_rows(read_metrics("DenseNet121", "external")).set_index("label")
    for ax, metric, title in zip(axes, ["auroc", "auprc"], ["AUROC", "AUPRC"]):
        for offset, source, color, marker, label_name in [
            (-0.12, raw_internal, "#2F6B9A", "o", "NIH internal"),
            (0.12, raw_external, "#B85C5C", "s", "VinDr external"),
        ]:
            vals = []
            xerr_low = []
            xerr_high = []
            yy = []
            for i, label in enumerate(table3["label"]):
                row = source.loc[label]
                val = float(row[metric]) if np.isfinite(row[metric]) else np.nan
                lo = float(row[f"{metric}_ci_lower"]) if np.isfinite(row[f"{metric}_ci_lower"]) else np.nan
                hi = float(row[f"{metric}_ci_upper"]) if np.isfinite(row[f"{metric}_ci_upper"]) else np.nan
                if np.isfinite(val):
                    vals.append(val)
                    xerr_low.append(max(0.0, val - lo) if np.isfinite(lo) else 0)
                    xerr_high.append(max(0.0, hi - val) if np.isfinite(hi) else 0)
                    yy.append(i + offset)
                elif source is raw_external:
                    ax.text(0.04, i + offset, "NA", color=color, fontsize=7, va="center")
            ax.errorbar(vals, yy, xerr=[xerr_low, xerr_high], fmt=marker, color=color, ecolor=color, ms=4, lw=1, capsize=2, label=label_name)
        ax.set_xlim(0, 1)
        ax.set_xlabel(title)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.25)
    axes[0].set_yticks(y, table3["label"])
    axes[1].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def save_figure3_prevalence_lift(auprc_table: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt

    sub = auprc_table[(auprc_table["model"].eq("DenseNet121")) & (auprc_table["status"].eq("evaluable"))].copy()
    labels = LABELS
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), dpi=160, sharey=True)
    for ax, dataset in zip(axes, ["NIH internal test", "VinDr external"]):
        d = sub[sub["dataset"].eq(dataset)].set_index("label").reindex(labels)
        y = np.arange(len(d))
        ax.barh(y - 0.18, d["auprc_baseline_prevalence"], height=0.32, color="#B8C6D6", label="Prevalence baseline")
        ax.barh(y + 0.18, d["auprc"], height=0.32, color="#386FA4", label="Observed AUPRC")
        for yi, row in enumerate(d.itertuples()):
            if np.isfinite(row.auprc_lift_over_prevalence):
                ax.text(min(row.auprc + 0.02, 0.95), yi + 0.18, f"{row.auprc_lift_over_prevalence:.1f}x", fontsize=7, va="center")
        ax.set_xlim(0, 1)
        ax.set_title(dataset)
        ax.set_xlabel("AUPRC or prevalence")
        ax.grid(axis="x", alpha=0.25)
    axes[0].set_yticks(np.arange(len(labels)), labels)
    axes[1].legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def compose_images(images: list[Path], out: Path, orientation: str = "horizontal") -> None:
    from PIL import Image

    opened = [Image.open(p).convert("RGB") for p in images if p.exists()]
    if not opened:
        return
    if orientation == "horizontal":
        target_h = 620
        resized = [im.resize((int(im.width * target_h / im.height), target_h)) for im in opened]
        canvas = Image.new("RGB", (sum(im.width for im in resized), target_h), "white")
        x = 0
        for im in resized:
            canvas.paste(im, (x, 0))
            x += im.width
    else:
        target_w = 1050
        resized = [im.resize((target_w, int(im.height * target_w / im.width))) for im in opened]
        canvas = Image.new("RGB", (target_w, sum(im.height for im in resized)), "white")
        y = 0
        for im in resized:
            canvas.paste(im, (0, y))
            y += im.height
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def save_figure6_drop(drop_table: pd.DataFrame, out: Path) -> None:
    import matplotlib.pyplot as plt

    sub = drop_table[(drop_table["average"].eq("label")) & (drop_table["metric"].eq("auroc"))].copy()
    sub["absolute_drop"] = pd.to_numeric(sub["absolute_drop"], errors="coerce")
    sub = sub.sort_values("absolute_drop")
    fig, ax = plt.subplots(figsize=(7.8, 4.4), dpi=160)
    colors = ["#B85C5C" if v > 0 else "#3E7C8A" for v in sub["absolute_drop"]]
    ax.barh(sub["label"], sub["absolute_drop"], color=colors)
    ax.axvline(0, color="#111827", lw=0.8)
    ax.set_xlabel("Internal AUROC minus external AUROC")
    ax.set_title("Direction and magnitude of external AUROC change")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)


def save_supp_roc_pr(pred: pd.DataFrame, out: Path, source_dir: Path) -> None:
    import matplotlib.pyplot as plt
    from sklearn.metrics import precision_recall_curve, roc_curve

    rows = []
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 8.2), dpi=150)
    panels = [
        ("NIH internal test", read_predictions("DenseNet121", "internal")),
        ("VinDr external", read_predictions("DenseNet121", "external")),
    ]
    for col, (dataset, df) in enumerate(panels):
        ax_roc = axes[0, col]
        ax_pr = axes[1, col]
        ax_roc.plot([0, 1], [0, 1], "--", color="#9CA3AF", lw=0.8)
        for label in LABELS:
            y = df[f"true_{label}"].to_numpy(dtype=int)
            prob = df[f"prob_{label}"].to_numpy(dtype=float)
            if len(np.unique(y)) < 2:
                continue
            fpr, tpr, roc_threshold = roc_curve(y, prob)
            precision, recall, pr_threshold = precision_recall_curve(y, prob)
            ax_roc.plot(fpr, tpr, lw=1.1, label=label)
            ax_pr.plot(recall, precision, lw=1.1, label=label)
            for f, t, thr in zip(fpr, tpr, np.r_[roc_threshold]):
                rows.append({"dataset": dataset, "label": label, "curve": "roc", "x": f, "y": t, "threshold": thr})
            for r, p in zip(recall, precision):
                rows.append({"dataset": dataset, "label": label, "curve": "pr", "x": r, "y": p, "threshold": np.nan})
        ax_roc.set_title(f"{dataset}: ROC")
        ax_roc.set_xlabel("False positive rate")
        ax_roc.set_ylabel("True positive rate")
        ax_roc.grid(alpha=0.25)
        ax_pr.set_title(f"{dataset}: precision-recall")
        ax_pr.set_xlabel("Recall")
        ax_pr.set_ylabel("Precision")
        ax_pr.grid(alpha=0.25)
    axes[0, 1].legend(fontsize=6, loc="lower right")
    axes[1, 1].legend(fontsize=6, loc="upper right")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    save_table(source_dir / "supplementary_roc_pr_curves_densenet121_source.csv", pd.DataFrame(rows))


def save_supp_probability_distributions(out: Path, source_dir: Path) -> None:
    import matplotlib.pyplot as plt

    rows = []
    fig, axes = plt.subplots(4, 2, figsize=(10.0, 12.0), dpi=150)
    internal = read_predictions("DenseNet121", "internal")
    external = read_predictions("DenseNet121", "external")
    for ax, label in zip(axes.ravel(), LABELS):
        for dataset, df, color in [("NIH internal test", internal, "#2F6B9A"), ("VinDr external", external, "#B85C5C")]:
            probs = df[f"prob_{label}"].to_numpy(dtype=float)
            ax.hist(probs, bins=np.linspace(0, 1, 31), density=True, histtype="step", lw=1.2, color=color, label=dataset)
            for value in probs:
                rows.append({"dataset": dataset, "label": label, "probability": value})
        ax.set_title(label, fontsize=9)
        ax.set_xlim(0, 1)
        ax.grid(alpha=0.2)
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300)
    fig.savefig(out.with_suffix(".pdf"))
    plt.close(fig)
    save_table(source_dir / "supplementary_probability_distributions_densenet121_source.csv", pd.DataFrame(rows))


def copy_or_create_gradcam_figure(out: Path) -> None:
    source = ROOT / "figures_large" / "figure4_gradcam_failure_modes_large.png"
    if source.exists():
        shutil.copy2(source, out)
        return
    internal = ROOT / "figures_large" / "gradcam_internal_examples.png"
    external = ROOT / "figures_large" / "gradcam_vindr_examples.png"
    compose_images([internal, external], out, orientation="horizontal")


def write_registry(registry: dict) -> None:
    out = ROOT / "outputs_large" / "manuscript_value_registry_10_upgrade.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def main() -> None:
    tables = ROOT / "tables_large"
    figs = ROOT / "figures_large"
    outputs = ROOT / "outputs_large"
    source_dir = outputs / "figure_source_data_10_upgrade"
    tables.mkdir(exist_ok=True)
    figs.mkdir(exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    internal_pred = read_predictions("DenseNet121", "internal")
    external_pred = read_predictions("DenseNet121", "external")
    internal_prev = label_prevalence_from_predictions(internal_pred)
    external_prev = label_prevalence_from_predictions(external_pred)
    external_eval_labels = external_prev.loc[external_prev["externally_evaluable"], "label"].tolist()

    table1 = make_table1()
    table2 = make_table2(external_prev)
    table3 = make_densenet_labelwise_table(internal_prev, external_prev)
    table4 = make_model_macro_table(external_eval_labels)
    table5 = make_calibration_table()
    table6 = make_subgroup_table(external_eval_labels)
    supp_resnet = make_comparator_labelwise_table("ResNet50")
    supp_eff = make_comparator_labelwise_table("EfficientNet-B0")
    supp_thresholds = pd.read_csv(tables / "thresholds_from_val.csv")
    supp_auprc = make_auprc_baseline_lift_table()
    supp_cal = pd.read_csv(tables / "calibration_metrics.csv")
    supp_hyper = make_hyperparameter_table()
    supp_repro = make_reproducibility_table()
    medmnist = pd.DataFrame(
        [
            {
                "analysis": "MedMNIST pipeline verification",
                "status": "not run in the final CXR upgrade",
                "result_reporting": "no MedMNIST performance is reported as evidence for the manuscript",
                "rationale": "the final analysis uses real NIH ChestX-ray14 and VinDr-derived CXR predictions only",
            }
        ]
    )

    paired_frames = []
    label_sets = [
        ("all_valid_labels", LABELS),
        ("external_evaluable_labels", external_eval_labels),
    ]
    for split, dataset_name in [("internal", "NIH internal test"), ("external", "VinDr external")]:
        for label_set_name, labels in label_sets:
            paired_frames.append(
                bootstrap_paired_model_comparison(
                    dataset_name=dataset_name,
                    split=split,
                    label_set_name=label_set_name,
                    labels=labels,
                    n_bootstrap=500,
                    seed=20260614,
                )
            )
    paired = pd.concat(paired_frames, ignore_index=True)

    outputs_to_save = {
        "table1_dataset_characteristics_upgraded.csv": table1,
        "table2_label_harmonization_analysis_role_upgraded.csv": table2,
        "table3_densenet121_labelwise_performance.csv": table3,
        "table4_architecture_comparison_macro_upgraded.csv": table4,
        "table5_calibration_metrics_upgraded.csv": table5,
        "table6_subgroup_sensitivity_analysis.csv": table6,
        "supplementary_table1_resnet50_labelwise_performance.csv": supp_resnet,
        "supplementary_table2_efficientnet_b0_labelwise_performance.csv": supp_eff,
        "supplementary_table3_per_label_thresholds.csv": supp_thresholds,
        "supplementary_table4_auprc_baseline_lift.csv": supp_auprc,
        "supplementary_table5_per_label_calibration_metrics.csv": supp_cal,
        "supplementary_table6_paired_bootstrap_model_comparison.csv": paired,
        "supplementary_table7_hyperparameters.csv": supp_hyper,
        "supplementary_table8_reproducibility_environment_commands.csv": supp_repro,
        "supplementary_table9_medmnist_pipeline_verification.csv": medmnist,
        "external_evaluable_label_set.csv": pd.DataFrame({"label": external_eval_labels}),
    }
    for name, df in outputs_to_save.items():
        save_table(tables / name, df)
        save_table(source_dir / name, df)

    save_workflow_figure(figs / "figure1_study_workflow_three_models.png")
    save_figure2_densenet_ci(table3, figs / "figure2_densenet121_internal_external_ci.png")
    save_figure3_prevalence_lift(supp_auprc, figs / "figure3_prevalence_auprc_baseline_lift.png")
    compose_images(
        [
            figs / "calibration" / "hf_large" / "reliability_NIH_internal_test.png",
            figs / "calibration" / "hf_large" / "reliability_VinDr_external.png",
        ],
        figs / "figure4_calibration_curves_upgraded.png",
        orientation="horizontal",
    )
    copy_or_create_gradcam_figure(figs / "figure5_gradcam_failure_modes_upgraded.png")
    save_figure6_drop(pd.read_csv(tables / "performance_drop.csv"), figs / "figure6_internal_minus_external_auroc.png")
    save_supp_roc_pr(internal_pred, figs / "supplementary_figure_roc_pr_curves_densenet121.png", source_dir)
    save_supp_probability_distributions(figs / "supplementary_figure_probability_distributions_densenet121.png", source_dir)

    # Keep compatibility with earlier requested figure names.
    compatibility = {
        "figure1_study_workflow_large.png": "figure1_study_workflow_three_models.png",
        "figure2_internal_vs_external_auroc_auprc_ci.png": "figure2_densenet121_internal_external_ci.png",
        "figure3_calibration_curves_large.png": "figure4_calibration_curves_upgraded.png",
        "figure4_gradcam_failure_modes_large.png": "figure5_gradcam_failure_modes_upgraded.png",
        "figure5_external_performance_drop_by_label.png": "figure6_internal_minus_external_auroc.png",
    }
    for old_name, new_name in compatibility.items():
        src = figs / new_name
        if src.exists():
            shutil.copy2(src, figs / old_name)

    densenet_internal = read_metrics("DenseNet121", "internal")
    densenet_external = read_metrics("DenseNet121", "external")
    macro_internal = macro_row(densenet_internal)
    macro_external = macro_row(densenet_external)
    model_table = table4.set_index("model")
    uncal_internal = table5[(table5["dataset"].eq("NIH_internal_test")) & (table5["calibration_method"].eq("uncalibrated"))].iloc[0]
    best_external_ece = table5[table5["dataset"].eq("VinDr_external")].sort_values("ece").iloc[0]
    registry = {
        "created_from": "real prediction CSVs and metrics CSVs only",
        "external_evaluable_labels": external_eval_labels,
        "dataset": {
            "nih_images": int(len(pd.read_csv(ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv"))),
            "nih_patients": int(pd.read_csv(ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv")["patient_id"].nunique()),
            "vindr_images": int(len(external_pred)),
            "vindr_patients": int(external_pred["patient_id"].nunique()),
        },
        "densenet121": {
            "internal_all_label_macro_auroc": fmt(macro_internal["auroc"]),
            "internal_all_label_macro_auprc": fmt(macro_internal["auprc"]),
            "external_reported_macro_auroc": fmt(macro_external["auroc"]),
            "external_reported_macro_auprc": fmt(macro_external["auprc"]),
            "internal_external_evaluable_macro_auroc": fmt(model_table.loc["DenseNet121", "internal_external_evaluable_labels_macro_auroc"]),
            "internal_external_evaluable_macro_auprc": fmt(model_table.loc["DenseNet121", "internal_external_evaluable_labels_macro_auprc"]),
            "external_nonzero_prevalence_macro_auroc": fmt(model_table.loc["DenseNet121", "external_nonzero_prevalence_labels_macro_auroc"]),
            "external_nonzero_prevalence_macro_auprc": fmt(model_table.loc["DenseNet121", "external_nonzero_prevalence_labels_macro_auprc"]),
        },
        "models": table4.to_dict(orient="records"),
        "calibration": {
            "internal_uncalibrated_brier": fmt(uncal_internal["brier_score"]),
            "internal_uncalibrated_ece": fmt(uncal_internal["ece"]),
            "internal_uncalibrated_mce": fmt(uncal_internal["mce"]),
            "internal_uncalibrated_slope": fmt(uncal_internal["calibration_slope"]),
            "internal_uncalibrated_intercept": fmt(uncal_internal["calibration_intercept"]),
            "best_external_ece_method": best_external_ece["calibration_method"],
            "best_external_ece": fmt(best_external_ece["ece"]),
        },
        "tables": {name: str(tables / name) for name in outputs_to_save},
        "figures": {
            "figure1": str(figs / "figure1_study_workflow_three_models.png"),
            "figure2": str(figs / "figure2_densenet121_internal_external_ci.png"),
            "figure3": str(figs / "figure3_prevalence_auprc_baseline_lift.png"),
            "figure4": str(figs / "figure4_calibration_curves_upgraded.png"),
            "figure5": str(figs / "figure5_gradcam_failure_modes_upgraded.png"),
            "figure6": str(figs / "figure6_internal_minus_external_auroc.png"),
        },
        "risk_guardrails": [
            "NIH split is patient-level.",
            "VinDr external subset was not used for threshold tuning, model selection, retraining, or calibration fitting.",
            "Calibration models were fitted on NIH calibration only.",
            "Edema and Pneumonia have zero external positives in the analyzed cached subset and are not used for external discrimination claims.",
            "Grad-CAM++ is reported only as qualitative failure-mode analysis.",
        ],
    }
    write_registry(registry)
    print(json.dumps(registry, indent=2))


if __name__ == "__main__":
    main()


