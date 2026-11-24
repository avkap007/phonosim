// All participant-facing text. Keep the consent text identical to the
// REB-approved consent form (study 30004064) once it is approved.
window.TEXT = {};

TEXT.consent = () => `
<div class="page">
<h2>How Hindi speakers hear English sounds</h2>
<p class="meta">SFU Study #30004064 | Online consent form | Version 1</p>
<p>This online study is hosted on a JATOS server and recruited through Prolific. Any data you
provide pass through these platforms. Privacy laws differ between countries and may not be as
strong as in Canada. You can read Prolific's privacy policy
<a href="https://researcher-help.prolific.co/hc/en-gb/articles/360009094594-Data-protection-and-privacy" target="_blank">here</a>.</p>

<h3>Who is running the study?</h3>
<p>Dr. Yue Wang (Principal Investigator), Department of Linguistics, Simon Fraser University,
and Avni Kapoor (Student Lead), Cognitive Science honours student, SFU.</p>

<h3>What is it about?</h3>
<p>Some English sound pairs, like v and w, are harder than others for people whose first language
is Hindi. This study tests whether a computer program can predict which pairs are hardest.</p>

<h3>What will you do?</h3>
<p>About ${CONFIG.MINUTES} minutes, on a laptop or desktop computer with headphones: a short
questionnaire, a headphone check, two listening tasks, and a few final questions. We do not
record your voice or video. The tasks measure the sounds, not how good your English is.</p>

<h3>Is it voluntary?</h3>
<p>Yes. You can stop at any time by closing this window, with no penalty.</p>

<h3>Risks and benefits</h3>
<p>The only expected risks are boredom or tiredness; you can take breaks. You may not benefit
directly, but you will help research on second-language speech perception.</p>

<h3>Payment</h3>
<p>${CONFIG.PAY_TEXT} through Prolific. If you stop partway, you are paid for the time you spent.</p>

<h3>Privacy</h3>
<p>We do not collect your name, email or signature. Your answers are stored under a random
code. Your Prolific ID is used only to pay you and handle withdrawal requests, and is kept
separately. Data are stored in encrypted SFU storage that only the research team can access.
Results are reported only as group averages. De-identified data may be shared in an open
repository (such as OSF) for other researchers.</p>

<h3>Withdrawing your data</h3>
<p>Within two weeks of your session, message us on Prolific or email us with your Prolific ID
and we will delete your data. After that your data can no longer be linked to you.</p>

<h3>Contact</h3>
<p>Questions: Avni Kapoor (aka262@sfu.ca) or Dr. Yue Wang (yuew@sfu.ca).
Concerns about your rights as a participant: Director, SFU Office of Research Ethics,
dore@sfu.ca, 778-782-6593.</p>

<p><b>By clicking "I agree" you confirm that you are 18 or older, have read this form, and
agree to take part.</b> You do not give up any legal rights. You can print or save this page.</p>
</div>`;

TEXT.noConsent = `<div class="page"><p>Thank you for your time. You have not taken part and no
data were saved. You will now be returned to Prolific.</p></div>`;

TEXT.background = `
<div class="page form">
<h3>About you</h3>
<p>Choose "Prefer not to answer" or leave a box blank for any question you'd rather skip.</p>
<label>Age <input name="age" type="number" min="18" max="99"></label>
<label>Gender <input name="gender" type="text"></label>
<label>Do you have any speech, hearing, or neurological difficulties?
  <select name="impairment" required>
    <option value="">choose</option><option>None</option><option>Speech</option>
    <option>Hearing</option><option>Neurological</option><option>Prefer not to answer</option>
  </select></label>
<label>What are you listening with right now?
  <select name="headphones" required>
    <option value="">choose</option><option>Over-ear headphones</option>
    <option>In-ear earbuds</option><option>Computer speakers</option><option>Other</option>
  </select></label>
<label>Current position (e.g., university student) <input name="position" type="text"></label>
<label>Where you live now (city, country) <input name="residence" type="text"></label>
<label>Where you mainly lived as a child (city, country) <input name="childhood_place" type="text"></label>
<label>Years lived in an English-speaking country <input name="years_english_country" type="number" min="0" max="99" step="0.5"></label>

<h3>Your languages</h3>
<label>Is Hindi your first language, learned from birth or early childhood?
  <select name="hindi_l1" required><option value="">choose</option><option>Yes</option><option>No</option></select></label>
<label>Did you learn English from birth, at the same time as Hindi?
  <select name="english_from_birth" required><option value="">choose</option><option>Yes</option><option>No</option></select></label>
<label>Age you started learning English <input name="english_aoa" type="number" min="0" max="99"></label>
<label>Was English the language of instruction at your school?
  <select name="english_medium"><option value="">choose</option><option>All years</option><option>Some years</option><option>No</option></select></label>
<label>Other languages you speak well (e.g., Punjabi, Urdu) <input name="other_languages" type="text"></label>
<label>English test score, if any (e.g., IELTS 7.5) <input name="english_test" type="text"></label>
<label>% of your day you use English now <input name="english_pct" type="number" min="0" max="100"></label>
<label>How well do you understand spoken English? (1 = very poorly, 7 = like a native speaker)
  <select name="english_listening_1to7" required><option value="">choose</option>
  <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option></select></label>
</div>`;

