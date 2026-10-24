"""How the teacher-run brief writes its steps: one command a line, the stage, the words on the screen."""

import json
import re
import subprocess

from test_teacher_run import BRIEF, LABELS, MISE, PRS, REPO, on_screen, section


def test_the_filter_trims_a_long_body():
    # The first run's 39 KB were cut off; the filter leaves each body its first 2500 characters.
    command = re.search(r"gh pr list [^\n]* -L 20 [^\n]*--jq '(.+)'$", section(PRS), re.M)
    assert command
    url = "https://github.com/pgoell/blattwerk/pull/7"
    prs = [
        {
            "number": 7,
            "title": "fix: a thing",
            "url": url,
            "body": "ä" * 10000,
            "mergedAt": "2026-10-10T10:00:00Z",
        }
    ]
    out = subprocess.run(
        ["jq", "-r", command.group(1)],
        input=json.dumps(prs),
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.startswith(f"#7 fix: a thing\n{url}\n")
    assert out.count("ä") == 2500
    assert len(out) < 2600


def test_a9_the_brief_starts_the_stage_first_and_stops_it_last():
    at = [
        BRIEF.index(part)
        for part in (
            "## Rules",
            f"{MISE} stage:up",
            "## Sign in",
            f"{MISE} teacher:page -- start",
            "## The five sheets",
            PRS,
            "## Issues",
            "## Clean up",
            f"{MISE} stage:down",
            "## Report",
        )
    ]
    # The window goes before the stage whose login it holds.
    clean = section("## Clean up")
    assert clean.index(f"{MISE} teacher:page -- stop") < clean.index(f"{MISE} stage:down")
    # A window of an earlier run goes before the folder that knows where it is.
    start = section("## Start the stage")
    assert start.index(f"{MISE} teacher:page -- stop\n") < start.index("rm -rf /tmp/teacher-run\n")
    assert at == sorted(at)
    # The window ends before the stage it looks at, and both in the part that is done always.
    assert f"{MISE} teacher:page -- stop" in section("## Clean up")


def test_a9_the_brief_quotes_the_words_on_the_screen():
    # A label the frontend renames fails here, before a reader looks for it in vain.
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    for label in LABELS:
        # As a word of the screen, or as the name a verb of the tool takes.
        assert f"`{label}`" in BRIEF or f'"{label}"' in BRIEF, label
        assert on_screen(label, source), label
    # The word every wait of the brief hangs on: the bar picks it in an expression.
    assert '"Gespeichert"' in source
    # The matcher tells a control's name from a string of the code.
    assert not on_screen("Quer", source)


def test_the_brief_waits_for_a_sheet_that_loads():
    # A sheet that loads shows the editor's frame and an empty page (#313): a snapshot of that
    # holds no control. The brief names what stands there, and both words to wait for.
    how = next(line for line in section("## How the editor works").splitlines() if "`Lädt`" in line)
    assert "`wait_for` the text `Gespeichert` before the first snapshot of a sheet" in how
    assert "the text `Neues Blatt` before the first snapshot of `Meine Blätter`" in how
    assert 'run `where "Gespeichert"` or `where "Neues Blatt"` until it prints a match' in how
    # The loading page says the word the brief quotes, and neither of those it waits for.
    blank = (REPO / "frontend/src/components/Blank.tsx").read_text()
    assert '"Lädt"' in blank
    assert "Gespeichert" not in blank and "Neues Blatt" not in blank


# What issue #366 found in the brief's third run, T1 to T9.


def test_t1_the_brief_clears_downloads_with_the_verb_tidy():
    # The session's permission check refused `rm -f ~/Downloads/TR*.pdf`.
    assert "rm -f ~/Downloads" not in BRIEF
    assert f"{MISE} teacher:page -- tidy" in section("## Start the stage")
    assert f"{MISE} teacher:page -- tidy" in section("## Clean up")


def test_t2_both_pr_lists_take_20_and_keep_five_by_merge_time():
    prs = section(PRS)
    commands = [line.strip() for line in prs.splitlines() if line.strip().startswith("gh pr list")]
    assert len(commands) == 3
    for command in commands:
        assert "-L 20 --json number,title,body,url,mergedAt" in command
        assert "--jq 'sort_by(.mergedAt) | reverse | " in command
    assert ".[0:5][] |" in commands[0]
    assert ".[5:10][] |" in commands[1]
    # Issue #497: a `test` title can still change the app, so the third list keeps those.
    assert 'test("^test[(:!]")' in commands[2]
    assert "-L 5 " not in prs


def test_t3_the_title_is_set_by_select_all_and_type_not_by_fill():
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if "name in `Titel`" in line)
    assert '`click "Titel"`, `key Control+a`, `type "' in bullet
    assert "`press_key` Control+A, `type_text` the name, `press_key` Enter" in bullet
    assert "Do not `fill` it" in bullet
    assert "`fill` the field `Titel`" not in BRIEF and "`fill` `Titel`" not in BRIEF


def test_t4_the_brief_answers_a_box_with_box_yes_or_box_no():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `box "))
    assert "`box yes VERB [ARGS]`" in listed and "`box no VERB [ARGS]`" in listed
    assert "A verb without `box` answers no." in listed
    assert "löschen" in listed and "`open`" in listed


def test_t5_the_brief_does_not_say_a_chained_line_is_refused():
    start = section("## Start the stage")
    assert "refused" not in start
    assert "Run each line as a command of its own." in start


def test_t6_the_brief_lists_expire_and_says_when_to_use_it():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `expire`"))
    assert "the page stays as it is" in listed
    line = "with the session run out: `expire`, then go on working; the MCP page stays signed in."
    assert line in section(PRS)


def test_t7_tidy_runs_after_the_stage_is_down_and_once_more_at_the_end():
    clean = section("## Clean up")
    assert clean.index(f"{MISE} stage:down") < clean.index(f"{MISE} teacher:page -- tidy")
    assert "very last command before the `herdr` line" in clean
    assert (
        "Keep the folder `/tmp/teacher-run` and its pictures, because the issues name its" in clean
    )
    report = section("## Report")
    assert re.search(r"^8\. What the last `tidy` deleted, if anything\.$", report, re.M)


def test_t8_the_brief_says_that_wait_for_answers_with_the_snapshot():
    how = next(line for line in section("## How the editor works").splitlines() if "`Lädt`" in line)
    assert "The answer of `wait_for` is a snapshot of the whole page" in how
    assert "take no `take_snapshot` right after it" in how


def test_t9_the_brief_says_to_start_at_once_and_ask_nobody():
    # The order comes right after the first paragraph, before the bar and the time.
    order = BRIEF.split("\n\n")[2]
    assert "whoever pasted it" in order
    assert "Start at once." in order
    assert "Ask nobody for a go" in order
    assert "end with one of the two last lines" in order
