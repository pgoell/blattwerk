"""The brief of the session that only uses the app (docs/teacher-run.md): what issues #220 and
#295 ask of it, that the words it quotes from the screen are still the frontend's, and that the
verbs it names are those of scripts/teacher-page.py. The tests read the files; nothing here starts
a stage or a browser.
"""

import importlib.util
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRIEF = (REPO / "docs/teacher-run.md").read_text()
MISE = "mise -C /home/pascal/Code/blattwerk run"
PRS = "## 25 minutes on the last five pull requests"
# The five sheets, each under a heading of its own.
TITLES = ["TR1 Rechnen", "TR2 Schreiben", "TR3 Bild und Tabelle", "TR4 Zwei Seiten", "TR5 Kopie"]
# The words a reader of the brief must find on the screen: to get through the five sheets, to
# know a page has loaded (`Neues Blatt`), and to give the tool a target by its name.
# `Quer` is not here: the source picks it in an expression, beside "Hoch" and "Wie Blatt". Nor is
# `Gespeichert`, the word the reader waits for in the editor: the bar picks it beside
# "Nicht gespeichert".
LABELS = [
    "PDF",
    "Lösungen",
    "Lösungen zeigen",
    "Anmelden",
    "E-Mail",
    "Passwort",
    "Beenden",
    "Meine Blätter",
    "Neues Blatt",
    "Titel",
    "Rückgängig",
    "Wiederholen",
    "Mehrere",
    "Y",
    "Höhe",
    "Füllung",
    "Füllung und Rand",
    "Farbe",
    "Rand",
    "Randstärke",
    "Schriftart",
    "Rechnen",
    "Zahlenraum",
    "Übertrag",
    "Eine Aufgabe mehr",
    "Eine Spalte mehr",
    "Lineatur",
    "Art der Lineatur",
    "Eine Zeile mehr",
    "Seitenbreite",
    "Ganze Seite",
    "Mehr",
    "Nachspurtext",
    "Tabelle",
    "Kopfzeile",
    "Neue Seite",
    "Nur diese Seite",
    "Meine Vorlagen",
    "Name der Vorlage",
    "Dieses Blatt als Vorlage",
]


def section(heading):
    """The brief from `heading` to the next heading of the same depth or above it."""
    depth = len(heading) - len(heading.lstrip("#"))
    rest = rf"[^\n]*\n(.*?)(?=^#{{1,{depth}}} |\Z)"
    found = re.search(rf"^{re.escape(heading)}{rest}", BRIEF, re.M | re.S)
    assert found, heading
    return found.group(1)


def on_screen(label, source):
    """Whether the frontend shows `label` to a user: as the text of an element, or as the name
    a control carries (`label`, `aria-label`, `title`, `placeholder`). A string elsewhere in the
    code does not count.
    """
    word = re.escape(label)
    named = rf'(?:label|title|placeholder)="{word}"'
    return re.search(rf"{named}|>\s*{word}\s*<|^\s*{word}\s*$", source, re.M)


