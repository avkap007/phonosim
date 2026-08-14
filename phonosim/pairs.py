"""Minimal-pair generation from orthographic wordlists via G2P."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from phonosim.features import normalize_ipa
from phonosim.g2p import to_ipa


@dataclass(frozen=True)
class MinimalPair:
    word_a: str
    word_b: str
    ipa_a: str
    ipa_b: str
    contrast: tuple[str, str]

    def as_dict(self) -> dict:
        return {
            "word_a": self.word_a,
            "word_b": self.word_b,
            "ipa_a": self.ipa_a,
            "ipa_b": self.ipa_b,
            "contrast": list(self.contrast),
        }


def _phones(ipa: str) -> list[str]:
    from phonosim.features import _feature_table

    return _feature_table().ipa_segs(ipa)


def differ_by_one_segment(ipa_a: str, ipa_b: str) -> tuple[str, str] | None:
    """If IPA strings differ by exactly one corresponding segment, return that pair."""
    a = _phones(ipa_a)
    b = _phones(ipa_b)
    if len(a) != len(b) or not a:
        return None
    diffs = [(x, y) for x, y in zip(a, b) if x != y]
    if len(diffs) != 1:
        return None
    return diffs[0]


def minimal_pair_generator(
    contrast: tuple[str, str],
    wordlist: list[str] | Path,
    *,
    lang: str = "eng-Latn",
    orthographic_pairs: list[tuple[str, str]] | None = None,
) -> list[MinimalPair]:
    """Find or validate minimal pairs for a target phoneme contrast.

    Preferred path for controlled experiments: pass ``orthographic_pairs`` of
    known pairs (e.g. vine/wine). The function transliterates and checks that
    IPA differs only in the target contrast (after normalization).

    If only ``wordlist`` is given, every pair of words is compared (O(n²)) —
    fine for small curated lists.
    """
    c0 = normalize_ipa(contrast[0])
    c1 = normalize_ipa(contrast[1])
    target = {c0, c1}

    if orthographic_pairs is None:
        if isinstance(wordlist, Path):
            words = [
                line.strip()
                for line in wordlist.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]
        else:
            words = list(wordlist)
        orthographic_pairs = [
            (words[i], words[j])
            for i in range(len(words))
            for j in range(i + 1, len(words))
        ]

    out: list[MinimalPair] = []
    for wa, wb in orthographic_pairs:
        ia = to_ipa(wa, lang=lang)
        ib = to_ipa(wb, lang=lang)
        diff = differ_by_one_segment(ia, ib)
        if diff is None:
            continue
        d0, d1 = normalize_ipa(diff[0], strict=False), normalize_ipa(diff[1], strict=False)
        if {d0, d1} == target:
            out.append(
                MinimalPair(
                    word_a=wa,
                    word_b=wb,
                    ipa_a=ia,
                    ipa_b=ib,
                    contrast=(c0, c1),
                )
            )
    return out
