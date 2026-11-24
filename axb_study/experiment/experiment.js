// AXB discrimination + sound-matching study for Hindi-L1 listeners (SFU study 30004064).
// Runs on JATOS (recruited via Prolific). Opened as a plain file it runs in local test
// mode and downloads the data at the end instead of submitting it.

const VERSION = "2026-11-09";
const LOCAL = typeof window.jatos === "undefined";

function start() {
  const params = new URLSearchParams(window.location.search);
  const prolific = {
    pid: params.get("PROLIFIC_PID") || "",
    study: params.get("STUDY_ID") || "",
    session: params.get("SESSION_ID") || "",
  };
  const participant = "P" + Math.random().toString(16).slice(2, 10).toUpperCase();
  let ENDING = "complete";        // complete | noconsent | screenout

  const jsPsych = initJsPsych({
    show_progress_bar: true,
    auto_update_progress_bar: false,
    on_finish: () => finish(jsPsych, ENDING, participant, prolific),
  });
  // The Prolific ID is NOT added to the trial data. It is saved as a separate
  // file (see finish) so it can be stored apart from the study data.
  jsPsych.data.addProperties({
    participant, version: VERSION, local_test: LOCAL, placeholder_audio: !!STIM.placeholders,
  });
  const K = CONFIG.RESPONSE_KEYS;
  const progress = (p) => ({ type: jsPsychCallFunction, func: () => jsPsych.progressBar.progress = p });
  const timeline = [];
  window.__jsPsych = jsPsych;   // handy for debugging in the browser console
  // ?quick=1 runs a short version (6 AXB trials, 4 sound-matching) for piloting the flow
  const QUICK = params.get("quick") === "1";

  // ---- 1. device check and consent -------------------------------------
  timeline.push({
    type: jsPsychBrowserCheck,
    inclusion_function: (d) => !d.mobile && d.width >= 700,
    exclusion_message: () => `<div class="page"><p>This study needs a laptop or desktop
      computer. Please return to Prolific and open the study on a computer.</p></div>`,
    data: { task: "browser_check" },
  });
  timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: TEXT.consent(),
    choices: ["I agree", "I do not agree"],
    data: { task: "consent" },
    on_finish: (d) => {
      d.consented = d.response === 0;
      if (!d.consented) { ENDING = "noconsent"; jsPsych.abortExperiment(TEXT.noConsent); }
    },
  });

  // ---- 2. background questionnaire --------------------------------------
  timeline.push({
    type: jsPsychSurveyHtmlForm,
    html: TEXT.background,
    button_label: "Continue",
    data: { task: "background" },
  });
  timeline.push(progress(0.1));

  // ---- 3. volume and headphone check ------------------------------------
  const hpFiles = STIM.headphone.map((t) => t.file);
  timeline.push({
    type: jsPsychPreload,
    audio: ["audio/calibration.wav", ...hpFiles, ...STIM.axb.filter((t) => t.practice).map((t) => t.file)],
    message: "<p>Loading sounds...</p>",
    data: { task: "preload_1" },
  });
  timeline.push({
    timeline: [{
      type: jsPsychAudioButtonResponse,
      stimulus: "audio/calibration.wav",
      prompt: TEXT.volume,
      choices: ["Play again", "Volume is comfortable"],
      response_allowed_while_playing: true,
      data: { task: "volume" },
    }],
    loop_function: (d) => d.values()[0].response === 0,
  });

  let hpAttempt = 0;
  const hpPassed = () => {
    const rows = jsPsych.data.get().filter({ task: "headphone", attempt: hpAttempt }).values();
    return rows.filter((r) => r.correct).length >= CONFIG.HEADPHONE_PASS;
  };
  timeline.push({
    timeline: [
      { type: jsPsychCallFunction, func: () => { hpAttempt += 1; } },
      { type: jsPsychHtmlButtonResponse, stimulus: TEXT.headphoneIntro, choices: ["Start"] },
      {
        timeline: jsPsych.randomization.shuffle(STIM.headphone).map((t) => ({
          type: jsPsychAudioButtonResponse,
          stimulus: t.file,
          choices: ["1", "2", "3"],
          prompt: "<p>Which tone was the quietest?</p>",
          response_allowed_while_playing: false,
          data: { task: "headphone", file: t.file, answer: t.answer },
          on_finish: (d) => { d.attempt = hpAttempt; d.correct = String(d.response + 1) === d.answer; },
        })),
      },
      {
        timeline: [{
          type: jsPsychHtmlButtonResponse,
          stimulus: () => TEXT.headphoneFail(hpAttempt >= CONFIG.HEADPHONE_ATTEMPTS),
          choices: ["Continue"],
          data: { task: "headphone_fail" },
          on_finish: () => {
            if (hpAttempt >= CONFIG.HEADPHONE_ATTEMPTS) {
              ENDING = "screenout";
              jsPsych.abortExperiment("<p>Returning you to Prolific...</p>");
            }
          },
        }],
        conditional_function: () => !hpPassed(),
      },
    ],
    loop_function: () => !hpPassed() && hpAttempt < CONFIG.HEADPHONE_ATTEMPTS,
  });
  timeline.push(progress(0.2));

  // ---- 4. AXB discrimination --------------------------------------------
  const axbTrial = (t, practice, block = 0) => ({
    type: jsPsychAudioKeyboardResponse,
    stimulus: t.file,
    choices: [K.first, K.last],
    prompt: TEXT.axbPrompt(K),
    response_allowed_while_playing: false,
    data: { ...t, task: practice ? "axb_practice" : "axb", block },
    on_finish: (d) => {
      d.response_side = d.response === K.first ? "first" : "last";
      d.correct = d.response_side === d.answer;
    },
  });
  const feedback = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: () => {
      const last = jsPsych.data.get().last(1).values()[0];
      return last.correct ? '<p class="fb good">Correct</p>'
        : `<p class="fb bad">Not quite: the middle word matched the <b>${last.answer}</b> word</p>`;
    },
    choices: "NO_KEYS",
    trial_duration: 1200,
  };
  timeline.push({ type: jsPsychHtmlButtonResponse, stimulus: TEXT.axbIntro(K), choices: ["Start practice"] });
  const practice = STIM.axb.filter((t) => t.practice);
  timeline.push({
    timeline: jsPsych.randomization.shuffle(
      Array(CONFIG.PRACTICE_REPS).fill(practice).flat()
    ).flatMap((t) => [axbTrial(t, true), feedback]),
  });
  timeline.push({ type: jsPsychHtmlButtonResponse, stimulus: TEXT.axbMainStart, choices: ["Start"] });

  const test = STIM.axb.filter((t) => !t.practice);
  const mainAudio = [...test.map((t) => t.file), ...STIM.assim.map((t) => t.file)];
  timeline.push({
    type: jsPsychPreload, audio: mainAudio,
    message: "<p>Loading the main task sounds. This can take a minute...</p>",
    data: { task: "preload_2" },
  });
  // shuffle so the same minimal pair never plays twice in a row
  let ordered = jsPsych.randomization.shuffleNoRepeats(
    Array(CONFIG.AXB_REPS).fill(test).flat(), (a, b) => a.pair_id === b.pair_id);
  if (QUICK) ordered = ordered.slice(0, 6);
  const nBlocks = Math.ceil(ordered.length / CONFIG.BLOCK_SIZE);
  for (let b = 0; b < nBlocks; b++) {
    const block = ordered.slice(b * CONFIG.BLOCK_SIZE, (b + 1) * CONFIG.BLOCK_SIZE)
      .map((t) => axbTrial(t, false, b + 1));
    timeline.push({ timeline: block });
    timeline.push(progress(0.25 + 0.5 * (b + 1) / nBlocks));
    if (b < nBlocks - 1) {
      timeline.push({ type: jsPsychHtmlButtonResponse, stimulus: TEXT.breakScreen(b + 1, nBlocks),
                      choices: ["Continue"], data: { task: "break" } });
    }
  }

  // ---- 5. sound-matching (assimilation) task ----------------------------
  if (CONFIG.ASSIM_ENABLED) {
    const opts = CONFIG.HINDI_OPTIONS.map(([dev, rom]) =>
      `<span class="dev">${dev}</span><span class="rom">${rom}</span>`);
    const labels = [...CONFIG.HINDI_OPTIONS.map(([dev]) => dev), CONFIG.NONE_LABEL];
    timeline.push({ type: jsPsychHtmlButtonResponse, stimulus: TEXT.assimIntro, choices: ["Start"] });
    timeline.push({
      timeline: jsPsych.randomization.shuffle(STIM.assim).slice(0, QUICK ? 4 : undefined).flatMap((t) => [
        {
          type: jsPsychAudioButtonResponse,
          stimulus: t.file,
          prompt: TEXT.assimPrompt,
          choices: [...opts, CONFIG.NONE_LABEL],
          button_layout: "grid",
          grid_columns: 5,
          response_allowed_while_playing: false,
          data: { ...t, task: "assim_choice" },
          on_finish: (d) => { d.hindi_choice = labels[d.response]; },
        },
        {
          timeline: [{
            type: jsPsychHtmlButtonResponse,
            stimulus: () => TEXT.goodnessPrompt(jsPsych.data.get().last(1).values()[0].hindi_choice),
            choices: ["1", "2", "3", "4", "5", "6", "7"],
            data: { ...t, task: "assim_goodness" },
            on_finish: (d) => { d.goodness = d.response + 1; },
          }],
          conditional_function: () =>
            jsPsych.data.get().last(1).values()[0].hindi_choice !== CONFIG.NONE_LABEL,
        },
      ]),
    });
  }
  timeline.push(progress(0.95));

  // ---- 6. closing questions and debrief ----------------------------------
  timeline.push({ type: jsPsychSurveyHtmlForm, html: TEXT.closing, button_label: "Continue",
                  data: { task: "closing" } });
  timeline.push({ type: jsPsychHtmlButtonResponse, stimulus: TEXT.debrief,
                  choices: ["Finish and return to Prolific"], data: { task: "debrief" } });

  jsPsych.run(timeline);
}

