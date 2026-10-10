"""The brief of the session that only uses the app (docs/teacher-run.md): what issue #220 asks
of it, and that the words it quotes from the screen are still the frontend's. The tests read the
files; nothing here starts a stage or a browser.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRIEF = (REPO / "docs/teacher-run.md").read_text()
MISE = "mise -C /home/pascal/Code/blattwerk run"
# The five sheets, each under a heading of its own.
TITLES = ["TR1 Rechnen", "TR2 Schreiben", "TR3 Bild und Tabelle", "TR4 Zwei Seiten", "TR5 Kopie"]
# The words a reader of the brief must find on the screen to get through the five sheets.
# `Quer` is not here: the source picks it in an expression, beside "Hoch" and "Wie Blatt".
LABELS = [
    "PDF",
    "Lösungen",
    "Lösungen zeigen",
    "Anmelden",
    "Beenden",
    "Neues Blatt",
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
    prs = section("## 15 minutes on the last five pull requests")
    assert "Stop after 15 minutes" in prs
    assert "gh pr list -R pgoell/blattwerk --state merged -L 5" in prs

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


def test_a9_the_brief_starts_the_stage_first_and_stops_it_last():
    at = [
        BRIEF.index(part)
        for part in (
            "## Rules",
            f"{MISE} stage:up",
            "## Sign in",
            "## The five sheets",
            "## 15 minutes on the last five pull requests",
            "## Issues",
            f"{MISE} stage:down",
            "## Report",
        )
    ]
    assert at == sorted(at)


def test_a9_the_brief_quotes_the_words_on_the_screen():
    # A label the frontend renames fails here, before a reader looks for it in vain.
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    for label in LABELS:
        assert f"`{label}`" in BRIEF, label
        assert on_screen(label, source), label
    # The matcher tells a control's name from a string of the code.
    assert not on_screen("Quer", source)
