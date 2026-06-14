from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_config, resolve_path
from .datasets import build_dataloaders, compute_positive_class_weights, get_label_columns
from .models import create_model, freeze_backbone, unfreeze_all
from .utils import ensure_dirs, environment_report, save_pip_freeze, set_seed, setup_logging, write_json


def macro_auprc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    from sklearn.metrics import average_precision_score

    scores = []
    for idx in range(y_true.shape[1]):
        positives = y_true[:, idx].sum()
        negatives = y_true.shape[0] - positives
        if positives == 0 or negatives == 0:
            continue
        scores.append(float(average_precision_score(y_true[:, idx], y_score[:, idx])))
    return float(np.mean(scores)) if scores else 0.0


def train_one_epoch(model, loader, criterion, optimizer, scaler, device, amp_enabled: bool, grad_clip_norm: float | None) -> float:
    import torch

    model.train()
    total_loss = 0.0
    total_examples = 0
    for batch in loader:
        images = batch["image"].to(device, non_blocking=True)
        targets = batch["target"].to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type=device.type, enabled=amp_enabled):
            logits = model(images)
            loss = criterion(logits, targets)
        scaler.scale(loss).backward()
        if grad_clip_norm is not None and grad_clip_norm > 0:
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=float(grad_clip_norm))
        scaler.step(optimizer)
        scaler.update()
        batch_size = images.shape[0]
        total_loss += float(loss.detach().cpu()) * batch_size
        total_examples += batch_size
    return total_loss / max(total_examples, 1)


def validate(model, loader, criterion, device, amp_enabled: bool) -> dict[str, float]:
    import torch

    model.eval()
    total_loss = 0.0
    total_examples = 0
    y_true = []
    y_score = []
    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device, non_blocking=True)
            targets = batch["target"].to(device, non_blocking=True)
            with torch.amp.autocast(device_type=device.type, enabled=amp_enabled):
                logits = model(images)
                loss = criterion(logits, targets)
            probs = torch.sigmoid(logits)
            batch_size = images.shape[0]
            total_loss += float(loss.detach().cpu()) * batch_size
            total_examples += batch_size
            y_true.append(targets.detach().cpu().numpy())
            y_score.append(probs.detach().cpu().numpy())
    y_true_np = np.concatenate(y_true, axis=0) if y_true else np.zeros((0, 0), dtype=np.float32)
    y_score_np = np.concatenate(y_score, axis=0) if y_score else np.zeros((0, 0), dtype=np.float32)
    return {
        "val_loss": total_loss / max(total_examples, 1),
        "val_macro_auprc": macro_auprc(y_true_np, y_score_np) if y_true_np.size else float("nan"),
    }


def _write_log_header(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "epoch",
                    "train_loss",
                    "val_loss",
                    "val_macro_auprc",
                    "lr",
                    "best_val_macro_auprc",
                    "improved",
                ],
            )
            writer.writeheader()


def _append_log(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "val_loss", "val_macro_auprc", "lr", "best_val_macro_auprc", "improved"])
        writer.writerow(row)


def save_checkpoint(path: Path, model, optimizer, scheduler, epoch: int, best_metric: float, config: dict[str, Any], label_cols: list[str]) -> None:
    import torch

    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
            "best_val_macro_auprc": best_metric,
            "config": config,
            "label_cols": label_cols,
        },
        path,
    )


def make_grad_scaler(torch_module, device_type: str, enabled: bool):
    try:
        return torch_module.amp.GradScaler(device_type, enabled=enabled)
    except TypeError:
        return torch_module.amp.GradScaler(enabled=enabled)


