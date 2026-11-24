# Study 1b analysis plan: accent marks beyond v/w (frozen specification)

**Status:** frozen on Tue Nov 24, 2026, before `analyze_marks.py` was run on real data. The
commit adding this file and `accentmarks/code/` comes before the run.

## Why
Studies 1 to 3 can only see substitutions between English phonemes, because L2-ARCTIC's
labels are ARPAbet. For Hindi speakers the main such pattern is v/w. Most other predictions
of the hand-built Hindi table (v2) concern sounds that stay inside an English category:
retroflex t and d, dental aspirated th, unaspirated p/t/k. Annotators could flag these only
as an accented version of the same phoneme, written `X,X*,s` ("accent mark"). Studies 1 to 3
never analysed these same-phoneme marks.

## Question
Do Hindi speakers' accent marks concentrate on the consonants that table v2 predicts differ
from their Hindi counterpart, more than other L1 groups' marks do on the same consonants,
with v and w excluded?

## Predictor (fixed by table v2, frozen Oct 7)
`pred_diff` = 1 if v2 types the consonant `exists_different_cues` or `no_equivalent`,
0 if `exists_similar`. With V and W excluded: pred_diff = 1 for P, T, D, K, HH, NG, R, TH,
DH, ZH (10); 0 for B, G, F, S, Z, SH, CH, JH, M, N, L, Y (12).

## Data, unit, outcome
- Primary: scripted annotations, the shared utterances used in Studies 1 and 2
  (annotated in at least 4 L1 groups), 24 speakers.
- Replication: unscripted suitcase narratives (22 speakers; 3 Hindi). Small (122 marks in
  total across all groups), reported as such.
- Unit: speaker x English consonant X. Outcome: tokens of X labelled `X,X*,s`.
  Exposure: tokens of X (correct, substituted or deleted), as in Study 1.
- Consonants with no accent marks for any speaker in a dataset are dropped from that
  dataset's models (they carry no information about the interaction and make the
  consonant fixed effect diverge). Which ones were dropped is reported.

## Primary test
Poisson GLM with log exposure offset, SEs clustered by speaker:
`marks ~ C(X) + is_hindi + is_hindi:pred_diff`.
Consonant fixed effects absorb how often each consonant is marked for everyone, so the key
term `is_hindi:pred_diff` asks whether Hindi speakers' excess marking (over the other five
groups, consonant by consonant) is larger on predicted-different consonants.
Prediction: IRR > 1. V and W excluded.

## Secondary and robustness (report all)
- The same model with V and W included.
- `pred_diff` split into its two types (different cues; no equivalent).
- Scripted data with the L1-targeted utterances included.
- Descriptive: mark rate per consonant for Hindi vs the other five groups, both datasets.

## What was known before freezing (disclosure)
- All Study 1 to 3 results, including v/w accent-mark counts by L1 (Study 1 secondary) and
  substitution rates such as Hindi k->g and th->t.
- Pooled totals of same-phoneme accent marks across all L1s (1,004 scripted; 122 unscripted),
  checked for feasibility. No breakdown by L1 or consonant was looked at.

## Known limits stated in advance
- Accent marks are annotators' judgements, and marking practice may differ by consonant and
  annotator; consonant fixed effects and the other-L1 comparison only partly control this.
- A mark says a token sounded accented, not how; it cannot confirm retroflexion or dentality.
- Four Hindi speakers (three in the unscripted set); speaker-clustered SEs with 24 clusters.

## Reporting
Every estimate is reported whether or not it supports the prediction.
