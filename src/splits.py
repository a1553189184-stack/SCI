from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config, resolve_path
from .label_mapping import harmonized_labels, load_label_map
from .utils import ensure_dirs, setup_logging


SPLIT_ORDER = ["train", "validation", "calibration", "internal_test"]


def _normalize_ratios(ratios: dict[str, float]) -> dict[str, float]:
    clean = {name: float(ratios[name]) for name in SPLIT_ORDER}
    total = sum(clean.values())
    if total <= 0:
        raise ValueError("Split ratios must sum to a positive value.")
    return {name: value / total for name, value in clean.items()}


def _target_patient_counts(n_patients: int, ratios: dict[str, float]) -> dict[str, int]:
    raw = {split: ratios[split] * n_patients for split in SPLIT_ORDER}
    counts = {split: int(np.floor(raw[split])) for split in SPLIT_ORDER}
    if n_patients >= len(SPLIT_ORDER):
        for split in SPLIT_ORDER:
            if ratios[split] > 0 and counts[split] == 0:
                counts[split] = 1
    while sum(counts.values()) > n_patients:
        candidates = [s for s in SPLIT_ORDER if counts[s] > (1 if n_patients >= len(SPLIT_ORDER) and ratios[s] > 0 else 0)]
        split = max(candidates, key=lambda s: counts[s] - raw[s])
        counts[split] -= 1
    while sum(counts.values()) < n_patients:
        split = max(SPLIT_ORDER, key=lambda s: raw[s] - counts[s])
        counts[split] += 1
    return counts


def _patient_label_table(df: pd.DataFrame, patient_col: str, labels: list[str]) -> pd.DataFrame:
    agg = df.groupby(patient_col)[labels].max().reset_index()
    counts = df.groupby(patient_col).size().rename("n_images").reset_index()
    out = agg.merge(counts, on=patient_col, how="left")
    out["label_sum"] = out[labels].sum(axis=1)
    return out


