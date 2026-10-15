"""The controls the browser draws itself, in a real window: a list, a colour picker, the file
dialog, and Tab through the panel. `mise run test:native` runs these, and nothing else runs them.

Headless Chromium opens no list and no picker, so the other tests fake the press. Here the mouse
and the keyboard do everything: a locator only finds the place to press and what to check. The
one way around is the file dialog, which is the system's: the file goes in through the chooser.

An open list and an open picker are windows of their own, and the mouse of the test reaches the
page only. So a pick is made with the keys: the arrows, then Enter.
"""

import pytest
from playwright.sync_api import expect
from test_suchsel import SUCHSEL
from ui import FIELD, RECT, RULING, TABLE, TEXT, at, box, centre, expect_picked, maths, png, user

pytestmark = pytest.mark.native

POPUP = ".panel select:open, .panel input[type=color]:open"
BLACK = {**TEXT, "color": "#000000"}
WALL = {"count": 4, "columns": 2, "max": 20, "op": "+", "given": "base", "empty": False, "seed": 7}
# A select of the panel, the block that shows it and the value it starts with.
LISTS = [
    ("Schriftart", "text", TEXT, "andika"),
    ("Art der Lineatur", "ruling", RULING, "l4"),
    ("Schriftart der Tabelle", "table", TABLE, "andika"),
]
# What Tab stops at from the panel's first field on, down to the kinds of border.
START = ["X", "Y", "Breite", "Höhe", "Drehung", "Seitenverhältnis sperren", "Breite %", "Höhe %"]
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
    "text": (
        TEXT,
        [*START, *FONT, *PLACE, *TURN[:-2], "Zeilennummern", *TURN[-2:], *OUTLINE, *FILL, *DASH],
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


def press(page, found):
    """Clicks the middle of what the locator finds, with the mouse."""
    page.mouse.click(*centre(found))


def control(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def until(page, key, check):
    """Presses the key until the check holds.

    A list and a picker are `:open` before they listen for keys, and a key that comes in between
    is lost. The key is pressed again only when the one before changed nothing.
    """
    for _ in range(4):
        page.keyboard.press(key)
        try:
            return check()
        except AssertionError:
            pass
    page.keyboard.press(key)
    check()


def opened(page, label):
    """Opens a list or a colour picker of the panel with the mouse."""
    found = control(page, label)
    press(page, found)
    expect(found).to_be_focused()
    expect(page.locator(POPUP)).to_have_count(1)
    return found


def shut(page, found, way):
    """Shuts what `opened` opened, with no pick."""
    if way == "escape":
        until(page, "Escape", lambda: expect(page.locator(POPUP)).to_have_count(0))
        return
    if way == "same":
        press(page, found)
    elif way == "ground":
        # The panel's bare ground, at its upper left corner.
        place = page.locator(".panel").bounding_box()
        page.mouse.click(place["x"] + 3, place["y"] + 3)
    elif way == "beside":
        page.mouse.click(5, 300)
    expect(page.locator(POPUP)).to_have_count(0)


def write(page, name):
    """Opens the text, types "Wort" over what it held and puts the caret before the last letter."""
    press(page, at(page, name))
    expect_picked(page, name)
    page.keyboard.press("Enter")
    # The field hears of a caret the browser moved only a moment later, but of a letter at once.
    page.keyboard.type("Wot")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("r")
    area = page.locator(FIELD)
    expect(area).to_be_focused()
    return area


# Asked #217: a real select opens and a pick lands


@pytest.mark.parametrize("label, kind, props, was", LISTS)
def test_the_arrows_and_enter_pick_in_a_real_list(editor, label, kind, props, was):
    page = editor(box("a", kind, props), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, label)
    expect(found).to_have_value(was)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value(was)
    # The pick gives the keys back to the sheet (#99): Tab picks the next block.
    expect(found).not_to_be_focused()
    page.keyboard.press("Tab")
    expect_picked(page, "b")


def test_a_pick_in_a_real_list_is_one_undo_step(editor):
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    expect(undo(page)).to_be_disabled()
    # The list walks two down and tells the page nothing until Enter.
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()
    page.keyboard.press("Enter")
    expect(found).not_to_have_value("l4")
    press(page, undo(page))
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_escape_in_a_real_list_with_no_arrow_adds_no_undo_step(editor):
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    shut(page, found, "escape")
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_escape_after_an_arrow_in_a_real_list_picks_as_chromium_does_in_one_step(editor):
    # Chromium takes the option the arrows went to when the list shuts, by Escape or by a click
    # anywhere, and sends `change`. So the page cannot tell it from a pick: it is one step.
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Escape")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value("l4")
    press(page, undo(page))
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_ctrl_z_right_after_a_pick_in_a_real_list_takes_it_back(editor):
    page = editor(box("a", "text", TEXT))
    press(page, at(page, "a"))
    found = opened(page, "Schriftart")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(found).not_to_have_value("andika")
    # No press in between: the key goes where the pick left the focus.
    page.keyboard.press("Control+z")
    expect(found).to_have_value("andika")
    expect(undo(page)).to_be_disabled()
    expect_picked(page, "a")


# Asked #212


@pytest.mark.parametrize("way", ["escape", "same", "ground"])
def test_a_letter_after_a_real_list_shut_with_no_pick_is_typed_in_the_text(editor, way):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    area = write(page, "a")
    found = opened(page, "Schriftart")
    shut(page, found, way)
    # The select would take an "l" as its own: another font starts with it.
    page.keyboard.type("l")
    expect(area).to_have_text("Worlt")
    expect(area).to_be_focused()
    expect(found).to_have_value("andika")
    expect_picked(page, "a")


def test_a_letter_after_a_click_beside_a_real_list_changes_no_font(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, "Schriftart")
    # In a real window the press beside the list shuts it and goes on to the page.
    shut(page, found, "beside")
    page.keyboard.type("l")
    expect(found).to_have_value("andika")
    expect(found).not_to_be_focused()
    # The sheet has the keys: the letter opens the picked text and lands after its words (#516).
    expect(at(page, "a").locator(".ProseMirror")).to_have_text("Hallol")
    page.keyboard.press("Escape")
    page.keyboard.press("Delete")
    expect(at(page, "a")).to_have_count(0)


# Asked #217: a real colour picker opens and a pick lands


def test_an_arrow_and_enter_pick_in_a_real_colour_picker(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    words = at(page, "a").get_by_text("Hallo")
    press(page, at(page, "a"))
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    found = opened(page, "Farbe")
    until(page, "ArrowRight", lambda: expect(found).not_to_have_value("#222222"))
    expect(words).not_to_have_css("color", "rgb(34, 34, 34)")
    page.keyboard.press("Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value("#222222")
    expect(found).not_to_be_focused()
    # The whole visit to the picker is one step.
    press(page, undo(page))
    expect(found).to_have_value("#222222")
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    expect(undo(page)).to_be_disabled()


# Asked #210


@pytest.mark.parametrize("way", ["escape", "ground", "beside"])
def test_tab_after_a_real_colour_picker_shut_with_no_pick_picks_the_next_block(editor, way):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, "Farbe")
    shut(page, found, way)
    expect(found).to_have_value("#222222")
    page.keyboard.press("Tab")
    expect_picked(page, "b")
    expect(found).not_to_be_focused()
    expect(undo(page)).to_be_disabled()


def test_delete_after_a_real_colour_picker_put_back_and_shut_deletes_the_block(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    found = opened(page, "Farbe")
    until(page, "ArrowRight", lambda: expect(found).not_to_have_value("#222222"))
    # The first Escape puts the colour back and leaves the picker open: Delete would be its own.
    page.keyboard.press("Escape")
    expect(found).to_have_value("#222222")
    expect(page.locator(POPUP)).to_have_count(1)
    # The second shuts it, and the next key is the sheet's.
    shut(page, found, "escape")
    page.keyboard.press("Delete")
    expect(at(page, "a")).to_have_count(0)
    expect(at(page, "b")).to_have_count(1)


def test_a_letter_after_a_real_colour_picker_shut_with_no_pick_is_typed_in_the_text(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    area = write(page, "a")
    found = opened(page, "Farbe")
    shut(page, found, "escape")
    page.keyboard.type("l")
    expect(area).to_have_text("Worlt")
    expect(area).to_be_focused()
    expect(found).to_have_value("#222222")
    expect_picked(page, "a")


# Asked #258


def test_a_real_colour_picker_moved_away_and_back_adds_no_undo_step(editor):
    # Black lies at the lower edge of the picker's field: one up and one down ends where it began.
    page = editor(box("a", "text", BLACK))
    press(page, at(page, "a"))
    found = opened(page, "Farbe")
    until(page, "ArrowUp", lambda: expect(found).not_to_have_value("#000000"))
    page.keyboard.press("ArrowDown")
    expect(found).to_have_value("#000000")
    shut(page, found, "escape")
    expect(found).to_have_value("#000000")
    expect(undo(page)).to_be_disabled()


# Asked #217: the file dialog of a picture upload


def test_a_picture_given_to_the_file_dialog_lands_on_the_sheet(editor):
    page = editor(box("a", "text", TEXT))
    with page.expect_file_chooser() as dialog:
        press(page, page.get_by_label("Bild", exact=True))
    # The dialog is the system's and no key of the test reaches it: the chooser takes the file.
    dialog.value.set_files({"name": "bild.png", "mimeType": "image/png", "buffer": png()})
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(page.locator(".block.sel img")).to_be_visible()
    expect(at(page, "a")).not_to_have_class("block sel")
    press(page, undo(page))
    expect(page.locator(".block[data-id]")).to_have_count(1)


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
