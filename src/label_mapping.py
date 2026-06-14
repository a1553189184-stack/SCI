from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_yaml


def canonical(text: Any) -> str:
    return str(text).strip().lower().replace("_", " ").replace("-", " ")


def split_labels(raw: Any) -> list[str]:
    if pd.isna(raw):
        return []
    text = str(raw).strip()
    if not text:
        return []
    for sep in ["|", ";"]:
        text = text.replace(sep, ",")
    return [part.strip() for part in text.split(",") if part.strip()]


def load_label_map(path: str | Path) -> dict[str, Any]:
    data = load_yaml(path)
    if "labels" not in data:
        raise ValueError(f"label_map file has no top-level 'labels': {path}")
    return data


def harmonized_labels(label_map: dict[str, Any], include_sensitivity: bool = True) -> list[str]:
    labels = []
    for item in label_map["labels"]:
        if include_sensitivity or item.get("status") not in {"sensitivity"}:
            labels.append(item["harmonized"])
    return labels


def source_lookup(label_map: dict[str, Any], source: str, include_sensitivity: bool = True) -> dict[str, list[str]]:
    lookup: dict[str, list[str]] = {}
    for item in label_map["labels"]:
        if not include_sensitivity and item.get("status") == "sensitivity":
            continue
        target = item["harmonized"]
        source_labels = item.get(source, {}).get("source_labels", [])
        for label in source_labels:
            lookup.setdefault(canonical(label), []).append(target)
    return lookup


def labels_from_raw(raw: Any, lookup: dict[str, list[str]], labels: list[str]) -> dict[str, int]:
    values = {label: 0 for label in labels}
    for source_label in split_labels(raw):
        for target in lookup.get(canonical(source_label), []):
            if target in values:
                values[target] = 1
    return values


def add_label_columns_from_raw(df: pd.DataFrame, raw_col: str, label_map: dict[str, Any], source: str, include_sensitivity: bool = True) -> tuple[pd.DataFrame, list[str]]:
    labels = harmonized_labels(label_map, include_sensitivity=include_sensitivity)
    lookup = source_lookup(label_map, source=source, include_sensitivity=include_sensitivity)
    label_rows = [labels_from_raw(raw, lookup, labels) for raw in df[raw_col]]
    label_df = pd.DataFrame(label_rows, index=df.index)
    return pd.concat([df, label_df], axis=1), labels


def aggregate_vindr_image_labels(labels_df: pd.DataFrame, image_col: str, label_col: str, label_map: dict[str, Any], include_sensitivity: bool = True) -> tuple[pd.DataFrame, list[str]]:
    labels = harmonized_labels(label_map, include_sensitivity=include_sensitivity)
    lookup = source_lookup(label_map, source="vindr", include_sensitivity=include_sensitivity)
    rows = []
    for image_id, group in labels_df.groupby(image_col, dropna=False):
        row = {"image_id": image_id}
        for label in labels:
            row[label] = 0
        raw_labels = []
        for raw in group[label_col].dropna().tolist():
            raw_labels.extend(split_labels(raw))
        row["source_labels"] = "|".join(sorted(set(raw_labels)))
        for raw in raw_labels:
            for target in lookup.get(canonical(raw), []):
                if target in row:
                    row[target] = 1
        rows.append(row)
    return pd.DataFrame(rows), labels


def label_warnings(label_map: dict[str, Any]) -> list[str]:
    warnings = []
    for item in label_map["labels"]:
        warning = item.get("warning")
        if warning:
            warnings.append(f"{item['harmonized']}: {warning}")
    warnings.extend(label_map.get("excluded_or_high_risk_notes", []))
    return warnings



