// Settings to check before launch. Everything marked CONFIRM needs Dr. Wang's sign-off.
window.CONFIG = {
  // Prolific completion codes (copy from the Prolific study page).
  PROLIFIC_COMPLETE_CODE: "CHANGE_ME_COMPLETE",
  PROLIFIC_SCREENOUT_CODE: "CHANGE_ME_SCREENOUT",   // failed headphone check (paid for time spent, CONFIRM)
  PROLIFIC_NOCONSENT_CODE: "CHANGE_ME_NOCONSENT",

  // AXB task
  RESPONSE_KEYS: { first: "f", last: "j" },
  AXB_REPS: 1,             // times each AXB file is played (192 test + 12 catch trials)
  BLOCK_SIZE: 51,          // trials between breaks (204 / 4 blocks)
  ITI_MS: 500,             // silence after each main AXB trial
  PRACTICE_REPS: 1,        // 8 practice trials with feedback

  // Headphone check. Default is Huggins pitch (Milne et al. 2021), whose authors
  // recommend 6 of 6. If you rebuild with --headphone-test antiphase (Woods et al. 2017),
  // set this to 5.
  HEADPHONE_PASS: 6,
  HEADPHONE_ATTEMPTS: 2,   // CONFIRM: allow one retry before screening out

  // Sound-matching task: 13 aCa syllables x 3 recordings = 39 trials
  ASSIM_ENABLED: true,

  // Hindi response options for the sound-matching task (needs piloting, CONFIRM)
  HINDI_OPTIONS: [
    ["व", "va"], ["ब", "ba"], ["भ", "bha"], ["प", "pa"], ["फ", "pha"], ["फ़", "fa"],
    ["त", "ta"], ["थ", "tha"], ["ट", "Ta"], ["द", "da"], ["ध", "dha"], ["ड", "Da"],
    ["ड़", "Ra"], ["र", "ra"], ["ज", "ja"], ["ज़", "za"], ["झ", "jha"], ["स", "sa"], ["श", "sha"],
    ["य", "ya"]   // added Nov 24: the automatic map predicts w and ɹ -> j
  ],
  NONE_LABEL: "None of these",

  // Payment shown to participants (CONFIRM)
  PAY_TEXT: "$9 CAD",
  MINUTES: 45,
};
