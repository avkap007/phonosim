"""Pronunciation-level (allophone) L1 projection.

Study 2 projected English consonants onto an L1's *phonemes* as written, and failed to
recover Hindi v/w: Hindi /ʋ/ as a symbol is far from English [v] and [w]. Listeners
compare new sounds with how native sounds are *pronounced*. This module projects onto
an L1's pronounced variants (allophones, from PHOIBLE) and maps each variant back to
its phoneme, so English [v] and [w] both land on Hindi /ʋ/ when PHOIBLE lists /ʋ/ as
[ʋ v w].

    inv = load_allophone_inventory("hindi", "allophone/data/phoible_selected.csv")
    project_allophone("v", inv)                      # -> ['ʋ']
    allophone_distance("v", "w", inv)                # -> 0.0 (same category)

Rule (same as phonosim.l1.project, applied to variants instead of phonemes):
    1. Fewest differing PanPhon features between the English segment and a variant.
    2. Ties broken by PanPhon's stock weighted distance.
    3. Remaining ties are kept; the categories are the parent phonemes of all tied
       variants, and distances average over them.
"""
from __future__ import annotations

import csv
import unicodedata
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Sequence

from phonosim.features import normalize_ipa
from phonosim.similarity import get_similarity

_EPS = 1e-9
# PHOIBLE spelling -> PanPhon-parseable spelling with the same category
_SUBS = [("ʱ", "̤"), ("g", "ɡ"), ("ʦ", "t͡s"), ("ʧ", "t͡ʃ"), ("ʤ", "d͡ʒ")]
_DROP = {"̠", "ː", "̚", "͈", "̙"}  # retraction, length, unreleased, fortis, RTR
_AFFRICATES = ["tʃ", "dʒ", "ts", "dz", "tɕ", "dʑ", "ʈʂ", "ɖʐ", "cç", "ɟʝ"]
# PanPhon ignores the voicing diacritics, so [s̬] would read as [s]. Rewrite them as the
# voiced or voiceless counterpart where one exists.
_VOICED = {"p": "b", "t": "d", "k": "ɡ", "s": "z", "f": "v", "θ": "ð", "ʃ": "ʒ", "x": "ɣ",
           "ç": "ʝ", "ɕ": "ʑ", "ʂ": "ʐ", "c": "ɟ", "q": "ɢ", "χ": "ʁ"}
_VOICELESS = {v: k for k, v in _VOICED.items()}

Pair = tuple[str, str]  # (variant, parent phoneme)


def clean(seg: str) -> str:
    """PHOIBLE symbol -> PanPhon-parseable symbol. Length, unreleased and retraction
    marks are dropped, so geminates and unreleased stops collapse onto the plain segment."""
    s = unicodedata.normalize("NFD", seg.split("|")[-1])
    for a, b in _SUBS:
        s = s.replace(a, b)
    s = "".join(ch for ch in s if ch not in _DROP).replace("͡", "")
    if "̤" in s and len(s.replace("̤", "")) == 2:  # d̤ʒ̤ -> d͡ʒ̤
        s = s.replace("̤", "") + "̤"
    for mark, table in (("̬", _VOICED), ("̥", _VOICELESS), ("̊", _VOICELESS)):
        if mark in s:
            base = s.replace(mark, "")
            if base[:1] in table:
                s = table[base[0]] + base[1:]
    for aff in _AFFRICATES:
        s = s.replace(aff, aff[0] + "͡" + aff[1:])
    return unicodedata.normalize("NFC", s)


def _parse(seg: str) -> str | None:
    try:
        return normalize_ipa(clean(seg))
    except (ValueError, KeyError, IndexError):
        return None


def load_allophone_inventory(l1: str, path: str | Path, include_marginal: bool = False,
                             add_glides: Sequence[str] = ()) -> tuple[Pair, ...]:
    """(variant, parent) pairs for one L1 from a phoible_selected.csv file.
    Variants or phonemes PanPhon cannot parse are skipped (see `skipped`).

    add_glides: glides (j, w) to add as their own categories when the source lacks them.
    Study 2's inclusion rule 2 counts non-syllabic glides even where a description treats
    them as parts of vowels; Study 3 applies the same rule (only Korean is affected)."""
    pairs: list[Pair] = []
    with open(path, encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["l1"] == l1]
    if not rows:
        raise KeyError(f"No inventory for {l1!r} in {path}")
    for r in rows:
        if r["marginal"] == "TRUE" and not include_marginal:
            continue
        parent = _parse(r["phoneme"])
        if parent is None:
            continue
        variants = r["allophones"].split() if r["allophones"] not in ("", "NA") else []
        for v in [r["phoneme"], *variants]:
            pv = _parse(v)
            if pv is not None and (pv, parent) not in pairs:
                pairs.append((pv, parent))
    present = {v for v, _ in pairs}
    for g in add_glides:
        g = normalize_ipa(g)
        if g not in present:
            pairs.append((g, g))
    return tuple(pairs)


def skipped(l1: str, path: str | Path) -> list[str]:
    """Symbols in the inventory that PanPhon cannot parse (reported, never silently lost)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["l1"] != l1:
                continue
            variants = r["allophones"].split() if r["allophones"] not in ("", "NA") else []
            out += [v for v in [r["phoneme"], *variants] if _parse(v) is None]
    return sorted(set(out))


def phonemes_of(inv: Sequence[Pair]) -> tuple[str, ...]:
    """The phoneme-only inventory (parents), for the same-source baseline."""
    out: list[str] = []
    for _, p in inv:
        if p not in out:
            out.append(p)
    return tuple(out)


@lru_cache(maxsize=None)
def _project(seg: str, inv: tuple[Pair, ...]) -> tuple[str, ...]:
    seg = normalize_ipa(seg)
    key = lambda v: (get_similarity(seg, v).n_differ,
                     get_similarity(seg, v, mode="panphon").weighted_distance)
    scored = [(key(v), parent) for v, parent in inv]
    best = min(k for k, _ in scored)
    parents = {p for k, p in scored
               if abs(k[0] - best[0]) < _EPS and abs(k[1] - best[1]) < _EPS}
    return tuple(sorted(parents))


def project_allophone(seg: str, inv: Sequence[Pair]) -> list[str]:
    """L1 phoneme(s) whose pronounced variant is nearest to the segment."""
    return list(_project(seg, tuple(inv)))


def allophone_distance(a: str, b: str, inv: Sequence[Pair]) -> float:
    """Feature distance (features that differ, out of 24) between the L1 categories that
    a and b project to. 0 when both land on the same category."""
    pa, pb = project_allophone(a, inv), project_allophone(b, inv)
    d = [get_similarity(x, y).n_differ for x, y in product(pa, pb)]
    return sum(d) / len(d)
