from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .config import load_config, resolve_path
from .inference import add_binary_predictions, predict_to_dataframe
from .metrics import add_ci_to_metrics, compare_internal_external, compute_metrics, patient_bootstrap_ci
from .utils import ensure_dirs, setup_logging


def evaluate_external(config_path: str | Path, checkpoint_path: str | Path | None = None) -> dict[str, str]:
    config = load_config(config_path)
    eval_cfg = config.get("evaluation", {})
    logger = setup_logging(resolve_path(config, "logs/evaluate_external.log"))

    checkpoint = resolve_path(config, checkpoint_path or eval_cfg.get("checkpoint_path"))
    vindr_csv = resolve_path(config, config["vindr"]["output_csv"])
    thresholds_csv = resolve_path(config, eval_cfg.get("thresholds_csv", "outputs/evaluation/thresholds_from_val.csv"))
    external_pred_csv = resolve_path(config, eval_cfg.get("external_predictions_csv", "predictions/external_vindr_predictions.csv"))
    external_metrics_csv = resolve_path(config, eval_cfg.get("external_metrics_csv", "outputs/evaluation/external_metrics.csv"))
    internal_metrics_csv = resolve_path(config, eval_cfg.get("internal_metrics_csv", "outputs/evaluation/internal_metrics.csv"))
    comparison_csv = resolve_path(config, eval_cfg.get("internal_external_comparison_csv", "outputs/evaluation/internal_external_comparison.csv"))
    drop_csv = resolve_path(config, eval_cfg.get("performance_drop_csv", "outputs/evaluation/performance_drop.csv"))
    ensure_dirs([external_pred_csv.parent, external_metrics_csv.parent, comparison_csv.parent, drop_csv.parent])
    if not thresholds_csv.exists():
        raise FileNotFoundError(f"Validation-derived threshold file not found. Run evaluate_internal.py first: {thresholds_csv}")

    thresholds = pd.read_csv(thresholds_csv)
    label_cols = thresholds["label"].tolist()
    logger.info("Predicting VinDr-CXR external validation with fixed NIH validation thresholds")
    external_pred = predict_to_dataframe(config, checkpoint, vindr_csv, external_pred_csv)
    external_pred = add_binary_predictions(external_pred, thresholds, label_cols)
    external_pred.to_csv(external_pred_csv, index=False)

    metrics = compute_metrics(external_pred, label_cols, dataset_name="VinDr_external")
    ci = patient_bootstrap_ci(
        external_pred,
        label_cols,
        dataset_name="VinDr_external",
        n_bootstrap=int(eval_cfg.get("bootstrap_iterations", 1000)),
        seed=int(eval_cfg.get("bootstrap_seed", 20260613)) + 17,
    )
    metrics_with_ci = add_ci_to_metrics(metrics, ci)
    metrics_with_ci.to_csv(external_metrics_csv, index=False)
    logger.info("Saved external metrics: %s", external_metrics_csv)

    if internal_metrics_csv.exists():
        internal_metrics = pd.read_csv(internal_metrics_csv)
        comparison, drop = compare_internal_external(internal_metrics, metrics_with_ci)
        comparison.to_csv(comparison_csv, index=False)
        drop.to_csv(drop_csv, index=False)
        logger.info("Saved internal-external comparison: %s", comparison_csv)
        logger.info("Saved performance-drop table: %s", drop_csv)
    else:
        logger.warning("Internal metrics not found; skipping internal-external comparison: %s", internal_metrics_csv)

    return {
        "external_predictions": str(external_pred_csv),
        "external_metrics": str(external_metrics_csv),
        "internal_external_comparison": str(comparison_csv),
        "performance_drop": str(drop_csv),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DenseNet121 unchanged on VinDr-CXR external validation.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--checkpoint", default=None)
    args = parser.parse_args()
    print(evaluate_external(args.config, checkpoint_path=args.checkpoint))


if __name__ == "__main__":
    main()



