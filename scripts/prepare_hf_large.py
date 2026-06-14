from __future__ import annotations

import argparse
import io
import json
import random
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from huggingface_hub import hf_hub_download, list_repo_files

from src.splits import create_patient_splits


NIH_REPO = "BahaaEldin0/NIH-Chest-Xray-14"
VIN_REPO = "sbandred/vinbig-cxr-processed"
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
PRIMARY_EXTERNAL_LABELS = ["Atelectasis", "Cardiomegaly", "Pleural Effusion", "Pneumothorax", "Consolidation"]


def _label_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        return [str(v) for v in list(value)]
    except Exception:
        return [str(value)]


def _nih_targets(raw_labels) -> dict[str, int]:
    source = set(_label_list(raw_labels))
    return {
        "Atelectasis": int("Atelectasis" in source),
        "Cardiomegaly": int("Cardiomegaly" in source),
        "Pleural Effusion": int("Effusion" in source or "Pleural Effusion" in source),
        "Pneumothorax": int("Pneumothorax" in source),
        "Consolidation": int("Consolidation" in source),
        "Edema": int("Edema" in source),
        "Pneumonia": int("Pneumonia" in source),
        "No Finding": int("No Finding" in source),
    }


def prepare_nih_large(max_images: int, n_train_shards: int, seed: int) -> Path:
    rows = []
    rng = random.Random(seed)
    needed = max_images
    image_dir = ROOT / "data" / "hf_large" / "nih_chestxray14" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    shard_frames = []
    for shard_idx in range(n_train_shards):
        shard_name = f"data/train-{shard_idx:05d}-of-00073.parquet"
        parquet_path = hf_hub_download(
            NIH_REPO,
            shard_name,
            repo_type="dataset",
            local_dir=ROOT / "data" / "hf_large" / "nih_parquet",
        )
        df = pd.read_parquet(parquet_path)
        df["_shard"] = shard_idx
        shard_frames.append(df)
        if sum(len(x) for x in shard_frames) >= max_images * 1.25:
            break

    all_df = pd.concat(shard_frames, ignore_index=True)
    all_df["_rand"] = [rng.random() for _ in range(len(all_df))]
    all_df = all_df.sort_values("_rand").head(needed).reset_index(drop=True)

    for idx, row in all_df.iterrows():
        image_obj = row["image"]
        source_name = Path(str(image_obj.get("path", f"nih_large_{idx:06d}.png"))).name
        image_name = f"nih_s{int(row['_shard']):02d}_{idx:06d}_{Path(source_name).stem}.png"
        out_path = image_dir / image_name
        if not out_path.exists():
            image = Image.open(io.BytesIO(image_obj["bytes"])).convert("RGB")
            image.save(out_path)
        targets = _nih_targets(row["label"])
        out_row = {
            "dataset": "NIH ChestX-ray14 HF public parquet large subset",
            "image_id": image_name,
            "study_id": image_name,
            "patient_id": str(row["Patient ID"]),
            "image_path": str(out_path.resolve()),
            "view_position": row["View Position"],
            "age": int(row["Patient Age"]),
            "sex": row["Patient Gender"],
            "source_labels": "|".join(_label_list(row["label"])),
        }
        out_row.update(targets)
        rows.append(out_row)

    out_csv = ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    return out_csv


def _download_vin_csvs() -> tuple[Path, Path]:
    raw_zip = Path(
        hf_hub_download(
            VIN_REPO,
            "_downloads/train_raw.csv",
            repo_type="dataset",
            local_dir=ROOT / "data" / "hf_large" / "vinbig_processed",
        )
    )
    meta_csv = Path(
        hf_hub_download(
            VIN_REPO,
            "_downloads/vinbig_png/train_meta.csv",
            repo_type="dataset",
            local_dir=ROOT / "data" / "hf_large" / "vinbig_processed",
        )
    )
    unzip_dir = raw_zip.parent / "train_raw_unzipped"
    unzip_dir.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(raw_zip):
        with zipfile.ZipFile(raw_zip) as zf:
            zf.extractall(unzip_dir)
        raw_csv = unzip_dir / "train.csv"
    else:
        raw_csv = raw_zip
    return raw_csv, meta_csv


def _vin_targets(labels: set[str]) -> dict[str, int]:
    abnormal = {lab for lab in labels if lab != "No finding"}
    return {
        "Atelectasis": int("Atelectasis" in labels),
        "Cardiomegaly": int("Cardiomegaly" in labels),
        "Pleural Effusion": int("Pleural effusion" in labels or "Pleural Effusion" in labels),
        "Pneumothorax": int("Pneumothorax" in labels),
        "Consolidation": int("Consolidation" in labels),
        "Edema": 0,
        "Pneumonia": 0,
        "No Finding": int(len(abnormal) == 0 and "No finding" in labels),
    }


