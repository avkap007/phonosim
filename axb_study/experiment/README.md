# AXB listening study (SFU REB #30004064)

Online experiment for Hindi-L1 listeners, built in jsPsych 8.3 to run on JATOS with Prolific recruitment. The order matches the Kuali protocol:

consent → background questionnaire → volume set → headphone check (Huggins pitch) → AXB practice → AXB main (192 test + 12 catch trials, 4 blocks with breaks) → sound-matching task (39 trials) → closing questions → debrief → back to Prolific.

## Try it now (placeholder beeps)

```bash
cd axb_study/experiment
python3 build_stimuli.py --placeholders   # makes the beep audio (not shipped, ~50 MB)
python3 -m http.server 8765
# open http://localhost:8765/index.html?quick=1
```

`?quick=1` shortens the run to 6 AXB trials and 4 sound-matching trials. Drop it for the full version. Opened outside JATOS, the experiment runs in local test mode and downloads a CSV at the end. Building the stimuli needs numpy (for the headphone check).

`tests/run_flow.py` clicks through the whole thing in headless Chrome and checks the data. `--jatos` runs it against a mock of jatos.js to check what reaches the server; `--full` runs every trial. Passed Nov 24, 2026 for: quick local run, headphone fail on JATOS, and the full run on JATOS.

## What's in the folder

| File | What it does |
| --- | --- |
| `stimuli/pairs.csv` | 8 contrasts × 6 vowel frames (aCa, iCi, uCu, eCe, oCo, aCi), all made-up words, plus 2 practice and 3 catch items. Columns `hand_merged` / `auto_merged` give each L1 map's prediction. **Check with Dr. Wang.** |
| `stimuli/assim_tokens.csv` | 13 aCa syllables for the sound-matching task, 3 recordings each |
| `stimuli/recording_list.csv` | Generated: every recording the talker needs (88 made-up words, 189 files) |
| `build_stimuli.py` | Builds one audio file per AXB trial (A, 500 ms gap, X, 500 ms gap, B), the headphone check, `stimuli/trials.js` and the recording list |
| `config.js` | Prolific codes, response keys, block size, headphone pass mark, Hindi response options, pay text |
| `text.js` | Every word participants see, including the on-screen consent |
| `experiment.js` | The timeline and data saving |
| `lib/` | jsPsych and plugins, bundled so nothing loads from a CDN |
| `tests/` | `run_flow.py` (headless click-through) and `mock_jatos.js` |
| `../analysis/` | Data prep, exclusions and models, tested on simulated listeners |

## Design choices

- **Hand map vs automatic map.** The 8 contrasts are chosen so the AXB tests Study 2's question directly. 2 contrasts are merged only by the hand-built Hindi table (v-w, ʒ-dʒ), 4 only by the automatic projection (θ-t, ð-d, v-f, w-ɹ), and 2 by neither (p-pʰ, ɹ-ɽ, the locked Term 1 contrasts). See `../analysis/README.md`.
- **Made-up words in one frame.** Every contrast appears in the same 6 vowel frames (aCa, iCi, uCu, eCe, oCo, aCi). Mixing real English words with nonwords would confound word status with contrast, and one trained talker can record everything. Names are lowercase only (macOS treats `ara` and `aRa` as the same file); ɽ is written `rx`.
- **AXB file per trial.** Each trial's audio is pre-joined, so the gaps are exactly 500 ms. `x_onset_ms`, `b_onset_ms` and `b_offset_ms` are stored with each trial.
- **X is a different recording.** A and B use token 1 of each word and X uses token 2, so listeners judge the sound, not an identical file.
- **4 orders per pair** (AAB, ABB, BBA, BAA), so "first" and "last" are each correct half the time.
- **Shuffled with no repeats**, 500 ms between trials. Responses only after the sound ends; `rt_from_b_offset` is the RT to analyse.
- **Catch trials.** 12 easy n vs s trials mixed into the main blocks. Exclusion below 10/12 is fixed in the analysis.
- **Headphone check: Huggins pitch** (Milne et al. 2021): three noise bursts, one has a faint tone that is only audible over headphones. Pass at 6/6 (the authors' recommendation), one retry. An example plays first. `--headphone-test antiphase` rebuilds the older Woods et al. (2017) test; then set `HEADPHONE_PASS` to 5.
- **Saved as you go.** On JATOS, rows are appended after the questionnaire, the headphone check, each AXB block and the sound-matching task (one JSON row per line). A dropout keeps the data so far; the consent text says so.
- **Prolific ID.** Never in the trial data. JATOS does record URL parameters, including the Prolific ID, with each session's metadata, so the consent text says the server records it and that it is removed before analysis or sharing. `prolific_id_link.json` is still saved as the master list.

## Before launch

1. **Record stimuli.** `stimuli/recording_list.csv` lists every file (2 tokens per made-up word, 3 for the sound-matching syllables). Save as `audio/recordings/<word>_t1.wav` etc., mono, 16-bit, 44.1 kHz, trimmed, matched loudness, monophthong vowels. One phonetically trained talker for everything, who produces /pʰ/ and /ɽ/ naturally and keeps English /v/ and /w/ clearly distinct (no [ʋ]). Check the recordings acoustically (e.g. VOT for p-pʰ) before building.
2. Run `python3 build_stimuli.py` (without `--placeholders`).
3. **Finalize the contrast set** with Dr. Wang, and rerun the power simulation (`../power/`) for this design.
4. **Pilot the Hindi response labels** in `config.js` with 2 or 3 Hindi speakers.
5. **Fill in the Prolific completion codes** in `config.js`, and make `text.js` consent match the approved consent form word for word.
6. **Set up JATOS.** Zip the folder into a JATOS study and import it on the lab's JATOS server (which server is still to confirm). Create a "General Multiple" worker link and append Prolific's placeholders: `&PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}`.
7. **Prolific screeners:** first language Hindi, age 18+, no hearing difficulties, desktop only.

## Data columns worth knowing

- `task`: axb, axb_practice, headphone, assim_choice, assim_goodness, background, closing, and others.
- AXB: `contrast`, `role` (test/catch), `pair_id`, `order`, `answer` (first/last), `response_side`, `correct`, `rt`, `rt_from_b_offset`, `block`, `hand_merged`, `auto_merged`.
- Sound matching: `phone`, `rep`, `hindi_choice`, `goodness` (1 to 7).
- Background: `response` holds the form answers as JSON.
