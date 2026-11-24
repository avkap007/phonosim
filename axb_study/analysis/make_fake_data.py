"""Simulate listeners in the JATOS export format, to test the analysis before real data.

NOT REAL DATA. The simulated truth: the hand-built map's merges (v-w, zh-dzh) cost
accuracy (logit -1.5), the automatic map's merges have no effect, distance helps a little,
and sound-matching choices mostly follow the hand-built map. The analysis should recover
that. Three extra listeners are built to be excluded (failed catch trials, Hindi not L1,
stopped after block 2).

    python make_fake_data.py fake_data/ [n_listeners]
"""
import json
import math
import random
import sys
from pathlib import Path

from common import CODE_IPA, CONTRAST_CODES, DEVANAGARI_IPA, l1_maps, load_stim
from phonosim.similarity import get_similarity

out = Path(sys.argv[1] if len(sys.argv) > 1 else "fake_data")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
rng = random.Random(30004064)
stim = load_stim()
hand, auto = l1_maps()
ipa_to_dev = {v: k for k, v in DEVANAGARI_IPA.items()}
dist = {c: get_similarity(CODE_IPA[a], CODE_IPA[b]).n_differ for c, (a, b) in CONTRAST_CODES.items()}
mean_d = sum(dist.values()) / len(dist)
sd_d = (sum((d - mean_d) ** 2 for d in dist.values()) / len(dist)) ** 0.5
con_noise = {c: rng.gauss(0, 0.4) for c in dist}
inv_logit = lambda x: 1 / (1 + math.exp(-x))


def listener(pid, kind="ok"):
    u0, u1 = rng.gauss(0, 0.6), rng.gauss(0, 0.6)
    rows = [{"task": "consent", "consented": True},
            {"task": "background", "response": {"hindi_l1": "No" if kind == "nonhindi" else "Yes",
                                                "age": str(rng.randint(19, 45))}}]
    rows += [{"task": "headphone", "attempt": 1, "correct": True} for _ in range(6)]
    trials = [t for t in stim["axb"] if not t["practice"]]
    rng.shuffle(trials)
    if kind == "incomplete":
        trials = trials[:102]
    for i, t in enumerate(trials):
        if t["role"] == "catch":
            p = 0.5 if kind == "inattentive" else 0.97
        else:
            c = t["contrast"]
            eta = (2.2 + 0.2 * (dist[c] - mean_d) / sd_d + con_noise[c] + u0
                   + (-1.5 + u1) * int(t["hand_merged"]) + 0.0 * int(t["auto_merged"]))
            p = inv_logit(eta)
        ok = rng.random() < p
        side = t["answer"] if ok else ("last" if t["answer"] == "first" else "first")
        rt = int(t["b_offset_ms"] + math.exp(rng.gauss(6.4, 0.4)))
        rows.append({**t, "task": "axb", "block": i // 51 + 1, "response_side": side, "correct": ok,
                     "rt": rt, "rt_from_b_offset": rt - t["b_offset_ms"]})
    if kind != "incomplete":
        for t in stim["assim"]:
            r = rng.random()
            target = hand[t["phone"]] if r < 0.7 else auto[t["phone"]] if r < 0.8 else None
            choice = ipa_to_dev.get(target) or rng.choice(list(DEVANAGARI_IPA))
            rows.append({**t, "task": "assim_choice", "hindi_choice": choice})
            if choice != "None of these":
                rows.append({**t, "task": "assim_goodness", "goodness": rng.randint(3, 7)})
        rows.append({"task": "debrief"})
    for i, r in enumerate(rows):
        r.update(participant=pid, trial_index=i, version="FAKE", placeholder_audio=True)
    d = out / f"study_result_{pid}" / "comp-result_1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "data.txt").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                                encoding="utf-8")


for k in range(N):
    listener(f"FAKE{k:02d}")
listener("FAKE_INATTENTIVE", "inattentive")
listener("FAKE_NONHINDI", "nonhindi")
listener("FAKE_INCOMPLETE", "incomplete")
print(f"wrote {N + 3} fake listeners to {out}/ (NOT REAL DATA)")
