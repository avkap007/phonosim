# ICPhS 2027 submission kit (deadline Fri Oct 9, 2026)

## Folder
- `ANALYSIS_PLAN.md` - frozen spec + decision log. Commit it first.
- `data/hindi_inventory_v2.yaml` - literature-audited Hindi table (primary), with sources.
- `data/hindi_inventory_v1.yaml` - original Term 1 table (sensitivity only).
- `code/extract_substitutions.py` - L2-ARCTIC annotation TextGrids -> one CSV of phones.
- `code/analyze.py` - models, table, figure, results.json.
- `code/make_fake_corpus.py` - synthetic corpus for testing the pipeline (NOT real data).
- `paper/main.tex`, `paper/refs.bib` - 4-page draft in the ICPhS template.

## Setup (once)
```
python -m venv .venv && source .venv/bin/activate
pip install panphon pyyaml pandas statsmodels scipy matplotlib
pip install -e /path/to/phonosim
```
(If `pip install panphon` fails building `unicodecsv`, use `uv pip install panphon`.)

## Run
```
cd code
python extract_substitutions.py /path/to/l2arctic_release_v5.0 phones.csv
python analyze.py phones.csv ../results
python analyze.py phones.csv ../results_nodev --no-deviations
python analyze.py phones.csv ../results_all  --include-l1-specific
```
Checks after extraction:
- 24 speakers, ~150 files each (YBAA has 149).
- Substitution count near the documented 14,098; malformed labels near zero.
- "Shared utterances" near 100. If not, change `--min-groups`.

## Paper
1. Make an Overleaf project from the official ICPhS LaTeX zip, upload `main.tex` and
   `refs.bib`, and set the compiler to **XeLaTeX** (Menu -> Compiler).
2. Upload `results/fig_compression.pdf` and `results/table_top_pairs.tex`.
3. Replace every bold **[XX]** with numbers from `results/results.json`.
   Rewrite the bracketed claims (e.g. "[more than / no more than]") to match what you find.
4. Before submitting: no names, no GitHub link (use anonymous.4open.science),
   `refs.bib` page range for Ohala (1999) checked, 4 pages + 1 of references.

A test compile with stand-in layout ends the body partway down page 3, leaving about a
page for results prose.

Order of operations: commit `ANALYSIS_PLAN.md` + `data/` + `code/` to GitHub FIRST, then run.
