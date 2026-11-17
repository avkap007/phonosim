# Cross-L1 analysis plan: frozen specification

**Status:** frozen Mon Nov 16, 2026, before `analyze_crossl1.py` was run on the real
L2-ARCTIC annotations. The commit that adds this file, `data/inventories.yaml`,
`code/analyze_crossl1.py` and `phonosim/l1/project.py` comes before the run.
`results.json` records the SHA-256 of the inventories and code.

## Question
The Oct 7 study showed that a hand-built Hindi layer predicts Hindi speakers'
substitutions (driven by v/w). This study asks whether the layer generalises:
if the L1 mapping is computed **automatically** from an L1 consonant inventory, does
each L1's projected distance predict that L1 group's substitutions better than the
other groups' projections do? L2-ARCTIC has six L1 groups of four speakers each.

## What was already known when this plan was written (disclosure)
- All Oct 7 Hindi results, including the v/w rates by L1 (`icphs2027/results/vw_by_l1.csv`:
  Mandarin speakers also show V->W).
- The projection tables printed by `phonosim.l1.project` for all six inventories.
  No inventory entry or rule was changed after seeing them, apart from notation
  (breathy-voiced stops rewritten so PanPhon can parse them).
- **Known before the run:** the automatic Hindi projection agrees with the hand-built
  v2 table on 17 of 24 English consonants. It does NOT merge v and w (v -> f, w -> j),
  because PanPhon puts v 1 feature from f and 6 features from ʋ. So the automatic layer
  cannot reproduce the v/w result. This is reported as a finding, not fixed.
- No substitution counts for the non-Hindi groups beyond the v/w table were inspected.

## Predictors
- `dist_english`: flat feature distance between two English consonants (as on Oct 7).
- `comp_<L1>` = dist_english - distance between the two consonants' nearest phonemes
  in that L1's inventory. Projection rule: fewest differing PanPhon features; ties broken
  by PanPhon stock weights; remaining ties averaged. Inventories and their inclusion
  rules are in `data/inventories.yaml`.
- `comp_matched`: `comp_<L1>` for the speaker's own L1.
- `comp_others`: mean of `comp_<L1>` over the five other L1s.

## Data, unit, model
Same as the Oct 7 plan: shared utterances (annotated in >= 4 L1 groups), 24 consonants,
`err` excluded, `*` deviations counted as substitutions. Unit: speaker x ordered pair.
Count model with log exposure offset, negative binomial by ML with the same Poisson
fallback as Oct 7, SEs clustered by speaker (24 clusters).

## Primary tests
- **P1 (matched vs mismatched):** all 24 speakers,
  `count ~ dist_english + comp_matched + comp_others`.
  Prediction: `comp_matched` IRR > 1 with `comp_others` in the model.
- **P2 (permutation):** refit `count ~ dist_english + comp_assigned` (Poisson) under all
  720 ways of assigning the six L1 predictors to the six speaker groups. Report where
  the true assignment's deviance ranks. Prediction: true assignment in the best 5%.
- **P3 (6 x 6 matrix):** for each speaker group and each L1 predictor, dAIC from adding
  the predictor to `dist_english`. Prediction: each group's own L1 is its best predictor.
  A predictor only counts as helping when its IRR is above 1 (the predicted direction).
  Report how many of the six rows that holds for.

## Hindi: automatic vs hand-built
H1 and H2 from the Oct 7 plan, run with the automatic Hindi predictor and with the
hand-built v2 predictor, side by side.

## Robustness (report all, whatever they show)
- P1 with V<->W pairs dropped.
- P1 leaving out each L1 group in turn.
- P1 with `--no-deviations`; P1 with the L1-targeted sentences included.
- P1 and P3 with the contrastive-feature projection (Yeo et al. 2026).
- P1 and P3 with the alternative varieties (Cairene Arabic, Castilian Spanish,
  Southern Vietnamese).

## Known limits stated in advance
- Four speakers per L1; their dialects are undocumented.
- Inventories were entered from standard references from memory and need checking
  against the originals before the thesis cites them.
- ARPAbet labels cannot show non-English realisations, so any L1 effect that lives in
  place or aspiration detail is invisible here (see the Oct 7 limits).
- Nearest-neighbour projection in a phonological feature space is a model of
  assimilation, not a measurement of it. Where it disagrees with the literature
  (Hindi v/w), the listening study designed in `axb_study/` is what would settle it.

## Reporting
Every estimate above is reported whether or not it supports the prediction.
