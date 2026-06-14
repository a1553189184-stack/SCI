from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def project_root(config: dict[str, Any]) -> Path:
    root = config.get("project", {}).get("root")
    if root:
        return Path(root)
    return Path.cwd()


def resolve_path(config: dict[str, Any], value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return project_root(config) / path


def load_config(path: str | Path) -> dict[str, Any]:
    config = load_yaml(path)
    config["_config_path"] = str(Path(path).resolve())
    return config



