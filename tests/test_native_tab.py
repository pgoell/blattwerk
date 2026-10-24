"""Tab through the panel in a real window, and the keys that set what Tab reaches.

The helpers live in test_native.py.
"""

import pytest
from playwright.sync_api import expect
from test_native import (
    press,
)
from test_suchsel import SUCHSEL
from ui import RECT, TEXT, at, box, expect_picked, maths, user

pytestmark = pytest.mark.native

WALL = {"count": 4, "columns": 2, "max": 20, "op": "+", "given": "base", "empty": False, "seed": 7}
# What Tab stops at from the panel's first field on, down to the kinds of border.
START = ["von", "X", "Y", "Breite", "Höhe", "Drehung"]
START += ["Seitenverhältnis sperren", "Breite %", "Höhe %"]
FONT = ["Schriftart", "Schrift kleiner", "Schrift größer", "Fett", "Kursiv", "Unterstrichen"]
PLACE = ["Aufzählung", "Nummerierung", "Links", "Mitte", "Rechts", "Oben", "Mitte", "Unten"]
TURN = [
    "Farbe",
    "Zeilenabstand",
    "Nachspurtext",
    "Silbenbögen",
    "Silbenfarbe",
    "Lücke",
    "Lücken gleich breit",
    "n",
    "Jedes n-te Wort",
    "Lösungswörter",
    "Text des Textfelds",
    "Schüttelwörter",
    "Rechtsdrehung 90°",
    "Linksdrehung 90°",
]
FLIP = ["Horizontal spiegeln", "Vertikal spiegeln"]
OUTLINE = ["Keine", "1 2 3", "a b c", "Symbol", "Eckig", "Abgerundet", "Rund", "Dreieck"]
FILL = ["Stern", "Sprechblase", "Füllung", "Rand"]
DASH = ["Randstärke", "Durchgezogen", "Gestrichelt", "Gepunktet"]
ORDER = {
    # A text alone has the switch of the line numbers after the solution words and Schüttelwörter.
    # Text anpassen is the first control of the text, after the place and the size.
    "text": (
        TEXT,
        [
            *START,
            "Text anpassen",
            *FONT,
            *PLACE,
            *TURN[:-2],
            "Zeilennummern",
            *TURN[-2:],
            *OUTLINE,
            *FILL,
            *DASH,
        ],
    ),
    # A shape can be mirrored, and its border, which it has, can be taken away.
    # The border's transparency (#129) comes after its width; a text has no border, so it is off.
    "shape": (
        RECT,
        [
            *START,
            *FONT,
            *PLACE,
            *TURN,
            *FLIP,
            *OUTLINE,
            *FILL,
            "Kein Rand",
            DASH[0],
            "Transparenz Linie",
            *DASH[1:],
        ],
    ),
    # "Lernwörter übernehmen" is off in this sheet, which has no Lernwörter, so Tab skips it.
    "suchsel": (
        SUCHSEL,
        [
            *START,
            "Wörter des Suchsels",
            "Eine Spalte weniger",
            "Eine Spalte mehr",
            "Eine Zeile weniger",
            "Eine Zeile mehr",
            "Richtungen",
            "Nur Großbuchstaben",
            "Umlaute und ß behalten",
            "Wörterliste",
            "Nur Anzahl",
            "Neu würfeln",
        ],
    ),
    # The base row is given, so the free choice's stones are not there. The fields run from the
    # top stone down.
    "zahlenmauer": (
        {**WALL, "base": 3},
        [
            *START,
            "Grundsteine",
            "Eine Mauer weniger",
            "Eine Mauer mehr",
            "Eine Spalte weniger",
            "Eine Spalte mehr",
            "Zahlenraum",
            "Plus",
            "Mal",
            "Gegebene Steine",
            "Leer",
            "Mauer für eigene Zahlen",
            "Zahl im Stein 1 der Reihe 3",
            "Zahl im Stein 1 der Reihe 2",
            "Zahl im Stein 2 der Reihe 2",
            "Zahl im Stein 1 der Reihe 1",
            "Zahl im Stein 2 der Reihe 1",
            "Zahl im Stein 3 der Reihe 1",
            "Neu würfeln",
        ],
    ),
    # The given fields are the inner ones, so the free choice's buttons are not there. The inputs
    # run in the drawing's order: the top, then the outer left, the outer right, and so on.
    "zahlenstrahl": (
        {
            "start": 2,
            "end": 20,
            "minor": 1,
            "major": 5,
            "labels": "major",
            "size": 12,
            "cut": False,
            "tasks": "random",
            "boxes": 3,
            "arrows": 0,
            "jumps": False,
            "seed": 7,
        },
        [
            *START,
            "Anfang",
            "Ende",
            "Schritt kleine Striche",
            "Schritt lange Striche",
            "Zahlen",
            "Schriftgröße",
            "Bruchstelle",
            "Aufgaben",
            "Ein Kästchen weniger",
            "Ein Kästchen mehr",
            # No arrows yet: "Ein Pfeil weniger" is disabled and Tab passes it.
            "Ein Pfeil mehr",
            "Neu würfeln",
            "Sprungbögen",
        ],
    ),
    "rechendreieck": (
        {"count": 3, "columns": 2, "max": 20, "given": "inner", "empty": False, "seed": 7},
        [
            *START,
            "Ein Dreieck weniger",
            "Ein Dreieck mehr",
            "Eine Spalte weniger",
            "Eine Spalte mehr",
            "Zahlenraum",
            "Gegebene Felder",
            "Leer",
            "Dreieck für eigene Zahlen",
            "Zahl im Feld innen oben",
            "Zahl im Feld außen links",
            "Zahl im Feld außen rechts",
            "Zahl im Feld innen links",
            "Zahl im Feld außen unten",
            "Zahl im Feld innen rechts",
            "Neu würfeln",
        ],
    ),
}
# Asked #217: Tab order through the panel


