"""Study 1b: do Hindi speakers' accent marks (X,X*,s) concentrate on consonants the
hand-built Hindi table predicts differ from Hindi? Spec: ../ANALYSIS_PLAN.md.

Usage (from the repo root):
    PYTHONPATH=. python accentmarks/code/analyze_marks.py icphs2027/phones.csv OUT --data scripted
    PYTHONPATH=. python accentmarks/code/analyze_marks.py phones_suitcase.csv OUT --data suitcase
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
from analyze import ARPA_TO_IPA, CONS, shared_utterances  # noqa: E402

V2 = ROOT / "icphs2027" / "data" / "hindi_inventory_v2.yaml"


def v2_types() -> dict[str, str]:
    t = yaml.safe_load(V2.read_text(encoding="utf-8"))["english_to_hindi"]
    return {x: t[ARPA_TO_IPA[x]]["type"] for x in CONS}


def table(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df.cpl.isin(CONS)]
    tok = df[df.tag.isin(["correct", "s", "d"])].groupby(["speaker", "l1", "cpl"]).size().rename("tokens")
    mk = df[(df.tag == "s") & (df.deviation == 1) & (df.ppl == df.cpl)].groupby(["speaker", "l1", "cpl"]).size().rename("marks")
    d = pd.concat([tok, mk], axis=1).fillna(0).reset_index().rename(columns={"cpl": "X"})
    d = d[d.tokens > 0].copy()
    # Consonants never marked for any speaker carry no information about the interaction
    # and make the consonant fixed effect diverge, so they are dropped (pre-stated rule).
    marked = d.groupby("X").marks.sum()
    d = d[d.X.isin(marked[marked > 0].index)].copy()
    types = v2_types()
    d["type"] = d.X.map(types)
    d["pred_diff"] = d.type.isin(["exists_different_cues", "no_equivalent"]).astype(int)
    d["diff_cues"] = (d.type == "exists_different_cues").astype(int)
    d["no_equiv"] = (d.type == "no_equivalent").astype(int)
    d["is_hindi"] = (d.l1 == "Hindi").astype(int)
    return d


def fit(formula: str, d: pd.DataFrame):
    return smf.glm(formula, data=d, family=sm.families.Poisson(), offset=np.log(d.tokens)).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(d.speaker)[0]})


def safe(fn):
    """Secondary models only: report a model that cannot be estimated instead of crashing
    (added after the freeze; see the deviation log in ANALYSIS_PLAN.md)."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"error": f"not estimable: {type(e).__name__}: {e}"}


def term(res, name: str) -> dict:
    ci = res.conf_int().loc[name]
    return {"irr": float(np.exp(res.params[name])), "ci_low": float(np.exp(ci[0])),
            "ci_high": float(np.exp(ci[1])), "p": float(res.pvalues[name])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phones_csv"); ap.add_argument("out_dir")
    ap.add_argument("--data", choices=["scripted", "suitcase"], required=True)
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(a.phones_csv, keep_default_na=False)
    df = raw[raw.utt.isin(shared_utterances(raw, 4))] if a.data == "scripted" else raw
    d = table(df)
    no_vw = d[~d.X.isin(["V", "W"])]
    f = "marks ~ C(X) + is_hindi + is_hindi:pred_diff"
    res = {"data": a.data,
           "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
                      ["accentmarks/code/analyze_marks.py", "icphs2027/data/hindi_inventory_v2.yaml"]},
           "n_speakers": int(d.speaker.nunique()),
           "marks_total": int(d.marks.sum()),
           "consonants_used": sorted(d.X.unique().tolist()),
           "primary_no_vw": term(fit(f, no_vw), "is_hindi:pred_diff"),
           "with_vw": safe(lambda: term(fit(f, d), "is_hindi:pred_diff"))}
    split = "marks ~ C(X) + is_hindi + is_hindi:diff_cues + is_hindi:no_equiv"
    res["split_types_no_vw"] = safe(lambda: {t: term(fit(split, no_vw), f"is_hindi:{t}")
                                             for t in ["diff_cues", "no_equiv"]})
    if a.data == "scripted":
        res["include_l1_specific_no_vw"] = safe(lambda: term(
            fit(f, table(raw)[lambda x: ~x.X.isin(["V", "W"])]), "is_hindi:pred_diff"))
    desc = (d.assign(group=np.where(d.is_hindi == 1, "Hindi", "Other five"))
            .groupby(["X", "type", "group"])[["marks", "tokens"]].sum().reset_index())
    desc["rate"] = desc.marks / desc.tokens
    wide = desc.pivot_table(index=["X", "type"], columns="group", values="rate").reset_index()
    wide["ipa"] = wide.X.map(ARPA_TO_IPA)
    wide.to_csv(out / "mark_rates_by_consonant.csv", index=False)
    d.to_csv(out / "speaker_consonant_table.csv", index=False)
    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    p = lambda t: t["error"] if "error" in t else \
        f"IRR {t['irr']:.2f} [{t['ci_low']:.2f}, {t['ci_high']:.2f}] p={t['p']:.3g}"
    print(f"== {a.data}: {res['n_speakers']} speakers, {res['marks_total']} marks, "
          f"consonants used: {len(res['consonants_used'])}")
    print("Primary (no v/w)  ", p(res["primary_no_vw"]))
    print("With v/w          ", p(res["with_vw"]))
    split = res["split_types_no_vw"]
    for k, v in (split.items() if "error" not in split else [("split", split)]):
        print(f"  {k:10s}       ", p(v))
    if "include_l1_specific_no_vw" in res:
        print("Incl. L1-specific ", p(res["include_l1_specific_no_vw"]))
    print(wide.sort_values("type").round(3).to_string(index=False))


if __name__ == "__main__":
    main()
