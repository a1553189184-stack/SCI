from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".dcm", ".dicom"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def ensure_dirs(paths: Iterable[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_path: Path | None = None) -> logging.Logger:
    logger = logging.getLogger("cxr_nih_to_vindr")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def first_existing_column(df: pd.DataFrame, candidates: list[str], required: bool = True) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    lower_to_original = {str(c).strip().lower(): c for c in df.columns}
    for candidate in candidates:
        found = lower_to_original.get(candidate.strip().lower())
        if found is not None:
            return found
    if required:
        raise KeyError(f"None of these columns were found: {candidates}. Available columns: {list(df.columns)}")
    return None


def build_image_index(image_root: Path) -> dict[str, Path]:
    """Index images by exact filename and by stem for flexible dataset metadata."""
    index: dict[str, Path] = {}
    if not image_root.exists():
        return index
    for path in image_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        index.setdefault(path.name, path)
        index.setdefault(path.stem, path)
    return index


def locate_image(image_id: str, image_index: dict[str, Path]) -> str:
    key = str(image_id)
    path = image_index.get(key) or image_index.get(Path(key).name) or image_index.get(Path(key).stem)
    return str(path) if path is not None else ""


def save_prevalence(df: pd.DataFrame, labels: list[str], path: Path, dataset_name: str) -> pd.DataFrame:
    rows = []
    n = len(df)
    for label in labels:
        positives = int(df[label].fillna(0).sum()) if label in df.columns else 0
        rows.append(
            {
                "dataset": dataset_name,
                "label": label,
                "n_images": n,
                "positive_images": positives,
                "prevalence": positives / n if n else 0.0,
            }
        )
    out = pd.DataFrame(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return out


def save_dataset_characteristics(df: pd.DataFrame, path: Path, dataset_name: str, role: str, image_format: str, label_source: str) -> pd.DataFrame:
    row = {
        "dataset": dataset_name,
        "role": role,
        "n_patients": int(df["patient_id"].nunique()) if "patient_id" in df.columns else "",
        "n_studies": int(df["study_id"].nunique()) if "study_id" in df.columns else "",
        "n_images": int(len(df)),
        "image_format": image_format,
        "label_source": label_source,
        "metadata_columns": ";".join(map(str, df.columns)),
    }
    out = pd.DataFrame([row])
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    return out


def save_pip_freeze(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=False)
    path.write_text(result.stdout, encoding="utf-8")


def environment_report() -> dict:
    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "python": sys.version,
        "executable": sys.executable,
    }
    try:
        import torch

        report.update(
            {
                "torch": torch.__version__,
                "cuda_available": bool(torch.cuda.is_available()),
                "torch_cuda": torch.version.cuda,
                "cuda_device_count": int(torch.cuda.device_count()),
                "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
            }
        )
    except Exception as exc:
        report["torch_error"] = repr(exc)
    return report



