"""Pick one PHOIBLE inventory per L1 by a fixed rule and save it with its allophones.

Rule (fixed before any Study 3 analysis): among PHOIBLE inventories for the L1, take the
one where the most consonant phonemes list at least one allophone different from the
phoneme itself. Ties go to PHOIBLE's own curated source ("ph").

Usage (PHOIBLE pinned to commit 5f82b9c, the same data as crossl1/INVENTORY_CHECK.md):
    curl -o phoible.csv https://raw.githubusercontent.com/phoible/dev/5f82b9c3fbb0b5c630de20e254c5fdad645e3e56/data/phoible.csv
    python allophone/code/select_inventories.py phoible.csv allophone/data/phoible_selected.csv
"""
import csv
import hashlib
import sys
from collections import defaultdict

L1_ISO = {"arabic": ["arb", "arz"], "hindi": ["hin"], "korean": ["kor"],
          "mandarin": ["cmn"], "spanish": ["spa"], "vietnamese": ["vie"]}


def main(src, out):
    rows = defaultdict(list)
    with open(src, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            for l1, isos in L1_ISO.items():
                if r["ISO6393"] in isos and r["SegmentClass"] == "consonant":
                    rows[(l1, r["InventoryID"])].append(r)

    def info(rs):
        return sum(1 for r in rs if r["Allophones"] not in ("", "NA")
                   and any(a != r["Phoneme"] for a in r["Allophones"].split()))

    chosen = []
    for l1 in L1_ISO:
        cands = [(info(rs), rs[0]["Source"] == "ph", iid, rs) for (l, iid), rs in rows.items() if l == l1]
        n, _, iid, rs = max(cands, key=lambda c: (c[0], c[1]))
        print(f"{l1:11s} PHOIBLE #{iid} ({rs[0]['Source']}: {rs[0]['LanguageName']}, "
              f"{rs[0]['SpecificDialect']}) {len(rs)} consonants, {n} with allophones")
        chosen += [{"l1": l1, "inventory_id": iid, "source": r["Source"],
                    "language": r["LanguageName"], "dialect": r["SpecificDialect"],
                    "phoneme": r["Phoneme"], "allophones": r["Allophones"],
                    "marginal": r["Marginal"]} for r in rs]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(chosen[0]))
        w.writeheader()
        w.writerows(chosen)
    print("phoible.csv sha256", hashlib.sha256(open(src, "rb").read()).hexdigest()[:16])
    print("wrote", out)


if __name__ == "__main__":
    main(*sys.argv[1:3])
