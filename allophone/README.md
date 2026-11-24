# Study 3: pronunciation-level (allophone) L1 layer

Projects English consonants onto each L1's pronounced variants from PHOIBLE and maps each
variant back to its phoneme (`phonosim/l1/allophone.py`). Frozen plan: `ANALYSIS_PLAN.md`.

```bash
# 1. inventories (already in data/; rerun only to check)
python allophone/code/select_inventories.py phoible.csv allophone/data/phoible_selected.csv
# 2. unscripted data (unzip suitcase_corpus.zip from L2-ARCTIC v5.0 first)
python allophone/code/extract_suitcase.py /path/to/suitcase_corpus phones_suitcase.csv
# 3. analysis
PYTHONPATH=. python allophone/code/analyze_allophone.py phones_suitcase.csv allophone/results_suitcase --data suitcase
PYTHONPATH=. python allophone/code/analyze_allophone.py icphs2027/phones.csv allophone/results_scripted --data scripted
```
Results folders are not committed.
