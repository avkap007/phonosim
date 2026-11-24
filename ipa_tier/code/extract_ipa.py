"""Extract L2-ARCTIC's IPA annotation tier, aligned to the English phone it describes.

L2-ARCTIC annotators added an "IPA" tier recording, in IPA, how each mispronounced phone
was realised (e.g. "t,ʈ,s": English t realised as retroflex ʈ). Each IPA interval shares its
boundaries with a phone interval; the English target is taken from the phones tier
(ARPAbet CPL) by largest time overlap.

Usage:
    python ipa_tier/code/extract_ipa.py scripted /path/to/l2arctic_release_v5.0 ipa_scripted.csv
    python ipa_tier/code/extract_ipa.py suitcase /path/to/suitcase_corpus ipa_suitcase.csv
Scripted annotations are read from the speaker zip files (<SPK>.zip), so nothing needs unzipping.
"""
import csv
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "icphs2027" / "code"))
from extract_substitutions import SPEAKER_L1, clean  # noqa: E402

IPA_TIERS = {"ipa"}


def intervals(text: str) -> dict[str, list[tuple[float, float, str]]]:
    out = {}
    for item in re.split(r"\n\s*item \[\d+\]:", text)[1:]:
        m = re.search(r'name = "([^"]*)"', item)
        if not m:
            continue
        ivs = re.findall(r'xmin = ([\d.eE+-]+)\s*\n\s*xmax = ([\d.eE+-]+)\s*\n\s*text = "((?:[^"]|"")*)"', item)
        out[m.group(1).strip().lower()] = [(float(a), float(b), t) for a, b, t in ivs]
    return out


def tokens(text: str):
    tiers = intervals(text)
    phones = tiers.get("phones", [])
    for name in IPA_TIERS & set(tiers):
        for a, b, lab in tiers[name]:
            lab = lab.strip()
            if not lab:
                continue
            best, ov = None, 0.0
            for pa, pb, pl in phones:
                o = min(b, pb) - max(a, pa)
                if o > ov:
                    best, ov = pl, o
            parts = [x.strip() for x in lab.split(",")]
            rec = {"ipa_raw": lab, "phone_raw": (best or "").strip(), "status": "ok"}
            if len(parts) != 3 or parts[2].lower() not in {"s", "d", "a"}:
                rec["status"] = "malformed"
            else:
                rec.update(canonical_ipa=parts[0], realised_ipa=parts[1].replace("*", ""),
                           tag=parts[2].lower())
            cpl = (best or "").split(",")[0].strip()
            rec["cpl"] = clean(cpl) if cpl else ""
            yield rec


def main(kind: str, src: str, out: str) -> None:
    rows, status = [], Counter()
    if kind == "scripted":
        for spk in SPEAKER_L1:
            with zipfile.ZipFile(Path(src) / f"{spk}.zip") as z:
                for n in sorted(z.namelist()):
                    if "/annotation/" in n and n.endswith(".TextGrid"):
                        for r in tokens(z.read(n).decode("utf-8", "replace")):
                            rows.append({"speaker": spk, "l1": SPEAKER_L1[spk], "utt": Path(n).stem, **r})
    else:
        for f in sorted((Path(src) / "annotation").glob("*.TextGrid")):
            spk = f.stem.upper()
            for r in tokens(f.read_text(encoding="utf-8", errors="replace")):
                rows.append({"speaker": spk, "l1": SPEAKER_L1[spk], "utt": "suitcase", **r})
    cols = ["speaker", "l1", "utt", "cpl", "phone_raw", "ipa_raw", "canonical_ipa",
            "realised_ipa", "tag", "status"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    status.update(r["status"] for r in rows)
    print(f"{len(rows)} IPA entries from {len({r['speaker'] for r in rows})} speakers; status {dict(status)}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
