"""Build the AXB study's audio and trial list.

Standard library only. Run from the experiment folder:

    python3 build_stimuli.py --placeholders   # beeps, to test the pipeline
    python3 build_stimuli.py                  # real recordings

Inputs
  stimuli/pairs.csv           one row per minimal pair (contrast, pair_id, word_a, word_b, ...)
  audio/recordings/<word>_t1.wav, <word>_t2.wav
                              two recorded tokens of every word (mono, 16-bit,
                              44.1 kHz). Token 1 is used for A and B, token 2
                              for X, so X is never the identical file as its
                              match and listeners must judge the sound, not
                              the recording.

Outputs
  audio/axb/<pair_id>_<order>.wav   one file per AXB trial: A, gap, X, gap, B
  audio/assim/<phone>_t<1|2>.wav    aCa syllables for the sound-matching task
                                    (from stimuli/assim_tokens.csv; recordings
                                    named <token>_t1.wav and <token>_t2.wav)
  audio/headphone/hp_<n>.wav        Woods et al. (2017) antiphase headphone check
  audio/calibration.wav             tone for setting a comfortable volume
  stimuli/trials.js                 trial list read by experiment.js
"""
import argparse
import csv
import json
import math
import os
import random
import struct
import sys
import wave

RATE = 44100
ISI_MS = 500          # gap between A, X and B (McGuire 2010: 100 to 1000 ms)
HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(HERE, *a)

# AXB orders: which word is A, X, B and whether X matches the First or Last sound
ORDERS = {
    "AAB": ("a", "a", "b", "first"),
    "ABB": ("a", "b", "b", "last"),
    "BBA": ("b", "b", "a", "first"),
    "BAA": ("b", "a", "a", "last"),
}


# ---------- small wav helpers --------------------------------------------
def read_mono(path):
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != RATE:
            sys.exit(f"{path}: needs mono, 16-bit, {RATE} Hz "
                     f"(got {w.getnchannels()} ch, {8*w.getsampwidth()}-bit, {w.getframerate()} Hz)")
        raw = w.readframes(w.getnframes())
    return list(struct.unpack("<%dh" % (len(raw) // 2), raw))


def write_wav(path, samples, channels=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    clipped = [max(-32767, min(32767, int(round(s)))) for s in samples]
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(struct.pack("<%dh" % len(clipped), *clipped))


def tone(freq, ms, amp=0.3, ramp_ms=10):
    n = int(RATE * ms / 1000)
    r = int(RATE * ramp_ms / 1000)
    out = []
    for i in range(n):
        env = min(1.0, i / r, (n - 1 - i) / r) if r else 1.0
        out.append(amp * 32767 * env * math.sin(2 * math.pi * freq * i / RATE))
    return out


def silence(ms):
    return [0.0] * int(RATE * ms / 1000)


# ---------- placeholder recordings ----------------------------------------
def make_placeholders(pairs, assim_tokens):
    """A distinct two-note beep per word and token, so the pipeline can be tested."""
    words = sorted({r["word_a"] for r in pairs} | {r["word_b"] for r in pairs}
                   | {r["token"] for r in assim_tokens})
    for idx, word in enumerate(words):
        base = 300 + 25 * idx
        for t in (1, 2):
            samples = tone(base, 180) + silence(40) + tone(base * (1.2 + 0.05 * t), 180)
            write_wav(P("audio", "recordings", f"{word}_t{t}.wav"), samples)
    print(f"placeholder recordings: {len(words)} words x 2 tokens")


# ---------- headphone check (Woods, Siegel, Traer & McDermott 2017) --------
def make_headphone_check():
    """Three 200 Hz tones; one is 6 dB quieter (the answer), one is in antiphase
    between the ears. Over loudspeakers the antiphase tone cancels and sounds
    quietest, so loudspeaker listeners tend to pick it; over headphones they
    hear the truly quieter one."""
    trials = []
    layouts = [(q, a) for q in range(3) for a in range(3) if a != q]
    random.Random(7).shuffle(layouts)
    for n, (quiet, anti) in enumerate(layouts):
        left, right = [], []
        for pos in range(3):
            amp = 0.5 * (10 ** (-6 / 20) if pos == quiet else 1.0)
            t = tone(200, 1000, amp=amp, ramp_ms=100)
            left += t
            right += [-s for s in t] if pos == anti else t
            if pos < 2:
                left += silence(500)
                right += silence(500)
        inter = [s for pair in zip(left, right) for s in pair]
        write_wav(P("audio", "headphone", f"hp_{n+1}.wav"), inter, channels=2)
        trials.append({"file": f"audio/headphone/hp_{n+1}.wav", "answer": str(quiet + 1)})
    write_wav(P("audio", "calibration.wav"), tone(440, 2500, amp=0.35, ramp_ms=50))
    return trials


# ---------- AXB triplets and single tokens ---------------------------------
def build(pairs):
    gap = [0] * int(RATE * ISI_MS / 1000)
    axb, assim = [], []
    for r in pairs:
        tok = {}
        for side in ("a", "b"):
            w = r[f"word_{side}"]
            tok[(side, 1)] = read_mono(P("audio", "recordings", f"{w}_t1.wav"))
            tok[(side, 2)] = read_mono(P("audio", "recordings", f"{w}_t2.wav"))
        for order, (sa, sx, sb, answer) in ORDERS.items():
            A, X, B = tok[(sa, 1)], tok[(sx, 2)], tok[(sb, 1)]
            fname = f"audio/axb/{r['pair_id']}_{order}.wav"
            write_wav(P(fname), A + gap + X + gap + B)
            axb.append({
                "file": fname, "contrast": r["contrast"], "pair_id": r["pair_id"],
                "order": order, "answer": answer,
                "word_a": r["word_a"], "word_b": r["word_b"],
                "ipa_a": r["ipa_a"], "ipa_b": r["ipa_b"],
                "x_word": r[f"word_{sx}"],
                "b_onset_ms": round(1000 * (len(A) + len(X) + 2 * len(gap)) / RATE),
                "practice": r["contrast"] == "practice",
            })
    with open(P("stimuli", "assim_tokens.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for t in (1, 2):
                fname = f"audio/assim/{r['phone']}_t{t}.wav"
                write_wav(P(fname), read_mono(P("audio", "recordings", f"{r['token']}_t{t}.wav")))
                assim.append({"file": fname, "phone": r["phone"], "token": r["token"],
                              "ipa": r["ipa"], "rep": t})
    return axb, assim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--placeholders", action="store_true",
                    help="generate beep recordings so the pipeline can be tested")
    args = ap.parse_args()
    with open(P("stimuli", "pairs.csv"), encoding="utf-8") as f:
        pairs = list(csv.DictReader(f))
    with open(P("stimuli", "assim_tokens.csv"), encoding="utf-8") as f:
        assim_tokens = list(csv.DictReader(f))
    if args.placeholders:
        make_placeholders(pairs, assim_tokens)
    hp = make_headphone_check()
    axb, assim = build(pairs)
    with open(P("stimuli", "trials.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by build_stimuli.py. Do not edit by hand.\n")
        f.write("window.STIM = " + json.dumps(
            {"isi_ms": ISI_MS, "headphone": hp, "axb": axb, "assim": assim,
             "placeholders": args.placeholders}, ensure_ascii=False, indent=1) + ";\n")
    n_test = sum(not t["practice"] for t in axb)
    print(f"AXB trials: {n_test} test + {len(axb) - n_test} practice; "
          f"sound-matching tokens: {len(assim)}; headphone trials: {len(hp)}")


if __name__ == "__main__":
    main()
