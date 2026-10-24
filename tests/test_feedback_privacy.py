"""The privacy check that stands between a teacher's feedback and a public issue."""

import importlib.util
import re
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).parent.parent / "scripts" / "feedback_privacy.py"
_SPEC = importlib.util.spec_from_file_location("feedback_privacy", _SCRIPT)
assert _SPEC and _SPEC.loader
feedback_privacy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(feedback_privacy)

check = feedback_privacy.check

EMAILS = [
    "anna.schmidt@gmail.com",
    "kollegium@astrid-lindgren-gs.de",
    "info@web.de",
    "kraus@t-online.de",
    "m.müller@schule-x.de",
    "łukasz.k@schule-x.de",
]
NAMES = ["2026-10-08T06-50-36-363466", "feedback.json", "screenshot-1.jpg", "/blatt/41"]
SOURCE = "die plus und minus tasten ändern den zoom immer um zwei prozent"
SEND = "Lena findet Aufgabe 3 zu schwer, und Tim aus der Klasse auch. Der Text passt nicht ins PDF."

KINDS = [
    "user email",
    "user name",
    "user id",
    "file name",
    "email address",
    "link",
    "mention",
    "class name",
    "school name",
    "copied words",
]

HITS = [
    ("user email", "Mail from Anna.Schmidt@GMAIL.com today"),
    ("user email", "reach kollegium@astrid-lindgren-gs.de"),
    ("user email", "info@web.de"),
    ("user name", "anna.schmidt reported the bug"),
    ("user name", "Schmidt reported the bug"),
    ("user name", "Der Schmidt-Fall"),
    ("user name", "schmidt2 reported the bug"),
    ("user name", "a note from Lindgren"),
    ("user name", "see astrid-lindgren-gs.de"),
    ("user name", "Kollegium meets today"),
    ("user id", "user 7 keeps failing"),
    ("user id", "users/7 can not log in"),
    ("user id", "Nutzer 7 sees nothing"),
    ("user id", "id 7 is broken"),
    ("user id", "User #12 says hello"),
    ("user id", "the bug is in user_id=3"),
    ("user id", "Benutzer:4 hat Fehler"),
    ("user id", "Konto 9"),
    ("user id", "teacher 3 asked"),
    ("user id", "userid7 is broken"),
    ("user id", "teacherid 7 is broken"),
    ("user id", "Benutzer-Nr. 7 sagt"),
    ("user id", "user no. 7 sagt"),
    ("user id", "Nutzernummer 12 sagt"),
    ("user name", "Frau Ｋｒａｕｓ sagt"),  # noqa: RUF001 (full-width letters are the test)
    ("user name", "Frau Kr​aus sagt"),
    ("user name", "Frau K̈raus sagt"),
    ("user name", "Müller reported the bug"),
    ("user name", "MÜLLER reported the bug"),
    ("user name", "muller reported the bug"),
    ("user name", "Łukasz sagt"),
    ("file name", "see 2026-10-08T06-50-36-363466"),
    ("file name", "folder 2026-01-02T03-04-05 is odd"),
    ("file name", "feedback.json attached"),
    ("file name", "see screenshot-1.jpg"),
    ("file name", "Screenshot-1.JPG shows it"),
    ("file name", "photo-2.heic shows it"),
    ("file name", "audio-3.mp3 attached"),
    ("file name", "see /blatt/41"),
    ("file name", "open /blatt/7 and see"),
    ("email address", "write to max.muster@example.org"),
    ("email address", "x@y.de"),
    ("link", "see https://example.org/x"),
    ("link", "see www.example.org"),
    ("link", "HTTP://EXAMPLE.ORG"),
    ("mention", "thanks @pgoell"),
    ("mention", "(@anna) asked"),
    ("class name", "it is a 3b thing"),
    ("class name", "4A is broken"),
    ("class name", "Klasse 3 cannot log in"),
    ("class name", "class 2 c has the bug"),
    ("class name", "Jahrgang 2 sees it"),
    ("school name", "Astrid-Lindgren-Schule"),
    ("school name", "Goethe-Grundschule"),
    ("school name", "Grundschule am Wald"),
    ("school name", "Grundschule Musterstadt"),
    ("school name", "GS Nordend"),
    ("school name", "Lincoln Primary School"),
    ("copied words", "Die PLUS, und minus Tasten ändern den Zoom"),
    ("copied words", "die plus! und; minus tasten"),
]

