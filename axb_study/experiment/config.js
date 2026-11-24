// Settings to check before launch. Everything marked CONFIRM needs Dr. Wang's sign-off.
window.CONFIG = {
  // Prolific completion codes (copy from the Prolific study page).
  PROLIFIC_COMPLETE_CODE: "CHANGE_ME_COMPLETE",
  PROLIFIC_SCREENOUT_CODE: "CHANGE_ME_SCREENOUT",   // failed headphone check (paid for time spent, CONFIRM)
  PROLIFIC_NOCONSENT_CODE: "CHANGE_ME_NOCONSENT",

  // AXB task
  RESPONSE_KEYS: { first: "f", last: "j" },
  AXB_REPS: 1,             // times each AXB file is played (1 x 192 test trials ~ 18 min)
  BLOCK_SIZE: 48,          // trials between breaks
  PRACTICE_REPS: 1,        // 8 practice trials with feedback

  // Headphone check (Woods et al. 2017): pass if at least this many of 6 correct
  HEADPHONE_PASS: 5,
  HEADPHONE_ATTEMPTS: 2,   // CONFIRM: allow one retry before screening out

  // Sound-matching task: 15 aCa tokens x 2 recordings = 30 trials
  ASSIM_ENABLED: true,

  // Hindi response options for the sound-matching task (needs piloting, CONFIRM)
  HINDI_OPTIONS: [
    ["व", "va"], ["ब", "ba"], ["भ", "bha"], ["प", "pa"], ["फ", "pha"], ["फ़", "fa"],
    ["त", "ta"], ["थ", "tha"], ["ट", "Ta"], ["द", "da"], ["ध", "dha"], ["ड", "Da"],
    ["ड़", "Ra"], ["र", "ra"], ["ज", "ja"], ["ज़", "za"], ["झ", "jha"], ["स", "sa"], ["श", "sha"]
  ],
  NONE_LABEL: "None of these",

  // Payment shown to participants (CONFIRM)
  PAY_TEXT: "$9 CAD",
  MINUTES: 45,
};
