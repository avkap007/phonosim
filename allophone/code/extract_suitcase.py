"""Extract every annotated phone from L2-ARCTIC's unscripted "suitcase" narratives.

Usage:
    python allophone/code/extract_suitcase.py /path/to/suitcase_corpus phones_suitcase.csv

<suitcase_corpus>/annotation/<speaker>.TextGrid, one long narrative per speaker (22
speakers; ASI and SKA did not record it). Same label conventions and output columns as
icphs2027/code/extract_substitutions.py, which this reuses; utt is "suitcase".
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
from extract_substitutions import SPEAKER_L1, parse_label, read_text, read_tier  # noqa: E402


def main(corpus: str, out: str) -> None:
    ann = Path(corpus) / "annotation"
    rows, malformed = [], Counter()
    files = sorted(ann.glob("*.[Tt]ext[Gg]rid"))
    for tg in files:
        spk = tg.stem.upper()
        if spk not in SPEAKER_L1:
            sys.exit(f"Unknown speaker file: {tg.name}")
        for lab in read_tier(read_text(tg), "phones"):
            rec = parse_label(lab)
            if rec is None:
                continue
            if rec.get("malformed"):
                malformed[spk] += 1
                continue
            rows.append({"speaker": spk, "l1": SPEAKER_L1[spk], "utt": "suitcase",
                         "raw": lab.strip(), **rec})
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["speaker", "l1", "utt", "cpl", "ppl", "tag",
                                           "deviation", "err", "raw"])
        w.writeheader()
        w.writerows(rows)
    tags = Counter(r["tag"] for r in rows)
    print(f"Files: {len(files)}; speakers by L1: {dict(Counter(SPEAKER_L1[f.stem.upper()] for f in files))}")
    print(f"Phone segments: {len(rows)}  tags: {dict(tags)}")
    print(f"Malformed labels skipped: {sum(malformed.values())} {dict(malformed)}")
    print("README reports about 9,458 phone segments and 1,673 substitutions; counts should be close.")
    print(f"Wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