def prepare_vindr_large(target_images: int, per_label_target: int, no_finding_target: int, seed: int) -> Path:
    raw_csv, meta_csv = _download_vin_csvs()
    raw = pd.read_csv(raw_csv)
    meta = pd.read_csv(meta_csv)
    files = list_repo_files(VIN_REPO, repo_type="dataset")
    train_image_ids = {Path(f).stem for f in files if f.startswith("train/") and f.endswith(".png")}

    grouped = raw.groupby("image_id")["class_name"].apply(lambda s: set(s.dropna().astype(str))).reset_index()
    grouped = grouped[grouped["image_id"].isin(train_image_ids)].copy()
    for label in LABELS:
        grouped[label] = grouped["class_name"].map(lambda labs, label=label: _vin_targets(labs)[label])

    rng = random.Random(seed)
    selected: set[str] = set()
    for label in PRIMARY_EXTERNAL_LABELS:
        ids = grouped.loc[grouped[label] == 1, "image_id"].tolist()
        rng.shuffle(ids)
        selected.update(ids[:per_label_target])

    nf_ids = grouped.loc[grouped["No Finding"] == 1, "image_id"].tolist()
    rng.shuffle(nf_ids)
    selected.update(nf_ids[:no_finding_target])

    remaining = grouped.loc[~grouped["image_id"].isin(selected), "image_id"].tolist()
    rng.shuffle(remaining)
    for image_id in remaining:
        if len(selected) >= target_images:
            break
        selected.add(image_id)

    selected = set(list(selected)[:target_images])
    image_dir = ROOT / "data" / "hf_large" / "vindr_cxr" / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    boxes = []
    meta_map = meta.set_index("image_id").to_dict("index")
    selected_df = grouped[grouped["image_id"].isin(selected)].copy().sort_values("image_id")

    for _, row in selected_df.iterrows():
        image_id = row["image_id"]
        src = Path(
            hf_hub_download(
                VIN_REPO,
                f"train/{image_id}.png",
                repo_type="dataset",
                local_dir=ROOT / "data" / "hf_large" / "vinbig_processed",
            )
        )
        dst = image_dir / f"{image_id}.png"
        if not dst.exists():
            shutil.copy2(src, dst)
        with Image.open(dst) as img:
            png_w, png_h = img.size
        out_row = {
            "dataset": "VinDr-CXR/VinBigData HF public PNG large subset",
            "image_id": f"{image_id}.png",
            "study_id": image_id,
            "patient_id": image_id,
            "image_path": str(dst.resolve()),
            "view_position": "frontal",
            "age": "",
            "sex": "",
            "source_labels": "|".join(sorted(row["class_name"])),
        }
        out_row.update({label: int(row[label]) for label in LABELS})
        rows.append(out_row)

        original = meta_map.get(image_id, {})
        orig_h = float(original.get("dim0", png_h) or png_h)
        orig_w = float(original.get("dim1", png_w) or png_w)
        sx = png_w / max(orig_w, 1.0)
        sy = png_h / max(orig_h, 1.0)
        sub = raw[(raw["image_id"] == image_id) & raw["x_min"].notna()].copy()
        for _, box in sub.iterrows():
            boxes.append(
                {
                    "image_id": f"{image_id}.png",
                    "source_label": box["class_name"],
                    "x_min": float(box["x_min"]) * sx,
                    "y_min": float(box["y_min"]) * sy,
                    "x_max": float(box["x_max"]) * sx,
                    "y_max": float(box["y_max"]) * sy,
                }
            )

    out_csv = ROOT / "metadata_large" / "hf_large_vindr_clean_metadata.csv"
    out_boxes = ROOT / "metadata_large" / "hf_large_vindr_boxes_clean.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    pd.DataFrame(boxes).to_csv(out_boxes, index=False)
    return out_csv


