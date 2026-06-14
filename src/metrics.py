from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


EPS = 1e-12


@dataclass
class MetricConfig:
    threshold_metric: str = "f1"


def _safe_metric(fn, y_true: np.ndarray, y_score: np.ndarray) -> float:
    try:
        if len(np.unique(y_true)) < 2:
            return float("nan")
        return float(fn(y_true, y_score))
    except Exception:
        return float("nan")


def _binary_counts(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    y_true = y_true.astype(int)
    y_pred = y_pred.astype(int)
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return tp, fp, tn, fn


def threshold_metrics_from_counts(tp: int, fp: int, tn: int, fn: int) -> dict[str, float]:
    return {
        "sensitivity": tp / (tp + fn + EPS),
        "specificity": tn / (tn + fp + EPS),
        "f1": 2 * tp / (2 * tp + fp + fn + EPS),
        "accuracy": (tp + tn) / (tp + tn + fp + fn + EPS),
        "ppv": tp / (tp + fp + EPS),
        "npv": tn / (tn + fn + EPS),
    }


def select_thresholds_from_validation(pred_df: pd.DataFrame, label_cols: list[str], metric: str = "f1") -> pd.DataFrame:
    rows = []
    grid = np.linspace(0.01, 0.99, 99)
    for label in label_cols:
        y_true = pred_df[f"true_{label}"].to_numpy(dtype=int)
        y_prob = pred_df[f"prob_{label}"].to_numpy(dtype=float)
        best_threshold = 0.5
        best_score = -float("inf")
        for threshold in grid:
            y_pred = (y_prob >= threshold).astype(int)
            counts = _binary_counts(y_true, y_pred)
            metrics = threshold_metrics_from_counts(*counts)
            score = metrics.get(metric, metrics["f1"])
            if score > best_score:
                best_score = score
                best_threshold = float(threshold)
        rows.append({"label": label, "threshold": best_threshold, f"validation_{metric}": best_score})
    return pd.DataFrame(rows)


def compute_metrics(pred_df: pd.DataFrame, label_cols: list[str], dataset_name: str) -> pd.DataFrame:
    from sklearn.metrics import average_precision_score, roc_auc_score

    rows: list[dict] = []
    thresholded = all(f"pred_{label}" in pred_df.columns for label in label_cols)
    per_label_values = []
    y_true_all = []
    y_prob_all = []
    y_pred_all = []
    for label in label_cols:
        y_true = pred_df[f"true_{label}"].to_numpy(dtype=int)
        y_prob = pred_df[f"prob_{label}"].to_numpy(dtype=float)
        y_pred = pred_df[f"pred_{label}"].to_numpy(dtype=int) if thresholded else (y_prob >= 0.5).astype(int)
        auroc = _safe_metric(roc_auc_score, y_true, y_prob)
        auprc = _safe_metric(average_precision_score, y_true, y_prob)
        tp, fp, tn, fn = _binary_counts(y_true, y_pred)
        thr = threshold_metrics_from_counts(tp, fp, tn, fn)
        row = {
            "dataset": dataset_name,
            "average": "label",
            "label": label,
            "n": int(len(y_true)),
            "positives": int(y_true.sum()),
            "auroc": auroc,
            "auprc": auprc,
            **thr,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }
        rows.append(row)
        per_label_values.append(row)
        y_true_all.append(y_true)
        y_prob_all.append(y_prob)
        y_pred_all.append(y_pred)

    macro = {"dataset": dataset_name, "average": "macro", "label": "macro", "n": int(len(pred_df)), "positives": int(sum(v["positives"] for v in per_label_values))}
    for metric in ["auroc", "auprc", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]:
        vals = [v[metric] for v in per_label_values if np.isfinite(v[metric])]
        macro[metric] = float(np.mean(vals)) if vals else float("nan")
    macro.update({"tp": "", "fp": "", "tn": "", "fn": ""})
    rows.append(macro)

    y_true_micro = np.concatenate(y_true_all)
    y_prob_micro = np.concatenate(y_prob_all)
    y_pred_micro = np.concatenate(y_pred_all)
    tp, fp, tn, fn = _binary_counts(y_true_micro, y_pred_micro)
    micro = {
        "dataset": dataset_name,
        "average": "micro",
        "label": "micro",
        "n": int(len(y_true_micro)),
        "positives": int(y_true_micro.sum()),
        "auroc": _safe_metric(roc_auc_score, y_true_micro, y_prob_micro),
        "auprc": _safe_metric(average_precision_score, y_true_micro, y_prob_micro),
        **threshold_metrics_from_counts(tp, fp, tn, fn),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }
    rows.append(micro)
    return pd.DataFrame(rows)


def patient_bootstrap_ci(
    pred_df: pd.DataFrame,
    label_cols: list[str],
    dataset_name: str,
    n_bootstrap: int,
    seed: int,
    patient_col: str = "patient_id",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    patients = pred_df[patient_col].astype(str).drop_duplicates().to_numpy()
    if len(patients) == 0:
        return pd.DataFrame()
    metric_rows = []
    for _ in range(int(n_bootstrap)):
        sampled = rng.choice(patients, size=len(patients), replace=True)
        pieces = []
        for sampled_idx, patient in enumerate(sampled):
            group = pred_df[pred_df[patient_col].astype(str) == str(patient)].copy()
            group[patient_col] = f"{patient}__boot{sampled_idx}"
            pieces.append(group)
        boot_df = pd.concat(pieces, ignore_index=True)
        metric_rows.append(compute_metrics(boot_df, label_cols, dataset_name))
    all_metrics = pd.concat(metric_rows, ignore_index=True)
    rows = []
    for (average, label), group in all_metrics.groupby(["average", "label"]):
        for metric in ["auroc", "auprc", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]:
            vals = group[metric].dropna().to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if len(vals) == 0:
                lo = hi = float("nan")
            else:
                lo, hi = np.percentile(vals, [2.5, 97.5])
            rows.append({"dataset": dataset_name, "average": average, "label": label, "metric": metric, "ci_lower": lo, "ci_upper": hi, "n_bootstrap": int(n_bootstrap)})
    return pd.DataFrame(rows)


def add_ci_to_metrics(metrics_df: pd.DataFrame, ci_df: pd.DataFrame) -> pd.DataFrame:
    if ci_df.empty:
        return metrics_df
    out = metrics_df.copy()
    for metric in ["auroc", "auprc", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]:
        sub = ci_df[ci_df["metric"] == metric][["average", "label", "ci_lower", "ci_upper"]].rename(
            columns={"ci_lower": f"{metric}_ci_lower", "ci_upper": f"{metric}_ci_upper"}
        )
        out = out.merge(sub, on=["average", "label"], how="left")
    return out


def compare_internal_external(internal_metrics: pd.DataFrame, external_metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    keep = ["average", "label", "auroc", "auprc", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]
    internal = internal_metrics[keep].add_prefix("internal_").rename(columns={"internal_average": "average", "internal_label": "label"})
    external = external_metrics[keep].add_prefix("external_").rename(columns={"external_average": "average", "external_label": "label"})
    comparison = internal.merge(external, on=["average", "label"], how="inner")
    drop_rows = []
    for _, row in comparison.iterrows():
        for metric in ["auroc", "auprc", "sensitivity", "specificity", "f1", "accuracy", "ppv", "npv"]:
            internal_value = row[f"internal_{metric}"]
            external_value = row[f"external_{metric}"]
            absolute_drop = internal_value - external_value if np.isfinite(internal_value) and np.isfinite(external_value) else float("nan")
            relative_drop = absolute_drop / internal_value if np.isfinite(absolute_drop) and internal_value not in (0, np.nan) else float("nan")
            drop_rows.append({"average": row["average"], "label": row["label"], "metric": metric, "internal": internal_value, "external": external_value, "absolute_drop": absolute_drop, "relative_drop": relative_drop})
    return comparison, pd.DataFrame(drop_rows)


