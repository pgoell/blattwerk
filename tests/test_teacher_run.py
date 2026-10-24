"""The brief of the session that only uses the app (docs/teacher-run.md joins docs/teacher-run/):
what issues #220 and #295 ask of it, that the words it quotes from the screen are still the
frontend's, and that the verbs it names are those of scripts/teacher-page.py. The tests read the
files; nothing here starts a stage or a browser.
"""

import importlib.util
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# The index at docs/teacher-run.md links these pages. Joined, they are the brief the tests read.
BRIEF_PARTS = (
    "order.md",
    "rules.md",
    "stage.md",
    "editor.md",
    "sheets.md",
    "pulls.md",
    "after.md",
)
BRIEF = "".join((REPO / "docs" / "teacher-run" / name).read_text() for name in BRIEF_PARTS)
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
    "Abmelden",
    "Andere Version laden",
    "Mit dieser überschreiben",
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
    # The tests of one behaviour each live beside test_teacher_page.py.
    tests = "\n".join(
        path.read_text() for path in sorted((REPO / "tests").glob("test_teacher_page*.py"))
    )
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
