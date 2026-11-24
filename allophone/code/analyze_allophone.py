"""Study 3: does a pronunciation-level (allophone) L1 layer predict each L1 group's own
substitutions? Spec: ../ANALYSIS_PLAN.md (frozen before this script was run on real data).

Usage (from the repo root):
    PYTHONPATH=. python allophone/code/analyze_allophone.py phones.csv OUT_DIR --data scripted
    PYTHONPATH=. python allophone/code/analyze_allophone.py phones_suitcase.csv OUT_DIR --data suitcase
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import permutations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
sys.path.insert(0, str(ROOT / "crossl1" / "code"))
from analyze import (ARPA_TO_IPA, CONS, build_table, fit, load_v2, nested,  # noqa: E402
                     shared_utterances, term, vw_targets)
from analyze_crossl1 import L1S, diag_summary, matrix, p1, permutation_test  # noqa: E402

from phonosim.l1.allophone import (allophone_distance, load_allophone_inventory,  # noqa: E402
                                   phonemes_of, project_allophone, skipped)
from phonosim.l1.project import load_inventory, project, projected_distance  # noqa: E402
from phonosim.similarity import get_similarity  # noqa: E402

PHOIBLE = ROOT / "allophone" / "data" / "phoible_selected.csv"
INV2 = ROOT / "crossl1" / "data" / "inventories.yaml"
V2 = ROOT / "icphs2027" / "data" / "hindi_inventory_v2.yaml"


def inventories() -> dict:
    """Allophone inventories, with Study 2's glide rule applied (adds j/w when the
    frozen Study 2 inventory has them and the PHOIBLE source does not)."""
    out = {}
    for l in L1S:
        s2 = load_inventory(l.lower(), INV2)
        out[l] = load_allophone_inventory(l.lower(), PHOIBLE,
                                          add_glides=[g for g in ("j", "w") if g in s2])
    return out


def predictors(layer: str, inv: dict) -> pd.DataFrame:
    """comp_<L1> = English distance minus distance between the L1 categories.
    layer: 'allophone' (Study 3), 'phoneme' (same PHOIBLE source, phonemes only),
    'study2' (the frozen Study 2 layer)."""
    v2 = load_v2(V2)
    rows = []
    for x, y in permutations(CONS, 2):
        a, b = ARPA_TO_IPA[x], ARPA_TO_IPA[y]
        r = {"X": x, "Y": y, "pair": f"{a}→{b}", "dist_english": get_similarity(a, b).n_differ}
        for l in L1S:
            if layer == "allophone":
                dp = allophone_distance(a, b, inv[l])
            elif layer == "phoneme":
                dp = projected_distance(a, b, phonemes_of(inv[l]))
            else:
                dp = projected_distance(a, b, load_inventory(l.lower(), INV2))
            r[f"comp_{l}"] = r["dist_english"] - dp
        r["comp_HindiHand"] = r["dist_english"] - get_similarity(v2[a], v2[b]).n_differ
        rows.append(r)
    return pd.DataFrame(rows)


def hindi_tests(d: pd.DataFrame) -> dict:
    h = d[d.l1 == "Hindi"]
    d = d.assign(is_hindi=(d.l1 == "Hindi").astype(int))
    out = {}
    for name, col in [("layer", "comp_Hindi"), ("hand", "comp_HindiHand")]:
        out[f"H1_{name}"] = nested(h, "dist_english", col)
        out[f"H2_{name}"] = term(fit(f"count ~ (dist_english + {col}) * is_hindi", d), f"{col}:is_hindi")
    return out


def run(df: pd.DataFrame, preds: pd.DataFrame) -> dict:
    d = build_table(df, preds, use_dev=True)
    m = matrix(d)
    return {"d": d, "m": m, "P1": p1(d), "P2": permutation_test(d), "P3": diag_summary(m),
            "hindi": hindi_tests(d)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phones_csv"); ap.add_argument("out_dir")
    ap.add_argument("--data", choices=["scripted", "suitcase"], required=True)
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(args.phones_csv, keep_default_na=False)
    if args.data == "scripted":
        df = df[df["utt"].isin(shared_utterances(df, 4))]

    inv = inventories()
    proj = pd.DataFrame([{"english": ARPA_TO_IPA[c],
                          **{f"{l}_allophone": "/".join(project_allophone(ARPA_TO_IPA[c], inv[l])) for l in L1S},
                          **{f"{l}_study2": "/".join(project(ARPA_TO_IPA[c], load_inventory(l.lower(), INV2))) for l in L1S},
                          "Hindi_hand_v2": load_v2(V2)[ARPA_TO_IPA[c]]} for c in CONS])
    proj.to_csv(out / "projection_table.csv", index=False)

    layers = {k: predictors(k, inv) for k in ("allophone", "phoneme", "study2")}
    for k, p in layers.items():
        p.to_csv(out / f"pair_predictors_{k}.csv", index=False)

    res = {"data": args.data,
           "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in
                      ["allophone/data/phoible_selected.csv", "phonosim/l1/allophone.py",
                       "allophone/code/analyze_allophone.py", "crossl1/data/inventories.yaml"]},
           "skipped_symbols": {l: skipped(l.lower(), PHOIBLE) for l in L1S},
           "n_speakers": int(df.speaker.nunique()),
           "speakers_by_l1": df.groupby("l1").speaker.nunique().to_dict()}

    # --- Primary: allophone layer
    a = run(df, layers["allophone"])
    a["m"].to_csv(out / "matrix_6x6_allophone.csv", index=False)
    res["subs_by_l1"] = {k: int(v) for k, v in a["d"].groupby("l1")["count"].sum().items()}
    res["allophone"] = {k: a[k] for k in ("P1", "P2", "P3", "hindi")}

    # --- Level comparison: same PHOIBLE source, phonemes only; and the frozen Study 2 layer
    for k in ("phoneme", "study2"):
        r = run(df, layers[k])
        r["m"].to_csv(out / f"matrix_6x6_{k}.csv", index=False)
        res[k] = {kk: r[kk] for kk in ("P1", "P2", "P3", "hindi")}

    # --- Robustness (all reported, whatever they show)
    d = a["d"]
    vw = ~(((d.X == "V") & (d.Y == "W")) | ((d.X == "W") & (d.Y == "V")))
    rob = {"P1_drop_vw": p1(d[vw]),
           "P1_no_deviations": p1(build_table(df, layers["allophone"], use_dev=False))}
    for l in L1S:
        if (d.l1 == l).any():
            rob[f"P1_leave_out_{l}"] = p1(d[d.l1 != l])
    res["robustness"] = rob

    # --- Descriptive: v/w target-level rates by L1 and speaker (as in Study 1)
    try:
        vw_spk, vw_l1 = vw_targets(df)
        vw_l1.to_csv(out / "vw_by_l1.csv", index=False)
        vw_spk.to_csv(out / "vw_by_speaker.csv", index=False)
    except Exception as e:  # report, don't hide
        res["vw_targets_error"] = repr(e)

    agg = d.groupby(["l1", "pair"])[["count", "tokens"]].sum().reset_index()
    agg["rate"] = agg["count"] / agg["tokens"]
    agg.to_csv(out / "pair_rates_by_l1.csv", index=False)
    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, default=float)

    f = lambda t: f"IRR {t['irr']:.2f} [{t['ci_low']:.2f}, {t['ci_high']:.2f}] p={t['p']:.3g}"
    print(f"== {args.data}: {res['n_speakers']} speakers {res['speakers_by_l1']}")
    for k in ("allophone", "phoneme", "study2"):
        r = res[k]
        print(f"[{k}] P1 matched {f(r['P1']['comp_matched'])} | others {f(r['P1']['comp_others'])} | "
              f"P2 rank {r['P2']['rank_true']}/{r['P2']['n_perms']} (p={r['P2']['p_all']:.3f}) | "
              f"P3 {r['P3']['n_diagonal_best']}/6 | "
              f"Hindi H1 {f(r['hindi']['H1_layer']['comp_Hindi'])} H2 {f(r['hindi']['H2_layer'])}")
    print(f"[hand v2] Hindi H1 {f(res['allophone']['hindi']['H1_hand']['comp_HindiHand'])} "
          f"H2 {f(res['allophone']['hindi']['H2_hand'])}")
    for k, v in rob.items():
        print(k, f(v["comp_matched"]))


if __name__ == "__main__":
    main()