@pytest.mark.parametrize("kind", ORDER)
def test_tab_walks_the_panel_in_its_order(editor, kind):
    props, order = ORDER[kind]
    page = editor(box("a", kind, props))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel.
    for _ in range(3):
        page.keyboard.press("F6")
    for i, label in enumerate(order):
        if i:
            page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_accessible_name(label)
    expect_picked(page, "a")


def test_tab_walks_the_new_settings_of_vergleichen(editor):
    """I4: After Vergleichen, Tab walks Seiten, the Abstand and = buttons, then the count."""
    client = user()
    page = editor(box("a", "maths", maths(client, format="compare")), client=client)
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel; Tab walks down from
    # there to the formats.
    for _ in range(3):
        page.keyboard.press("F6")
    for _ in range(60):
        if page.locator(":focus").inner_text() == "Vergleichen":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_text("Vergleichen")
    # Each button of a seg is a stop of its own, as the buttons of Wörterliste and Nur Anzahl are.
    order = ["Seiten", "Beliebig", "Knapp", "Keine mit =", "Einige mit =", "Eine Aufgabe weniger"]
    for label in order:
        page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_accessible_name(label)
    expect_picked(page, "a")


def test_tab_walks_the_new_settings_of_three_numbers(editor):
    """I4: After Vergleichen, Tab walks 2 Zahlen, 3 Zahlen, Punkt vor Strich, mit Klammern."""
    client = user()
    # + and * with three numbers leave nothing greyed, so Tab reaches every switch.
    page = editor(
        box("a", "maths", maths(client, ops=["+", "*"], numbers=3, pvs=True)), client=client
    )
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel; Tab walks down from
    # there to the formats.
    for _ in range(3):
        page.keyboard.press("F6")
    for _ in range(60):
        if page.locator(":focus").inner_text() == "Vergleichen":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_text("Vergleichen")
    order = ["2 Zahlen", "3 Zahlen", "Punkt vor Strich", "mit Klammern", "Eine Aufgabe weniger"]
    for label in order:
        page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_accessible_name(label)
    expect_picked(page, "a")


