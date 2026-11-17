"""Cross-L1 test: does an automatically projected L1 distance predict each L1 group's
own substitutions in L2-ARCTIC better than the other groups' projections do?
Spec: ../ANALYSIS_PLAN.md (frozen before this script was run on the real corpus).

Usage (from the repo root):
    PYTHONPATH=. python crossl1/code/analyze_crossl1.py icphs2027/phones.csv crossl1/results
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
from analyze import (ARPA_TO_IPA, CONS, build_table, fit, load_v2, nested,  # noqa: E402
                     shared_utterances, term)

from phonosim.l1.project import load_inventory, project, projected_distance  # noqa: E402
from phonosim.similarity import get_similarity  # noqa: E402

L1S = ["Arabic", "Hindi", "Korean", "Mandarin", "Spanish", "Vietnamese"]
INV = ROOT / "crossl1" / "data" / "inventories.yaml"
V2 = ROOT / "icphs2027" / "data" / "hindi_inventory_v2.yaml"


def predictors(method: str = "hamming", variant: str = "primary") -> pd.DataFrame:
    invs = {l: load_inventory(l.lower(), INV, variant) for l in L1S}
    v2 = load_v2(V2)
    rows = []
    for x, y in permutations(CONS, 2):
        a, b = ARPA_TO_IPA[x], ARPA_TO_IPA[y]
        r = {"X": x, "Y": y, "pair": f"{a}→{b}",
             "dist_english": get_similarity(a, b).n_differ,
             "same_cat_v1": 0}
        for l in L1S:
            r[f"comp_{l}"] = r["dist_english"] - projected_distance(a, b, invs[l], method)
        r["comp_HindiHand"] = r["dist_english"] - get_similarity(v2[a], v2[b]).n_differ
        rows.append(r)
    return pd.DataFrame(rows)


def add_matched(d: pd.DataFrame, assign: dict[str, str] | None = None) -> pd.DataFrame:
    """comp_matched = compression under the speaker's own L1 (or under `assign`);
    comp_others = mean compression under the five other L1s."""
    d = d.copy()
    assign = assign or {l: l for l in L1S}
    d["comp_matched"] = 0.0
    d["comp_others"] = 0.0
    for l in L1S:
        m = d.l1 == l
        own = assign[l]
        d.loc[m, "comp_matched"] = d.loc[m, f"comp_{own}"]
        d.loc[m, "comp_others"] = d.loc[m, [f"comp_{o}" for o in L1S if o != own]].mean(axis=1)
    return d


def p1(d: pd.DataFrame) -> dict:
    res = fit("count ~ dist_english + comp_matched + comp_others", add_matched(d))
    return {"family": res.family_name, "nb_alpha": res.nb_alpha,
            **{t: term(res, t) for t in ["dist_english", "comp_matched", "comp_others"]}}


def poisson_dev(d: pd.DataFrame, col: str) -> float:
    X = sm.add_constant(d[["dist_english", col]])
    return float(sm.GLM(d["count"], X, family=sm.families.Poisson(),
                        offset=np.log(d["tokens"])).fit().deviance)


def permutation_test(d: pd.DataFrame) -> dict:
    devs = {}
    for perm in permutations(L1S):
        assign = dict(zip(L1S, perm))
        devs[perm] = poisson_dev(add_matched(d, assign), "comp_matched")
    true = devs[tuple(L1S)]
    allv = np.array(list(devs.values()))
    der = np.array([v for p, v in devs.items() if all(a != b for a, b in zip(L1S, p))])
    return {"deviance_true": true, "n_perms": len(allv),
            "p_all": float((allv <= true + 1e-9).mean()),
            "rank_true": int((allv < true - 1e-9).sum()) + 1,
            "deviance_perm_median": float(np.median(allv)),
            "deviance_perm_min": float(allv.min()),
            "n_derangements": len(der),
            "share_derangements_beaten": float((der > true).mean())}


def matrix(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for g in L1S:
        dg = d[d.l1 == g]
        for l in L1S:
            n = nested(dg, "dist_english", f"comp_{l}")
            t = n[f"comp_{l}"]
            rows.append({"speakers": g, "predictor": l, "delta_aic": n["delta_aic"],
                         "irr": t["irr"], "ci_low": t["ci_low"], "ci_high": t["ci_high"],
                         "p": t["p"], "family": n["family"]})
    return pd.DataFrame(rows)


def diag_summary(m: pd.DataFrame) -> dict:
    # Signed fit gain: a predictor only counts when it points the predicted way (IRR > 1).
    m = m.assign(signed=np.where(m.irr > 1, m.delta_aic, -m.delta_aic.abs()))
    w = m.pivot(index="speakers", columns="predictor", values="signed")
    best = w.idxmax(axis=1)
    return {"diagonal_is_row_best": {g: bool(best[g] == g) for g in L1S},
            "n_diagonal_best": int(sum(best[g] == g for g in L1S)),
            "row_best": best.to_dict()}


def load(phones: str, min_groups: int = 4, include_l1_specific: bool = False) -> pd.DataFrame:
    df = pd.read_csv(phones, keep_default_na=False)
    if not include_l1_specific:
        df = df[df["utt"].isin(shared_utterances(df, min_groups))]
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phones_csv"); ap.add_argument("out_dir")
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    df = load(args.phones_csv)

    preds = predictors()
    preds.to_csv(out / "pair_predictors.csv", index=False)
    proj = pd.DataFrame(
        [{"english": ARPA_TO_IPA[c],
          **{l: "/".join(project(ARPA_TO_IPA[c], load_inventory(l.lower(), INV))) for l in L1S},
          "Hindi_hand_v2": load_v2(V2)[ARPA_TO_IPA[c]]} for c in CONS])
    proj.to_csv(out / "projection_table.csv", index=False)

    d = build_table(df, preds, use_dev=True)
    res = {"inventories_sha256": hashlib.sha256(INV.read_bytes()).hexdigest(),
           "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "project_sha256": hashlib.sha256((ROOT / "phonosim/l1/project.py").read_bytes()).hexdigest(),
           "n_rows": len(d), "subs_by_l1": {k: int(v) for k, v in d.groupby("l1")["count"].sum().items()},
           "hindi_auto_vs_hand_agreement": int((proj.Hindi == proj.Hindi_hand_v2).sum())}

    # --- Primary
    res["P1_matched_vs_others"] = p1(d)
    res["P2_permutation"] = permutation_test(d)
    m = matrix(d); m.to_csv(out / "matrix_6x6.csv", index=False)
    res["P3_matrix"] = diag_summary(m)

    # --- Hindi: automatic projection vs the hand-built literature table (v2)
    h = d[d.l1 == "Hindi"]; d["is_hindi"] = (d.l1 == "Hindi").astype(int)
    res["hindi_auto_vs_hand"] = {
        "H1_auto": nested(h, "dist_english", "comp_Hindi"),
        "H1_hand": nested(h, "dist_english", "comp_HindiHand"),
        "H2_auto": term(fit("count ~ (dist_english + comp_Hindi) * is_hindi", d), "comp_Hindi:is_hindi"),
        "H2_hand": term(fit("count ~ (dist_english + comp_HindiHand) * is_hindi", d), "comp_HindiHand:is_hindi"),
    }

    # --- Robustness (all reported, whatever they show)
    rob = {}
    vw = ~(((d.X == "V") & (d.Y == "W")) | ((d.X == "W") & (d.Y == "V")))
    rob["P1_drop_vw"] = p1(d[vw])
    for l in L1S:
        rob[f"P1_leave_out_{l}"] = p1(d[d.l1 != l])
    d_nodev = build_table(df, preds, use_dev=False)
    rob["P1_no_deviations"] = p1(d_nodev)
    pc = predictors(method="contrastive")
    dc = build_table(df, pc, use_dev=True)
    rob["P1_contrastive"] = p1(dc)
    mc = matrix(dc); mc.to_csv(out / "matrix_6x6_contrastive.csv", index=False)
    rob["P3_contrastive"] = diag_summary(mc)
    pa = predictors(variant="alt")
    da = build_table(df, pa, use_dev=True)
    rob["P1_alt_inventories"] = p1(da)
    ma = matrix(da); ma.to_csv(out / "matrix_6x6_alt.csv", index=False)
    rob["P3_alt_inventories"] = diag_summary(ma)
    dall = build_table(load(args.phones_csv, include_l1_specific=True), preds, use_dev=True)
    rob["P1_include_l1_specific"] = p1(dall)
    res["robustness"] = rob

    # --- Descriptives: top matched-compression pairs per L1 with rates
    agg = d.groupby(["l1", "pair"])[["count", "tokens"]].sum().reset_index()
    agg["rate"] = agg["count"] / agg["tokens"]
    agg = agg.merge(preds[["pair", "dist_english"] + [f"comp_{l}" for l in L1S]], on="pair")
    agg.to_csv(out / "pair_rates_by_l1.csv", index=False)

    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, default=float)

    f = lambda t: f"IRR {t['irr']:.2f} [{t['ci_low']:.2f}, {t['ci_high']:.2f}] p={t['p']:.3g}"
    print("P1 matched:", f(res["P1_matched_vs_others"]["comp_matched"]),
          "| others:", f(res["P1_matched_vs_others"]["comp_others"]),
          "|", res["P1_matched_vs_others"]["family"])
    print("P2:", res["P2_permutation"])
    print("P3:", res["P3_matrix"])
    print(m.pivot(index="speakers", columns="predictor", values="delta_aic").round(1))
    print(m.pivot(index="speakers", columns="predictor", values="irr").round(2))
    for k, v in res["hindi_auto_vs_hand"].items():
        print(k, f(v) if "irr" in v else f"dAIC={v['delta_aic']:.1f} " + f(v[[t for t in v if t.startswith('comp')][0]]))
    for k, v in rob.items():
        print(k, f(v["comp_matched"]) if "comp_matched" in v else v)


if __name__ == "__main__":
    main()
