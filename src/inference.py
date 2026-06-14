from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .datasets import make_dataloader, make_dataset
from .models import create_model


def _collated_value(values: Any, index: int) -> Any:
    try:
        value = values[index]
    except Exception:
        value = values
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def load_checkpoint_model(config: dict[str, Any], checkpoint_path: str | Path, device):
    import torch

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    label_cols = checkpoint.get("label_cols")
    if not label_cols:
        raise KeyError(f"Checkpoint has no label_cols: {checkpoint_path}")
    model = create_model(config, num_labels=len(label_cols))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()
    return model, label_cols, checkpoint


def predict_to_dataframe(
    config: dict[str, Any],
    checkpoint_path: str | Path,
    csv_path: str | Path,
    output_csv: str | Path,
    batch_size: int | None = None,
    num_workers: int | None = None,
    max_samples: int | None = None,
) -> pd.DataFrame:
    import torch

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, label_cols, _ = load_checkpoint_model(config, checkpoint_path, device)
    dl_cfg = config.get("dataloader", {})
    dataset = make_dataset(config, csv_path, train=False, max_samples=max_samples)
    loader = make_dataloader(
        dataset,
        batch_size=int(batch_size or dl_cfg.get("eval_batch_size", 64)),
        shuffle=False,
        num_workers=int(num_workers if num_workers is not None else dl_cfg.get("num_workers", 4)),
        pin_memory=bool(dl_cfg.get("pin_memory", True)),
        persistent_workers=bool(dl_cfg.get("persistent_workers", True)),
    )

    rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device, non_blocking=True)
            logits = model(images)
            probs = torch.sigmoid(logits)
            logits_np = logits.detach().cpu().numpy()
            probs_np = probs.detach().cpu().numpy()
            targets_np = batch["target"].detach().cpu().numpy()
            batch_size_actual = images.shape[0]
            for i in range(batch_size_actual):
                row = {
                    "dataset": _collated_value(batch["metadata"]["dataset"], i)
                    if isinstance(batch["metadata"], dict) and "dataset" in batch["metadata"]
                    else "",
                    "patient_id": _collated_value(batch["patient_id"], i),
                    "image_id": _collated_value(batch["image_id"], i),
                    "image_path": _collated_value(batch.get("image_path", ""), i),
                }
                if isinstance(batch["metadata"], dict):
                    for key, values in batch["metadata"].items():
                        row[key] = _collated_value(values, i)
                for j, label in enumerate(label_cols):
                    row[f"true_{label}"] = float(targets_np[i, j])
                    row[f"logit_{label}"] = float(logits_np[i, j])
                    row[f"prob_{label}"] = float(probs_np[i, j])
                rows.append(row)
    df = pd.DataFrame(rows)
    output_csv = Path(output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    return df


def add_binary_predictions(pred_df: pd.DataFrame, thresholds_df: pd.DataFrame, label_cols: list[str]) -> pd.DataFrame:
    out = pred_df.copy()
    threshold_map = dict(zip(thresholds_df["label"], thresholds_df["threshold"]))
    for label in label_cols:
        threshold = float(threshold_map[label])
        out[f"pred_{label}"] = (out[f"prob_{label}"] >= threshold).astype(int)
    return out


def prediction_arrays(pred_df: pd.DataFrame, label_cols: list[str], prob_prefix: str = "prob") -> tuple[np.ndarray, np.ndarray]:
    y_true = pred_df[[f"true_{label}" for label in label_cols]].to_numpy(dtype=float)
    y_score = pred_df[[f"{prob_prefix}_{label}" for label in label_cols]].to_numpy(dtype=float)
    return y_true, y_score


