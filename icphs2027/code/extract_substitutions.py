"""Extract every annotated phone from L2-ARCTIC's manual annotations into one CSV.

Usage:
    python extract_substitutions.py /path/to/l2arctic_release_v5.0 phones.csv

Reads <corpus>/<SPEAKER>/annotation/*.TextGrid (the hand-annotated subset,
about 150 utterances per speaker). Skips suitcase_corpus (spontaneous speech).

Label conventions (L2-ARCTIC docs, v4.0+):
    correct        "EH1"            -> canonical phone, produced as expected
    substitution   "CPL,PPL,s"      -> CPL expected, PPL perceived
    deletion       "CPL,sil,d"
    addition       "sil,PPL,a"
    unclear        "CPL,err,s"      -> perceived phone not judgeable
    deviation      "AH,AO*,s"       -> PPL with a foreign-accent deviation mark

One output row per non-silence phone segment:
    speaker, l1, utt, cpl, ppl, tag, deviation, err, raw
tag is one of: correct, s, d, a
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

SPEAKER_L1 = {
    "ABA": "Arabic", "SKA": "Arabic", "YBAA": "Arabic", "ZHAA": "Arabic",
    "BWC": "Mandarin", "LXC": "Mandarin", "NCC": "Mandarin", "TXHC": "Mandarin",
    "ASI": "Hindi", "RRBI": "Hindi", "SVBI": "Hindi", "TNI": "Hindi",
    "HJK": "Korean", "HKK": "Korean", "YDCK": "Korean", "YKWK": "Korean",
    "EBVS": "Spanish", "ERMS": "Spanish", "MBMPS": "Spanish", "NJS": "Spanish",
    "HQTV": "Vietnamese", "PNV": "Vietnamese", "THV": "Vietnamese", "TLV": "Vietnamese",
}
SILENCE = {"", "sil", "sp", "spn", "SIL", "SP", "SPN"}


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            text = raw.decode(enc)
            if "TextGrid" in text:
                return text
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Cannot decode {path}")


def read_tier(text: str, tier_name: str) -> list[str]:
    """Return interval labels of one IntervalTier from a long-format TextGrid."""
    items = re.split(r"\n\s*item \[\d+\]:", text)
    for item in items[1:]:
        m = re.search(r'name = "([^"]*)"', item)
        if not m or m.group(1).strip().lower() != tier_name:
            continue
        return re.findall(r'text = "((?:[^"]|"")*)"', item)
    return []


def clean(label: str) -> str:
    return re.sub(r"\d", "", label.strip()).upper()


def parse_label(label: str) -> dict | None:
    lab = label.strip().replace('""', '"')
    if lab in SILENCE:
        return None
    if "," not in lab:
        p = clean(lab)
        return {"cpl": p, "ppl": p, "tag": "correct", "deviation": 0, "err": 0}
    parts = [x.strip() for x in lab.split(",")]
    if len(parts) != 3:
        return {"malformed": True}
    cpl, ppl, tag = parts
    tag = tag.lower()
    if tag not in {"s", "d", "a"}:
        return {"malformed": True}
    deviation = int("*" in ppl)
    ppl = ppl.replace("*", "")
    err = int(ppl.lower() == "err")
    return {
        "cpl": clean(cpl),
        "ppl": "ERR" if err else clean(ppl),
        "tag": tag,
        "deviation": deviation,
        "err": err,
    }


def main(corpus: str, out: str) -> None:
    root = Path(corpus)
    rows, malformed, files = [], Counter(), Counter()
    for spk_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        spk = spk_dir.name.upper()
        if spk not in SPEAKER_L1:
            continue
        ann = spk_dir / "annotation"
        for tg in sorted(ann.glob("*.[Tt]ext[Gg]rid")):
            files[spk] += 1
            labels = read_tier(read_text(tg), "phones")
            for lab in labels:
                rec = parse_label(lab)
                if rec is None:
                    continue
                if rec.get("malformed"):
                    malformed[spk] += 1
                    continue
                rows.append({"speaker": spk, "l1": SPEAKER_L1[spk], "utt": tg.stem,
                             "raw": lab.strip(), **rec})
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["speaker", "l1", "utt", "cpl", "ppl", "tag",
                                           "deviation", "err", "raw"])
        w.writeheader()
        w.writerows(rows)

    tags = Counter(r["tag"] for r in rows)
    print(f"Files read: {sum(files.values())} across {len(files)} speakers")
    for spk in sorted(files):
        print(f"  {spk:6s} {SPEAKER_L1[spk]:10s} {files[spk]:4d} files")
    print(f"Phone segments: {len(rows)}  tags: {dict(tags)}")
    print(f"Malformed labels skipped: {sum(malformed.values())} {dict(malformed)}")
    print("Docs report 14,098 subs / 3,420 dels / 1,092 adds for the scripted set;"
          " counts should land close to that.")
    print(f"Wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
