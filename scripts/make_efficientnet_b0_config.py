from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    src = ROOT / "configs" / "hf_large.yaml"
    dst = ROOT / "configs" / "hf_large_efficientnet_b0.yaml"
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))

    cfg["model"]["name"] = "efficientnet_b0"
    cfg["training"]["run_name"] = "hf_large_efficientnet_b0"
    cfg["training"]["output_dir"] = "outputs_large/training/hf_large_efficientnet_b0"
    cfg["training"]["checkpoint_dir"] = "models_large/hf_large_efficientnet_b0"
    cfg["training"]["log_csv"] = "logs_large/hf_large_efficientnet_b0_train_log.csv"

    cfg["evaluation"]["checkpoint_path"] = "models_large/hf_large_efficientnet_b0/best_efficientnet_b0.pt"
    cfg["evaluation"]["validation_predictions_csv"] = "predictions_large/efficientnet_b0_nih_validation_predictions.csv"
    cfg["evaluation"]["internal_predictions_csv"] = "predictions_large/efficientnet_b0_internal_test_predictions.csv"
    cfg["evaluation"]["internal_metrics_csv"] = "tables_large/efficientnet_b0_internal_metrics.csv"
    cfg["evaluation"]["thresholds_csv"] = "tables_large/efficientnet_b0_thresholds_from_val.csv"
    cfg["evaluation"]["bootstrap_ci_csv"] = "tables_large/efficientnet_b0_bootstrap_ci.csv"
    cfg["evaluation"]["external_predictions_csv"] = "predictions_large/efficientnet_b0_external_vindr_predictions.csv"
    cfg["evaluation"]["external_metrics_csv"] = "tables_large/efficientnet_b0_external_metrics.csv"
    cfg["evaluation"]["internal_external_comparison_csv"] = "tables_large/efficientnet_b0_internal_external_comparison.csv"
    cfg["evaluation"]["performance_drop_csv"] = "tables_large/efficientnet_b0_performance_drop.csv"

    cfg["calibration"]["output_dir"] = "outputs_large/calibration/hf_large_efficientnet_b0"
    cfg["calibration"]["raw_calibration_predictions_csv"] = "predictions_large/efficientnet_b0_nih_calibration_predictions.csv"
    cfg["calibration"]["raw_internal_predictions_csv"] = "predictions_large/efficientnet_b0_internal_test_predictions.csv"
    cfg["calibration"]["raw_external_predictions_csv"] = "predictions_large/efficientnet_b0_external_vindr_predictions.csv"
    cfg["calibration"]["calibrated_predictions_csv"] = "outputs_large/calibration/hf_large_efficientnet_b0/calibrated_predictions.csv"
    cfg["calibration"]["calibration_metrics_csv"] = "tables_large/efficientnet_b0_calibration_metrics.csv"
    cfg["calibration"]["curves_dir"] = "figures_large/calibration/hf_large_efficientnet_b0"

    cfg["gradcam"]["output_dir"] = "figures_large/gradcam/hf_large_efficientnet_b0"
    cfg["gradcam"]["case_index_csv"] = "tables_large/efficientnet_b0_gradcam_case_index.csv"
    cfg["gradcam"]["localization_metrics_csv"] = "tables_large/efficientnet_b0_gradcam_localization_metrics.csv"
    cfg["gradcam"]["internal_predictions_csv"] = "predictions_large/efficientnet_b0_internal_test_predictions.csv"
    cfg["gradcam"]["external_predictions_csv"] = "predictions_large/efficientnet_b0_external_vindr_predictions.csv"

    dst.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()


