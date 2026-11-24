"""Study 1c: do the L1 layers predict how each group actually realises English consonants,
as recorded in L2-ARCTIC's IPA tier? Spec: ../ANALYSIS_PLAN.md (frozen before real data).

For every IPA-annotated consonant substitution, d(layer) = mean number of differing PanPhon
features between the realised IPA segment and the layer's predicted L1 category (averaged
over tied categories). Lower = the layer predicts the realisation better.

Usage (from the repo root):
    PYTHONPATH=. python ipa_tier/code/analyze_ipa.py ipa_scripted.csv OUT --data scripted \
        --shared-from icphs2027/phones.csv
    PYTHONPATH=. python ipa_tier/code/analyze_ipa.py ipa_suitcase.csv OUT --data suitcase
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
from analyze import ARPA_TO_IPA, CONS, load_v2, shared_utterances  # noqa: E402

from phonosim.features import normalize_ipa  # noqa: E402
from phonosim.l1.allophone import clean, load_allophone_inventory, project_allophone  # noqa: E402
from phonosim.l1.project import load_inventory, project  # noqa: E402
from phonosim.similarity import get_similarity  # noqa: E402

L1S = ["Arabic", "Hindi", "Korean", "Mandarin", "Spanish", "Vietnamese"]
PHOIBLE = ROOT / "allophone" / "data" / "phoible_selected.csv"
INV2 = ROOT / "crossl1" / "data" / "inventories.yaml"
V2 = ROOT / "icphs2027" / "data" / "hindi_inventory_v2.yaml"
N_BOOT, SEED = 2000, 30004064


def parse(seg: str) -> str | None:
    try:
        return normalize_ipa(clean(seg))
    except (ValueError, KeyError, IndexError):
        return None


def categories() -> dict[str, dict[str, dict[str, list[str]]]]:
    """layer -> L1 -> English consonant (IPA) -> predicted L1 categories."""
    out = {"allophone": {}, "study2": {}}
    for l in L1S:
        s2 = load_inventory(l.lower(), INV2)
        inv = load_allophone_inventory(l.lower(), PHOIBLE, add_glides=[g for g in ("j", "w") if g in s2])
        out["allophone"][l] = {ARPA_TO_IPA[c]: project_allophone(ARPA_TO_IPA[c], inv) for c in CONS}
        out["study2"][l] = {ARPA_TO_IPA[c]: project(ARPA_TO_IPA[c], s2) for c in CONS}
    v2 = load_v2(V2)
    out["hand"] = {"Hindi": {ARPA_TO_IPA[c]: [v2[ARPA_TO_IPA[c]]] for c in CONS}}
    return out


def dist(r: str, cats: list[str]) -> float:
    return float(np.mean([get_similarity(r, c).n_differ for c in cats]))


def prepare(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n0 = len(df)
    df = df[(df.status == "ok") & (df.tag == "s") & df.cpl.isin(CONS)].copy()
    df = df[~df.realised_ipa.str.lower().isin(["err", "sil", ""])]
    df["r"] = df.realised_ipa.map(parse)
    info = {"entries": n0, "consonant_substitutions": len(df),
            "unparseable_realised": int(df.r.isna().sum()),
            "unparseable_examples": sorted(df[df.r.isna()].realised_ipa.unique().tolist())[:30]}
    df = df[df.r.notna()].copy()
    df["X"] = df.cpl.map(ARPA_TO_IPA)
    return df, info


def score(df: pd.DataFrame, cats: dict) -> pd.DataFrame:
    df = df.copy()
    memo = {}
    for layer in ("allophone", "study2"):
        for l in L1S:
            col = f"d_{layer}_{l}"
            df[col] = [memo.setdefault((layer, l, x, r), dist(r, cats[layer][l][x]))
                       for x, r in zip(df.X, df.r)]
    df["d_hand_Hindi"] = [dist(r, cats["hand"]["Hindi"][x]) for x, r in zip(df.X, df.r)]
    df["d_english"] = [get_similarity(r, x).n_differ for x, r in zip(df.X, df.r)]
    return df


def boot(df: pd.DataFrame, stat, rng) -> tuple[float, float]:
    """Speaker-cluster bootstrap: resample speakers within each L1 group."""
    spk = {g: df[df.l1 == g].speaker.unique() for g in df.l1.unique()}
    by = {s: d for s, d in df.groupby("speaker")}
    vals = []
    for _ in range(N_BOOT):
        parts = [by[s] for g in spk for s in rng.choice(spk[g], len(spk[g]), replace=True)]
        vals.append(stat(pd.concat(parts)))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def tests(df: pd.DataFrame, layer: str, rng) -> dict:
    own = np.array([df.loc[i, f"d_{layer}_{g}"] for i, g in zip(df.index, df.l1)])
    others = np.array([np.mean([df.loc[i, f"d_{layer}_{o}"] for o in L1S if o != g])
                       for i, g in zip(df.index, df.l1)])
    df = df.assign(gain=others - own)
    p1 = {"mean_gain_own_vs_others": float(df.gain.mean()),
          "ci95": boot(df, lambda x: x.gain.mean(), rng), "n_tokens": int(len(df))}
    # P2: total d under every assignment of layers to groups
    sums = {(g, l): df.loc[df.l1 == g, f"d_{layer}_{l}"].sum() for g in L1S for l in L1S}
    groups = [g for g in L1S if (df.l1 == g).any()]
    totals = {p: sum(sums[(g, l)] for g, l in zip(groups, p)) for p in permutations(L1S, len(groups))}
    true = sum(sums[(g, g)] for g in groups)
    allv = np.array(list(totals.values()))
    p2 = {"rank_true": int((allv < true - 1e-9).sum()) + 1, "n_perms": len(allv),
          "p": float((allv <= true + 1e-9).mean())}
    # P3: which layer predicts each group's realisations best
    means = pd.DataFrame({l: df.groupby("l1")[f"d_{layer}_{l}"].mean() for l in L1S})
    best = means.idxmin(axis=1)
    p3 = {"best_layer": best.to_dict(), "n_diagonal": int(sum(best[g] == g for g in best.index)),
          "mean_d": means.round(3).to_dict()}
    return {"P1": p1, "P2": p2, "P3": p3}


def hindi(df: pd.DataFrame, rng) -> dict:
    h = df[df.l1 == "Hindi"]
    out = {"n_tokens": int(len(h))}
    for col in ["d_hand_Hindi", "d_allophone_Hindi", "d_study2_Hindi", "d_english"]:
        out[col] = {"mean": float(h[col].mean()), "ci95": boot(h, lambda x, c=col: x[c].mean(), rng)}
    # Specificity: hand-table gain over the English baseline, Hindi minus other groups
    g = df.assign(gain=df.d_english - df.d_hand_Hindi, hi=(df.l1 == "Hindi"))
    stat = lambda x: x[x.hi].gain.mean() - x[~x.hi].gain.mean()
    out["hand_gain_hindi_minus_others"] = {"value": float(stat(g)), "ci95": boot(g, stat, rng)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ipa_csv"); ap.add_argument("out_dir")
    ap.add_argument("--data", choices=["scripted", "suitcase"], required=True)
    ap.add_argument("--shared-from", help="phones.csv used to define the shared utterances")
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    raw = pd.read_csv(a.ipa_csv, keep_default_na=False)
    df, info = prepare(raw)
    cats = categories()
    res = {"data": a.data, "parse": info,
           "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                      ["ipa_tier/code/analyze_ipa.py", "phonosim/l1/allophone.py",
                       "allophone/data/phoible_selected.csv", "crossl1/data/inventories.yaml",
                       "icphs2027/data/hindi_inventory_v2.yaml"]}}
    if a.data == "scripted":
        shared = shared_utterances(pd.read_csv(a.shared_from, keep_default_na=False), 4)
        df_all = df
        df = df[df.utt.isin(shared)]
    sc = score(df, cats)
    sc.to_csv(out / "scored_tokens.csv", index=False)
    no_vw = sc[~sc.cpl.isin(["V", "W"])]
    res["n_by_l1"] = sc.l1.value_counts().to_dict()
    res["primary_allophone_no_vw"] = tests(no_vw, "allophone", rng)
    res["hindi_no_vw"] = hindi(no_vw, rng)
    res["secondary"] = {"allophone_with_vw": tests(sc, "allophone", rng),
                        "study2_no_vw": tests(no_vw, "study2", rng),
                        "hindi_with_vw": hindi(sc, rng)}
    if a.data == "scripted":
        s_all = score(df_all, cats)
        res["secondary"]["allophone_no_vw_all_utterances"] = tests(s_all[~s_all.cpl.isin(["V", "W"])],
                                                                    "allophone", rng)
    # Descriptive: most common realisation per English consonant, Hindi vs other groups
    desc = (sc.assign(group=np.where(sc.l1 == "Hindi", "Hindi", "Other five"))
            .groupby(["X", "group"]).r.agg(lambda s: "; ".join(f"{k} {v}" for k, v in s.value_counts().head(4).items()))
            .unstack())
    desc.to_csv(out / "realisations_by_consonant.csv")
    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False)

    f = lambda t: f"{t['mean_gain_own_vs_others']:+.3f} features [{t['ci95'][0]:+.3f}, {t['ci95'][1]:+.3f}]"
    print(f"== {a.data}: {res['parse']}")
    print("tokens by L1:", res["n_by_l1"])
    for k, t in [("PRIMARY allophone, no v/w", res["primary_allophone_no_vw"]),
                 ("allophone, with v/w", res["secondary"]["allophone_with_vw"]),
                 ("study2 layer, no v/w", res["secondary"]["study2_no_vw"])] + \
            ([("allophone, no v/w, all utterances", res["secondary"]["allophone_no_vw_all_utterances"])]
             if a.data == "scripted" else []):
        print(f"{k:36s} P1 own-vs-others {f(t['P1'])} | P2 rank {t['P2']['rank_true']}/{t['P2']['n_perms']} "
              f"(p={t['P2']['p']:.3f}) | P3 {t['P3']['n_diagonal']}/6 {t['P3']['best_layer']}")
    h = res["hindi_no_vw"]
    print("Hindi (no v/w), mean features from realisation:",
          {k: f"{v['mean']:.2f} [{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]" for k, v in h.items()
           if k.startswith("d_")})
    s = h["hand_gain_hindi_minus_others"]
    print(f"Hand-table gain over English baseline, Hindi minus others: {s['value']:+.3f} "
          f"[{s['ci95'][0]:+.3f}, {s['ci95'][1]:+.3f}]")
    print(desc.to_string())


if __name__ == "__main__":
    main()