def write_large_config(nih_csv: Path, vindr_csv: Path, epochs: int, seed: int) -> Path:
    base = yaml.safe_load((ROOT / "configs" / "config.yaml").read_text(encoding="utf-8"))
    base["project"]["root"] = str(ROOT).replace("\\", "/")
    base["project"]["seed"] = seed
    base["nih"]["output_csv"] = str(nih_csv.relative_to(ROOT)).replace("\\", "/")
    base["vindr"]["output_csv"] = str(vindr_csv.relative_to(ROOT)).replace("\\", "/")
    base["vindr"]["boxes_output_csv"] = "metadata_large/hf_large_vindr_boxes_clean.csv"
    base["paths"]["metadata_dir"] = "metadata_large"
    base["paths"]["tables_dir"] = "tables_large"
    base["paths"]["splits_dir"] = "splits_large"
    base["splits"]["input_csv"] = str(nih_csv.relative_to(ROOT)).replace("\\", "/")
    base["splits"]["output_prefix"] = "splits_large/hf_large_nih"
    base["splits"]["split_stats_csv"] = "splits_large/hf_large_nih_split_statistics.csv"
    base["splits"]["split_summary_csv"] = "tables_large/table1_nih_split_summary.csv"
    base["dataloader"]["num_workers"] = 2
    base["dataloader"]["persistent_workers"] = True
    base["dataloader"]["train_batch_size"] = 24
    base["dataloader"]["eval_batch_size"] = 48
    base["training"]["run_name"] = "hf_large_densenet121"
    base["training"]["output_dir"] = "outputs_large/training/hf_large_densenet121"
    base["training"]["checkpoint_dir"] = "models_large/hf_large_densenet121"
    base["training"]["log_csv"] = "logs_large/hf_large_densenet121_train_log.csv"
    base["training"]["epochs"] = epochs
    base["training"]["early_stopping_patience"] = 3
    base["training"]["save_every_epoch"] = False
    base["evaluation"]["checkpoint_path"] = "models_large/hf_large_densenet121/best_densenet121.pt"
    base["evaluation"]["validation_predictions_csv"] = "predictions_large/nih_validation_predictions.csv"
    base["evaluation"]["internal_predictions_csv"] = "predictions_large/internal_test_predictions.csv"
    base["evaluation"]["external_predictions_csv"] = "predictions_large/external_vindr_predictions.csv"
    base["evaluation"]["internal_metrics_csv"] = "tables_large/internal_metrics.csv"
    base["evaluation"]["external_metrics_csv"] = "tables_large/external_metrics.csv"
    base["evaluation"]["internal_external_comparison_csv"] = "tables_large/internal_external_comparison.csv"
    base["evaluation"]["performance_drop_csv"] = "tables_large/performance_drop.csv"
    base["evaluation"]["thresholds_csv"] = "tables_large/thresholds_from_val.csv"
    base["evaluation"]["bootstrap_ci_csv"] = "tables_large/bootstrap_ci.csv"
    base["evaluation"]["bootstrap_iterations"] = 500
    base["calibration"]["raw_calibration_predictions_csv"] = "predictions_large/nih_calibration_predictions.csv"
    base["calibration"]["raw_internal_predictions_csv"] = "predictions_large/internal_test_predictions.csv"
    base["calibration"]["raw_external_predictions_csv"] = "predictions_large/external_vindr_predictions.csv"
    base["calibration"]["calibrated_predictions_csv"] = "outputs_large/calibration/hf_large/calibrated_predictions.csv"
    base["calibration"]["calibration_metrics_csv"] = "tables_large/calibration_metrics.csv"
    base["calibration"]["curves_dir"] = "figures_large/calibration/hf_large"
    base["gradcam"]["output_dir"] = "figures_large/gradcam/hf_large"
    base["gradcam"]["case_index_csv"] = "tables_large/gradcam_case_index.csv"
    base["gradcam"]["localization_metrics_csv"] = "tables_large/gradcam_localization_metrics.csv"
    base["gradcam"]["internal_predictions_csv"] = "predictions_large/internal_test_predictions.csv"
    base["gradcam"]["external_predictions_csv"] = "predictions_large/external_vindr_predictions.csv"
    base["gradcam"]["max_cases_per_label"] = 1
    config_path = ROOT / "configs" / "hf_large.yaml"
    config_path.write_text(yaml.safe_dump(base, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_path


def label_prevalence(csv_path: Path, output_path: Path) -> None:
    df = pd.read_csv(csv_path)
    rows = []
    for label in LABELS:
        positives = int(df[label].sum()) if label in df.columns else 0
        rows.append({"label": label, "n_images": len(df), "positive_images": positives, "prevalence": positives / len(df) if len(df) else 0.0})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare larger real public NIH and VinDr-derived subsets.")
    parser.add_argument("--nih-max-images", type=int, default=5000)
    parser.add_argument("--nih-train-shards", type=int, default=5)
    parser.add_argument("--vindr-target-images", type=int, default=1000)
    parser.add_argument("--vindr-per-label", type=int, default=150)
    parser.add_argument("--vindr-no-finding", type=int, default=300)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260614)
    args = parser.parse_args()

    nih_csv = prepare_nih_large(args.nih_max_images, args.nih_train_shards, args.seed)
    vindr_csv = prepare_vindr_large(args.vindr_target_images, args.vindr_per_label, args.vindr_no_finding, args.seed)
    config_path = write_large_config(nih_csv, vindr_csv, args.epochs, args.seed)
    create_patient_splits(config_path)
    label_prevalence(nih_csv, ROOT / "tables_large" / "hf_large_nih_label_prevalence.csv")
    label_prevalence(vindr_csv, ROOT / "tables_large" / "hf_large_vindr_label_prevalence.csv")
    manifest = {
        "nih_metadata": str(nih_csv),
        "vindr_metadata": str(vindr_csv),
        "config": str(config_path),
        "nih_max_images": args.nih_max_images,
        "vindr_target_images": args.vindr_target_images,
        "note": "Real public HF larger subset. Not synthetic. Edema/Pneumonia are unavailable in the VinDr-derived external labels and should not support external main claims.",
    }
    out = ROOT / "outputs_large" / "hf_large_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()


