from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.prepare_nih import prepare_nih
from src.prepare_vindr import prepare_vindr
from src.splits import create_patient_splits
from src.utils import environment_report, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run steps 1-6: environment report, NIH prep, VinDr prep, NIH patient splits.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--skip-env", action="store_true")
    args = parser.parse_args()

    if not args.skip_env:
        report = environment_report()
        write_json(ROOT / "logs" / "environment_report.json", report)
        print("Environment report saved to logs/environment_report.json")
    prepare_nih(args.config)
    prepare_vindr(args.config)
    create_patient_splits(args.config)
    print("Steps 1-6 completed.")


if __name__ == "__main__":
    main()



