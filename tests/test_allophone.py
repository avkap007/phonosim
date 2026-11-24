"""Tests for the pronunciation-level (allophone) L1 layer (Study 3)."""
from pathlib import Path

import pytest

from phonosim.l1.allophone import (allophone_distance, clean, load_allophone_inventory,
                                   phonemes_of, project_allophone, skipped)
from phonosim.l1.project import load_inventory, project

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "allophone" / "data" / "phoible_selected.csv"
INV2 = ROOT / "crossl1" / "data" / "inventories.yaml"
L1S = ["arabic", "hindi", "korean", "mandarin", "spanish", "vietnamese"]


def inv(l1):
    s2 = load_inventory(l1, INV2)
    return load_allophone_inventory(l1, P, add_glides=[g for g in ("j", "w") if g in s2])


def test_hindi_v_and_w_land_on_ʋ():
    """The Study 2 failure: PHOIBLE lists Hindi /ʋ/ as [ʋ v w]."""
    h = inv("hindi")
    assert project_allophone("v", h) == ["ʋ"]
    assert project_allophone("w", h) == ["ʋ"]
    assert allophone_distance("v", "w", h) == 0


def test_phoneme_only_baseline_does_not_merge_v_w():
    h = inv("hindi")
    assert project("v", phonemes_of(h)) == ["f"]


def test_voicing_diacritics_parse_as_counterparts():
    assert clean("s̬") == "z"
    assert clean("θ̬") == "ð"
    assert clean("b̥") == "p"


def test_length_and_unreleased_collapse():
    assert clean("pː") == "p"
    assert clean("p̚") == "p"


def test_glide_rule_only_adds_missing_glides():
    k = inv("korean")
    assert ("w", "w") in k and ("j", "j") in k
    assert project_allophone("w", k) == ["w"]
    # Hindi has no /w/ in Study 2's inventory, so none is added
    assert ("w", "w") not in inv("hindi")


@pytest.mark.parametrize("l1", L1S)
def test_every_l1_loads_and_projects(l1):
    i = inv(l1)
    assert len(i) > 15
    for seg in ["p", "t", "k", "s", "m", "n", "l"]:
        assert project_allophone(seg, i)


def test_known_unparseable_symbols_are_reported():
    assert skipped("arabic", P) == ["d̪ʒ", "xʀ̥"]
    assert skipped("hindi", P) == []
