from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.splits import create_patient_splits
from scripts.prepare_hf_large import LABELS, _vin_targets, label_prevalence, write_large_config


def raw_paths() -> tuple[Path, Path]:
    base = ROOT / "data" / "hf_large" / "vinbig_processed" / "_downloads"
    raw_zip = base / "train_raw.csv"
    meta_csv = base / "vinbig_png" / "train_meta.csv"
    unzip_dir = base / "train_raw_unzipped"
    unzip_dir.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(raw_zip):
        with zipfile.ZipFile(raw_zip) as zf:
            zf.extractall(unzip_dir)
        raw_csv = unzip_dir / "train.csv"
    else:
        raw_csv = raw_zip
    if not raw_csv.exists() or not meta_csv.exists():
        raise FileNotFoundError("VinDr/VinBigData raw CSV files are missing. Re-run prepare_hf_large.py.")
    return raw_csv, meta_csv


def finalize_vindr_from_cached() -> Path:
    raw_csv, meta_csv = raw_paths()
    raw = pd.read_csv(raw_csv)
    meta = pd.read_csv(meta_csv)
    image_dir = ROOT / "data" / "hf_large" / "vindr_cxr" / "images"
    cached = sorted(image_dir.glob("*.png"))
    if not cached:
        raise FileNotFoundError(f"No cached VinDr PNG files found in {image_dir}")
    cached_ids = {p.stem for p in cached}
    grouped = raw.groupby("image_id")["class_name"].apply(lambda s: set(s.dropna().astype(str))).reset_index()
    grouped = grouped[grouped["image_id"].isin(cached_ids)].copy()
    for label in LABELS:
        grouped[label] = grouped["class_name"].map(lambda labs, label=label: _vin_targets(labs)[label])
    meta_map = meta.set_index("image_id").to_dict("index")

    rows = []
    boxes = []
    for _, row in grouped.sort_values("image_id").iterrows():
        image_id = row["image_id"]
        path = image_dir / f"{image_id}.png"
        with Image.open(path) as img:
            png_w, png_h = img.size
        out_row = {
            "dataset": "VinDr-CXR/VinBigData HF public PNG large cached subset",
            "image_id": f"{image_id}.png",
            "study_id": image_id,
            "patient_id": image_id,
            "image_path": str(path.resolve()),
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize hf_large metadata from already cached files.")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260614)
    args = parser.parse_args()
    nih_csv = ROOT / "metadata_large" / "hf_large_nih_clean_metadata.csv"
    if not nih_csv.exists():
        raise FileNotFoundError(f"Missing NIH metadata: {nih_csv}")
    vindr_csv = finalize_vindr_from_cached()
    config_path = write_large_config(nih_csv, vindr_csv, args.epochs, args.seed)
    create_patient_splits(config_path)
    label_prevalence(nih_csv, ROOT / "tables_large" / "hf_large_nih_label_prevalence.csv")
    label_prevalence(vindr_csv, ROOT / "tables_large" / "hf_large_vindr_label_prevalence.csv")
    manifest = {
        "nih_metadata": str(nih_csv),
        "vindr_metadata": str(vindr_csv),
        "config": str(config_path),
        "nih_images": int(len(pd.read_csv(nih_csv))),
        "vindr_images": int(len(pd.read_csv(vindr_csv))),
        "note": "Large run finalized from cached real public files after network timeout. Not synthetic.",
    }
    out = ROOT / "outputs_large" / "hf_large_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()


