# Study 1c analysis plan: L1 layers against L2-ARCTIC's IPA tier (frozen specification)

**Status:** frozen on Tue Nov 24, 2026, before `extract_ipa.py` or `analyze_ipa.py` was run on
the corpus. The commit adding this file and `ipa_tier/code/` comes before both.

## Why
Studies 1 to 3 used ARPAbet labels, which can only show substitutions between English
phonemes; for Hindi speakers that is mainly v/w. L2-ARCTIC annotators also wrote an "IPA"
tier recording how each mispronounced phone was realised (e.g. `t,ʈ,s`: English t realised
as retroflex ʈ). All 24 scripted speakers (259 to 1,398 entries each) and all 22 unscripted
speakers have it. This lets the layers be tested on realisations ARPAbet cannot show:
retroflex, dental, unaspirated, [ʋ].

## Question
Does each L1 layer predict how that L1 group's speakers realise English consonants better
than the other groups' layers do, with v and w excluded? And does the hand-built Hindi table
predict Hindi speakers' realisations, specifically?

## Measure
For each IPA-annotated consonant substitution (tag `s`; English target from the aligned phones
tier, one of the 24 consonants; realised segment parsed by PanPhon), and each layer L:
`d_L` = mean number of differing PanPhon features between the realised segment and L's
predicted category for the English consonant (averaged over tied categories). Lower is better.
Realisations PanPhon cannot parse as one segment (and `err`, `sil`) are excluded and reported.

Layers: the Study 3 allophone layer (primary), the frozen Study 2 phoneme layer, the hand-built
Hindi table v2, and the English target itself as a baseline (d_english).

## Data
- Primary: scripted annotations, the shared utterances of Studies 1 and 2 (annotated in at
  least 4 L1 groups, defined from `icphs2027/phones.csv`).
- Replication (held-out for this question): unscripted suitcase narratives.
- Secondary: scripted, all annotated utterances.

## Primary tests (allophone layer, v and w excluded)
- **P1:** mean over tokens of (mean d under the other five L1 layers minus d under the own-L1
  layer). Prediction: > 0, with a 95% speaker-cluster bootstrap CI (2,000 resamples of
  speakers within L1 groups) above 0.
- **P2:** total d under each of the 720 assignments of layers to groups; prediction: true
  assignment in the best 5%.
- **P3:** for each group, the layer with the lowest mean d; report how many groups' own layer wins.

## Hindi tests (v and w excluded)
- Mean d for Hindi speakers' tokens under the hand table, allophone layer, Study 2 layer and the
  English baseline, with bootstrap CIs. Prediction: hand table < English baseline.
- Specificity: (d_english - d_hand) for Hindi tokens minus the same for other groups' tokens.
  Prediction: > 0 (CI above 0).

## Secondary (report all)
The same tests with v and w included; P1 to P3 with the Study 2 layer; scripted with all
utterances. Descriptive: the four most common realisations of each English consonant, Hindi
versus the other five groups.

## What was known before freezing (disclosure)
- The IPA content of one utterance (ASI arctic_a0003, 12 entries, e.g. t realised as ʈ and
  unaspirated t, n as ɳ, θ as ʈ), seen while checking the Allosaurus recogniser for Study 4.
- Entry counts per speaker for the IPA tier (scripted and unscripted); no content.
- Study 1b accent-mark rates (Hindi speakers' marks on t, d, p, l, n).
- All Study 1 to 3 results. The pipeline was tested only on synthetic data.

## Known limits stated in advance
- The IPA tier records only tokens the annotators judged mispronounced, and annotators differ
  in how much detail they wrote (Study 1b showed annotator differences in accent marking).
- The realised segment is an annotator's transcription, not an acoustic measurement.
- Feature distance treats all features alike; d is a coarse measure of fit.
- Few speakers per L1 (4 scripted; 3 or 4 unscripted).

## Reporting
Every estimate above is reported, for both datasets, whether or not it supports the prediction.
