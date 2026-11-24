# Study 3 analysis plan: frozen specification

**Status:** frozen on Tue Nov 24, 2026, before `analyze_allophone.py` was run on any real
L2-ARCTIC data (scripted or unscripted). The commit that adds this file,
`phonosim/l1/allophone.py`, `allophone/data/phoible_selected.csv` and `allophone/code/`
comes before both runs. `results.json` records SHA-256 hashes of the layer, data and script.

## Question
Study 2 found that an L1 layer computed from each L1's *phonemes* does not pick out each
speaker group's own L1, and that the automatic Hindi layer does not merge v and w
(PanPhon puts English v one feature from Hindi f and six from Hindi ʋ). The diagnosis:
listeners compare new sounds with how native sounds are *pronounced*, not with phoneme
symbols. Study 3 tests that diagnosis: if English consonants are projected onto each L1's
pronounced variants (allophones, from PHOIBLE) and mapped back to the variant's phoneme,
does the layer (a) predict Hindi speakers' substitutions specifically, and (b) predict each
L1 group's own substitutions better than the other groups' layers?

## The layer (fixed without looking at any substitution data)
- **Source:** PHOIBLE (Moran & McCloy 2019), commit 5f82b9c, the same data as
  `crossl1/INVENTORY_CHECK.md`. Nothing is entered by hand.
- **Selection rule:** for each L1, the PHOIBLE inventory in which the most consonant phonemes
  list at least one allophone different from the phoneme itself; ties to PHOIBLE's own
  source ("ph"). Result (`allophone/code/select_inventories.py`): Hindi #2190 (ph, Standard
  Hindi; 19 phonemes with allophones), Korean #2197 (ph; 18), Spanish #164 (spa; 15),
  Mandarin #16 (spa; 13), Vietnamese #15 (spa; 7), Arabic #2157 (ph; 1).
- **Projection:** each English consonant goes to the nearest variant by number of differing
  PanPhon features, ties broken by PanPhon stock weights; its category is the variant's
  phoneme; remaining ties are kept and distances average over them (same rule as Study 2,
  applied to variants instead of phonemes).
- **Parsing:** length, unreleased and retraction marks dropped (geminates and unreleased stops
  collapse onto the plain segment); voicing diacritics rewritten as the voiced or voiceless
  counterpart (PanPhon ignores them, so [s̬] would otherwise read as [s]). Symbols PanPhon
  cannot parse are skipped and listed in `results.json` (Arabic d̪ʒ, xʀ̥; Korean lʎ;
  Vietnamese ŋm). Marginal phonemes excluded.
- **Glide rule:** Study 2's inclusion rule 2 (glides j, w count even where the description
  treats them as parts of vowels) is applied: j and w are added as their own categories when
  the frozen Study 2 inventory has them and the PHOIBLE source does not. Only Korean
  (#2197 lists no glides) is affected.

## What was already known when this plan was written (disclosure)
- All Study 1 and Study 2 results on the scripted data. The allophone idea was motivated by
  them (Hindi v/w), so the scripted data are not an independent test of it.
- The projection tables of the new layer for all six L1s (no outcome data involved). Under
  it, English v and w both project to Hindi ʋ; Hindi differs from the Study 2 layer on 4 of
  24 English consonants, Spanish on 12, Arabic on 8, Mandarin on 6, Korean on 4,
  Vietnamese on 1.
- The pipeline was tested only on the synthetic corpus from `icphs2027/code/make_fake_corpus.py`.
- For the unscripted ("suitcase") data: only the README and the file names. 22 speakers (ASI
  and SKA did not record it), so **3 Hindi speakers** and 3 Arabic; about 9,458 phones and
  1,673 substitutions in total. No annotation was opened.
- No layer choice was changed after any analysis: there are no tuned parameters.

## Data
1. **Unscripted narratives (held-out test).** `suitcase_corpus/annotation/<spk>.TextGrid`,
   extracted with `allophone/code/extract_suitcase.py` (same label conventions as Study 1).
   All utterances used (one narrative per speaker).
2. **Scripted sentences (reported alongside, not independent).** `icphs2027/phones.csv`, the
   same subset as Studies 1 and 2 (utterances annotated in at least 4 L1 groups).

Unit, outcome, exposure and model exactly as Study 2: speaker x ordered consonant pair,
substitution counts with the speaker's tokens of X as exposure, negative binomial by ML
with Poisson fallback, SEs clustered by speaker. 24 consonants, `err` excluded, `*`
deviations counted as substitutions.

## Primary tests (unscripted data)
- **P1 (matched vs mismatched):** `count ~ dist_english + comp_matched + comp_others` with
  allophone-layer compression. Prediction: `comp_matched` IRR > 1.
- **P2 (permutation):** all 720 assignments of the six layers to the six groups; prediction:
  true assignment in the best 5%.
- **P3 (6 x 6):** own L1 the best predictor for each group (count of rows).
- **H2 (Hindi-specific):** `count ~ (dist_english + comp_Hindi) * is_hindi`; prediction:
  interaction IRR > 1. H1 (Hindi speakers only) reported with it.

## Level comparison (both datasets)
The same tests with (a) a **phoneme-only layer from the same PHOIBLE inventories** (isolates
the effect of adding allophones from the change of source) and (b) the **frozen Study 2
layer**; Hindi H1/H2 also with the hand-built table v2. Reported side by side; the
prediction is that the allophone layer beats both phoneme-level layers on P1 and Hindi H2.

## Robustness (report all, whatever they show)
P1 with V<->W pairs dropped; P1 without deviation-marked substitutions; P1 leaving out each
L1 group in turn.

## Descriptive
V and W target-level rates (partner substitution or accented distortion) by L1 and by
speaker, as in Study 1.

## Known limits stated in advance
- **Low power on the held-out data.** About 1,673 substitutions across 22 speakers, roughly
  a tenth of the scripted set, and 3 Hindi speakers. A null result here is weak evidence;
  intervals will be wide (Kirby & Sonderegger 2018).
- Same speakers as the scripted data: the unscripted test is new speech, not new people.
- PHOIBLE coverage is uneven: Arabic has allophones for only one phoneme, so its layer is
  nearly the phoneme layer; the selected Spanish source is Castilian-type and treats
  [β ð ɣ] as categories, while L2-ARCTIC's Spanish speakers' varieties are undocumented.
- ARPAbet labels still cannot show non-English realisations (Study 1 limits).
- Nearest-variant projection is a model of assimilation, not a measurement of it.

## Reporting
Every estimate above is reported whether or not it supports the prediction, for both
datasets, labelled held-out (unscripted) or non-independent (scripted).