def test_a9_the_brief_names_what_the_issue_asks():
    lines = [line for line in BRIEF.splitlines() if line.strip()]
    # The orchestrator waits for this line, and the reader copies it from the brief's end.
    assert lines[-1] == "DONE teacher-run"
    assert BRIEF.endswith("DONE teacher-run\n")
    assert "BLOCKED teacher-run: <reason>" in BRIEF

    # The stage, and the three lines it prints for the login.
    start = section("## Start the stage")
    assert f"{MISE} stage:up" in start
    for line in ("URL: http://127.0.0.1:8220", "E-Mail: teacher-run@stage.invalid", "Passwort: "):
        assert f"\n   {line}" in start, line
    assert f"{MISE} stage:down" in section("## Clean up")

    # Each sheet has its title in its heading and ends in the export and the look at the PDF.
    sheets = section("## The five sheets")
    assert len(re.findall(r"^### ", sheets, re.M)) == 5
    for n, title in enumerate(TITLES, 1):
        assert re.search(r"^\d+\. Export and compare\.", section(f"### {n}. "), re.M), title
        assert re.search(rf"^### {n}\. .*title `{title}`$", sheets, re.M), title
    assert "Click `PDF`" in section("## Export and compare")
    assert "`Lösungen`" in section("### 1. ")

    # The time box of the last part, and where its pull requests come from.
    prs = section(PRS)
    assert "Stop after 25 minutes" in prs
    assert "gh pr list -R pgoell/blattwerk --state merged -L 20" in prs
    # The boxes add up: 50 minutes in all, 25 of them here, and no word of the old 15.
    assert (
        "Time: 50 minutes in all. Start and sign in take 3, the five sheets 15, "
        "the pull requests 25, issues and clean up 7."
    ) in BRIEF
    assert "then spend 25 minutes trying to break" in BRIEF
    assert "15 minutes" not in BRIEF
    assert "more than 4 minutes is a finding" in BRIEF
    # Depth: a try for each claim, and no early end.
    assert "five claims gets five tries, not one" in prs
    assert "do not stop early" in prs

    issues = section("## Issues")
    for label in ("regression", "bug", "wish"):
        assert f"- `{label}`:" in issues, label
    assert "Open at most 8 issues in a run." in issues

    # No dash and no middle dot stands in for a comma. The app's own minus sign is neither.
    for mark in (0x2014, 0x2013, 0xB7):
        assert chr(mark) not in BRIEF, hex(mark)
    # A hyphen between two words with a blank on each side; a list's own hyphen starts its line.
    assert not re.search(r"\S - \S", BRIEF)


def test_a9_the_brief_forbids_all_but_the_use_of_the_app():
    rules = section("## Rules")
    allowed, forbidden = rules.split("\nForbidden:\n")
    assert "Real clicks and keys only." in allowed
    for ban in (
        "`evaluate_script`",
        "`curl`",
        "docker",
        "`/admin`",
        "`~/.local/share`",
        "Reading any file under `/home/pascal/Code/blattwerk`",
        "`gh pr diff`",
        "`gh pr view --json files`",
        "`blattwerk.pgoell.com`",
    ):
        assert ban in forbidden, ban
    # None of them is among the tools the brief hands out.
    assert "evaluate_script" not in allowed
    # The second tool and the way to mend one's own issue are handed out, and the tool is no way
    # around the bans.
    assert f"`{MISE} teacher:page -- <verb>`" in allowed
    assert "`gh issue edit`" in allowed
    assert "`open` takes paths of the stage only" in forbidden
    assert "gh issue edit <number> -R pgoell/blattwerk" in section("## Issues")
    assert "you opened in this run, and no other issue" in section("## Issues")


def brief_verbs():
    """The verbs of the tool as the brief names them: the list under Allowed, each call it
    spells out in full, and each it writes short with a target, a name or a key.
    """
    allowed = section("## Rules").split("\nForbidden:\n")[0]
    listed = re.findall(r"^  - `([a-z-]+)", allowed, re.M)
    called = re.findall(r"teacher:page -- ([a-z-]+)", BRIEF)
    short = re.findall(r'`([a-z-]+) (?:"|X,Y|[A-Z])', BRIEF)
    return listed, {*listed, *called, *short}


def test_every_verb_of_the_brief_is_a_verb_of_the_tool_and_has_a_test():
    spec = importlib.util.spec_from_file_location("teacher_page", REPO / "scripts/teacher-page.py")
    assert spec and spec.loader
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    # `start` and `stop` open and end the window; the tool keeps them apart from the rest.
    # `tidy` and `box` are no verb of a window: `main` takes them beside `start` and `stop`.
    verbs = {"start", "stop", "tidy", "box", *tool.VERBS}
    listed, named = brief_verbs()
    assert len(listed) == len(set(listed))
    assert named - verbs == set()
    assert verbs - set(listed) == set()
    tests = (REPO / "tests/test_teacher_page.py").read_text()
    for verb in tool.VERBS:
        assert re.search(rf"^def test_{verb.replace('-', '_')}_", tests, re.M), verb
    assert re.search(r"^def test_tidy_", tests, re.M)
    assert re.search(r"^def test_(a_)?box_", tests, re.M)


