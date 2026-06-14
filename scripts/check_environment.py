from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils import environment_report, save_pip_freeze, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Python, PyTorch, CUDA, and GPU environment.")
    parser.add_argument("--save-freeze", action="store_true", help="Save pip freeze to logs/pip_freeze.txt.")
    args = parser.parse_args()

    logs = ROOT / "logs"
    report = environment_report()
    for key, value in report.items():
        print(f"{key}: {value}")
    write_json(logs / "environment_report.json", report)
    if args.save_freeze:
        save_pip_freeze(logs / "pip_freeze.txt")
        print(f"Saved {logs / 'pip_freeze.txt'}")


if __name__ == "__main__":
    main()



