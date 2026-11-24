# AXB study analysis

Written and tested on simulated listeners (Nov 24, 2026) before any real data exist.

```bash
pip install -e "../..[analysis]"            # phonosim, from the repo root
python make_fake_data.py fake_data 20       # optional: simulated listeners (NOT REAL DATA)
python prepare.py results  <JATOS export folder or local CSVs>
Rscript models.R results                    # needs R with lme4
```

## Pre-stated rules

**Exclusions** (listener level, in `prepare.py`):
1. Hindi not reported as first language.
2. Fewer than 10 of 12 catch trials correct. Catch trials are easy n vs s pairs mixed into the main blocks; 10 or more correct by guessing has a 2% chance.
3. Fewer than 90% of the 192 test trials answered.

Listeners who fail the headphone check (Huggins pitch, 6/6, one retry) never reach the AXB task.

**Predictors** for each of the 8 contrasts:

| Contrast | Features differ | Hand map merges | Automatic map merges |
|---|---|---|---|
| v-w | 7/24 | yes (ʋ) | no (f, j) |
| ʒ-dʒ | 2/24 | yes (dʒ) | no (ʃ, dʒ) |
| θ-t | 2/24 | no (t̪ʰ, ʈ) | yes (t̪) |
| ð-d | 2/24 | no (d̪, ɖ) | yes (d̪) |
| v-f | 1/24 | no (ʋ, f) | yes (f) |
| w-ɹ | 5/24 | no (ʋ, r) | yes (j) |
| p-pʰ | 1/24 | no | no |
| ɹ-ɽ | 6/24 | no | no |

Hand map: `icphs2027/data/hindi_inventory_v2.yaml`. Automatic map: `phonosim.l1.project` with `crossl1/data/inventories.yaml`. Both are recomputed by the code; `tests/test_project.py` keeps the automatic merges fixed.

**Primary analysis** (`models.R`): trial-level logistic mixed models, `correct ~ distance (+ map predictor) + (1|listener) + (1|contrast) + (1|item)`. Each map's predictor is tested against the distance-only model by likelihood ratio, and the two maps are compared by AIC.

**Also reported:**
- d′ per listener and contrast. The yes/no formula z(H) − z(F) is used, with H = P("first" | X matches first) and F = P("first" | X matches last), and 0.5 added to the counts. It is not converted to an AXB decision model, so it's for comparing contrasts, not absolute sensitivity.
- Sound matching: the share of choices that match each map's predicted Hindi category, per English sound (`assim_by_phone.csv`).
- Each listener's categorisation overlap per contrast, used as a predictor.
- Secondary: log RT from the end of B, correct trials only, 50 to 3000 ms.

## What the fake-data check showed

The simulated truth is that hand-map merges cost accuracy (−1.5 log-odds) and automatic-map merges cost nothing. The models recovered it: hand −1.64, LRT p < .001; automatic alone p = .53, and AIC favours the hand map.

**Caveat:** with both maps in one model, the automatic predictor came out at −0.46 (p = .012) even though its true effect is zero. With only 8 contrasts, contrast-level noise can look like a map effect. The power simulation in `../power/` was run for the earlier design and should be rerun for this one before relying on the joint model. The per-map likelihood-ratio tests and the AIC comparison are the primary tests.
