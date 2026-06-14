from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


PRIMARY_LABELS = [
    "Atelectasis",
    "Cardiomegaly",
    "Effusion",
    "Pneumothorax",
    "Consolidation",
    "Edema",
    "Pneumonia",
    "No Finding",
]


VINDR_LABELS = [
    "Atelectasis",
    "Cardiomegaly",
    "Pleural effusion",
    "Pneumothorax",
    "Consolidation",
    "Pulmonary edema",
    "Pneumonia",
    "No finding",
]


def make_image(path: Path, seed: int, label_index: int) -> None:
    rng = np.random.default_rng(seed)
    base = rng.normal(loc=115, scale=28, size=(256, 256)).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(base, mode="L").convert("RGB")
    draw = ImageDraw.Draw(img)
    x0 = 24 + (label_index * 13) % 120
    y0 = 30 + (label_index * 17) % 120
    draw.ellipse((x0, y0, x0 + 42, y0 + 32), outline=(230, 230, 230), width=3)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def create_synthetic_smoke(root: Path, out_dir: Path, seed: int = 20260613) -> Path:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    nih_image_dir = out_dir / "data" / "nih_chestxray14" / "images_001" / "images"
    vindr_image_dir = out_dir / "data" / "vindr_cxr" / "images"
    nih_rows = []
    # 80 patients x 2 images = 160 images. The 70% split gives >100 train images,
    # and the smoke config caps training at 100 images.
    for patient_idx in range(80):
        for image_repeat in range(2):
            image_idx = patient_idx * 2 + image_repeat
            filename = f"nih_smoke_{image_idx:04d}.png"
            label = PRIMARY_LABELS[(patient_idx + image_repeat) % (len(PRIMARY_LABELS) - 1)]
            if rng.random() < 0.12:
                finding = "No Finding"
            elif rng.random() < 0.25 and label != "No Finding":
                second = PRIMARY_LABELS[(patient_idx + 3) % (len(PRIMARY_LABELS) - 1)]
                finding = f"{label}|{second}"
            else:
                finding = label
            make_image(nih_image_dir / filename, seed + image_idx, patient_idx % len(PRIMARY_LABELS))
            nih_rows.append(
                {
                    "Image Index": filename,
                    "Patient ID": patient_idx,
                    "Finding Labels": finding,
                    "View Position": "PA" if patient_idx % 3 else "AP",
                    "Patient Age": int(30 + patient_idx % 55),
                    "Patient Gender": "M" if patient_idx % 2 else "F",
                }
            )
    nih_csv = out_dir / "data" / "nih_chestxray14" / "Data_Entry_2017.csv"
    nih_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(nih_rows).to_csv(nih_csv, index=False)

    vindr_rows = []
    for image_idx in range(32):
        image_id = f"vindr_smoke_{image_idx:04d}"
        label = VINDR_LABELS[image_idx % len(VINDR_LABELS)]
        make_image(vindr_image_dir / f"{image_id}.png", seed + 10000 + image_idx, image_idx % len(VINDR_LABELS))
        if label.lower() == "no finding":
            vindr_rows.append({"image_id": image_id, "class_name": label, "x_min": "", "y_min": "", "x_max": "", "y_max": ""})
        else:
            vindr_rows.append(
                {
                    "image_id": image_id,
                    "class_name": label,
                    "x_min": 30,
                    "y_min": 35,
                    "x_max": 105,
                    "y_max": 120,
                }
            )
    vindr_csv = out_dir / "data" / "vindr_cxr" / "annotations_train.csv"
    vindr_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(vindr_rows).to_csv(vindr_csv, index=False)

    base_config = yaml.safe_load((root / "configs" / "config.yaml").read_text(encoding="utf-8"))
    base_config["nih"]["metadata_csv"] = str((nih_csv.relative_to(root)).as_posix())
    base_config["nih"]["image_root"] = str(((out_dir / "data" / "nih_chestxray14").relative_to(root)).as_posix())
    base_config["nih"]["output_csv"] = str(((out_dir / "metadata" / "nih_clean_metadata.csv").relative_to(root)).as_posix())
    base_config["nih"]["table1_csv"] = str(((out_dir / "tables" / "table1_nih_characteristics.csv").relative_to(root)).as_posix())
    base_config["nih"]["prevalence_csv"] = str(((out_dir / "tables" / "nih_label_prevalence.csv").relative_to(root)).as_posix())
    base_config["vindr"]["labels_csv"] = str((vindr_csv.relative_to(root)).as_posix())
    base_config["vindr"]["boxes_csv"] = str((vindr_csv.relative_to(root)).as_posix())
    base_config["vindr"]["image_root"] = str(((out_dir / "data" / "vindr_cxr").relative_to(root)).as_posix())
    base_config["vindr"]["output_csv"] = str(((out_dir / "metadata" / "vindr_clean_metadata.csv").relative_to(root)).as_posix())
    base_config["vindr"]["boxes_output_csv"] = str(((out_dir / "metadata" / "vindr_boxes_clean.csv").relative_to(root)).as_posix())
    base_config["vindr"]["table1_csv"] = str(((out_dir / "tables" / "table1_vindr_characteristics.csv").relative_to(root)).as_posix())
    base_config["vindr"]["prevalence_csv"] = str(((out_dir / "tables" / "vindr_label_prevalence.csv").relative_to(root)).as_posix())
    base_config["splits"]["input_csv"] = str(((out_dir / "metadata" / "nih_clean_metadata.csv").relative_to(root)).as_posix())
    base_config["splits"]["output_prefix"] = str(((out_dir / "splits" / "nih").relative_to(root)).as_posix())
    base_config["splits"]["split_stats_csv"] = str(((out_dir / "splits" / "nih_split_statistics.csv").relative_to(root)).as_posix())
    base_config["splits"]["split_summary_csv"] = str(((out_dir / "tables" / "table1_nih_split_summary.csv").relative_to(root)).as_posix())
    base_config["smoke_test"]["output_dir"] = str(((out_dir / "training_output").relative_to(root)).as_posix())
    base_config["smoke_test"]["checkpoint_dir"] = str(((out_dir / "models").relative_to(root)).as_posix())
    base_config["smoke_test"]["log_csv"] = str(((out_dir / "logs" / "synthetic_smoke_train_log.csv").relative_to(root)).as_posix())
    base_config["smoke_test"]["epochs"] = 1
    base_config["smoke_test"]["max_train_images"] = 100
    base_config["smoke_test"]["max_validation_images"] = 32
    base_config["smoke_test"]["max_vindr_images"] = 32
    base_config["smoke_test"]["num_workers"] = 0
    base_config["evaluation"]["checkpoint_path"] = str(((out_dir / "models" / "best_densenet121.pt").relative_to(root)).as_posix())
    base_config["evaluation"]["output_dir"] = str(((out_dir / "evaluation").relative_to(root)).as_posix())
    base_config["evaluation"]["validation_predictions_csv"] = str(((out_dir / "predictions" / "nih_validation_predictions.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["internal_predictions_csv"] = str(((out_dir / "predictions" / "internal_test_predictions.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["internal_metrics_csv"] = str(((out_dir / "evaluation" / "internal_metrics.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["thresholds_csv"] = str(((out_dir / "evaluation" / "thresholds_from_val.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["bootstrap_ci_csv"] = str(((out_dir / "evaluation" / "bootstrap_ci.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["external_predictions_csv"] = str(((out_dir / "predictions" / "external_vindr_predictions.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["external_metrics_csv"] = str(((out_dir / "evaluation" / "external_metrics.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["internal_external_comparison_csv"] = str(((out_dir / "evaluation" / "internal_external_comparison.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["performance_drop_csv"] = str(((out_dir / "evaluation" / "performance_drop.csv").relative_to(root)).as_posix())
    base_config["evaluation"]["bootstrap_iterations"] = 50
    base_config["calibration"]["output_dir"] = str(((out_dir / "calibration").relative_to(root)).as_posix())
    base_config["calibration"]["raw_calibration_predictions_csv"] = str(((out_dir / "predictions" / "nih_calibration_predictions.csv").relative_to(root)).as_posix())
    base_config["calibration"]["raw_internal_predictions_csv"] = str(((out_dir / "predictions" / "internal_test_predictions.csv").relative_to(root)).as_posix())
    base_config["calibration"]["raw_external_predictions_csv"] = str(((out_dir / "predictions" / "external_vindr_predictions.csv").relative_to(root)).as_posix())
    base_config["calibration"]["calibrated_predictions_csv"] = str(((out_dir / "calibration" / "calibrated_predictions.csv").relative_to(root)).as_posix())
    base_config["calibration"]["calibration_metrics_csv"] = str(((out_dir / "calibration" / "calibration_metrics.csv").relative_to(root)).as_posix())
    base_config["calibration"]["curves_dir"] = str(((out_dir / "figures" / "calibration").relative_to(root)).as_posix())
    base_config["gradcam"]["output_dir"] = str(((out_dir / "figures" / "gradcam").relative_to(root)).as_posix())
    base_config["gradcam"]["case_index_csv"] = str(((out_dir / "gradcam" / "case_index.csv").relative_to(root)).as_posix())
    base_config["gradcam"]["localization_metrics_csv"] = str(((out_dir / "gradcam" / "localization_metrics.csv").relative_to(root)).as_posix())
    base_config["gradcam"]["internal_predictions_csv"] = str(((out_dir / "predictions" / "internal_test_predictions.csv").relative_to(root)).as_posix())
    base_config["gradcam"]["external_predictions_csv"] = str(((out_dir / "predictions" / "external_vindr_predictions.csv").relative_to(root)).as_posix())
    config_path = out_dir / "synthetic_smoke_config.yaml"
    config_path.write_text(yaml.safe_dump(base_config, sort_keys=False), encoding="utf-8")
    return config_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a synthetic local smoke dataset for code-path validation only.")
    parser.add_argument("--out-dir", default="outputs/synthetic_smoke_100")
    parser.add_argument("--seed", type=int, default=20260613)
    args = parser.parse_args()
    config_path = create_synthetic_smoke(ROOT, ROOT / args.out_dir, seed=args.seed)
    print(config_path)


if __name__ == "__main__":
    main()