def test_the_brief_finds_its_verbs_where_it_writes_them():
    # Without the tool's file: the three ways the brief names a verb all find some.
    listed, named = brief_verbs()
    assert listed[:3] == ["start", "stop", "open"]
    assert {"shift-click", "double-click", "hover", "drag", "key", "type", "where"} <= named
    # A shell command or a tool of the MCP page is no verb.
    assert not named & {"mise", "gh", "rm", "fill", "pdftoppm"}
    # Nor is any other word: all the brief names are in its own list.
    assert named == set(listed)


def test_the_colour_recipe_presses_each_arrow_60_times():
    # Issue #314: one arrow moved #222222 to a grey the eye cannot tell from it.
    how = section("## How the editor works")
    assert "then `key ArrowUp 60`, `key ArrowRight 60`, `key Enter`. The picker" in how
    # No recipe of the brief ends a colour on one arrow up or to the side.
    assert not re.search(r"`key Arrow(?:Up|Left|Right)`, `key Enter`", BRIEF)


# What issue #321 found in the brief's second run, T1 to T9.


def test_t1_no_command_of_the_brief_chains_another():
    # Auto mode refused `stop; rm -rf … && mkdir … && rm -f …` as one line.
    blocks = re.findall(r"^ *```sh\n(.*?)^ *```$", BRIEF, re.M | re.S)
    assert len(blocks) > 10
    for block in blocks:
        lines = block.strip().splitlines()
        assert len(lines) == 1, block
        # What stands in quotes is a script or a word for another program, not the shell's.
        bare = re.sub(r"\"[^\"]*\"|'[^']*'", "", lines[0])
        assert not re.search(r";|&&|\|", bare), block
    # The matcher sees a chain: the line the brief had.
    assert re.search(r";|&&|\|", "teacher:page -- stop; rm -rf /tmp/teacher-run && mkdir x")
    start = section("## Start the stage")
    tidy = f"{MISE} teacher:page -- tidy"
    for line in ("rm -rf /tmp/teacher-run", "mkdir /tmp/teacher-run", tidy):
        assert f"```sh\n   {line}\n   ```" in start, line
    assert "Run each line as a command of its own" in start


def test_t2_the_export_fits_the_whole_page_before_its_screenshot():
    # The editor opens at 88 % with the page cut.
    export = section("## Export and compare")
    first = next(line for line in export.splitlines() if line.startswith("1. "))
    assert first.index("Click `Ganze Seite` in the bar first") < first.index("`take_screenshot`")
    by_tool = next(line for line in export.splitlines() if line.startswith("In the tool's window"))
    assert by_tool.index('`click "Ganze Seite"`') < by_tool.index("`screenshot 3-screen`")


def test_t3_the_two_pages_of_sheet_4_are_shot_in_the_tools_window():
    # The MCP page has no wheel, and PageUp does nothing there.
    sheet4 = section("### 4. ")
    assert "the MCP page cannot scroll back to page 1" in sheet4
    last = sheet4.strip().splitlines()[-1]
    assert last.startswith("6. Export and compare. Here in the tool's window.")
    at = [last.index(f"`{call}`") for call in ("screenshot 4-screen-1", "wheel X,Y 1000", "pdf")]
    assert at == sorted(at)
    assert at[1] < last.index("`screenshot 4-screen-2`") < at[2]
    # The sheet is in one window at a time: it leaves the MCP page first, and the tool's after.
    assert '`open /`, `click "TR4 Zwei Seiten"`' in sheet4
    assert last.endswith("Then `open /`: sheet 5 starts in the MCP page.")
    assert "from the tool's window: see sheet 4" in section("## Export and compare")


