"""Automatic projection of segments onto an L1 consonant inventory.

Term 1 shipped a hand-built English -> Hindi table. This module computes the same kind
of mapping for ANY inventory: each segment goes to the nearest L1 phoneme by PanPhon
feature distance. Swap the inventory, get a different L1.

    inv = load_inventory("mandarin", "inventories.yaml")
    project("v", inv)                    # -> ['f']  (nearest Mandarin category)
    projected_distance("v", "w", inv)    # distance between the two projections

Nearest-neighbour rule
    1. Fewest differing PanPhon features (flat Hamming over 24 features).
    2. Ties broken by PanPhon's stock weighted distance.
    3. Any tie that is left is kept: ``project`` returns every tied candidate and
       ``projected_distance`` averages over them (an expected distance).

``method="contrastive"`` is the Yeo et al. (2026) variant: a feature only counts when it
takes both + and - somewhere in the L1 inventory.
"""
from __future__ import annotations

from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Literal, Sequence

import yaml

from phonosim.features import get_features, normalize_ipa
from phonosim.similarity import get_similarity

Method = Literal["hamming", "contrastive"]
_EPS = 1e-9


def load_inventory(l1: str, path: str | Path, variant: str = "primary") -> tuple[str, ...]:
    """Read one L1's consonant list from an inventories YAML file."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if l1 not in data:
        raise KeyError(f"No inventory for {l1!r}; available: {sorted(data)}")
    entry = data[l1]
    segs = entry.get(variant) or entry["primary"]
    out: list[str] = []
    for s in segs:
        try:
            n = normalize_ipa(s)
        except ValueError:
            # PanPhon cannot parse the diacritic (e.g. Korean tense t͈͡ɕ): fall back to
            # the base segment so the category is still represented.
            n = normalize_ipa("".join(ch for ch in s if ch != "\u0348"))
        if n not in out:  # collapse symbols PanPhon cannot tell apart
            out.append(n)
    return tuple(out)


def contrastive_features(inventory: Sequence[str]) -> list[str]:
    """Features that take both + and - within the inventory (Yeo et al. 2026)."""
    feats = [get_features(s) for s in inventory]
    return [n for n in feats[0] if {1, -1} <= {f[n] for f in feats}]


@lru_cache(maxsize=None)
def _project(seg: str, inventory: tuple[str, ...], method: str) -> tuple[str, ...]:
    seg = normalize_ipa(seg)
    if method == "hamming":
        key = lambda c: (get_similarity(seg, c).n_differ,
                         get_similarity(seg, c, mode="panphon").weighted_distance)
    elif method == "contrastive":
        active = set(contrastive_features(inventory))
        fs = get_features(seg)
        def key(c):
            fc = get_features(c)
            return (sum(1 for n in active if fs[n] != fc[n]),
                    get_similarity(seg, c).n_differ)
    else:
        raise ValueError(f"Unknown method {method!r}")
    scored = [(key(c), c) for c in inventory]
    best = min(k for k, _ in scored)
    return tuple(c for k, c in scored
                 if abs(k[0] - best[0]) < _EPS and abs(k[1] - best[1]) < _EPS)


def project(seg: str, inventory: Sequence[str], method: Method = "hamming") -> list[str]:
    """Nearest L1 phoneme(s) for a segment. More than one only on an exact tie."""
    return list(_project(seg, tuple(inventory), method))


def projected_distance(a: str, b: str, inventory: Sequence[str],
                       method: Method = "hamming") -> float:
    """Feature distance (features that differ, out of 24) between the L1 projections."""
    pa, pb = project(a, inventory, method), project(b, inventory, method)
    d = [get_similarity(x, y).n_differ for x, y in product(pa, pb)]
    return sum(d) / len(d)


def projection_table(segments: Sequence[str], inventory: Sequence[str],
                     method: Method = "hamming") -> dict[str, list[str]]:
    return {normalize_ipa(s): project(s, inventory, method) for s in segments}