function finish(jsPsych, ending, participant, prolific) {
  const code = { complete: CONFIG.PROLIFIC_COMPLETE_CODE, screenout: CONFIG.PROLIFIC_SCREENOUT_CODE,
                 noconsent: CONFIG.PROLIFIC_NOCONSENT_CODE }[ending];
  const url = `https://app.prolific.com/submissions/complete?cc=${code}`;
  const idLink = JSON.stringify({ participant, ending, ...prolific });
  const csv = jsPsych.data.get().csv();

  if (LOCAL) {
    if (ending !== "noconsent") jsPsych.data.get().localSave("csv", `axb_${participant}.csv`);
    document.body.innerHTML = `<div class="page"><h3>Local test finished (${ending})</h3>
      <p>On JATOS this would now redirect to:<br><code>${url}</code></p>
      <p>Data downloaded as axb_${participant}.csv. Prolific ID link (stored separately on JATOS):<br>
      <code>${idLink}</code></p></div>`;
    return;
  }
  // Declined consent: save nothing, just return to Prolific.
  if (ending === "noconsent") { jatos.endStudyAndRedirect(url, true, "no consent"); return; }
  jatos.submitResultData(csv)
    .then(() => jatos.uploadResultFile(idLink, "prolific_id_link.json"))
    .then(() => jatos.endStudyAndRedirect(url, true, ending))
    .catch(() => jatos.endStudyAndRedirect(url, false, "save error"));
}

if (LOCAL) window.addEventListener("load", start);
else jatos.onLoad(start);
