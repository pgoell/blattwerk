"""The brief of the session that only uses the app (docs/teacher-run.md): what issue #220 asks
of it, and that the words it quotes from the screen are still the frontend's. The test reads the
files; nothing here starts a stage or a browser.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BRIEF = (REPO / "docs/teacher-run.md").read_text()
MISE = "mise -C /home/pascal/Code/blattwerk run"
# The words a reader of the brief must find on the screen to get through the five sheets.
LABELS = [
    "PDF",
    "Lösungen",
    "Lösungen zeigen",
    "Anmelden",
    "Neues Blatt",
    "Rechnen",
    "Lineatur",
    "Tabelle",
    "Neue Seite",
    "Nachspurtext",
    "Kopfzeile",
    "Dieses Blatt als Vorlage",
]


def on_screen(label, source):
    """Whether the frontend shows `label` whole: as a string, between tags or alone on a line."""
    word = re.escape(label)
    return re.search(rf'"{word}"|>{word}<|^\s*{word}\s*$', source, re.M)


def test_a9_the_brief_names_what_the_issue_asks():
    lines = [line for line in BRIEF.splitlines() if line.strip()]
    # The orchestrator waits for this line, and the reader copies it from the brief's end.
    assert lines[-1] == "DONE teacher-run"
    assert BRIEF.endswith("DONE teacher-run\n")
    assert "BLOCKED teacher-run: <reason>" in BRIEF

    assert f"{MISE} stage:up" in BRIEF
    assert f"{MISE} stage:down" in BRIEF
    assert "http://127.0.0.1:8220" in BRIEF
    assert "gh pr list -R pgoell/blattwerk --state merged -L 5" in BRIEF

    for label in ("regression", "bug", "wish"):
        assert f"- `{label}`:" in BRIEF, label
    assert "Open at most 8 issues in a run." in BRIEF

    # No dash and no middle dot stands in for a comma. The app's own minus sign is neither.
    for mark in (0x2014, 0x2013, 0xB7):
        assert chr(mark) not in BRIEF, hex(mark)
    # A hyphen between two words with a blank on each side; a list's own hyphen starts its line.
    assert not re.search(r"\S - \S", BRIEF)

    # A label the frontend renames fails here, before a reader looks for it in vain.
    source = "\n".join(p.read_text() for p in sorted((REPO / "frontend/src").rglob("*.tsx")))
    for label in LABELS:
        assert f"`{label}`" in BRIEF, label
        assert on_screen(label, source), label
