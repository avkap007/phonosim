# Term 1 writeup: phonosim toolkit

## What this term was for

This term was for building the first version of the toolkit, not for running the perception study. The study (AXB with Hindi-L1 listeners), ethics, and a fuller Hindi-aware layer are for next term.

The package is called phonosim. It sits on top of existing libraries. It does not reimplement feature tables or grapheme-to-IPA rules.

## What we used

- PanPhon (Mortensen et al., 2016): maps an IPA symbol to a bundle of articulatory features and can score how far two sounds are from each other.
- Epitran: turns writing into IPA. Hindi (hin-Deva) works directly. English (eng-Latn) needs an extra speech tool (flite). If that tool is missing, English falls back to g2p_en (CMU ARPABET to IPA).
- g2p_en: English fallback for word-to-IPA.
- pytest: unit tests for known sound pairs.

We wrap PanPhon and Epitran. We do not fork them.

## What changed from the original proposal

The proposal assumed that sounds which are close in features would be the hard ones, and that /v/ vs /w/ was a small featural distance. After using PanPhon that is not true.

- PanPhon uses 24 features (22 articulatory plus 2 tone features), not about 21.
- /p/ vs /pʰ/ differ on 1 feature (spread glottis, i.e. aspiration). Featurally close.
- /v/ vs /w/ differ on 7 features. Featurally far, not close. Hindi listeners still mix them up because Hindi treats both as one category (ʋ).
- The proposal wrote /r/ for English r. In IPA, /r/ is a trill. English r is /ɹ/. /ɽ/ vs /r/ is 1 feature apart; /ɽ/ vs /ɹ/ is 6. We locked English r as /ɹ/.
- The proposal title mentioned Mandarin; the body used Hindi. Target L1 is now Hindi.
- PanPhon distance does not know the listener’s first language. The same /v/–/w/ number comes out for everyone. An L1 layer has to sit on top.
- PanPhon’s default weights treat aspiration (sg) and voicing as cheap (0.125). That is a developer judgment for NLP, not a Hindi listener model.

So the research question is no longer “does small distance predict confusion.” It is: when does feature distance help, and when does L1 category mapping have to explain the rest?

Locked contrasts for the later study:

- /p/ vs /pʰ/: close in features (1/24). Hindi has aspiration, but the cues are not identical to English. Distance should help.
- /v/ vs /w/: far in features (7/24), but one Hindi category. Distance predicts easy; L1 predicts hard. This is the main failure case for a distance-only score.
- /ɽ/ vs /ɹ/: far in features (6/24). No clean English-ɹ match in Hindi. Second L1-driven case.

## What is actually built (v0.1)

Working Python package in this folder:

- normalize_ipa: fixes common input issues (e.g. tʃ without a tie bar would otherwise split into two sounds).
- get_features: feature bundle for one IPA symbol.
- get_similarity: three modes
  - hamming: flat count (every differing feature = 1)
  - panphon: PanPhon’s built-in weights (baseline)
  - hindi: our first-pass Hindi cue-weight file (starting values, not fitted to data)
- to_ipa: spelling to IPA (Epitran, with English fallback).
- map_to_l1 / predict_difficulty: first-pass Hindi table plus a combined “distance + L1” readout.
- minimal_pair_generator and stimulus_export: starter path to PsychoPy CSV / jsPsych JSON.

Tests cover the three locked pairs, affricate normalization, and a small G2P check. A demo script prints the same worked examples.

The Hindi pieces that exist now are a starter, not the finished layer:

- hindi_inventory.yaml: hand-made English-to-Hindi category table (merged, exists with different cues, no equivalent).
- hindi_cue_weights.yaml: we upweight aspiration-related features (sg, voi) relative to PanPhon. These numbers are theory-seeded priors. They are not estimated from listener data.

## What I learned

- PanPhon is built for NLP (loanwords, name matching), not for predicting L2 listening difficulty.
- Flat distance is just a count. Weighted distance is still not “how Hindi speakers listen.” PanPhon’s weights make aspiration look even cheaper.
- Cue weighting (Dr. Wang): listeners do not attend equally to every part of a sound. Hindi vs English may weight aspiration, voicing, and pitch differently on the same physical contrast.
- For /v/ vs /w/, changing cue weights does not fix the story. The important fact is the L1 merger, not a small feature gap.
- Cue weights matter most for contrasts that exist in both languages but are cued differently (aspiration).

## Blockers

None blocking the Term 1 code. Open points for Term 2:

- Cue weights still need a short written justification from readings (how Hindi vs English signal aspiration), then a sensitivity check so we do not overclaim the exact numbers.
- English Epitran still needs flite for a pure Epitran path; the fallback is fine for now.
- Ethics / AXB protocol / recruitment were marked ahead of the timeline. They are not done until submitted.

## What is left (next term)

- Ground and revise the Hindi-aware layer: readings on Hindi vs English aspiration cues, edit the weight file, expand the inventory if needed.
- Expand the contrast set and curated minimal pairs; confirm exports load in PsychoPy / jsPsych.
- Draft the AXB protocol from toolkit stimuli; ethics (REB); recruit Hindi-L1 speakers.
- Run the experiment and test whether the toolkit’s predictions (distance plus L1) match discrimination accuracy.
- Optional later check: L2-ARCTIC Hindi speakers’ substitutions. Production is not the same as perception; AXB is the main test.

## One paragraph for the submission

This term I built phonosim, a small Python toolkit on top of PanPhon and Epitran. It looks up articulatory features, scores phoneme distance (flat, PanPhon-weighted, or a first-pass Hindi cue profile), and can export simple AXB stimulus tables. Using PanPhon showed that the original proposal was wrong on /v/ vs /w/: those sounds are featurally far, not close. Hindi listeners still confuse them because both map to one native category. Distance alone is therefore not a difficulty score. Next term I will develop the Hindi-aware layer more fully (cue weights justified from how Hindi vs English mark aspiration, plus L1 category mapping), then test the toolkit with an AXB study with Hindi-L1 listeners.
