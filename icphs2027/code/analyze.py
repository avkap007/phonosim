"""Does an L1-aware (Hindi-projected) feature distance predict L2-ARCTIC substitutions
better than a language-neutral English feature distance? Spec: ANALYSIS_PLAN.md.

Usage:
    python analyze.py phones.csv out_dir/ --table ../data/hindi_inventory_v2.yaml \
        --table-v1 ../data/hindi_inventory_v1.yaml [--include-l1-specific] [--no-deviations]

Unit: speaker x ordered consonant pair (X expected, Y produced), 24 consonants -> 552 pairs.
Outcome: count of X->Y substitutions; exposure: tokens of X for that speaker.

Predictors (all computed with phonosim / PanPhon, 24 features):
  dist_english    feature distance between the two English phonemes (language-neutral)
  dist_projected  feature distance between their nearest Hindi categories (table v2)
  compression     dist_english - dist_projected: how much closer the pair becomes when
                  viewed through Hindi categories (v/w: 7; f/v: -6)
  same_cat_v1     original Term 1 binary flag (table v1), sensitivity only

Primary tests (negative binomial GLM, log exposure, SEs clustered by speaker):
  H1  Hindi speakers:  count ~ dist_english   vs   count ~ dist_english + compression
  H2  All speakers:    count ~ (dist_english + compression) * is_hindi
      key term compression:is_hindi (L1 layer predicts Hindi speakers' errors specifically)
Target-level (v and w): errors of any kind, incl. accented distortions, by L1 and speaker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yaml
from scipy.stats import spearmanr

from phonosim.similarity import get_similarity

warnings.filterwarnings("ignore")

ARPA_TO_IPA = {
    "P": "p", "B": "b", "T": "t", "D": "d", "K": "k", "G": "ɡ",
    "F": "f", "V": "v", "TH": "θ", "DH": "ð", "S": "s", "Z": "z",
    "SH": "ʃ", "ZH": "ʒ", "HH": "h", "CH": "t͡ʃ", "JH": "d͡ʒ",
    "M": "m", "N": "n", "NG": "ŋ", "L": "l", "R": "ɹ", "W": "w", "Y": "j",
}
CONS = list(ARPA_TO_IPA)


# ---------------------------------------------------------------- predictors
def load_v2(path: Path) -> dict[str, str]:
    table = yaml.safe_load(path.read_text(encoding="utf-8"))["english_to_hindi"]
    missing = [ipa for ipa in ARPA_TO_IPA.values() if ipa not in table]
    if missing:
        raise SystemExit(f"Table v2 is missing English consonants: {missing}")
    return {ipa: row["hindi"] for ipa, row in table.items()}


def load_v1(path: Path) -> dict[str, str | None]:
    table = yaml.safe_load(path.read_text(encoding="utf-8"))["english_to_hindi"]
    out = {}
    for ipa in ARPA_TO_IPA.values():
        row = table.get(ipa)
        c = None if row is None else row.get("closest_hindi")
        if isinstance(c, list):
            c = c[0] if len(c) == 1 else None
        out[ipa] = c
    return out


def pair_predictors(v2: dict, v1: dict) -> pd.DataFrame:
    rows = []
    for x, y in permutations(CONS, 2):
        a, b = ARPA_TO_IPA[x], ARPA_TO_IPA[y]
        ha, hb = v2[a], v2[b]
        rows.append({
            "X": x, "Y": y, "pair": f"{a}→{b}", "hindi_pair": f"{ha}→{hb}",
            "dist_english": get_similarity(a, b).n_differ,
            "dist_projected": get_similarity(ha, hb).n_differ,
            "w_english_panphon": get_similarity(a, b, mode="panphon").weighted_distance,
            "w_projected_panphon": get_similarity(ha, hb, mode="panphon").weighted_distance,
            "w_english_hindi": get_similarity(a, b, mode="hindi").weighted_distance,
            "w_projected_hindi": get_similarity(ha, hb, mode="hindi").weighted_distance,
            "same_cat_v1": int(v1[a] is not None and v1[a] == v1[b]),
        })
    df = pd.DataFrame(rows)
    df["compression"] = df.dist_english - df.dist_projected
    df["compression_panphon"] = df.w_english_panphon - df.w_projected_panphon
    df["compression_hindi"] = df.w_english_hindi - df.w_projected_hindi
    return df


# ---------------------------------------------------------------- data
def shared_utterances(df: pd.DataFrame, min_groups: int) -> set[str]:
    groups = df.groupby("utt")["l1"].nunique()
    return set(groups[groups >= min_groups].index)


def build_table(df: pd.DataFrame, preds: pd.DataFrame, use_dev: bool) -> pd.DataFrame:
    df = df[df["cpl"].isin(CONS)]
    tokens = (df[df["tag"].isin(["correct", "s", "d"])]
              .groupby(["speaker", "cpl"]).size().rename("tokens").reset_index()
              .rename(columns={"cpl": "X"}))
    subs = df[(df["tag"] == "s") & (df["err"] == 0) & df["ppl"].isin(CONS)
              & (df["ppl"] != df["cpl"])]
    if not use_dev:
        subs = subs[subs["deviation"] == 0]
    counts = (subs.groupby(["speaker", "cpl", "ppl"]).size().rename("count").reset_index()
              .rename(columns={"cpl": "X", "ppl": "Y"}))
    spk = df[["speaker", "l1"]].drop_duplicates()
    grid = spk.merge(preds, how="cross")
    grid = grid.merge(tokens, on=["speaker", "X"], how="left")
    grid = grid.merge(counts, on=["speaker", "X", "Y"], how="left")
    grid["tokens"] = grid["tokens"].fillna(0)
    grid["count"] = grid["count"].fillna(0).astype(int)
    grid = grid[grid["tokens"] > 0].copy()
    grid["is_hindi"] = (grid["l1"] == "Hindi").astype(int)
    return grid


# ---------------------------------------------------------------- models
def fit(formula: str, data: pd.DataFrame, alpha: float | None = None, estimate: bool = True):
    """NB GLM with ML alpha (shared across nested models), speaker-clustered SEs."""
    groups = pd.factorize(data["speaker"])[0]
    offset = np.log(data["tokens"])
    if estimate:
        try:
            nb = smf.negativebinomial(formula, data, exposure=data["tokens"]).fit(
                method="bfgs", maxiter=2000, disp=0)
            alpha = float(nb.params["alpha"])
            if not (np.isfinite(alpha) and 1e-6 < alpha < 100):
                alpha = None
        except Exception:
            alpha = None
    fam = sm.families.Poisson() if alpha is None else sm.families.NegativeBinomial(alpha=alpha)
    if len(set(groups)) > 1:
        res = smf.glm(formula, data, family=fam, offset=offset).fit(
            cov_type="cluster", cov_kwds={"groups": groups})
    else:  # single speaker: robust (HC0) SEs
        res = smf.glm(formula, data, family=fam, offset=offset).fit(cov_type="HC0")
    res.nb_alpha = alpha
    res.family_name = "poisson" if alpha is None else "negbin"
    return res


def term(res, name: str) -> dict:
    ci = res.conf_int().loc[name]
    return {"term": name, "coef": float(res.params[name]),
            "irr": float(np.exp(res.params[name])),
            "ci_low": float(np.exp(ci[0])), "ci_high": float(np.exp(ci[1])),
            "p": float(res.pvalues[name])}


def nested(data: pd.DataFrame, base: str, added: str) -> dict:
    full = fit(f"count ~ {base} + {added}", data)
    red = fit(f"count ~ {base}", data, alpha=full.nb_alpha, estimate=False)
    return {"family": full.family_name, "nb_alpha": full.nb_alpha,
            "aic_base": red.aic, "aic_full": full.aic, "delta_aic": red.aic - full.aic,
            base: term(full, base), added: term(full, added)}


def interaction(data: pd.DataFrame, dist: str, l1term: str) -> dict:
    res = fit(f"count ~ ({dist} + {l1term}) * is_hindi", data)
    return {"family": res.family_name,
            **{t: term(res, t) for t in [dist, l1term, f"{dist}:is_hindi", f"{l1term}:is_hindi"]}}


# ---------------------------------------------------------------- target-level v/w
def vw_targets(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d = df[df["cpl"].isin(["V", "W"])].copy()
    other = {"V": "W", "W": "V"}
    d["outcome"] = "correct"
    d.loc[(d.tag == "s") & (d.ppl == d.cpl.map(other)), "outcome"] = "to_partner"
    d.loc[(d.tag == "s") & (d.ppl == d.cpl) & (d.deviation == 1), "outcome"] = "distortion"
    d.loc[(d.tag == "s") & (d.outcome == "correct"), "outcome"] = "other_error"
    d.loc[d.tag == "d", "outcome"] = "deletion"
    per_spk = (pd.crosstab([d.l1, d.speaker, d.cpl], d.outcome)
               .reindex(columns=["correct", "to_partner", "distortion", "other_error", "deletion"],
                        fill_value=0))
    per_spk["tokens"] = per_spk.sum(axis=1)
    per_spk["any_error_rate"] = 1 - per_spk["correct"] / per_spk["tokens"]
    per_spk["partner_or_distortion_rate"] = (per_spk.to_partner + per_spk.distortion) / per_spk.tokens
    per_spk = per_spk.reset_index()
    by_l1 = (per_spk.groupby(["l1", "cpl"])[["correct", "to_partner", "distortion",
                                             "other_error", "deletion", "tokens"]].sum())
    by_l1["any_error_rate"] = 1 - by_l1.correct / by_l1.tokens
    by_l1["partner_or_distortion_rate"] = (by_l1.to_partner + by_l1.distortion) / by_l1.tokens
    return per_spk, by_l1.reset_index()


def vw_model(per_spk: pd.DataFrame) -> dict:
    """Binomial GLM: v/w partner-substitution-or-distortion ~ is_hindi, clustered by speaker."""
    d = per_spk.copy()
    d["is_hindi"] = (d.l1 == "Hindi").astype(int)
    d["hits"] = d.to_partner + d.distortion
    out = {}
    for target in ["V", "W"]:
        t = d[d.cpl == target]
        if t.tokens.sum() == 0 or t.hits.sum() == 0:
            continue
        if (t.groupby("is_hindi").hits.sum() == 0).any():
            out[target] = {"note": "one group has zero errors (separation); report rates only"}
            continue
        res = sm.GLM(np.column_stack([t.hits, t.tokens - t.hits]),
                     sm.add_constant(t[["is_hindi"]]), family=sm.families.Binomial()
                     ).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(t.speaker)[0]})
        ci = res.conf_int().loc["is_hindi"]
        out[target] = {"odds_ratio": float(np.exp(res.params["is_hindi"])),
                       "ci_low": float(np.exp(ci[0])), "ci_high": float(np.exp(ci[1])),
                       "p": float(res.pvalues["is_hindi"])}
    return out


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phones_csv")
    ap.add_argument("out_dir")
    ap.add_argument("--table", default=str(Path(__file__).parent.parent / "data/hindi_inventory_v2.yaml"))
    ap.add_argument("--table-v1", default=str(Path(__file__).parent.parent / "data/hindi_inventory_v1.yaml"))
    ap.add_argument("--include-l1-specific", action="store_true",
                    help="also use the ~50 L1-targeted utterances per speaker (biased)")
    ap.add_argument("--no-deviations", action="store_true",
                    help="drop substitutions carrying the * deviation mark")
    ap.add_argument("--min-groups", type=int, default=4)
    args = ap.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    t2, t1 = Path(args.table), Path(args.table_v1)

    df = pd.read_csv(args.phones_csv, keep_default_na=False)
    shared = shared_utterances(df, args.min_groups)
    print(f"Shared utterances (annotated in >= {args.min_groups} L1 groups): {len(shared)}")
    if not args.include_l1_specific:
        df = df[df["utt"].isin(shared)]

    preds = pair_predictors(load_v2(t2), load_v1(t1))
    preds.to_csv(out / "pair_predictors.csv", index=False)
    data = build_table(df, preds, use_dev=not args.no_deviations)
    data.to_csv(out / "pair_table.csv", index=False)
    hindi = data[data.is_hindi == 1]

    res = {
        "settings": vars(args),
        "table_v2_sha256": hashlib.sha256(t2.read_bytes()).hexdigest(),
        "table_v1_sha256": hashlib.sha256(t1.read_bytes()).hexdigest(),
        "n_shared_utts": len(shared),
        "n_consonant_tokens": int(data.drop_duplicates(["speaker", "X"]).tokens.sum()),
        "subs_by_l1": {k: int(v) for k, v in data.groupby("l1")["count"].sum().items()},
        "corr_english_projected": float(np.corrcoef(preds.dist_english, preds.dist_projected)[0, 1]),
        "primary": {}, "robustness": {}, "per_speaker_H1": {}}

    # Primary
    res["primary"]["H1"] = nested(hindi, "dist_english", "compression")
    res["primary"]["H2"] = interaction(data, "dist_english", "compression")
    # Robustness: weighted distances, original v1 flag
    res["robustness"]["H1_panphon_weights"] = nested(hindi, "w_english_panphon", "compression_panphon")
    res["robustness"]["H1_hindi_weights"] = nested(hindi, "w_english_hindi", "compression_hindi")
    res["robustness"]["H1_v1_flag"] = nested(hindi, "dist_english", "same_cat_v1")
    res["robustness"]["H2_v1_flag"] = interaction(data, "dist_english", "same_cat_v1")
    # Per Hindi speaker (n=4)
    for spk, g in hindi.groupby("speaker"):
        try:
            r = fit("count ~ dist_english + compression", g)
            res["per_speaker_H1"][spk] = term(r, "compression")
        except Exception as e:  # noqa: BLE001
            res["per_speaker_H1"][spk] = {"error": str(e)}

    # Descriptives
    agg = (data.groupby(["l1", "pair", "dist_english", "dist_projected", "compression"])
           [["count", "tokens"]].sum().reset_index())
    agg["rate"] = agg["count"] / agg["tokens"]
    agg.to_csv(out / "pair_rates_by_l1.csv", index=False)
    res["spearman_rate"] = {
        l1: {"english": float(spearmanr(g.dist_english, g.rate)[0]),
             "projected": float(spearmanr(g.dist_projected, g.rate)[0])}
        for l1, g in agg.groupby("l1")}

    vw_spk, vw_l1 = vw_targets(df)
    vw_spk.to_csv(out / "vw_by_speaker.csv", index=False)
    vw_l1.to_csv(out / "vw_by_l1.csv", index=False)
    res["vw_target_model"] = vw_model(vw_spk)

    wide = agg.pivot_table(index=["pair", "dist_english", "dist_projected", "compression"],
                           columns="l1", values="rate").reset_index()
    others = [c for c in wide.columns if c not in ("pair", "dist_english", "dist_projected",
                                                   "compression", "Hindi")]
    wide["other_mean"] = wide[others].mean(axis=1)
    wide.to_csv(out / "pair_rates_wide.csv", index=False)
    top = wide.sort_values("Hindi", ascending=False).head(10)

    with open(out / "results.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, ensure_ascii=False, default=float)
    write_latex_table(top, out / "table_top_pairs.tex")
    plot(agg, out / "fig_compression.pdf")
    print_summary(res, top, vw_l1)


def write_latex_table(top: pd.DataFrame, path: Path) -> None:
    lines = [r"\begin{tabular}{lcccc}", r"\toprule",
             r"Substitution & Eng. & Hindi & \multicolumn{2}{c}{Rate}\\",
             r" & dist. & dist. & Hindi & Other\\", r"\midrule"]
    for _, r in top.iterrows():
        lines.append(f"\\ipa{{{r.pair}}} & {int(r.dist_english)} & {int(r.dist_projected)} & "
                     f"{100*r.Hindi:.1f}\\% & {100*r.other_mean:.1f}\\%\\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    path.write_text("\n".join(lines), encoding="utf-8")


def plot(agg: pd.DataFrame, path: Path) -> None:
    """Hindi minus other-L1 substitution rate, by compression."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "serif", "font.size": 8})
    w = agg.pivot_table(index=["pair", "compression"], columns="l1", values="rate").reset_index()
    oth = [c for c in w.columns if c not in ("pair", "compression", "Hindi")]
    w["excess"] = 100 * (w["Hindi"] - w[oth].mean(axis=1))
    w = w.dropna(subset=["excess"])
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(3.15, 2.3))
    ax.axhline(0, color="0.8", lw=0.6)
    ax.scatter(w.compression + rng.uniform(-0.15, 0.15, len(w)), w.excess,
               s=7, c="#1b4f9c", alpha=0.6, linewidths=0)
    for _, r in w.sort_values("excess", ascending=False).head(3).iterrows():
        ax.annotate(r.pair, (r.compression, r.excess), fontsize=6.5,
                    xytext=(-4, -2), textcoords="offset points", ha="right")
    means = w.groupby("compression").excess.mean()
    ax.plot(means.index, means.values, color="#c0392b", lw=1, marker="o", ms=2.5,
            label="Mean per level")
    ax.set_xlabel("L1 compression (English dist. − Hindi-projected dist.)")
    ax.set_ylabel("Hindi − other L1s (pp)")
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    fig.savefig(path.with_suffix(".png"), dpi=300)


