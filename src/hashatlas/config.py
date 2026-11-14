"""Read project settings, resolve data paths and serialise artifact values."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "config.yaml"
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
ARTIFACTS = ROOT / "artifacts"
MODELS = ROOT / "models"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
WEB_DATA = ROOT / "web" / "public" / "data"


@lru_cache(maxsize=1)
def cfg() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_dirs() -> None:
    for p in (RAW, INTERIM, PROCESSED, ARTIFACTS, MODELS, FIGURES, WEB_DATA):
        p.mkdir(parents=True, exist_ok=True)


def _clean(o):
    """Recursively convert numpy / pandas scalars and NaN to JSON-safe values."""
    import numpy as np

    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return [_clean(v) for v in o.tolist()]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        return None if (math.isnan(f) or math.isinf(f)) else f
    if isinstance(o, Path):
        return str(o.relative_to(ROOT)) if o.is_relative_to(ROOT) else str(o)
    return o


def write_json(path: Path, obj, indent: int | None = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(_clean(obj), fh, indent=indent, ensure_ascii=False, separators=None if indent else (",", ":"))
        fh.write("\n")


def read_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
