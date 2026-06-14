from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.datasets import build_dataloaders
from src.train import train
from src.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a 100-image DenseNet121 smoke test on NIH splits and build VinDr DataLoader.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--check-loaders-only", action="store_true", help="Create DataLoaders, including VinDr, but do not train.")
    args = parser.parse_args()
    if args.check_loaders_only:
        config = load_config(args.config)
        loaders = build_dataloaders(config, smoke=True)
        for name, loader in loaders.items():
            print(f"{name}: {len(loader.dataset)} images, batch_size={loader.batch_size}")
        return
    summary = train(args.config, smoke=True)
    print(summary)


if __name__ == "__main__":
    main()



