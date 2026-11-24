"""Turn raw AXB study data into analysis tables, applying the pre-stated exclusions.

Input: JATOS exports (folders of data.txt files, one JSON row per line) and/or local-test
CSVs. Output (in OUT_DIR): participants.csv, axb_trials.csv, dprime.csv, assim.csv,
assim_by_phone.csv, overlap.csv, summary.txt.

    python prepare.py OUT_DIR INPUT [INPUT ...]

Exclusion rules (fixed before any real data):
  1. Hindi not reported as first language.
  2. Fewer than 10 of 12 catch trials correct (chance of 10+ by guessing is 2%).
  3. Fewer than 90% of the 192 test trials answered (stopped early).
Listeners who fail the headphone check never reach the AXB task.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import NormalDist

from common import CODE_IPA, CONTRAST_CODES, DEVANAGARI_IPA, l1_maps
from phonosim.similarity import get_similarity

CATCH_MIN, CATCH_N, TEST_N, TEST_MIN_SHARE = 10, 12, 192, 0.9
z = NormalDist().inv_cdf


def norm(v):
    if isinstance(v, str):
        return {"true": True, "false": False, "": None}.get(v, v)
    return v


def read_rows(paths):
    rows = []
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
        for f in files:
            if f.suffix == ".csv":
                with f.open(encoding="utf-8") as fh:
                    rows += [{k: norm(v) for k, v in r.items()} for r in csv.DictReader(fh)]
            elif f.suffix in (".txt", ".jsonl", ".json"):
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("{"):
                        rows.append(json.loads(line))
    return rows


def write(path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(out, inputs):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = read_rows(inputs)
    by_p = defaultdict(list)
    for r in rows:
        by_p[r["participant"]].append(r)
    hand, auto = l1_maps()
    dist = {c: get_similarity(CODE_IPA[a], CODE_IPA[b]).n_differ for c, (a, b) in CONTRAST_CODES.items()}

    parts, keep = [], set()
    for pid, rs in sorted(by_p.items()):
        bg = next((r["response"] for r in rs if r.get("task") == "background"), {}) or {}
        if isinstance(bg, str):
            bg = json.loads(bg)
        axb = [r for r in rs if r.get("task") == "axb"]
        catch = [r for r in axb if r.get("role") == "catch"]
        test = [r for r in axb if r.get("role") == "test"]
        reasons = []
        if bg.get("hindi_l1") != "Yes":
            reasons.append("hindi_not_l1")
        if sum(bool(r["correct"]) for r in catch) < CATCH_MIN:
            reasons.append(f"catch_{sum(bool(r['correct']) for r in catch)}of{len(catch)}")
        if len(test) < TEST_MIN_SHARE * TEST_N:
            reasons.append(f"incomplete_{len(test)}of{TEST_N}")
        if not reasons:
            keep.add(pid)
        parts.append({"participant": pid, "n_test": len(test),
                      "catch_correct": sum(bool(r["correct"]) for r in catch),
                      "test_accuracy": round(sum(bool(r["correct"]) for r in test) / max(1, len(test)), 3),
                      "hindi_l1": bg.get("hindi_l1"), "excluded": ";".join(reasons)})
    write(out / "participants.csv", parts)

    trials = []
    for pid in sorted(keep):
        for r in by_p[pid]:
            if r.get("task") == "axb" and r.get("role") == "test":
                trials.append({"listener": pid, "contrast": r["contrast"], "pair_id": r["pair_id"],
                               "order": r["order"], "answer": r["answer"],
                               "response_side": r["response_side"], "correct": int(bool(r["correct"])),
                               "rt_from_b_offset": r["rt_from_b_offset"], "block": r["block"],
                               "distance": dist[r["contrast"]],
                               "hand_merged": int(r["hand_merged"]), "auto_merged": int(r["auto_merged"])})
    write(out / "axb_trials.csv", trials)

    # d' per listener x contrast: H = P(first | answer first), F = P(first | answer last),
    # log-linear correction (add 0.5 to counts). Yes/no formula z(H) - z(F); not converted
    # to an AXB decision model (Macmillan & Creelman 2005), so compare it across contrasts only.
    cell = defaultdict(lambda: Counter())
    for t in trials:
        k = (t["listener"], t["contrast"])
        cell[k][(t["answer"], t["response_side"] == "first")] += 1
    dp = []
    for (pid, c), n in sorted(cell.items()):
        H = (n[("first", True)] + 0.5) / (n[("first", True)] + n[("first", False)] + 1)
        F = (n[("last", True)] + 0.5) / (n[("last", True)] + n[("last", False)] + 1)
        dp.append({"listener": pid, "contrast": c, "dprime": round(z(H) - z(F), 3),
                   "hand_merged": int(c in ("v-w", "zh-dzh")),
                   "auto_merged": int(c in ("th-t", "dh-d", "v-f", "w-r"))})
    write(out / "dprime.csv", dp)

    # sound matching: which map's category did listeners choose?
    assim, good = [], {}
    for pid in sorted(keep):
        for r in by_p[pid]:
            if r.get("task") == "assim_goodness":
                good[(pid, r["file"])] = r["goodness"]
        for r in by_p[pid]:
            if r.get("task") == "assim_choice":
                ipa = DEVANAGARI_IPA.get(r["hindi_choice"], "?")
                assim.append({"listener": pid, "phone": r["phone"], "rep": r["rep"], "choice": ipa,
                              "goodness": good.get((pid, r["file"]), ""),
                              "hand_pred": hand[r["phone"]], "auto_pred": auto[r["phone"]],
                              "matches_hand": int(ipa == hand[r["phone"]]),
                              "matches_auto": int(ipa in auto[r["phone"]].split("/"))})
    write(out / "assim.csv", assim)
    by_phone = []
    for ph in CODE_IPA:
        a = [x for x in assim if x["phone"] == ph]
        if not a:
            continue
        top = Counter(x["choice"] for x in a).most_common(1)[0]
        by_phone.append({"phone": CODE_IPA[ph], "n": len(a), "hand_pred": hand[ph], "auto_pred": auto[ph],
                         "share_hand": round(sum(x["matches_hand"] for x in a) / len(a), 3),
                         "share_auto": round(sum(x["matches_auto"] for x in a) / len(a), 3),
                         "modal_choice": top[0], "modal_share": round(top[1] / len(a), 3)})
    write(out / "assim_by_phone.csv", by_phone)

    # per-listener categorisation overlap for each contrast: sum over categories of
    # min(P(cat | sound a), P(cat | sound b)). 1 = both sounds always put in the same
    # Hindi category (single-category assimilation), 0 = never.
    ov = []
    for pid in sorted(keep):
        dist_by = defaultdict(Counter)
        for x in assim:
            if x["listener"] == pid:
                dist_by[x["phone"]][x["choice"]] += 1
        for c, (a, b) in CONTRAST_CODES.items():
            na, nb = sum(dist_by[a].values()), sum(dist_by[b].values())
            if na and nb:
                o = sum(min(dist_by[a][k] / na, dist_by[b][k] / nb) for k in set(dist_by[a]) | set(dist_by[b]))
                ov.append({"listener": pid, "contrast": c, "overlap": round(o, 3)})
    write(out / "overlap.csv", ov)

    lines = [f"listeners: {len(by_p)}, kept: {len(keep)}"]
    lines += [f"  excluded {p['participant']}: {p['excluded']}" for p in parts if p["excluded"]]
    lines.append("accuracy by contrast (kept listeners):")
    for c in CONTRAST_CODES:
        t = [x["correct"] for x in trials if x["contrast"] == c]
        d = [x["dprime"] for x in dp if x["contrast"] == c]
        if t:
            lines.append(f"  {c:7s} dist {dist[c]}/24  hand {int(c in ('v-w','zh-dzh'))} "
                         f"auto {int(c in ('th-t','dh-d','v-f','w-r'))}  acc {sum(t)/len(t):.2f}  "
                         f"mean d' {sum(d)/len(d):.2f}")
    if assim:
        lines.append(f"sound matching: {sum(x['matches_hand'] for x in assim)/len(assim):.2f} of choices "
                     f"match the hand map, {sum(x['matches_auto'] for x in assim)/len(assim):.2f} the automatic map")
    (out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
