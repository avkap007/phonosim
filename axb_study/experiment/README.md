# AXB listening study (SFU REB #30004064)

Online experiment for Hindi-L1 listeners, built in jsPsych 8.3 to run on JATOS with Prolific recruitment. The order matches the Kuali protocol:

consent → background questionnaire → volume set → headphone check → AXB practice → AXB main (4 blocks with breaks) → sound-matching task → closing questions → debrief → back to Prolific.

## Try it now (placeholder beeps)

```bash
cd axb_study/experiment
python3 build_stimuli.py --placeholders   # makes the beep audio (not shipped, ~50 MB)
python3 -m http.server 8765
# open http://localhost:8765/index.html?quick=1
```

`?quick=1` shortens the run to 6 AXB trials and 4 sound-matching trials. Drop it for the full ~45-minute version. Opened outside JATOS, the experiment runs in local test mode and downloads a CSV at the end.

`tests/run_flow.py` clicks through the whole thing in headless Chrome and checks the data. It passed for the complete path and for the headphone-fail path.

## What's in the folder

| File | What it does |
| --- | --- |
| `stimuli/pairs.csv` | Minimal pairs: 8 contrasts × 6 pairs, plus 2 practice pairs. **Draft list, check with Dr. Wang.** |
| `stimuli/assim_tokens.csv` | 15 aCa syllables for the sound-matching task (aCa so spelling doesn't give the sound away) |
| `build_stimuli.py` | Builds one audio file per AXB trial (A, 500 ms gap, X, 500 ms gap, B), the headphone check and `stimuli/trials.js` |
| `config.js` | Prolific codes, response keys, block size, headphone pass mark, Hindi response options, pay text |
| `text.js` | Every word participants see, including the on-screen consent |
| `experiment.js` | The timeline and data saving |
| `lib/` | jsPsych and plugins, bundled so nothing loads from a CDN |

## Design choices

- **AXB file per trial.** Each trial's audio is pre-joined, so the gaps are exactly 500 ms. Chaining three separate sounds in the browser would add jitter. `b_onset_ms` is stored with each trial.
- **X is a different recording.** A and B use token 1 of each word and X uses token 2. Listeners have to judge the sound, not match an identical file. So every word needs **two recordings**.
- **4 orders per pair** (AAB, ABB, BBA, BAA), so "first" and "last" are each the right answer half the time. That keeps d′ computable (Keating 2005).
- **Shuffled with no repeats.** The same minimal pair never plays twice in a row.
- **Responses only after the sound ends.** `rt` is measured from trial start.
- **Headphone check.** Uses Woods et al. (2017) antiphase tones and needs 5 of 6 correct. One retry is allowed, then the participant is screened out with the screen-out code.
- **Prolific ID kept separate.** It never goes into the trial data. On JATOS it's saved as a separate result file (`prolific_id_link.json`), to match the REB's "master list stored separately".

## Before launch

1. **Record stimuli.** Two tokens of every word in `pairs.csv` and every token in `assim_tokens.csv`. Save as `audio/recordings/<word>_t1.wav` and `_t2.wav`, mono, 16-bit, 44.1 kHz, trimmed, with matched loudness. /pʰ/ and /ɽ/ need a talker who produces them naturally, such as a Hindi-English bilingual phonetician.
2. Run `python3 build_stimuli.py` (without `--placeholders`).
3. **Finalize the contrast set.** Swap or drop pairs in `pairs.csv` as needed. The power analysis (`../power/`) explains why 8 or more contrasts beats 3.
4. **Pilot the Hindi response labels** in `config.js` with 2 or 3 Hindi speakers.
5. **Fill in the Prolific completion codes** in `config.js`, and make `text.js` consent match the approved consent form word for word.
6. **Set up JATOS.** Zip the folder into a JATOS study and import it on the lab's JATOS server (which server is still to confirm). Create a "General Multiple" worker link and append Prolific's placeholders: `&PROLIFIC_PID={{%PROLIFIC_PID%}}&STUDY_ID={{%STUDY_ID%}}&SESSION_ID={{%SESSION_ID%}}`.
7. **Prolific screeners:** first language Hindi, age 18+, no hearing difficulties, desktop only.

## Data columns worth knowing

- `task`: axb, axb_practice, headphone, assim_choice, assim_goodness, background, closing, and others.
- AXB: `contrast`, `pair_id`, `order`, `answer` (first/last), `response_side`, `correct`, `rt`, `block`, `b_onset_ms`.
- Sound matching: `phone`, `rep`, `hindi_choice`, `goodness` (1 to 7).
- Background: `response` holds the form answers as JSON.
