from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config, resolve_path
from .inference import add_binary_predictions, predict_to_dataframe
from .metrics import add_ci_to_metrics, compute_metrics, patient_bootstrap_ci, select_thresholds_from_validation
from .utils import ensure_dirs, setup_logging


def evaluate_internal(config_path: str | Path, checkpoint_path: str | Path | None = None) -> dict[str, str]:
    config = load_config(config_path)
    eval_cfg = config.get("evaluation", {})
    splits_cfg = config["splits"]
    logger = setup_logging(resolve_path(config, "logs/evaluate_internal.log"))

    checkpoint = resolve_path(config, checkpoint_path or eval_cfg.get("checkpoint_path"))
    prefix = resolve_path(config, splits_cfg["output_prefix"])
    validation_csv = Path(f"{prefix}_validation.csv")
    internal_csv = Path(f"{prefix}_internal_test.csv")
    validation_pred_csv = resolve_path(config, eval_cfg.get("validation_predictions_csv", "predictions/nih_validation_predictions.csv"))
    internal_pred_csv = resolve_path(config, eval_cfg.get("internal_predictions_csv", "predictions/internal_test_predictions.csv"))
    thresholds_csv = resolve_path(config, eval_cfg.get("thresholds_csv", "outputs/evaluation/thresholds_from_val.csv"))
    metrics_csv = resolve_path(config, eval_cfg.get("internal_metrics_csv", "outputs/evaluation/internal_metrics.csv"))
    ci_csv = resolve_path(config, eval_cfg.get("bootstrap_ci_csv", "outputs/evaluation/bootstrap_ci.csv"))
    ensure_dirs([validation_pred_csv.parent, internal_pred_csv.parent, thresholds_csv.parent, metrics_csv.parent, ci_csv.parent])

    logger.info("Predicting NIH validation split for threshold selection: %s", validation_csv)
    val_pred = predict_to_dataframe(config, checkpoint, validation_csv, validation_pred_csv)
    label_cols = [col.replace("true_", "") for col in val_pred.columns if col.startswith("true_")]
    thresholds = select_thresholds_from_validation(val_pred, label_cols, metric=eval_cfg.get("threshold_metric", "f1"))
    thresholds.to_csv(thresholds_csv, index=False)
    logger.info("Saved validation-derived thresholds: %s", thresholds_csv)

    logger.info("Predicting NIH internal test split: %s", internal_csv)
    internal_pred = predict_to_dataframe(config, checkpoint, internal_csv, internal_pred_csv)
    internal_pred = add_binary_predictions(internal_pred, thresholds, label_cols)
    internal_pred.to_csv(internal_pred_csv, index=False)
    logger.info("Saved internal test predictions: %s", internal_pred_csv)

    metrics = compute_metrics(internal_pred, label_cols, dataset_name="NIH_internal_test")
    ci = patient_bootstrap_ci(
        internal_pred,
        label_cols,
        dataset_name="NIH_internal_test",
        n_bootstrap=int(eval_cfg.get("bootstrap_iterations", 1000)),
        seed=int(eval_cfg.get("bootstrap_seed", 20260613)),
    )
    metrics_with_ci = add_ci_to_metrics(metrics, ci)
    metrics_with_ci.to_csv(metrics_csv, index=False)
    ci.to_csv(ci_csv, index=False)
    logger.info("Saved internal metrics: %s", metrics_csv)
    logger.info("Saved bootstrap CI: %s", ci_csv)
    return {
        "validation_predictions": str(validation_pred_csv),
        "thresholds": str(thresholds_csv),
        "internal_predictions": str(internal_pred_csv),
        "internal_metrics": str(metrics_csv),
        "bootstrap_ci": str(ci_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DenseNet121 on NIH ChestX-ray14 internal test set.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()
    print(evaluate_internal(args.config, checkpoint_path=args.checkpoint))


if __name__ == "__main__":
    main()



