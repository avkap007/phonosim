"""Hindi L1 inventory mapping for English segments."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml

from phonosim.features import normalize_ipa

AssimilationType = Literal["merged", "exists_different_cues", "no_equivalent", "exists_similar"]


@dataclass(frozen=True)
class L1Mapping:
    english: str
    closest_hindi: str | list[str]
    assimilation_type: AssimilationType
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "english": self.english,
            "closest_hindi": self.closest_hindi,
            "assimilation_type": self.assimilation_type,
            "notes": self.notes,
        }


def _inventory_path() -> Path:
    try:
        root = resources.files("phonosim") / "data"
        candidate = root / "hindi_inventory.yaml"
        if candidate.is_file():
            return Path(str(candidate))
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        pass
    repo = Path(__file__).resolve().parents[2] / "data" / "hindi_inventory.yaml"
    if repo.is_file():
        return repo
    return Path(__file__).resolve().parents[1] / "data" / "hindi_inventory.yaml"


@lru_cache(maxsize=1)
def _load_inventory() -> dict:
    path = _inventory_path()
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def map_to_l1(ipa: str, l1: str = "hindi") -> L1Mapping:
    """Map an English IPA segment onto the Hindi L1 category table."""
    if l1 != "hindi":
        raise NotImplementedError(
            f"L1 profile {l1!r} is not shipped yet; only 'hindi' is available in v0.1."
        )
    seg = normalize_ipa(ipa)
    data = _load_inventory()
    mappings = data.get("english_to_hindi", {})
    entry = mappings.get(seg) or mappings.get(ipa.strip().strip("/"))
    if entry is None:
        return L1Mapping(
            english=seg,
            closest_hindi="?",
            assimilation_type="no_equivalent",
            notes="Not in curated Hindi mapping table; add to data/hindi_inventory.yaml",
        )
    return L1Mapping(
        english=seg,
        closest_hindi=entry.get("closest_hindi", "?"),
        assimilation_type=entry.get("assimilation_type", "no_equivalent"),
        notes=entry.get("notes", ""),
    )


def contrast_assimilation(a: str, b: str, l1: str = "hindi") -> dict:
    """How an English contrast relates to Hindi categories.

    ``merged`` means both English phones are explicitly typed as merging into the
    *same singleton* L1 category (e.g. v and w → ʋ). A list of approximate
    targets (e.g. ɹ → [r, ɽ]) must not count as a merger with ɽ.
    """
    ma = map_to_l1(a, l1=l1)
    mb = map_to_l1(b, l1=l1)

    def _singleton(x: str | list[str]) -> str | None:
        if isinstance(x, list):
            return x[0] if len(x) == 1 else None
        return None if x == "?" else x

    sa, sb = _singleton(ma.closest_hindi), _singleton(mb.closest_hindi)
    both_marked_merged = (
        ma.assimilation_type == "merged" and mb.assimilation_type == "merged"
    )
    same_category = bool(sa and sb and sa == sb and both_marked_merged)

    if same_category:
        relation = "merged"
    elif (
        ma.assimilation_type == "exists_different_cues"
        or mb.assimilation_type == "exists_different_cues"
    ):
        relation = "exists_different_cues"
    elif ma.assimilation_type == "no_equivalent" or mb.assimilation_type == "no_equivalent":
        relation = "no_equivalent"
    else:
        relation = "two_category"

    return {
        "a": ma.as_dict(),
        "b": mb.as_dict(),
        "relation": relation,
        "same_l1_category": same_category,
    }
