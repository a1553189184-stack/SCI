from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import load_config, resolve_path
from .label_mapping import add_label_columns_from_raw, label_warnings, load_label_map
from .utils import (
    build_image_index,
    ensure_dirs,
    first_existing_column,
    locate_image,
    save_dataset_characteristics,
    save_prevalence,
    setup_logging,
)


def prepare_nih(config_path: str | Path) -> pd.DataFrame:
    config = load_config(config_path)
    nih_cfg = config["nih"]
    labels_cfg = config.get("labels", {})
    metadata_csv = resolve_path(config, nih_cfg["metadata_csv"])
    image_root = resolve_path(config, nih_cfg["image_root"])
    output_csv = resolve_path(config, nih_cfg["output_csv"])
    table1_csv = resolve_path(config, nih_cfg["table1_csv"])
    prevalence_csv = resolve_path(config, nih_cfg["prevalence_csv"])
    label_map_path = resolve_path(config, config["paths"]["label_map"])

    ensure_dirs([output_csv.parent, table1_csv.parent, prevalence_csv.parent])
    logger = setup_logging(resolve_path(config, "logs/prepare_nih.log"))
    logger.info("Reading NIH metadata: %s", metadata_csv)
    df = pd.read_csv(metadata_csv)

    cols = nih_cfg["columns"]
    image_col = first_existing_column(df, cols["image_id"])
    patient_col = first_existing_column(df, cols["patient_id"])
    labels_col = first_existing_column(df, cols["labels"])
    view_col = first_existing_column(df, cols.get("view_position", []), required=False)
    age_col = first_existing_column(df, cols.get("age", []), required=False)
    sex_col = first_existing_column(df, cols.get("sex", []), required=False)

    out = pd.DataFrame(
        {
            "dataset": "NIH ChestX-ray14",
            "image_id": df[image_col].astype(str),
            "patient_id": df[patient_col].astype(str),
            "study_id": df[image_col].astype(str),
            "source_labels": df[labels_col].astype(str),
        }
    )
    out["view_position"] = df[view_col].astype(str) if view_col else ""
    out["age"] = df[age_col] if age_col else ""
    out["sex"] = df[sex_col] if sex_col else ""

    if nih_cfg.get("filter_frontal", True) and view_col:
        allowed = {str(v).lower() for v in nih_cfg.get("allowed_views", ["PA", "AP"])}
        before = len(out)
        out = out[out["view_position"].str.lower().isin(allowed)].copy()
        logger.info("Filtered frontal views: %d -> %d images", before, len(out))

    logger.info("Indexing NIH images under: %s", image_root)
    image_index = build_image_index(image_root)
    out["image_path"] = out["image_id"].map(lambda x: locate_image(x, image_index))
    if nih_cfg.get("verify_image_paths", True):
        before = len(out)
        out = out[out["image_path"].astype(bool)].copy()
        logger.info("Verified image paths: %d -> %d images", before, len(out))

    label_map = load_label_map(label_map_path)
    for warning in label_warnings(label_map):
        logger.warning("Label harmonization note: %s", warning)
    out, labels = add_label_columns_from_raw(
        out,
        raw_col="source_labels",
        label_map=label_map,
        source="nih",
        include_sensitivity=bool(labels_cfg.get("include_sensitivity_labels", True)),
    )

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
    logger.info("Saved NIH clean metadata: %s", output_csv)

    save_prevalence(out, labels, prevalence_csv, dataset_name="NIH ChestX-ray14")
    save_dataset_characteristics(
        out,
        table1_csv,
        dataset_name="NIH ChestX-ray14",
        role="Development/internal validation",
        image_format="PNG",
        label_source="Report-mined image-level labels",
    )
    logger.info("Saved NIH prevalence and Table 1 characteristics")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare NIH ChestX-ray14 metadata for steps 1-6.")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()
    prepare_nih(args.config)


if __name__ == "__main__":
    main()