CLEAN = [
    "1. Open the editor.\n2. Press Ctrl and plus.\n3. The zoom changes by 2%.",
    "A4 paper, 10 pt font, step 3 of the guide.",
    "A Grundschule teacher asked for a dark theme.",
    "Primary school teachers want larger buttons.",
    "The info page and the mail button need work.",
    "The web looks fine in gmail, a plain word here.",
    "Annual reports load slowly on the start page.",
    "Schmidts are not the topic here.",
    "Bei uns sind die plus und die Tasten kaputt.",
    "Would a dark mode help teachers in the evening?",
    "the user interface has three tabs",
    "The teacher zooms in 2 times",
]


@pytest.mark.parametrize("reason, text", HITS)
def test_hit(reason, text):
    assert reason in check(text, EMAILS, NAMES, SOURCE)


@pytest.mark.parametrize("text", CLEAN)
def test_clean(text):
    assert check(text, EMAILS, NAMES, SOURCE) == []


@pytest.mark.parametrize(
    "text",
    [
        "Lena's view: Task 3 is too hard",
        "Tim cannot solve it",
        "the Aufgabe is too hard",
    ],
)
def test_word_from_send_hit(text):
    assert "word from the send" in check(text, EMAILS, NAMES, SEND)


@pytest.mark.parametrize(
    "text, source",
    [
        (
            "A pupil finds task 3 too hard, and so does a second one. "
            "The text does not fit into the PDF.",
            SEND,
        ),
        ("The task is too hard", "The task is simple and fine."),
    ],
)
def test_word_from_send_clean(text, source):
    assert check(text, EMAILS, NAMES, source) == []


def test_reason_names_the_kind_only():
    text = (
        "anna.schmidt@gmail.com, see https://x.de, @pgoell, class 3b, user 7, "
        "screenshot-1.jpg, Astrid-Lindgren-Schule and Lindgren, "
        "die plus und minus tasten ändern den zoom."
    )
    reasons = check(text, EMAILS, NAMES, SOURCE)
    assert reasons == KINDS
    joined = " ".join(reasons).lower()
    for secret in ["anna", "schmidt", "gmail", "lindgren", "pgoell", "3b", "screenshot"]:
        assert secret not in joined


def test_each_kind_once_with_two_hits():
    text = (
        "anna.schmidt@gmail.com and kollegium@astrid-lindgren-gs.de; "
        "https://a.de and www.b.de; user 7 and user 8; @pgoell @anna"
    )
    assert check(text, EMAILS, NAMES, SOURCE) == [
        "user email",
        "user name",
        "user id",
        "email address",
        "link",
        "mention",
    ]


def test_empty_names_do_not_hit():
    assert check("Ein sauberer Text ohne alles.", EMAILS, ["", "/blatt/41"], SOURCE) == []


@pytest.mark.parametrize(
    "text, reasons",
    [
        ("Anna wrote the bug report", []),
        ("Schritt 3 auf /blatt/7 und https://x.org", ["file name", "link"]),
    ],
)
def test_no_users(text, reasons):
    assert check(text, [], [], SOURCE) == reasons


@pytest.mark.parametrize(
    "text, send",
    [
        ("The Lineatur block shows one row too few", "Die Lineatur hat eine Zeile zu wenig"),
        ("The Uhr block draws the hands wrong", "Die Uhr zeigt falsch"),
        ("The Lineaturen are too thin", "Die Lineaturen sind zu dünn"),
    ],
)
def test_block_names_are_no_send_words(text, send):
    assert check(text, EMAILS, NAMES, send) == []


def test_a_name_beside_a_block_name_is_still_caught():
    send = "Lena sagt, die Lineatur ist zu klein"
    assert "word from the send" in check("Lena says the Lineatur is too small", EMAILS, NAMES, send)


def test_copied_words_beside_a_block_name_are_still_caught():
    send = "Die Lineatur hat eine Zeile zu wenig für Paul"
    text = "Die Lineatur hat eine Zeile zu wenig, sagt er"
    assert "copied words" in check(text, EMAILS, NAMES, send)


def test_every_editor_block_name_is_allowed():
    editor = "\n".join(
        p.read_text()
        for p in sorted((Path(__file__).parent.parent / "frontend/src/pages/editor").rglob("*"))
        if p.suffix in {".ts", ".tsx"}
    )
    names = []
    for const in ("NAMES", "PLURALS"):
        body = re.search(rf"const {const}\b[^=]*= \{{(.*?)\n\}};", editor, re.DOTALL)
        assert body, f"{const} not found in the editor modules"
        names += re.findall(r'"([^"]+)"', body.group(1))
    single = [n for n in names if " " not in n]
    assert len(single) > 30
    for name in single:
        assert name in feedback_privacy.BLOCK_NAMES, name
