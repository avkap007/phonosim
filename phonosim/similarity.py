"""Similarity / distance over PanPhon features, including our Hindi cue weights."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from phonosim.cue_weights import load_weights, panphon_stock_weights
from phonosim.features import (
    ACTIVE_FEATURES,
    differing_features,
    get_features,
    normalize_ipa,
)

Mode = Literal["hamming", "panphon", "hindi"]
Denominator = Literal["all", "active"]


@dataclass(frozen=True)
class SimilarityResult:
    a: str
    b: str
    mode: str
    n_differ: int
    n_features: int
    distance: float
    similarity: float
    differing: list[str]
    weighted_distance: float | None = None

    def as_dict(self) -> dict:
        return {
            "a": self.a,
            "b": self.b,
            "mode": self.mode,
            "n_differ": self.n_differ,
            "n_features": self.n_features,
            "distance": self.distance,
            "similarity": self.similarity,
            "differing": list(self.differing),
            "weighted_distance": self.weighted_distance,
        }


def _feature_names(denominator: Denominator) -> list[str]:
    if denominator == "active":
        return list(ACTIVE_FEATURES)
    # PanPhon FeatureTable includes hitone/hireg → 24
    from phonosim.features import _feature_table

    return list(_feature_table().names)


def _weights_for_mode(mode: Mode, custom: Mapping[str, float] | None) -> dict[str, float] | None:
    if custom is not None:
        return dict(custom)
    if mode == "hamming":
        return None
    if mode == "panphon":
        return panphon_stock_weights()
    if mode == "hindi":
        return load_weights("hindi")
    raise ValueError(f"Unknown mode: {mode!r}")


def get_similarity(
    a: str,
    b: str,
    *,
    mode: Mode = "hamming",
    denominator: Denominator = "all",
    weights: Mapping[str, float] | None = None,
) -> SimilarityResult:
    """Compute feature distance / similarity between two IPA segments.

    Modes:
    - ``hamming`` — each differing feature counts as 1 (flat)
    - ``panphon`` — PanPhon's hand-assigned linguistic weights (baseline)
    - ``hindi`` — our Hindi L1 cue-weight profile (editable YAML)

    ``denominator``:
    - ``all`` — 24 PanPhon features (incl. tone)
    - ``active`` — 22 articulatory features (excl. hitone/hireg)
    """
    a_n = normalize_ipa(a)
    b_n = normalize_ipa(b)
    names = _feature_names(denominator)
    fa = get_features(a_n, include_tone=True)
    fb = get_features(b_n, include_tone=True)
    assert isinstance(fa, dict) and isinstance(fb, dict)

    differ = [name for name in names if fa[name] != fb[name]]
    n_features = len(names)
    n_differ = len(differ)

    wmap = _weights_for_mode(mode, weights)

    if wmap is None:
        distance = n_differ / n_features if n_features else 0.0
        weighted_distance = None
    else:
        weighted_distance = sum(float(wmap.get(name, 1.0)) for name in differ)
        # Normalize by max possible weighted cost over the feature set used.
        max_cost = sum(float(wmap.get(name, 1.0)) for name in names)
        distance = weighted_distance / max_cost if max_cost else 0.0

    similarity = 1.0 - distance
    return SimilarityResult(
        a=a_n,
        b=b_n,
        mode=mode if weights is None else "custom",
        n_differ=n_differ,
        n_features=n_features,
        distance=distance,
        similarity=similarity,
        differing=differ,
        weighted_distance=weighted_distance,
    )


def hamming_summary(a: str, b: str) -> str:
    """Human-readable flat difference, e.g. ``1/24 (sg)``."""
    r = get_similarity(a, b, mode="hamming", denominator="all")
    feats = ",".join(r.differing) if r.differing else "none"
    return f"{r.n_differ}/{r.n_features} ({feats})"
