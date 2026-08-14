"""IPA normalization and PanPhon feature lookup."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from panphon import FeatureTable

# Affricates commonly typed without a tie bar; PanPhon splits them otherwise.
_AFFRICATE_TIEBAR = {
    "tʃ": "t͡ʃ",
    "dʒ": "d͡ʒ",
    "ts": "t͡s",
    "dz": "d͡z",
    "tɕ": "t͡ɕ",
    "dʑ": "d͡ʑ",
    "ʈʂ": "ʈ͡ʂ",
    "ɖʐ": "ɖ͡ʐ",
    "pf": "p͡f",
    "bv": "b͡v",
}

# Tone features are inert for most consonant work; expose both counts.
ACTIVE_FEATURES = (
    "syl",
    "son",
    "cons",
    "cont",
    "delrel",
    "lat",
    "nas",
    "strid",
    "voi",
    "sg",
    "cg",
    "ant",
    "cor",
    "distr",
    "lab",
    "hi",
    "lo",
    "back",
    "round",
    "velaric",
    "tense",
    "long",
)


@lru_cache(maxsize=1)
def _feature_table() -> FeatureTable:
    return FeatureTable()


def normalize_ipa(symbol: str, *, strict: bool = True) -> str:
    """Normalize an IPA segment for single-segment feature lookup.

    Adds tie bars for common affricates so ``tʃ`` parses as one segment.
    Raises ``ValueError`` if ``strict`` and the result is not one known segment.
    """
    raw = symbol.strip().strip("/").strip("[]")
    if not raw:
        raise ValueError("Empty IPA symbol")

    candidate = _AFFRICATE_TIEBAR.get(raw, raw)
    ft = _feature_table()
    segs = ft.ipa_segs(candidate)

    if len(segs) == 1:
        return segs[0]

    # Try tie-barring adjacent pairs if PanPhon split an untied affricate.
    if len(segs) == 2:
        joined = segs[0] + "͡" + segs[1]
        if len(ft.ipa_segs(joined)) == 1:
            return joined

    if strict:
        raise ValueError(
            f"Expected one IPA segment, got {len(segs)} from {symbol!r}: {segs}. "
            "Use a tie bar for affricates (e.g. t͡ʃ)."
        )
    return candidate


def get_features(
    ipa: str,
    *,
    as_dict: bool = True,
    include_tone: bool = True,
) -> dict[str, int] | list[int]:
    """Return PanPhon articulatory features for a single IPA segment.

    Feature values are ``+1`` / ``-1`` / ``0`` (unspecified), matching PanPhon.
    """
    seg = normalize_ipa(ipa)
    ft = _feature_table()
    segments = ft.word_fts(seg)
    if not segments:
        raise ValueError(f"Unknown IPA segment after normalization: {ipa!r} → {seg!r}")

    segment = segments[0]
    names = list(ft.names) if include_tone else list(ACTIVE_FEATURES)
    feats = {name: int(segment[name]) for name in names}
    if as_dict:
        return feats
    return [feats[name] for name in names]


def differing_features(a: str, b: str, *, include_tone: bool = True) -> list[str]:
    """Feature names that differ between two segments."""
    fa = get_features(a, include_tone=include_tone)
    fb = get_features(b, include_tone=include_tone)
    assert isinstance(fa, dict) and isinstance(fb, dict)
    return [k for k in fa if fa[k] != fb[k]]


def feature_vector(ipa: str, *, include_tone: bool = True) -> list[int]:
    result = get_features(ipa, as_dict=False, include_tone=include_tone)
    assert isinstance(result, list)
    return result


def panphon_info() -> dict[str, Any]:
    ft = _feature_table()
    return {
        "n_features_all": len(ft.names),
        "n_features_active": len(ACTIVE_FEATURES),
        "feature_names": list(ft.names),
        "active_features": list(ACTIVE_FEATURES),
    }