def test_t4_the_picture_and_the_table_of_sheet_3_each_get_a_y():
    # The picture landed on top of the heading. The heading ends 29 mm from the top, and the
    # picture, 100 mm wide at most, is 67 high.
    steps = section("### 3. ").splitlines()
    picture = next(line for line in steps if line.startswith("3. "))
    table = next(line for line in steps if line.startswith("4. "))
    assert "on top of the heading. Move it below: `fill` the field `Y` with `40`" in picture
    assert "below the picture: `fill` the field `Y` with `115`" in table
    assert 15 + 14 < 40 and 40 + 67 < 115


def test_t5_the_colour_recipe_reads_the_colour_with_the_verb_value():
    how = section("## How the editor works")
    assert 'read the colour before and after, with `value "Rand"`' in how
    assert "  - `value NAME`: prints what the field of that name holds" in BRIEF


def test_t6_a_reload_in_the_tools_window_is_open_and_not_f5():
    prs = section(PRS)
    assert "`key F5` does not reload the tool's window: there a reload is `open /blatt/N`" in prs
    # No step of the brief asks for the key.
    assert BRIEF.count("F5") == 1


def test_t7_where_takes_a_part_and_a_target_the_whole_name():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `where NAME`"))
    assert "A whole name or text goes first." in listed
    assert "each name or text that holds `NAME`, with capitals as written" in listed
    assert "a control's whole name or a whole text on the screen" in BRIEF


def test_t8_a_name_the_narrow_bar_folded_away_lies_under_mehr():
    allowed = section("## Rules").split("\nForbidden:\n")[0]
    assert "at 820 wide the zoom's `Ganze Seite`" in allowed
    assert 'the error then says the name may lie under `Mehr`, so `click "Mehr"`' in allowed
    # The words are the tool's.
    assert 'it may lie under "Mehr"' in (REPO / "scripts/teacher-page.py").read_text()


def test_t9_the_brief_says_that_pdf_leaves_the_focus_where_it_was():
    listed = next(line for line in BRIEF.splitlines() if line.startswith("  - `pdf [TARGET]`"))
    assert "The focus stays where it was: a slider you clicked before still takes" in listed


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
    assert len(commands) == 2
    for command in commands:
        assert "-L 20 --json number,title,body,url,mergedAt" in command
        assert "--jq 'sort_by(.mergedAt) | reverse | " in command
    assert ".[0:5][] |" in commands[0]
    assert ".[5:10][] |" in commands[1]
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
    assert "Keep `/tmp/teacher-run`, because the issues name its screenshots." in clean
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


# What issue #406 found in the brief's fourth run, 1 to 11. Point 1 is a test of the tool.


def test_406_2_sheet_4_sets_the_title_in_the_window_that_built_the_sheet():
    sheet4 = section("### 4. ")
    mcp, built_in_tool = sheet4.split("- built in the tool's window:")
    assert "- built in the MCP page:" in mcp
    assert "`type_text` `TR4 Zwei Seiten`" in mcp
    tool_title = '`click "Titel"`, `key Control+a`, `type "TR4 Zwei Seiten"`, `key Enter`'
    assert tool_title in built_in_tool
    assert "`fill`" not in sheet4


def test_406_3_a_control_below_the_window_gets_a_wheel_on_the_panel_first():
    how = section("## How the editor works")
    lines = how.splitlines()
    bullet = next(line for line in lines if line.startswith("  - a control of the right panel"))
    assert "below the window's lower edge" in bullet
    assert "`wheel`" in bullet and "the panel first" in bullet
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    for label in ("Randstärke", "Jedes n-te Wort", "Lösungswörter"):
        assert f"`{label}`" in bullet, label
        assert on_screen(label, source), label


