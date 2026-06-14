from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    src = ROOT / "configs" / "hf_large.yaml"
    dst = ROOT / "configs" / "hf_large_resnet50.yaml"
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))

    cfg["model"]["name"] = "resnet50"
    cfg["training"]["run_name"] = "hf_large_resnet50"
    cfg["training"]["output_dir"] = "outputs_large/training/hf_large_resnet50"
    cfg["training"]["checkpoint_dir"] = "models_large/hf_large_resnet50"
    cfg["training"]["log_csv"] = "logs_large/hf_large_resnet50_train_log.csv"

    cfg["evaluation"]["checkpoint_path"] = "models_large/hf_large_resnet50/best_resnet50.pt"
    cfg["evaluation"]["validation_predictions_csv"] = "predictions_large/resnet50_nih_validation_predictions.csv"
    cfg["evaluation"]["internal_predictions_csv"] = "predictions_large/resnet50_internal_test_predictions.csv"
    cfg["evaluation"]["internal_metrics_csv"] = "tables_large/resnet50_internal_metrics.csv"
    cfg["evaluation"]["thresholds_csv"] = "tables_large/resnet50_thresholds_from_val.csv"
    cfg["evaluation"]["bootstrap_ci_csv"] = "tables_large/resnet50_bootstrap_ci.csv"
    cfg["evaluation"]["external_predictions_csv"] = "predictions_large/resnet50_external_vindr_predictions.csv"
    cfg["evaluation"]["external_metrics_csv"] = "tables_large/resnet50_external_metrics.csv"
    cfg["evaluation"]["internal_external_comparison_csv"] = "tables_large/resnet50_internal_external_comparison.csv"
    cfg["evaluation"]["performance_drop_csv"] = "tables_large/resnet50_performance_drop.csv"

    cfg["calibration"]["output_dir"] = "outputs_large/calibration/hf_large_resnet50"
    cfg["calibration"]["raw_calibration_predictions_csv"] = "predictions_large/resnet50_nih_calibration_predictions.csv"
    cfg["calibration"]["raw_internal_predictions_csv"] = "predictions_large/resnet50_internal_test_predictions.csv"
    cfg["calibration"]["raw_external_predictions_csv"] = "predictions_large/resnet50_external_vindr_predictions.csv"
    cfg["calibration"]["calibrated_predictions_csv"] = "outputs_large/calibration/hf_large_resnet50/calibrated_predictions.csv"
    cfg["calibration"]["calibration_metrics_csv"] = "tables_large/resnet50_calibration_metrics.csv"
    cfg["calibration"]["curves_dir"] = "figures_large/calibration/hf_large_resnet50"

    cfg["gradcam"]["output_dir"] = "figures_large/gradcam/hf_large_resnet50"
    cfg["gradcam"]["case_index_csv"] = "tables_large/resnet50_gradcam_case_index.csv"
    cfg["gradcam"]["localization_metrics_csv"] = "tables_large/resnet50_gradcam_localization_metrics.csv"
    cfg["gradcam"]["internal_predictions_csv"] = "predictions_large/resnet50_internal_test_predictions.csv"
    cfg["gradcam"]["external_predictions_csv"] = "predictions_large/resnet50_external_vindr_predictions.csv"

    dst.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main()


