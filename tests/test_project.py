"""Tests for the automatic L1 projection (phonosim.l1.project).

The fixture is the projection table written by the frozen cross-L1 run on Nov 17, 2026
(commit 5f99ff1). If PanPhon, the inventories or the nearest-neighbour rule change, these
tests fail, so a silent change to Study 2's predictors can't slip through.
"""
import csv
from pathlib import Path

import pytest

from phonosim.features import normalize_ipa
from phonosim.l1.project import (contrastive_features, load_inventory, project,
                                 projected_distance)

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "crossl1" / "data" / "inventories.yaml"
FIXTURE = Path(__file__).parent / "fixtures" / "projection_table_2026-11-17.csv"
L1S = ["Arabic", "Hindi", "Korean", "Mandarin", "Spanish", "Vietnamese"]


def _fixture():
    with FIXTURE.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.mark.parametrize("l1", L1S)
def test_projection_matches_frozen_run(l1):
    inv = load_inventory(l1.lower(), INV)
    for row in _fixture():
        got = sorted(project(row["english"], inv))
        want = sorted(row[l1].split("/"))  # ties are written a/b in the fixture
        assert got == want, (
            f"{l1}: /{row['english']}/ now projects to {got}, frozen run had {want}")


def test_hindi_automatic_vs_hand_disagreements():
    """Study 2, Result 1: 7 of 24 English consonants differ from the hand v2 table."""
    rows = _fixture()
    assert len(rows) == 24
    diff = {r["english"] for r in rows if r["Hindi"] != r["Hindi_hand_v2"]}
    assert diff == {"t", "d", "v", "w", "θ", "ʒ", "ɹ"}


def test_automatic_hindi_does_not_merge_v_w():
    inv = load_inventory("hindi", INV)
    assert project("v", inv) == ["f"]
    assert project("w", inv) == ["j"]
    assert projected_distance("v", "w", inv) > 0


@pytest.mark.parametrize("a,b", [("v", "f"), ("w", "ɹ"), ("ʒ", "ʃ"), ("θ", "t"), ("ð", "d")])
def test_automatic_hindi_merges(a, b):
    """Contrasts the automatic map merges but the hand map keeps apart (AXB design)."""
    inv = load_inventory("hindi", INV)
    assert projected_distance(a, b, inv) == 0


def test_segment_already_in_inventory_maps_to_itself():
    for l1 in L1S:
        inv = load_inventory(l1.lower(), INV)
        for seg in inv:
            assert seg in project(seg, inv), f"{l1}: {seg} did not map to itself"


def test_alt_varieties_load_and_differ():
    for l1 in ["arabic", "spanish", "vietnamese"]:
        assert set(load_inventory(l1, INV, "alt")) != set(load_inventory(l1, INV))


def test_unknown_l1_raises():
    with pytest.raises(KeyError):
        load_inventory("klingon", INV)


def test_contrastive_method_runs_and_uses_fewer_features():
    inv = load_inventory("mandarin", INV)
    active = contrastive_features(inv)
    assert 0 < len(active) < 24
    assert project("v", inv, method="contrastive")


def test_tie_is_averaged():
    # Two equidistant candidates: projected_distance averages over both.
    inv = ("p", "b")
    assert project("p", inv) == ["p"]
    d = projected_distance("p", "b", inv)
    assert d == 1


def test_inventory_symbols_are_panphon_parseable():
    for l1 in L1S:
        for seg in load_inventory(l1.lower(), INV):
            assert normalize_ipa(seg) == seg
