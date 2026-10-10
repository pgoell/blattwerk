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
    assert "gh pr list -R pgoell/blattwerk --state merged -L 5" in prs
    # The boxes add up: 45 minutes in all, 25 of them here, and no word of the old 15.
    assert "Time: 45 minutes in all. Start and sign in take 3, the five sheets 15, " in BRIEF
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
    verbs = {"start", "stop", *tool.VERBS}
    listed, named = brief_verbs()
    assert len(listed) == len(set(listed))
    assert named - verbs == set()
    assert verbs - set(listed) == set()
    tests = (REPO / "tests/test_teacher_page.py").read_text()
    for verb in tool.VERBS:
        assert re.search(rf"^def test_{verb.replace('-', '_')}_", tests, re.M), verb


def test_the_brief_finds_its_verbs_where_it_writes_them():
    # Without the tool's file: the three ways the brief names a verb all find some.
    listed, named = brief_verbs()
    assert listed[:3] == ["start", "stop", "open"]
    assert {"shift-click", "double-click", "hover", "drag", "key", "type", "where"} <= named
    # A shell command or a tool of the MCP page is no verb.
    assert not named & {"mise", "gh", "rm", "fill", "pdftoppm"}
    # Nor is any other word: all the brief names are in its own list.
    assert named == set(listed)


def test_the_filter_trims_a_long_body():
    # The first run's 39 KB were cut off; the filter leaves each body its first 2500 characters.
    command = re.search(r"gh pr list [^\n]* -L 5 [^\n]*--jq '(.+)'$", section(PRS), re.M)
    assert command
    url = "https://github.com/pgoell/blattwerk/pull/7"
    prs = [{"number": 7, "title": "fix: a thing", "url": url, "body": "ä" * 10000}]
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
            f"{MISE} teacher:page -- stop",
            f"{MISE} stage:down",
            "## Report",
        )
    ]
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
    # The matcher tells a control's name from a string of the code.
    assert not on_screen("Quer", source)
