from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import resolve_path
from .label_mapping import harmonized_labels, load_label_map
from .preprocessing import build_transforms, image_loader_from_config


class ChestXrayDataset:
    def __init__(
        self,
        csv_path: str | Path,
        label_cols: list[str],
        transform=None,
        image_loader=None,
        max_samples: int | None = None,
        require_existing_paths: bool = True,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.df = pd.read_csv(self.csv_path)
        if max_samples is not None:
            self.df = self.df.head(int(max_samples)).copy()
        self.label_cols = label_cols
        self.transform = transform
        self.image_loader = image_loader
        self.require_existing_paths = require_existing_paths
        required_cols = {"image_path", "image_id", "patient_id"}
        missing = sorted(required_cols - set(self.df.columns))
        if missing:
            raise KeyError(f"{self.csv_path} is missing required columns: {missing}")
        missing_labels = [label for label in label_cols if label not in self.df.columns]
        if missing_labels:
            raise KeyError(f"{self.csv_path} is missing label columns: {missing_labels}")
        if require_existing_paths:
            missing_paths = [p for p in self.df["image_path"].astype(str).tolist() if not Path(p).exists()]
            if missing_paths:
                raise FileNotFoundError(f"{len(missing_paths)} image paths do not exist. First missing path: {missing_paths[0]}")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, index: int) -> dict[str, Any]:
        row = self.df.iloc[index]
        image = self.image_loader(row["image_path"]) if self.image_loader is not None else row["image_path"]
        if self.transform is not None:
            image = self.transform(image)
        labels = row[self.label_cols].fillna(0).astype("float32").to_numpy()
        import torch

        target = torch.tensor(labels, dtype=torch.float32)
        metadata = {
            "dataset": row.get("dataset", ""),
            "study_id": row.get("study_id", ""),
            "view_position": row.get("view_position", ""),
            "age": row.get("age", ""),
            "sex": row.get("sex", ""),
        }
        return {
            "image": image,
            "target": target,
            "patient_id": str(row["patient_id"]),
            "image_id": str(row["image_id"]),
            "image_path": str(row["image_path"]),
            "metadata": metadata,
        }


def get_label_columns(config: dict[str, Any]) -> list[str]:
    label_map_path = resolve_path(config, config["paths"]["label_map"])
    label_map = load_label_map(label_map_path)
    return harmonized_labels(label_map, include_sensitivity=bool(config.get("labels", {}).get("include_sensitivity_labels", True)))


def make_dataset(
    config: dict[str, Any],
    csv_path: str | Path,
    train: bool,
    max_samples: int | None = None,
    require_existing_paths: bool = True,
) -> ChestXrayDataset:
    labels = get_label_columns(config)
    transform = build_transforms(config, train=train)
    loader = image_loader_from_config(config)
    return ChestXrayDataset(
        csv_path=csv_path,
        label_cols=labels,
        transform=transform,
        image_loader=loader,
        max_samples=max_samples,
        require_existing_paths=require_existing_paths,
    )


def make_dataloader(dataset, batch_size: int, shuffle: bool, num_workers: int, pin_memory: bool, persistent_workers: bool):
    from torch.utils.data import DataLoader

    use_persistent = bool(persistent_workers and num_workers > 0)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=int(num_workers),
        pin_memory=bool(pin_memory),
        persistent_workers=use_persistent,
    )


def build_dataloaders(config: dict[str, Any], smoke: bool = False) -> dict[str, Any]:
    splits_cfg = config["splits"]
    dl_cfg = dict(config.get("dataloader", {}))
    smoke_cfg = config.get("smoke_test", {}) if smoke else {}
    if smoke:
        dl_cfg["train_batch_size"] = smoke_cfg.get("train_batch_size", dl_cfg.get("train_batch_size", 8))
        dl_cfg["eval_batch_size"] = smoke_cfg.get("eval_batch_size", dl_cfg.get("eval_batch_size", 8))
        dl_cfg["num_workers"] = smoke_cfg.get("num_workers", 0)
        dl_cfg["persistent_workers"] = False

    prefix = resolve_path(config, splits_cfg["output_prefix"])
    train_csv = Path(f"{prefix}_train.csv")
    val_csv = Path(f"{prefix}_validation.csv")
    calibration_csv = Path(f"{prefix}_calibration.csv")
    internal_test_csv = Path(f"{prefix}_internal_test.csv")
    vindr_csv = resolve_path(config, config["vindr"]["output_csv"])

    train_ds = make_dataset(config, train_csv, train=True, max_samples=smoke_cfg.get("max_train_images"))
    val_ds = make_dataset(config, val_csv, train=False, max_samples=smoke_cfg.get("max_validation_images"))
    loaders = {
        "train": make_dataloader(
            train_ds,
            batch_size=int(dl_cfg.get("train_batch_size", 32)),
            shuffle=True,
            num_workers=int(dl_cfg.get("num_workers", 4)),
            pin_memory=bool(dl_cfg.get("pin_memory", True)),
            persistent_workers=bool(dl_cfg.get("persistent_workers", True)),
        ),
        "validation": make_dataloader(
            val_ds,
            batch_size=int(dl_cfg.get("eval_batch_size", 64)),
            shuffle=False,
            num_workers=int(dl_cfg.get("num_workers", 4)),
            pin_memory=bool(dl_cfg.get("pin_memory", True)),
            persistent_workers=bool(dl_cfg.get("persistent_workers", True)),
        ),
    }
    optional_sets = {
        "calibration": calibration_csv,
        "internal_test": internal_test_csv,
        "vindr": vindr_csv,
    }
    for name, csv_path in optional_sets.items():
        if csv_path is not None and Path(csv_path).exists():
            max_samples = smoke_cfg.get("max_vindr_images") if name == "vindr" else smoke_cfg.get("max_validation_images")
            ds = make_dataset(config, csv_path, train=False, max_samples=max_samples)
            loaders[name] = make_dataloader(
                ds,
                batch_size=int(dl_cfg.get("eval_batch_size", 64)),
                shuffle=False,
                num_workers=int(dl_cfg.get("num_workers", 4)),
                pin_memory=bool(dl_cfg.get("pin_memory", True)),
                persistent_workers=bool(dl_cfg.get("persistent_workers", True)),
            )
    return loaders


def compute_positive_class_weights(dataset: ChestXrayDataset, label_cols: list[str]):
    import torch

    labels = dataset.df[label_cols].fillna(0).astype("float32")
    positives = torch.tensor(labels.sum(axis=0).to_numpy(), dtype=torch.float32)
    total = float(len(labels))
    negatives = torch.tensor(total, dtype=torch.float32) - positives
    weights = negatives / torch.clamp(positives, min=1.0)
    weights = torch.clamp(weights, min=1.0, max=100.0)
    return weights