def test_the_decimal_controls_stand_in_the_tab_order_and_work_from_the_keyboard(editor):
    """I6: After Zahlenraum, Tab walks the Nachkommastellen and Geld; Enter on 1 sets it."""
    client = user()
    page = editor(box("a", "maths", maths(client, ops=["+"], max=20)), client=client)
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel; Tab walks down from
    # there to the Zahlenraum.
    for _ in range(3):
        page.keyboard.press("F6")
    for _ in range(60):
        if page.locator(":focus").get_attribute("aria-label") == "Zahlenraum":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Zahlenraum")
    for label in ["0 Nachkommastellen", "1 Nachkommastelle", "2 Nachkommastellen", "Geld"]:
        page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_accessible_name(label)
        if label == "1 Nachkommastelle":
            page.keyboard.press("Enter")
            expect(page.locator(":focus")).to_have_attribute("aria-pressed", "true")
    expect_picked(page, "a")


def test_tab_reaches_the_families_and_the_keyboard_sets_them(editor):
    """I1: Tab from 3 Zahlen reaches Aufgabenfamilien; the keys pick Nachbar, then Enter sets b."""
    client = user()
    page = editor(box("a", "maths", maths(client, ops=["+", "*"], max=20, count=4)), client=client)
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel; Tab walks down from
    # there to the 3 Zahlen switch. Punkt vor Strich is greyed with two numbers, so Tab skips it.
    for _ in range(3):
        page.keyboard.press("F6")
    for _ in range(60):
        if page.locator(":focus").get_attribute("aria-label") == "3 Zahlen":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("3 Zahlen")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Aufgabenfamilien")
    # A select takes the arrow keys: three down from Keine is Nachbaraufgaben.
    for _ in range(3):
        page.keyboard.press("ArrowDown")
    expect(page.locator(":focus")).to_have_value("neighbour")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("1. Zahl wandert")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("2. Zahl wandert")
    page.keyboard.press("Enter")
    expect(page.locator(":focus")).to_have_attribute("aria-pressed", "true")
    expect_picked(page, "a")


def test_tab_reaches_the_switches_and_the_gap_boxes_and_the_keyboard_sets_them(editor):
    """I1: Tab from the Rechenart buttons reaches the four switches, then the Lücke boxes."""
    client = user()
    props = maths(client, ops=["+", "*"], max=20, count=4, format="gap")
    page = editor(box("a", "maths", props), client=client)
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel, as in the test above.
    for _ in range(3):
        page.keyboard.press("F6")
    # The switches come straight after the Rechenart buttons: Tab from the last one, ":".
    for _ in range(60):
        if page.locator(":focus").inner_text() == ":":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name(":")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Aufgaben mit 0")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name(
        "Aufgaben mit 1 beim Malnehmen und Teilen"
    )
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Kleines Einmaleins")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("keine gleichen Zahlen")
    page.keyboard.press("Space")
    expect(page.locator(":focus")).to_have_attribute("aria-pressed", "true")
    expect(page.locator(":focus")).to_have_accessible_name("keine gleichen Zahlen")
    # The gap boxes come after the Format buttons; Tab walks there.
    for _ in range(60):
        if page.locator(":focus").get_attribute("aria-label") == "Lücke: 1. Zahl":
            break
        page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Lücke: 1. Zahl")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Lücke: 2. Zahl")
    page.keyboard.press("Tab")
    expect(page.locator(":focus")).to_have_accessible_name("Lücke: Ergebnis")
    page.keyboard.press("Enter")
    expect(page.locator(":focus")).to_have_attribute("aria-pressed", "true")
    expect_picked(page, "a")
