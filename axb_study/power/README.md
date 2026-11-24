# Power and design analysis for the AXB study

Prospective, simulation-based design analysis in the style of Kirby and Sonderegger (2018). It answers Dr. Wang's REB comment: "how is this sample size determined?"

## Bottom line

- **A large L1 effect is detected reliably with 15 to 20 listeners.** "Large" means merged contrasts like v/w drop from 90% to about 67% correct. Power is 92 to 99% across every design tested, and significant estimates are not inflated (Type M ≈ 1.0).
- **A small L1 effect (90% to about 81%) is detected only about half the time, and more listeners barely help.** Power stays at 44 to 60% from 15 to 30 listeners. When it is significant, the estimate overstates the true effect by 30 to 40% (Type M 1.3 to 1.4).
- **The limit is the contrasts, not the listeners.** Under the v2 Hindi table only two English pairs are merged into one Hindi category (v/w and ʒ/dʒ). Contrast-level noise therefore can't be averaged out, however many people take part.
- **Three contrasts can't answer the research question.** With the locked set (p/pʰ, v/w, ɽ/ɹ), contrast-to-contrast differences can't be separated from the L1 effect. The model then credits anything special about v/w to "L1": 3 to 10% of significant results even have the wrong sign. Use the 8-contrast set.

**Recommendation:** recruit up to 25 to get 20 usable Hindi-L1 listeners. Use 8 contrasts × 6 minimal pairs × 4 AXB orders = 192 test trials (about 18 minutes). Treat the L1 estimate as a noisy proof-of-concept estimate and report it with its CI whatever it shows. The cheapest power gain is the sound-matching task: per-listener assimilation scores give the L1 predictor variation within each contrast, not just between contrasts.

## Results (200 simulated experiments per row)

| L1 effect (logit) | Merged-contrast accuracy | Contrasts | Listeners | Power | Type M | Type S |
| --- | --- | --- | --- | --- | --- | --- |
| −1.5 (large) | ~67% | 8 | 15 | 0.92 | 1.02 | 0 |
| −1.5 (large) | ~67% | 8 | 20 | 0.97 | 0.98 | 0 |
| −1.5 (large) | ~67% | 8 | 30 | 0.99 | 0.99 | 0 |
| −1.5 (large) | ~67% | 12 | 20 | 0.98 | 1.03 | 0 |
| −0.75 (small) | ~81% | 8 | 15 | 0.48 | 1.40 | 0.01 |
| −0.75 (small) | ~81% | 8 | 20 | 0.44 | 1.38 | 0.01 |
| −0.75 (small) | ~81% | 8 | 30 | 0.58 | 1.32 | 0.01 |
| −0.75 (small) | ~81% | 12 | 20 | 0.60 | 1.30 | 0 |
| −0.75 (small) | ~81% | 3 (locked set) | 20 | 0.68* | 1.48 | 0.10 |

\*Not trustworthy: with 3 contrasts there is no contrast random effect, so the test is anticonservative. All 24 rows are in `power_results.csv`.

## Assumptions (all on the logit scale, all editable at the top of `power_sim.R`)

- **Non-merged contrast of average distance:** 90% correct (intercept 2.2).
- **Distance effect:** +0.2 per SD of PanPhon distance (farther pairs are slightly easier).
- **Variability:** listener SD 0.6, listener-by-merged slope SD 0.6, contrast SD 0.4, minimal-pair SD 0.3.
- **Contrast distances:** from phonosim (`icphs2027/results/pair_predictors.csv`).
- **Merged coding:** from `hindi_inventory_v2.yaml`.
- **Test:** likelihood-ratio test of distance-only against distance + merged, α = .05. GLMMs fitted with lme4 (`glmer`, `nAGQ = 0` for speed).

These effect sizes are guesses, because there is no published AXB data for Hindi listeners on these English contrasts. That is why two effect sizes are shown, and why the pilot (2 to 3 people) should be used to check the 90% baseline.

Run it again with `Rscript power_sim.R 200 2` (200 simulations per cell, 2 cores, about 45 minutes).
