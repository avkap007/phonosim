"""Click through the whole experiment in headless Chrome and check the data.

    python3 -m http.server 8765 &      # from the experiment folder
    python3 tests/run_flow.py [--fail-headphones] [--jatos] [--full]

--jatos  serves tests/mock_jatos.js as jatos.js, so the experiment runs in JATOS mode and
         the test checks what would be appended to the server (one JSON row per line).
--full   runs all trials instead of the ?quick=1 version (takes about 10 minutes).
"""
import csv, io, json, os, shutil, sys, time
from playwright.sync_api import sync_playwright

FAIL_HP = "--fail-headphones" in sys.argv
JATOS = "--jatos" in sys.argv
FULL = "--full" in sys.argv
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = ("http://localhost:8765/index.html?" + ("" if FULL else "quick=1&")
       + "PROLIFIC_PID=TESTPID&STUDY_ID=S1&SESSION_ID=X1")
if JATOS:
    shutil.copy(os.path.join(HERE, "tests", "mock_jatos.js"), os.path.join(HERE, "jatos.js"))


def jatos_rows(page, dump=False):
    log = page.evaluate("window.__jatosLog")
    rows = [json.loads(l) for chunk in log["appended"] for l in chunk.splitlines() if l]
    if dump:  # same layout as a JATOS export, so ../analysis/prepare.py can read it
        d = os.path.join("/tmp", "jatos_mock_export", rows[0]["participant"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "data.txt"), "w", encoding="utf-8") as fh:
            fh.write("".join(log["appended"]))
        print("server data written to", d)
    return log, rows


def cur(page, expr):
    return page.evaluate(f"(() => {{ const t = window.__jsPsych.getCurrentTrial(); return {expr}; }})()")