def greedy_multilabel_split(patient_df: pd.DataFrame, patient_col: str, labels: list[str], ratios: dict[str, float], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    patients = patient_df.sample(frac=1.0, random_state=seed).copy()
    patients["_shuffle"] = rng.random(len(patients))
    patients = patients.sort_values(["label_sum", "n_images", "_shuffle"], ascending=[False, False, True])

    n_patients = len(patients)
    global_label_counts = patients[labels].sum(axis=0).astype(float)
    target_patients = _target_patient_counts(n_patients, ratios)
    target_labels = {
        split: global_label_counts * ratios[split]
        for split in SPLIT_ORDER
    }

    assigned_rows = []
    split_patient_counts = {split: 0 for split in SPLIT_ORDER}
    split_label_counts = {split: pd.Series(0.0, index=labels) for split in SPLIT_ORDER}

    for _, row in patients.iterrows():
        row_labels = row[labels].astype(float)
        best_split = None
        best_score = None
        for split in SPLIT_ORDER:
            if split_patient_counts[split] >= target_patients[split]:
                continue
            next_label_counts = split_label_counts[split] + row_labels
            label_score = (((next_label_counts - target_labels[split]) ** 2) / (target_labels[split] + 1.0)).sum()
            fill_fraction = (split_patient_counts[split] + 1) / max(target_patients[split], 1)
            score = float(label_score + 0.01 * fill_fraction)
            if best_score is None or score < best_score:
                best_score = score
                best_split = split
        if best_split is None:
            best_split = min(SPLIT_ORDER, key=lambda split: split_patient_counts[split])
        split_patient_counts[best_split] += 1
        split_label_counts[best_split] = split_label_counts[best_split] + row_labels
        assigned_rows.append({patient_col: row[patient_col], "split": best_split})

    return pd.DataFrame(assigned_rows)


def random_patient_split(patient_df: pd.DataFrame, patient_col: str, ratios: dict[str, float], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    patients = patient_df[patient_col].astype(str).sample(frac=1.0, random_state=seed).tolist()
    rng.shuffle(patients)
    counts = _target_patient_counts(len(patients), ratios)
    assignments = {}
    start = 0
    for split in SPLIT_ORDER:
        end = start + counts[split]
        for patient in patients[start:end]:
            assignments[patient] = split
        start = end
    return pd.DataFrame({patient_col: list(assignments.keys()), "split": list(assignments.values())})


def split_statistics(df: pd.DataFrame, labels: list[str], split_col: str = "split") -> pd.DataFrame:
    rows = []
    for split, group in df.groupby(split_col):
        row = {
            "split": split,
            "n_patients": int(group["patient_id"].nunique()),
            "n_images": int(len(group)),
        }
        for label in labels:
            positives = int(group[label].fillna(0).sum())
            row[f"{label}_positive_images"] = positives
            row[f"{label}_prevalence"] = positives / len(group) if len(group) else 0.0
        rows.append(row)
    return pd.DataFrame(rows).sort_values("split")


def verify_no_patient_overlap(df: pd.DataFrame, patient_col: str = "patient_id", split_col: str = "split") -> None:
    split_counts = df.groupby(patient_col)[split_col].nunique()
    leaked = split_counts[split_counts > 1]
    if len(leaked):
        raise RuntimeError(f"Patient-level leakage detected for {len(leaked)} patients.")


def create_patient_splits(config_path: str | Path) -> pd.DataFrame:
    config = load_config(config_path)
    split_cfg = config["splits"]
    seed = int(config.get("project", {}).get("seed", 20260613))
    logger = setup_logging(resolve_path(config, "logs/create_patient_splits.log"))

    input_csv = resolve_path(config, split_cfg["input_csv"])
    output_prefix = resolve_path(config, split_cfg["output_prefix"])
    stats_csv = resolve_path(config, split_cfg["split_stats_csv"])
    summary_csv = resolve_path(config, split_cfg["split_summary_csv"])
    label_map = load_label_map(resolve_path(config, config["paths"]["label_map"]))
    labels = harmonized_labels(label_map, include_sensitivity=bool(config.get("labels", {}).get("include_sensitivity_labels", True)))

    ensure_dirs([output_prefix.parent, stats_csv.parent, summary_csv.parent])
    df = pd.read_csv(input_csv)
    patient_col = split_cfg.get("patient_col", "patient_id")
    if patient_col not in df.columns:
        raise KeyError(f"Patient column '{patient_col}' not found in {input_csv}.")
    missing_labels = [label for label in labels if label not in df.columns]
    if missing_labels:
        raise KeyError(f"Missing label columns in NIH metadata: {missing_labels}")

    ratios = _normalize_ratios(split_cfg["ratios"])
    patient_df = _patient_label_table(df, patient_col, labels)
    logger.info("Creating patient-level splits for %d patients and %d images", len(patient_df), len(df))
    if split_cfg.get("strategy", "greedy_multilabel") == "random":
        assignments = random_patient_split(patient_df, patient_col, ratios, seed)
    else:
        assignments = greedy_multilabel_split(patient_df, patient_col, labels, ratios, seed)

    out = df.merge(assignments, on=patient_col, how="left")
    if out["split"].isna().any():
        raise RuntimeError("Some images did not receive a split assignment.")
    verify_no_patient_overlap(out, patient_col=patient_col)

    for split in SPLIT_ORDER:
        split_df = out[out["split"] == split].copy()
        split_path = Path(f"{output_prefix}_{split}.csv")
        split_df.to_csv(split_path, index=False)
        logger.info("Saved %s: %d images, %d patients", split_path, len(split_df), split_df[patient_col].nunique())

    all_path = Path(f"{output_prefix}_all_splits.csv")
    out.to_csv(all_path, index=False)
    stats = split_statistics(out, labels)
    stats.to_csv(stats_csv, index=False)
    stats.to_csv(summary_csv, index=False)
    logger.info("Saved split statistics: %s", stats_csv)
    logger.info("Saved Table 1 split summary: %s", summary_csv)
    logger.info("External VinDr-CXR data were not used for NIH splitting.")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Create patient-level NIH train/validation/calibration/internal-test splits.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    create_patient_splits(args.config)


if __name__ == "__main__":
    main()


