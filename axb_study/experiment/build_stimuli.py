"""Build the AXB study's audio and trial list.

Run from the experiment folder:

    python3 build_stimuli.py --placeholders   # beeps, to test the pipeline
    python3 build_stimuli.py                  # real recordings

Needs numpy (for the Huggins-pitch headphone check); everything else is standard library.

Inputs
  stimuli/pairs.csv           one row per item: contrast, pair_id, word_a, word_b, ipa,
                              hand_merged / auto_merged (the two L1 maps' predictions),
                              role (practice, catch or test)
  stimuli/assim_tokens.csv    aCa syllables for the sound-matching task
  audio/recordings/<word>_t1.wav, <word>_t2.wav   (and _t3 for sound-matching syllables)
                              mono, 16-bit, 44.1 kHz. Token 1 is used for A and B, token 2
                              for X, so X is never the identical file as its match and
                              listeners must judge the sound, not the recording.

Outputs
  audio/axb/<pair_id>_<order>.wav   one file per AXB trial: A, gap, X, gap, B
  audio/assim/<phone>_t<n>.wav      sound-matching syllables (3 tokens each)
  audio/headphone/hp_<n>.wav        Huggins-pitch headphone check (Milne et al. 2021),
                                    or Woods et al. (2017) antiphase with --headphone-test antiphase
  audio/headphone/hp_example.wav    example interval with the faint tone
  audio/calibration.wav             tone for setting a comfortable volume
  stimuli/trials.js                 trial list read by experiment.js
  stimuli/recording_list.csv        every recording the talker needs to make
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
ASSIM_TOKENS = 3      # recordings per sound-matching syllable (each heard once)
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
    if not os.path.exists(path):
        sys.exit(f"Missing recording: {path} (see stimuli/recording_list.csv)")
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


def ms(samples):
    return round(1000 * len(samples) / RATE)


# ---------- recordings needed ----------------------------------------------
def recordings_needed(pairs, assim_tokens):
    """(word, ipa, n_tokens) for every recording the talker has to make."""
    need = {}
    for r in pairs:
        for s in "ab":
            need[r[f"word_{s}"]] = [r[f"ipa_{s}"], 2]
    for r in assim_tokens:
        need.setdefault(r["token"], [r["ipa"], 0])
        need[r["token"]][1] = max(need[r["token"]][1], ASSIM_TOKENS)
    return sorted((w, ipa, n) for w, (ipa, n) in need.items())


def write_recording_list(needed):
    with open(P("stimuli", "recording_list.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["word", "ipa", "tokens", "files"])
        for w, ipa, n in needed:
            wr.writerow([w, ipa, n, " ".join(f"{w}_t{t}.wav" for t in range(1, n + 1))])


# ---------- placeholder recordings ----------------------------------------
def make_placeholders(needed):
    """A distinct two-note beep per word and token, so the pipeline can be tested."""
    for idx, (word, _, n) in enumerate(needed):
        base = 300 + 7 * idx
        for t in range(1, n + 1):
            samples = tone(base, 180) + silence(40) + tone(base * (1.2 + 0.05 * t), 180)
            write_wav(P("audio", "recordings", f"{word}_t{t}.wav"), samples)
    print(f"placeholder recordings: {len(needed)} words")


# ---------- headphone checks -----------------------------------------------
def make_huggins(n_trials=6, seed=11):
    """Huggins-pitch test (Milne et al. 2021, Behav Res Methods 53:1551-1562).

    Three 1000 ms white-noise intervals with 500 ms gaps. Two are diotic (same noise in
    both ears). In the target, the right ear gets the same noise with a 180 degree phase
    shift over a narrow band (600 Hz +/- 6%). Over headphones this produces a faint
    tone; over loudspeakers it doesn't. Listeners pick the interval with the tone.
    """
    try:
        import numpy as np
    except ImportError:
        sys.exit("The Huggins-pitch check needs numpy: pip install numpy "
                 "(or use --headphone-test antiphase)")
    rng = np.random.default_rng(seed)
    n = RATE  # 1000 ms
    ramp = int(0.02 * RATE)
    env = np.ones(n)
    env[:ramp] = np.sin(np.linspace(0, np.pi / 2, ramp)) ** 2
    env[-ramp:] = env[:ramp][::-1]
    freqs = np.fft.rfftfreq(n, 1 / RATE)
    band = (freqs >= 600 * 0.94) & (freqs <= 600 * 1.06)
    amp = 0.25 * 32767

    def interval(target):
        noise = rng.standard_normal(n)
        noise /= np.max(np.abs(noise))
        left = noise
        if target:
            spec = np.fft.rfft(noise)
            spec[band] *= -1
            right = np.fft.irfft(spec, n)
        else:
            right = noise
        return left * env * amp, right * env * amp

    gap = np.zeros(int(0.5 * RATE))
    trials = []
    answers = [1, 2, 3] * (n_trials // 3)
    random.Random(seed).shuffle(answers)
    for k, ans in enumerate(answers):
        L, R = [], []
        for pos in (1, 2, 3):
            l, r = interval(pos == ans)
            L += [l] + ([gap] if pos < 3 else [])
            R += [r] + ([gap] if pos < 3 else [])
        L, R = np.concatenate(L), np.concatenate(R)
        inter = np.empty(2 * len(L))
        inter[0::2], inter[1::2] = L, R
        write_wav(P("audio", "headphone", f"hp_{k+1}.wav"), inter.tolist(), channels=2)
        trials.append({"file": f"audio/headphone/hp_{k+1}.wav", "answer": str(ans)})
    l, r = interval(True)
    ex = np.empty(2 * n)
    ex[0::2], ex[1::2] = l, r
    write_wav(P("audio", "headphone", "hp_example.wav"), ex.tolist(), channels=2)
    return trials


def make_antiphase():
    """Woods et al. (2017): three 200 Hz tones, one 6 dB quieter (the answer), one in
    antiphase between the ears (sounds quietest over loudspeakers)."""
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
    return trials


# ---------- AXB triplets and single tokens ---------------------------------
def build(pairs, assim_tokens):
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
                "hand_merged": r.get("hand_merged", ""), "auto_merged": r.get("auto_merged", ""),
                "x_onset_ms": ms(A) + ms(gap),
                "b_onset_ms": ms(A) + ms(X) + 2 * ms(gap),
                "b_offset_ms": ms(A) + ms(X) + ms(B) + 2 * ms(gap),
                "role": r["role"],
                "practice": r["role"] == "practice",
            })
    for r in assim_tokens:
        for t in range(1, ASSIM_TOKENS + 1):
            fname = f"audio/assim/{r['phone']}_t{t}.wav"
            write_wav(P(fname), read_mono(P("audio", "recordings", f"{r['token']}_t{t}.wav")))
            assim.append({"file": fname, "phone": r["phone"], "token": r["token"],
                          "ipa": r["ipa"], "rep": t})
    return axb, assim


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--placeholders", action="store_true",
                    help="generate beep recordings so the pipeline can be tested")
    ap.add_argument("--headphone-test", choices=["huggins", "antiphase"], default="huggins")
    args = ap.parse_args()
    with open(P("stimuli", "pairs.csv"), encoding="utf-8") as f:
        pairs = list(csv.DictReader(f))
    with open(P("stimuli", "assim_tokens.csv"), encoding="utf-8") as f:
        assim_tokens = list(csv.DictReader(f))
    needed = recordings_needed(pairs, assim_tokens)
    write_recording_list(needed)
    if args.placeholders:
        make_placeholders(needed)
    hp = make_huggins() if args.headphone_test == "huggins" else make_antiphase()
    write_wav(P("audio", "calibration.wav"), tone(440, 2500, amp=0.35, ramp_ms=50))
    axb, assim = build(pairs, assim_tokens)
    with open(P("stimuli", "trials.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by build_stimuli.py. Do not edit by hand.\n")
        f.write("window.STIM = " + json.dumps(
            {"isi_ms": ISI_MS, "headphone_test": args.headphone_test, "headphone": hp,
             "axb": axb, "assim": assim, "placeholders": args.placeholders},
            ensure_ascii=False, indent=1) + ";\n")
    count = lambda role: sum(t["role"] == role for t in axb)
    print(f"AXB trials: {count('test')} test + {count('catch')} catch + {count('practice')} practice; "
          f"sound-matching: {len(assim)}; headphone ({args.headphone_test}): {len(hp)}; "
          f"recordings needed: {sum(n for *_, n in needed)} files for {len(needed)} words")


if __name__ == "__main__":
    main()
