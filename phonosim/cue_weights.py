"""Cue-weight profiles: PanPhon stock vs our Hindi L1 profile."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Mapping

import yaml

# PanPhon feature_weights.csv order (22 articulatory; no tone).
# From panphon/data/feature_weights.csv — used only as comparison baseline.
_PANPHON_STOCK = {
    "syl": 1.0,
    "son": 1.0,
    "cons": 1.0,
    "cont": 0.5,
    "delrel": 0.25,
    "lat": 0.25,
    "nas": 0.25,
    "strid": 0.125,
    "voi": 0.125,
    "sg": 0.125,
    "cg": 0.125,
    "ant": 0.25,
    "cor": 0.25,
    "distr": 0.125,
    "lab": 0.25,
    "hi": 0.25,
    "lo": 0.25,
    "back": 0.25,
    "round": 0.25,
    "tense": 0.25,
    "long": 0.125,
    "velaric": 0.25,
    # Tone inert for consonants; keep low if included in denominator.
    "hitone": 0.125,
    "hireg": 0.125,
}


def panphon_stock_weights() -> dict[str, float]:
    return dict(_PANPHON_STOCK)


def _data_path(name: str) -> Path:
    # Prefer package data; fall back to repo data/ for editable installs.
    try:
        root = resources.files("phonosim") / "data"
        candidate = root / name
        if candidate.is_file():
            return Path(str(candidate))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        pass
    repo = Path(__file__).resolve().parent.parent / "data" / name
    if repo.is_file():
        return repo
    pkg = Path(__file__).resolve().parent / "data" / name
    return pkg


@lru_cache(maxsize=4)
def load_weights(profile: str = "hindi") -> dict[str, float]:
    """Load a named cue-weight profile from YAML.

    Unknown features default to 1.0 at use time; YAML may omit tone features.
    """
    if profile == "panphon":
        return panphon_stock_weights()

    path = _data_path(f"{profile}_cue_weights.yaml")
    if not path.is_file():
        raise FileNotFoundError(
            f"Cue-weight profile not found: {path}. "
            "Expected data/{profile}_cue_weights.yaml"
        )
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    weights = raw.get("weights", raw)
    return {str(k): float(v) for k, v in weights.items()}


def merge_weights(base: Mapping[str, float], overrides: Mapping[str, float]) -> dict[str, float]:
    out = dict(base)
    out.update({str(k): float(v) for k, v in overrides.items()})
    return out