TEXT.volume = `<div class="page"><h3>Set your volume</h3>
<p>Put on your headphones. Press <b>Play</b> and set your computer's volume so the tone is
clear and comfortable, not loud. You can play it as many times as you like.</p></div>`;

TEXT.headphoneIntro = `<div class="page"><h3>Headphone check</h3>
<p>You will hear three tones. Click which one was the <b>quietest</b>: 1, 2 or 3.
Each sound plays once, so listen carefully. There are 6 of these.</p></div>`;

TEXT.headphoneFail = (last) => last
  ? `<div class="page"><p>It looks like you may not be wearing headphones, which this study needs.
     Thank you for your time. You will be returned to Prolific and paid for the time you spent.</p></div>`
  : `<div class="page"><p>That check didn't quite work. Please make sure your headphones are
     plugged in and on both ears, then try once more.</p></div>`;

TEXT.axbIntro = (k) => `<div class="page"><h3>Listening task 1</h3>
<p>On each trial you will hear three words. The <b>middle</b> word is the same as either the
<b>first</b> word or the <b>last</b> word.</p>
<p>Press <b>${k.first.toUpperCase()}</b> if the middle word matches the <b>first</b>,
or <b>${k.last.toUpperCase()}</b> if it matches the <b>last</b>.</p>
<p>The voices may differ slightly; listen for the sounds. Some trials are hard. Just give your
best guess. First, a few practice trials with feedback.</p></div>`;

TEXT.axbPrompt = (k) => `<p class="prompt">Middle matches: <b>${k.first.toUpperCase()}</b> = first &nbsp;&nbsp; <b>${k.last.toUpperCase()}</b> = last</p>`;

TEXT.axbMainStart = `<div class="page"><p>Practice done. Now the main task begins, with no feedback.
It is split into short blocks with breaks in between.</p></div>`;

TEXT.breakScreen = (done, total) => `<div class="page"><p>Block ${done} of ${total} done.
Take a short break if you like.</p></div>`;

TEXT.assimIntro = `<div class="page"><h3>Listening task 2</h3>
<p>You will hear short syllables like "aba". Listen to the <b>consonant in the middle</b>.
Choose the Hindi sound it is most like, then rate how good a match it is.</p></div>`;

TEXT.assimPrompt = `<p>Which Hindi sound is the middle consonant most like?</p>`;
TEXT.goodnessPrompt = (choice) => `<p>How good an example of <b>${choice}</b> was that sound?</p>
<p class="meta">1 = very poor match, 7 = excellent match</p>`;

TEXT.closing = `
<div class="page form">
<h3>Last questions</h3>
<label>Which sound pairs, if any, felt hard to tell apart?<textarea name="hard_pairs" rows="3"></textarea></label>
<label>Do you notice difficulty with any of these sounds in everyday English?
  <select name="everyday_difficulty"><option value="">choose</option><option>Often</option><option>Sometimes</option><option>Rarely</option><option>Never</option></select></label>
<label>Anything else you'd like to tell us? (e.g., noise, technical problems)<textarea name="comments" rows="3"></textarea></label>
</div>`;

TEXT.debrief = `<div class="page"><h3>Thank you!</h3>
<p>This study tests whether a feature-based computer score, combined with how English sounds map
onto Hindi sound categories, predicts which English contrasts are hardest for Hindi speakers to
hear. Pairs like v/w are predicted to be hard because Hindi has one sound (व) where English has two.</p>
<p>If you'd like a plain-language summary of the results, email aka262@sfu.ca.</p>
<p>Click below to return to Prolific and receive payment.</p></div>`;