def train(config_path: str | Path, smoke: bool = False) -> dict[str, Any]:
    import torch
    import yaml

    config = load_config(config_path)
    seed = int(config.get("project", {}).get("seed", 20260613))
    set_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True

    training_cfg = dict(config.get("training", {}))
    if smoke:
        smoke_cfg = config.get("smoke_test", {})
        training_cfg["output_dir"] = smoke_cfg.get("output_dir", training_cfg.get("output_dir"))
        training_cfg["checkpoint_dir"] = smoke_cfg.get("checkpoint_dir", training_cfg.get("checkpoint_dir"))
        training_cfg["log_csv"] = smoke_cfg.get("log_csv", training_cfg.get("log_csv"))
        training_cfg["epochs"] = smoke_cfg.get("epochs", 1)

    output_dir = resolve_path(config, training_cfg.get("output_dir", "outputs/training/densenet121_nih_224"))
    checkpoint_dir = resolve_path(config, training_cfg.get("checkpoint_dir", "models/densenet121_nih_224"))
    log_csv = resolve_path(config, training_cfg.get("log_csv", "logs/densenet121_nih_224_train_log.csv"))
    ensure_dirs([output_dir, checkpoint_dir, log_csv.parent])
    logger = setup_logging(output_dir / "train.log")
    logger.info("Starting %s training", "smoke" if smoke else "full")

    shutil.copy2(resolve_path(config, config["paths"]["label_map"]), output_dir / "label_map.yaml")
    shutil.copy2(Path(config_path), output_dir / "config.yaml")
    write_json(output_dir / "environment_report.json", environment_report())
    save_pip_freeze(output_dir / "pip_freeze.txt")
    (output_dir / "resolved_training_config.yaml").write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp_enabled = bool(training_cfg.get("amp", True)) and device.type == "cuda"
    logger.info("Device: %s | AMP: %s", device, amp_enabled)

    loaders = build_dataloaders(config, smoke=smoke)
    label_cols = get_label_columns(config)
    model = create_model(config, num_labels=len(label_cols)).to(device)
    freeze_epochs = int(config.get("model", {}).get("freeze_backbone_epochs", 0))
    if freeze_epochs > 0:
        freeze_backbone(model)
        logger.info("Backbone frozen for %d epochs", freeze_epochs)

    pos_weight = compute_positive_class_weights(loaders["train"].dataset, label_cols).to(device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(training_cfg.get("learning_rate", 1e-4)),
        weight_decay=float(training_cfg.get("weight_decay", 1e-4)),
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
    scaler = make_grad_scaler(torch, device.type, amp_enabled)

    epochs = int(training_cfg.get("epochs", 30))
    patience = int(training_cfg.get("early_stopping_patience", 6))
    min_delta = float(training_cfg.get("min_delta", 1e-4))
    grad_clip = training_cfg.get("gradient_clip_norm", 1.0)
    model_name = str(config.get("model", {}).get("name", "densenet121")).lower().replace("-", "_")
    best_metric = -float("inf")
    bad_epochs = 0
    best_path = checkpoint_dir / f"best_{model_name}.pt"
    last_path = checkpoint_dir / f"last_{model_name}.pt"
    if log_csv.exists():
        log_csv.unlink()
    _write_log_header(log_csv)

    for epoch in range(1, epochs + 1):
        if freeze_epochs > 0 and epoch == freeze_epochs + 1:
            unfreeze_all(model)
            optimizer = torch.optim.AdamW(model.parameters(), lr=float(training_cfg.get("learning_rate", 1e-4)), weight_decay=float(training_cfg.get("weight_decay", 1e-4)))
            scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)
            logger.info("Backbone unfrozen at epoch %d", epoch)
        train_loss = train_one_epoch(model, loaders["train"], criterion, optimizer, scaler, device, amp_enabled, grad_clip)
        val_metrics = validate(model, loaders["validation"], criterion, device, amp_enabled)
        metric = float(val_metrics["val_macro_auprc"])
        scheduler.step(metric if np.isfinite(metric) else -1.0)
        improved = bool(np.isfinite(metric) and metric > best_metric + min_delta)
        if improved:
            best_metric = metric
            bad_epochs = 0
            save_checkpoint(best_path, model, optimizer, scheduler, epoch, best_metric, config, label_cols)
        else:
            bad_epochs += 1
        save_checkpoint(last_path, model, optimizer, scheduler, epoch, best_metric, config, label_cols)
        if bool(training_cfg.get("save_every_epoch", False)):
            save_checkpoint(checkpoint_dir / f"epoch_{epoch:03d}.pt", model, optimizer, scheduler, epoch, best_metric, config, label_cols)

        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_metrics["val_loss"],
            "val_macro_auprc": metric,
            "lr": optimizer.param_groups[0]["lr"],
            "best_val_macro_auprc": best_metric,
            "improved": improved,
        }
        _append_log(log_csv, row)
        logger.info(
            "epoch=%d train_loss=%.5f val_loss=%.5f val_macro_auprc=%.5f best=%.5f improved=%s",
            epoch,
            train_loss,
            val_metrics["val_loss"],
            metric,
            best_metric,
            improved,
        )
        if bad_epochs >= patience:
            logger.info("Early stopping triggered after %d non-improving epochs", bad_epochs)
            break

    summary = {
        "best_checkpoint": str(best_path),
        "last_checkpoint": str(last_path),
        "log_csv": str(log_csv),
        "best_val_macro_auprc": best_metric,
        "labels": label_cols,
        "smoke": smoke,
    }
    write_json(output_dir / "training_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DenseNet121 on NIH ChestX-ray14.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--smoke", action="store_true", help="Run the 100-image smoke-test training configuration.")
    args = parser.parse_args()
    train(args.config, smoke=args.smoke)


if __name__ == "__main__":
    main()


