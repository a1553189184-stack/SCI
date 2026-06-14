from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import load_config, resolve_path
from .label_mapping import aggregate_vindr_image_labels, label_warnings, load_label_map
from .utils import (
    build_image_index,
    ensure_dirs,
    first_existing_column,
    locate_image,
    save_dataset_characteristics,
    save_prevalence,
    setup_logging,
)


def _optional_csv(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    return pd.read_csv(path)


def _clean_boxes(df: pd.DataFrame, cfg: dict, image_col: str, label_col: str) -> pd.DataFrame | None:
    cols = cfg["columns"]
    x_min = first_existing_column(df, cols.get("box_x_min", []), required=False)
    y_min = first_existing_column(df, cols.get("box_y_min", []), required=False)
    x_max = first_existing_column(df, cols.get("box_x_max", []), required=False)
    y_max = first_existing_column(df, cols.get("box_y_max", []), required=False)
    if not all([x_min, y_min, x_max, y_max]):
        return None
    boxes = df[[image_col, label_col, x_min, y_min, x_max, y_max]].copy()
    boxes.columns = ["image_id", "source_label", "x_min", "y_min", "x_max", "y_max"]
    for col in ["x_min", "y_min", "x_max", "y_max"]:
        boxes[col] = pd.to_numeric(boxes[col], errors="coerce")
    boxes = boxes.dropna(subset=["x_min", "y_min", "x_max", "y_max"]).copy()
    return boxes


def prepare_vindr(config_path: str | Path) -> pd.DataFrame:
    config = load_config(config_path)
    vindr_cfg = config["vindr"]
    labels_cfg = config.get("labels", {})
    labels_csv = resolve_path(config, vindr_cfg["labels_csv"])
    metadata_csv = resolve_path(config, vindr_cfg.get("metadata_csv"))
    boxes_csv = resolve_path(config, vindr_cfg.get("boxes_csv"))
    image_root = resolve_path(config, vindr_cfg["image_root"])
    output_csv = resolve_path(config, vindr_cfg["output_csv"])
    boxes_output_csv = resolve_path(config, vindr_cfg["boxes_output_csv"])
    table1_csv = resolve_path(config, vindr_cfg["table1_csv"])
    prevalence_csv = resolve_path(config, vindr_cfg["prevalence_csv"])
    label_map_path = resolve_path(config, config["paths"]["label_map"])

    ensure_dirs([output_csv.parent, boxes_output_csv.parent, table1_csv.parent, prevalence_csv.parent])
    logger = setup_logging(resolve_path(config, "logs/prepare_vindr.log"))
    logger.info("Reading VinDr labels: %s", labels_csv)
    label_df = pd.read_csv(labels_csv)
    cols = vindr_cfg["columns"]
    image_col = first_existing_column(label_df, cols["image_id"])
    label_col = first_existing_column(label_df, cols["labels"])

    label_map = load_label_map(label_map_path)
    for warning in label_warnings(label_map):
        logger.warning("Label harmonization note: %s", warning)
    image_labels, labels = aggregate_vindr_image_labels(
        label_df,
        image_col=image_col,
        label_col=label_col,
        label_map=label_map,
        include_sensitivity=bool(labels_cfg.get("include_sensitivity_labels", True)),
    )

    metadata_df = _optional_csv(metadata_csv)
    if metadata_df is not None:
        meta_image_col = first_existing_column(metadata_df, cols["image_id"])
        meta = metadata_df.copy()
        meta = meta.rename(columns={meta_image_col: "image_id"})
        out = image_labels.merge(meta, on="image_id", how="left", suffixes=("", "_meta"))
    else:
        out = image_labels

    patient_col = first_existing_column(out, cols.get("patient_id", []), required=False)
    study_col = first_existing_column(out, cols.get("study_id", []), required=False)
    view_col = first_existing_column(out, cols.get("view_position", []), required=False)
    age_col = first_existing_column(out, cols.get("age", []), required=False)
    sex_col = first_existing_column(out, cols.get("sex", []), required=False)

    out["dataset"] = "VinDr-CXR"
    out["patient_id"] = out[patient_col].astype(str) if patient_col else out["image_id"].astype(str)
    out["study_id"] = out[study_col].astype(str) if study_col else out["image_id"].astype(str)
    out["view_position"] = out[view_col].astype(str) if view_col else ""
    out["age"] = out[age_col] if age_col else ""
    out["sex"] = out[sex_col] if sex_col else ""
    if patient_col is None:
        logger.warning("VinDr patient_id column not found; using image_id as patient_id for external metadata.")

    if vindr_cfg.get("filter_frontal", False) and view_col:
        allowed = {str(v).lower() for v in vindr_cfg.get("allowed_views", [])}
        before = len(out)
        out = out[out["view_position"].str.lower().isin(allowed)].copy()
        logger.info("Filtered frontal views: %d -> %d images", before, len(out))

    logger.info("Indexing VinDr images under: %s", image_root)
    image_index = build_image_index(image_root)
    out["image_path"] = out["image_id"].map(lambda x: locate_image(x, image_index))
    if vindr_cfg.get("verify_image_paths", True):
        before = len(out)
        out = out[out["image_path"].astype(bool)].copy()
        logger.info("Verified image paths: %d -> %d images", before, len(out))

    ordered_cols = [
        "dataset",
        "image_id",
        "patient_id",
        "study_id",
        "image_path",
        "view_position",
        "age",
        "sex",
        "source_labels",
    ] + labels
    out = out[ordered_cols].sort_values(["patient_id", "image_id"]).reset_index(drop=True)
    out.to_csv(output_csv, index=False)
    logger.info("Saved VinDr clean metadata: %s", output_csv)

    save_prevalence(out, labels, prevalence_csv, dataset_name="VinDr-CXR")
    save_dataset_characteristics(
        out,
        table1_csv,
        dataset_name="VinDr-CXR",
        role="Independent external validation",
        image_format="DICOM/PNG/JPG",
        label_source="Radiologist annotations",
    )

    boxes_df = _optional_csv(boxes_csv)
    if boxes_df is not None:
        box_image_col = first_existing_column(boxes_df, cols["image_id"])
        box_label_col = first_existing_column(boxes_df, cols["labels"])
        boxes = _clean_boxes(boxes_df, vindr_cfg, box_image_col, box_label_col)
        if boxes is not None and len(boxes):
            boxes.to_csv(boxes_output_csv, index=False)
            logger.info("Saved VinDr bounding boxes: %s", boxes_output_csv)
        else:
            logger.warning("No usable VinDr bounding-box columns found.")

    logger.info("Saved VinDr prevalence and Table 1 characteristics")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare VinDr-CXR metadata for steps 1-6.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    prepare_vindr(args.config)


if __name__ == "__main__":
    main()



