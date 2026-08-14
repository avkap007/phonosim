"""Grapheme-to-IPA via Epitran (Hindi etc.) with English fallback when flite is absent."""

from __future__ import annotations

from functools import lru_cache

# ARPABET (CMU) → IPA used by g2p_en fallback for English.
_ARPA_TO_IPA = {
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ʌ",
    "AO": "ɔ",
    "AW": "aʊ",
    "AY": "aɪ",
    "B": "b",
    "CH": "t͡ʃ",
    "D": "d",
    "DH": "ð",
    "EH": "ɛ",
    "ER": "ɝ",
    "EY": "eɪ",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "IH": "ɪ",
    "IY": "i",
    "JH": "d͡ʒ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "OW": "oʊ",
    "OY": "ɔɪ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "UH": "ʊ",
    "UW": "u",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
}


@lru_cache(maxsize=8)
def _epitran(lang: str):
    import epitran

    return epitran.Epitran(lang)


@lru_cache(maxsize=1)
def _g2p_en():
    from g2p_en import G2p

    return G2p()


def _arpa_phone_to_ipa(phone: str) -> str:
    base = "".join(c for c in phone if c.isalpha())
    return _ARPA_TO_IPA.get(base, "")


def _english_via_g2p(text: str) -> str:
    tokens = _g2p_en()(text)
    ipa_parts: list[str] = []
    for tok in tokens:
        if not tok or tok.isspace():
            continue
        # g2p_en leaves punctuation as-is
        if tok in {".", ",", "!", "?", ";", ":", "'", '"', "-", " "}:
            continue
        ipa = _arpa_phone_to_ipa(tok)
        if ipa:
            ipa_parts.append(ipa)
    return "".join(ipa_parts)


def to_ipa(text: str, lang: str = "eng-Latn") -> str:
    """Convert orthography to IPA.

    - ``hin-Deva`` and other Epitran rule-based codes use Epitran directly.
    - ``eng-Latn`` prefers Epitran (requires CMU flite ``lex_lookup``). If flite
      is not installed, falls back to ``g2p_en`` (ARPABET → IPA), which is the
      usual English companion to PanPhon when flite is unavailable.
    """
    text = text.strip()
    if not text:
        return ""

    if lang == "eng-Latn":
        try:
            epi = _epitran(lang)
            # Probe once: Flite without lex_lookup raises KeyError on empty ARPA.
            return epi.transliterate(text)
        except (KeyError, OSError, RuntimeError, ValueError):
            return _english_via_g2p(text)

    return _epitran(lang).transliterate(text)