def print_summary(res: dict, top: pd.DataFrame, vw_l1: pd.DataFrame) -> None:
    def fmt(t):
        return f"IRR {t['irr']:.2f} [{t['ci_low']:.2f}, {t['ci_high']:.2f}] p={t['p']:.3g}"
    print("\n=== PRIMARY ===")
    h1, h2 = res["primary"]["H1"], res["primary"]["H2"]
    print(f"H1 (Hindi): dAIC={h1['delta_aic']:.1f}; compression {fmt(h1['compression'])}")
    print(f"H2 (all):   compression x Hindi {fmt(h2['compression:is_hindi'])}")
    print("\n=== ROBUSTNESS ===")
    for k, v in res["robustness"].items():
        key = [t for t in v if t.startswith(("compression", "same_cat")) and isinstance(v[t], dict)]
        key = [t for t in key if ("is_hindi" in t) == k.startswith("H2")]
        print(f"{k}: {fmt(v[key[0]])}" + (f"  dAIC={v['delta_aic']:.1f}" if "delta_aic" in v else ""))
    print("\nPer Hindi speaker (compression):",
          {k: (round(v['irr'], 2) if 'irr' in v else v) for k, v in res["per_speaker_H1"].items()})
    print("\nv/w target rates by L1:")
    print(vw_l1[["l1", "cpl", "tokens", "to_partner", "distortion",
                 "partner_or_distortion_rate"]].to_string(index=False))
    print("v/w Hindi vs others:", res["vw_target_model"])
    print("\nTop Hindi substitutions:")
    print(top[["pair", "dist_english", "dist_projected", "Hindi", "other_mean"]].to_string(index=False))


if __name__ == "__main__":
    main()
