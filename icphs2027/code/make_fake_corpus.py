"""Build a small fake L2-ARCTIC-shaped corpus to test the pipeline end to end.

NOT real data. Hindi speakers get injected v<->w and z->JH substitutions so the
analysis has something to find; every speaker gets distance-driven noise.
"""
import random
import sys
from pathlib import Path

from extract_substitutions import SPEAKER_L1
from analyze import ARPA_TO_IPA, CONS
from phonosim.similarity import get_similarity

VOWELS = ["AA1", "AE1", "AH0", "EH1", "IH1", "IY1", "UW1", "OW1"]
random.seed(1)
DIST = {(x, y): get_similarity(ARPA_TO_IPA[x], ARPA_TO_IPA[y]).n_differ
        for x in CONS for y in CONS if x != y}
HINDI_SWAPS = {"V": "W", "W": "V", "Z": "JH", "DH": "D"}


def textgrid(labels):
    n, t = len(labels), 0.1
    parts = [f'File type = "ooTextFile"\nObject class = "TextGrid"\n\nxmin = 0 \nxmax = {n*t} \n'
             f'tiers? <exists> \nsize = 1 \nitem []: \n    item [1]:\n        class = "IntervalTier" \n'
             f'        name = "phones" \n        xmin = 0 \n        xmax = {n*t} \n'
             f'        intervals: size = {n} \n']
    for i, lab in enumerate(labels):
        parts.append(f'        intervals [{i+1}]:\n            xmin = {i*t:.2f} \n'
                     f'            xmax = {(i+1)*t:.2f} \n            text = "{lab}" \n')
    return "".join(parts)


def utterance(spk_is_hindi):
    labels = ["sil"]
    for _ in range(28):
        if random.random() < 0.45:
            labels.append(random.choice(VOWELS))
            continue
        x = random.choice(CONS)
        if spk_is_hindi and x in HINDI_SWAPS and random.random() < 0.35:
            labels.append(f"{x},{HINDI_SWAPS[x]}*,s")
        elif spk_is_hindi and x in ("V", "W") and random.random() < 0.3:
            labels.append(f"{x},{x}*,s")  # accented distortion ([ʋ])
        elif random.random() < 0.04:
            ys = [y for y in CONS if y != x]
            w = [2.0 ** -DIST[(x, y)] for y in ys]
            labels.append(f"{x},{random.choices(ys, w)[0]},s")
        elif random.random() < 0.01:
            labels.append(f"{x},sil,d")
        else:
            labels.append(x)
    return labels + ["sil"]


def main(root):
    root = Path(root)
    for spk, l1 in SPEAKER_L1.items():
        d = root / spk / "annotation"
        d.mkdir(parents=True, exist_ok=True)
        ids = [f"arctic_a{i:04d}" for i in range(1, 101)]
        ids += [f"arctic_b{l1[:2].lower()}{i:02d}" for i in range(50)]
        for u in ids:
            (d / f"{u}.TextGrid").write_text(textgrid(utterance(l1 == "Hindi")))
    print("fake corpus at", root)


if __name__ == "__main__":
    main(sys.argv[1])
