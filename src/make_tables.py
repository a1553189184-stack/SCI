from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_10_upgrade_assets as assets  # noqa: E402


TABLE_OUTPUTS = [
    "table1_dataset_characteristics_upgraded.csv",
    "table2_label_harmonization_analysis_role_upgraded.csv",
    "table3_densenet121_labelwise_performance.csv",
    "table4_architecture_comparison_macro_upgraded.csv",
    "table5_calibration_metrics_upgraded.csv",
    "table6_subgroup_sensitivity_analysis.csv",
    "supplementary_table1_resnet50_labelwise_performance.csv",
    "supplementary_table2_efficientnet_b0_labelwise_performance.csv",
    "supplementary_table3_per_label_thresholds.csv",
    "supplementary_table4_auprc_baseline_lift.csv",
    "supplementary_table5_per_label_calibration_metrics.csv",
    "supplementary_table6_paired_bootstrap_model_comparison.csv",
    "supplementary_table7_hyperparameters.csv",
    "supplementary_table8_reproducibility_environment_commands.csv",
    "supplementary_table9_medmnist_pipeline_verification.csv",
    "external_evaluable_label_set.csv",
]


def build_tables(rebuild_figures_too: bool = False) -> list[Path]:
    """Create manuscript-ready table CSV files from real prediction/metric CSVs.

    The canonical builder also refreshes figures and registry files. This wrapper
    exposes the table-generation step from src/ so reviewers have a stable entry
    point without having to know the manuscript packaging script name.
    """

    assets.main()
    tables_dir = ROOT / "tables_large"
    outputs_dir = ROOT / "outputs_large" / "figure_source_data_10_upgrade"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name in TABLE_OUTPUTS:
        path = tables_dir / name
        if path.exists():
            shutil.copy2(path, outputs_dir / name)
            written.append(path)
    if not rebuild_figures_too:
        print("Note: canonical asset builder refreshes figures as well as tables.")
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manuscript-ready table CSV files.")
    parser.add_argument(
        "--rebuild-figures-too",
        action="store_true",
        help="Document that figures are also refreshed by the canonical asset builder.",
    )
    args = parser.parse_args()
    paths = build_tables(rebuild_figures_too=args.rebuild_figures_too)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