def click_enabled(page, selector, timeout=20000):
    page.wait_for_selector(selector + ":not([disabled])", timeout=timeout)
    page.click(selector)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                          args=["--autoplay-policy=no-user-gesture-required"])
    page = b.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL)

    click_enabled(page, "button:has-text('I agree')")
    page.select_option("select[name=impairment]", "None")
    page.select_option("select[name=headphones]", "Over-ear headphones")
    page.select_option("select[name=hindi_l1]", "Yes")
    page.select_option("select[name=english_from_birth]", "No")
    page.select_option("select[name=english_listening_1to7]", "6")
    page.fill("input[name=age]", "24")
    page.click("#jspsych-survey-html-form-next")
    click_enabled(page, "button:has-text('Volume is comfortable')", timeout=60000)

    attempts = 2 if FAIL_HP else 1
    for a in range(attempts):
        click_enabled(page, "button:has-text('Start')")
        if page.evaluate("STIM.headphone_test") == "huggins":
            click_enabled(page, "button:has-text('Continue')", timeout=20000)
        for _ in range(6):
            page.wait_for_selector("button:has-text('3')")
            ans = cur(page, "t.data.answer")
            pick = ans if not FAIL_HP else str((int(ans) % 3) + 1)
            click_enabled(page, f"#jspsych-audio-button-response-btngroup button:text-is('{pick}')", timeout=20000)
        if FAIL_HP:
            click_enabled(page, "button:has-text('Continue')")

    if FAIL_HP:
        if JATOS:
            page.wait_for_selector("text=JATOS mock", timeout=20000)
            log, rows = jatos_rows(page)
            print("ended:", log["ended"], "| rows saved:", len(rows),
                  "| id file:", log["files"].get("prolific_id_link.json"))
        else:
            page.wait_for_selector("text=Local test finished", timeout=20000)
            print(page.inner_text("body"))
        print("errors:", errors)
        if JATOS: os.remove(os.path.join(HERE, "jatos.js"))
        sys.exit(0)

    page.screenshot(path="/tmp/shot_hp_done.png")
    click_enabled(page, "button:has-text('Start practice')")
    n_axb = 0
    while True:
        page.wait_for_function("() => document.body.innerText.includes('Middle matches') || "
                               "document.body.innerText.includes('Practice done')", timeout=30000)
        if "Practice done" in page.inner_text("body"):
            break
        time.sleep(0.05)
        ans = cur(page, "t.data && t.data.answer")
        page.wait_for_function("() => !!document.querySelector('audio') || true")
        # responses are accepted only after the audio ends
        for _ in range(100):
            page.keyboard.press("f" if ans == "first" else "j")
            time.sleep(0.15)
            if "Middle matches" not in page.inner_text("body") or cur(page, "t.data.answer") != ans:
                break
        n_axb += 1
    print("practice trials answered:", n_axb)
    click_enabled(page, "button:has-text('Start')")

    # main AXB (quick mode: 6 trials); answer 'last' always so accuracy is ~50%
    with_download = None
    while True:
        page.wait_for_function("() => document.body.innerText.includes('Middle matches') || "
                               "document.body.innerText.includes('Take a short break') || "
                               "document.body.innerText.includes('Listening task 2')", timeout=60000)
        body = page.inner_text("body")
        if "Listening task 2" in body:
            break
        if "Take a short break" in body:
            n_breaks = locals().get("n_breaks", 0) + 1
            if JATOS:
                print(f"break {n_breaks}: rows on server so far:", len(jatos_rows(page)[1]))
            click_enabled(page, "button:has-text('Continue')")
            continue
        before = page.evaluate("window.__jsPsych.data.get().count()")
        page.screenshot(path="/tmp/shot_axb.png")
        for _ in range(100):
            page.keyboard.press("j")
            time.sleep(0.15)
            if page.evaluate("window.__jsPsych.data.get().count()") > before:
                break
    click_enabled(page, "button:has-text('Start')")

    # sound matching: pick the first option, rate 5
    for i in range(39 if FULL else 4):
        page.wait_for_selector("#jspsych-audio-button-response-btngroup button:first-of-type:not([disabled])", timeout=20000)
        if i == 0: page.screenshot(path="/tmp/shot_assim.png")
        click_enabled(page, "#jspsych-audio-button-response-btngroup button:first-of-type", timeout=20000)
        click_enabled(page, "button:text-is('5')")

    page.fill("textarea[name=hard_pairs]", "v and w")
    page.click("#jspsych-survey-html-form-next")
    if JATOS:
        click_enabled(page, "button:has-text('Finish')")
        page.wait_for_selector("text=JATOS mock", timeout=20000)
        log, rows = jatos_rows(page, dump=True)
        rows = [{k: ("true" if v is True else "false" if v is False else "" if v is None else str(v))
                 for k, v in r.items()} for r in rows]
        print("JATOS appends:", len(log["appended"]), "| ended:", log["ended"])
        print("id file:", log["files"].get("prolific_id_link.json"))
        all_rows = page.evaluate("window.__jsPsych.data.get().values()")
        saved = {int(r["trial_index"]) for r in rows}
        lost = [(r["trial_index"], r.get("trial_type"), r.get("task")) for r in all_rows
                if r["trial_index"] not in saved]
        print("rows in browser:", len(all_rows), "| rows on server:", len(rows), "| not on server:", lost)
        os.remove(os.path.join(HERE, "jatos.js"))
    else:
        with page.expect_download() as dl:
            page.click("button:has-text('Finish')")
        path = dl.value.path()
        rows = list(csv.DictReader(open(path, encoding="utf-8")))
        page.wait_for_selector("text=Local test finished")
        print(page.inner_text("body"))
    tasks = {}
    for r in rows:
        tasks[r.get("task", "")] = tasks.get(r.get("task", ""), 0) + 1
    print("rows by task:", tasks)
    axb = [r for r in rows if r.get("task") == "axb"]
    print("axb example:", {k: axb[0][k] for k in ["contrast", "role", "pair_id", "order", "answer", "response_side", "correct", "rt", "b_offset_ms", "rt_from_b_offset", "hand_merged", "auto_merged", "block"]})
    print("axb trials by role:", {r: sum(x["role"] == r for x in axb) for r in ("test", "catch")},
          "| blocks:", sorted({x["block"] for x in axb}))
    print("rt_from_b_offset all >= 0:", all(float(x["rt_from_b_offset"]) >= 0 for x in axb))
    print("axb correct == (answer=='last'):", all((r["correct"] == "true") == (r["answer"] == "last") for r in axb))
    hp = [r for r in rows if r.get("task") == "headphone"]
    print("headphone correct:", sum(r["correct"] == "true" for r in hp), "/", len(hp))
    print("assim choices:", [(r["phone"], r["hindi_choice"]) for r in rows if r.get("task") == "assim_choice"])
    print("goodness:", [r["goodness"] for r in rows if r.get("task") == "assim_goodness"])
    print("PID in trial data?", any("TESTPID" in ",".join(r.values()) for r in rows))
    print("page errors:", errors)
    b.close()
