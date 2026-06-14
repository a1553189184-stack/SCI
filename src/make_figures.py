from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_10_upgrade_assets as assets  # noqa: E402


FIGURE_OUTPUTS = [
    "figure1_study_workflow_three_models.png",
    "figure2_densenet121_internal_external_ci.png",
    "figure3_prevalence_auprc_baseline_lift.png",
    "figure4_calibration_curves_upgraded.png",
    "figure5_gradcam_failure_modes_upgraded.png",
    "figure6_internal_minus_external_auroc.png",
    "supplementary_figure_roc_pr_curves_densenet121.png",
    "supplementary_figure_probability_distributions_densenet121.png",
]


def build_figures(rebuild_tables_too: bool = False) -> list[Path]:
    """Create manuscript-ready figures from real table and prediction outputs."""

    assets.main()
    figs_dir = ROOT / "figures_large"
    paths = [figs_dir / name for name in FIGURE_OUTPUTS if (figs_dir / name).exists()]
    if not rebuild_tables_too:
        print("Note: canonical asset builder refreshes tables as well as figures.")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manuscript-ready figure files.")
    parser.add_argument(
        "--rebuild-tables-too",
        action="store_true",
        help="Document that tables are also refreshed by the canonical asset builder.",
    )
    args = parser.parse_args()
    paths = build_figures(rebuild_tables_too=args.rebuild_tables_too)
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