def test_406_4_a_snapshot_is_searched_in_its_file_with_the_grep_tool():
    allowed = section("## Rules").split("\nForbidden:\n")[0]
    grep = "- The Grep tool, on a snapshot file in `/tmp/teacher-run` and on nothing else."
    assert grep in allowed
    assert "`take_snapshot` with its `filePath` `/tmp/teacher-run/" in allowed
    assert "do not search that answer" in allowed


def test_406_5_the_jq_leaves_out_the_types_a_teacher_cannot_see_before_five_are_taken():
    prs = section(PRS)
    commands = re.findall(r"gh pr list [^\n]*--jq '(.+)'$", prs, re.M)
    assert len(commands) == 2
    # Sixteen merged pull requests, newest first. The ones that are no teacher's: 1, 3, 5, 7, 9, 10.
    titles = [
        "ci(deps): bump a runner",
        "feat: a word",
        "docs: the readme",
        "fix: a line",
        "chore: bump",
        "perf: a list",
        "test: a case",
        "feat(ui): a panel",
        "build: a script",
        "refactor: a helper",
        "fix!: a page",
        "feat: a word",
        "perf: a sum",
        "fix: a box",
        "feat: a bank",
        "fix: a tab",
    ]
    merged = [
        {
            "number": n + 1,
            "title": title,
            "url": f"https://github.com/pgoell/blattwerk/pull/{n + 1}",
            "body": "a body",
            "mergedAt": f"2026-10-{30 - n:02d}T10:00:00Z",
        }
        for n, title in enumerate(titles)
    ]
    listed = []
    for command in commands:
        out = subprocess.run(
            ["jq", "-r", command],
            input=json.dumps(merged),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        listed.append([int(n) for n in re.findall(r"^#(\d+) ", out, re.M)])
    assert listed == [[2, 4, 6, 8, 11], [12, 13, 14, 15, 16]]


def test_406_7_a_delete_in_the_mcp_page_is_answered_with_handle_dialog():
    para = next(line for line in BRIEF.splitlines() if line.startswith("Which window for what."))
    delete = "A delete in the MCP page (a button whose name ends in `löschen`) opens a browser box"
    assert delete in para
    assert "answer it with `handle_dialog`" in para
    assert "`handle_dialog`" in section("## Rules").split("\nForbidden:\n")[0]


def test_406_9_tidy_is_the_last_command_and_the_herdr_line_follows_it():
    clean = section("## Clean up")
    assert clean.rindex(f"{MISE} teacher:page -- tidy") < clean.index("`herdr` line")
    assert "very last command before the `herdr` line" in clean
    assert "the `herdr` line that the orchestrator's prompt gives you" in clean


def test_406_10_the_above_all_split_still_adds_up_to_50_minutes():
    split = next(part for part in BRIEF.split("\n\n") if "above all" in part)
    assert "five sheets get 10 minutes, not 15" in split
    assert "build sheets 1, 3 and 4 only" in split
    assert "pull requests get 30 minutes, not 25" in split
    assert "at least 20 of the 30 minutes" in split
    assert "Issues and clean up keep 7" in split
    sheets = re.search(r"sheets get (\d+) minutes", split)
    pulls = re.search(r"pull requests get (\d+) minutes", split)
    issues = re.search(r"clean up keep (\d+)", split)
    assert sheets and pulls and issues
    # The start takes 3, as the time box above says.
    assert "Start and sign in take 3" in BRIEF
    assert 3 + int(sheets[1]) + int(pulls[1]) + int(issues[1]) == 50
    # Step 1 of the pull requests says the same stop: 30 minutes with an "above all".
    step = next(line for line in section(PRS).splitlines() if line.startswith("1. Note the time"))
    assert 'Stop after 25 minutes (30 when an "above all" is named' in step


def test_406_11_a_gap_of_two_words_has_its_steps():
    how = section("## How the editor works")
    bullet = next(line for line in how.splitlines() if line.startswith("- A gap of two words"))
    assert "`key Home`" in bullet
    assert "`key Control+Shift+ArrowRight 2`" in bullet
    assert '`click "Lücke"`' in bullet
