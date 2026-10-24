"""A press that changes nothing adds no undo step, as in PowerPoint."""

import pytest
from playwright.sync_api import expect
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    saved,
    upload,
    user,
)

# A text and a shape that every setting of the panel names, small and in the page's corner: so
# each of the presses below asks for what the block has.
PLAIN = {"size": 8, "fill": "#ffff00", "stroke": "#222222"}
CORNER = {"x": 0, "y": 0}
# The fields for a place and a size, and what lines up with the page's left and upper edge: `nth`
# tells a button from one of the same name before it in the panel. The buttons of the order are
# grey where they would change nothing (test_order.py).
GEO = [("type", name, 0) for name in ("X", "Y", "Breite", "Höhe", "Drehung")]
FRAME = [("same", name, 0) for name in ("Füllung", "Transparenz", "Rand", "Randstärke")]
WORDS = [
    ("same", "Schriftart", 0),
    ("same", "Farbe", 0),
    ("same", "Zeilenabstand", 0),
    ("press", "Schrift kleiner", 0),
    ("press", "Eckig", 0),
    ("press", "Durchgezogen", 0),
    ("press", "Keine", 0),
    # The text's own "Links" and "Oben" come before those that line the block up.
    ("press", "Links", 1),
    ("press", "Oben", 1),
]
# What the bar holds that changes no block: a copy, the brush picked up and put down, the
# answers, and the zoom.
BAR = [
    ("bar", name, 0)
    for name in ("Kopieren", "Format übertragen", "Lösungen zeigen", "Größer", "Kleiner")
]
# Every control of the panel that can ask for what a block has already, by the block's kind:
# how it is worked, its name, and which of the buttons of that name it is.
CONTROLS = {
    "text": [*GEO, *WORDS, ("press", "Links", 0), ("press", "Oben", 0), *FRAME],
    "shape": [
        *GEO,
        *WORDS,
        # A shape's words stand in its middle, across and down, where it names no place.
        ("press", "Mitte", 0),
        ("press", "Mitte", 1),
        # A level box looks the same mirrored.
        ("press", "Horizontal spiegeln", 0),
        ("press", "Vertikal spiegeln", 0),
        *FRAME,
    ],
    "line": [
        *GEO[:2],
        ("same", "Füllung", 0),
        ("same", "Rand", 0),
        ("same", "Randstärke", 0),
        ("same", "Länge in cm", 0),
        ("press", "Durchgezogen", 0),
        # The numbering's, then the one of "Länge anschreiben".
        ("press", "Keine", 0),
        ("press", "Keine", 1),
        ("press", "Links", 0),
        ("press", "Oben", 0),
    ],
    "picture": [
        *GEO,
        ("press", "Keine", 0),
        ("press", "Links", 0),
        ("press", "Oben", 0),
        # Crop mode entered and left with the frame as it was.
        ("twice", "Zuschneiden", 0),
    ],
    "table": [
        *GEO[:4],
        ("same", "Schriftart der Tabelle", 0),
        ("same", "Farbe", 0),
        ("same", "Linien", 0),
        ("press", "Eine Zeile weniger", 0),
        ("press", "Schrift kleiner", 0),
        ("press", "Mitte", 0),
        ("press", "Keine", 0),
        ("same", "Linienart", 0),
        # The table's own "Links" comes first, then the border button "Links", which draws a
        # line, as the border button "Oben" does.
        ("press", "Links", 2),
        ("press", "Oben", 1),
    ],
    "ruling": [
        *GEO,
        ("same", "Art der Lineatur", 0),
        ("same", "Farbe", 0),
        ("same", "Schriftart auf den Zeilen", 0),
        ("press", "Seitenbreite", 0),
        ("press", "Bis Seitenende", 0),
        ("press", "Keine", 0),
    ],
    "maths": [
        *GEO,
        # The only kind of sum stays.
        ("press", "+", 0),
        ("press", "Eine Spalte weniger", 0),
        ("press", "Schrift kleiner", 0),
        # The numbering of the exercises, then the block's.
        ("press", "Keine", 0),
        ("press", "Keine", 1),
        ("press", "Links", 0),
        ("press", "Oben", 0),
    ],
    "group": [
        *GEO[:2],
        *WORDS,
        ("press", "Links", 0),
        ("press", "Oben", 0),
        ("same", "Füllung", 0),
        ("same", "Rand", 0),
    ],
}
CASES = [(kind, *control) for kind, controls in CONTROLS.items() for control in [*controls, *BAR]]
# The limits of a maths block that ask the server: it makes the same exercises again.
ASKS = [
    ("press", "Egal"),
    ("press", "Zeile"),
    ("press", "Eine Aufgabe weniger"),
    ("same", "Zahlenraum"),
    ("same", "E von"),
    ("same", "Z bis"),
]
SAME = """(el) => {
    const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    own.set.call(el, el.value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
}"""


def field(page, label):
    """A field or a control of the format panel, by its label."""
    # A maths block has a field of each name for either number.
    return page.locator(".panel").get_by_label(label, exact=True).first


def opened(editor, kind):
    """The editor on one block of the kind, or one group, selected and set as CONTROLS wants."""
    client = user()
    blocks = {
        "text": [box("a", "text", {**TEXT, **PLAIN}, **CORNER)],
        "shape": [box("a", "shape", {**RECT, **PLAIN}, **CORNER)],
        # A line lines up by its stroke (#677): this one's reaches past its ends to the left and up.
        "line": [box("a", "shape", LINE, x=0.03, y=0.25)],
        "picture": [{**picture(upload(client)), "id": "a", **CORNER}],
        "table": [box("a", "table", {**TABLE, "cells": [["H", "Z"]], "size": 8}, **CORNER)],
        # As wide as the room between the margins, and down to the lower one.
        "ruling": [box("a", "ruling", RULING, y=32, h=250)],
        "maths": [box("a", "maths", maths(client, count=1, columns=1, size=8), **CORNER)],
        "group": [
            box("a", "text", {**TEXT, **PLAIN}, **CORNER, w=40, group=["g"]),
            box("b", "text", {**TEXT, **PLAIN}, z=2, x=45, y=0, w=40, group=["g"]),
        ],
    }[kind]
    page = editor(*blocks, client=client)
    at(page, "a").click()
    expect_picked(page, *(b["id"] for b in blocks))
    return page


def work(page, how, label, nth=0):
    """Asks a control for what the selection has already."""
    if how == "type":
        number = field(page, label)
        number.fill(number.input_value())
        number.press("Enter")
    elif how == "same":
        control = field(page, label)
        if control.evaluate("el => el.tagName") == "SELECT":
            # Sends the `change` a list sends, though no browser does for the value it shows.
            control.select_option(control.input_value())
        else:
            control.evaluate(SAME)
    else:
        scope = page.locator("header, .dock" if how == "bar" else ".panel")
        scope.get_by_role("button", name=label, exact=True).nth(nth).click()
        if how == "twice":
            scope.get_by_role("button", name="Fertig", exact=True).click()


def steps(page):
    """How many steps undo holds: takes them all back and does them again."""
    undo, redo = (page.get_by_label(name, exact=True) for name in ("Rückgängig", "Wiederholen"))
    n = 0
    while undo.is_enabled():
        undo.click()
        n += 1
    for _ in range(n):
        redo.click()
    return n


# Asked #238, A1


@pytest.mark.parametrize("kind, how, label, nth", CASES)
def test_a_control_asked_for_what_the_block_has_adds_no_undo_step(editor, kind, how, label, nth):
    page = opened(editor, kind)
    work(page, how, label, nth)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")
    # The next change is one step.
    page.get_by_label("Duplizieren", exact=True).click()
    assert steps(page) == 1


@pytest.mark.parametrize("how, label", ASKS)
def test_a_limit_of_a_maths_block_set_as_it_is_adds_no_undo_step(editor, how, label):
    page = opened(editor, "maths")
    columns = page.locator(".panel output", has_text="Spalten")
    with page.expect_response("**/api/maths") as answer:
        work(page, how, label)
    answer.value.finished()
    # The answer is on the sheet before the next press: a late one would take the column away.
    page.get_by_label("Eine Spalte mehr").click()
    expect(columns).to_have_text("2 Spalten")
    assert steps(page) == 1
    expect(columns).to_have_text("2 Spalten")


def test_the_last_row_of_a_ruling_stays_with_no_undo_step(editor):
    page = editor(box("a", "ruling", RULING, h=10))
    pick(page, "a")
    page.get_by_label("Eine Zeile weniger").click()
    expect(page.locator(".panel output").first).to_have_text("1 Zeile")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


@pytest.mark.parametrize("own", [False, True])
def test_the_view_set_as_it_is_adds_no_undo_step(editor, own):
    page = editor(box("a", "text", TEXT))
    panel = page.locator(".panel")
    page.get_by_role("tab", name="Ansicht").click()
    if own:
        panel.get_by_role("button", name="Nur diese Seite").click()
        # The page's format, then its grid.
        for nth in (0, 1):
            panel.get_by_role("button", name="Wie Blatt").nth(nth).click()
    else:
        # Two buttons read Aus: the Raster's and the Seitenzahlen' (#88). Both are set as they are.
        for name in ("Alle Seiten", "Hoch"):
            panel.get_by_role("button", name=name, exact=True).click()
        panel.get_by_role("button", name="Aus", exact=True).first.click()
        panel.get_by_role("group", name="Seitenzahlen").get_by_role("button", name="Aus").click()
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")


# What a block shows where it names nothing, by the block's kind: the prop, its control (none
# for buttons), a value away from what is shown, what is shown, and that as the sheet stores it.
# A button is its name and which of that name it is.
UNNAMED = [
    ("text", "font", "Schriftart", None, "andika", "andika"),
    ("text", "color", "Farbe", "#ff0000", "#222222", "#222222"),
    ("text", "spacing", "Zeilenabstand", "2", "1.3", 1.3),
    ("text", "strokeWidth", "Randstärke", "2", "0.5", 0.5),
    ("text", "opacity", "Transparenz", "50", "0", 1),
    ("text", "valign", None, ("Unten", 0), ("Oben", 0), "top"),
    ("text", "kind", None, ("Rund", 0), ("Eckig", 0), "rect"),
    ("shape", "font", "Schriftart", None, "andika", "andika"),
    ("shape", "color", "Farbe", "#ff0000", "#222222", "#222222"),
    ("shape", "spacing", "Zeilenabstand", "2", "1.3", 1.3),
    ("shape", "opacity", "Transparenz", "50", "0", 1),
    # A shape's words stand in the middle where a text's stand at the top.
    ("shape", "valign", None, ("Oben", 0), ("Mitte", 1), "middle"),
    ("shape", "align", None, ("Links", 0), ("Mitte", 0), "center"),
    ("table", "font", "Schriftart der Tabelle", None, "andika", "andika"),
    ("ruling", "font", "Schriftart auf den Zeilen", None, "andika", "andika"),
    ("group", "font", "Schriftart", None, "andika", "andika"),
    ("group", "valign", None, ("Unten", 0), ("Oben", 0), "top"),
]
SET = """(el, to) => {
    el.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
    const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    own.set.call(el, to);
    el.dispatchEvent(new Event("input", { bubbles: true }));
}"""


# How a block is drawn, as the browser works it out: a colour named or not looks the same.
LOOK = """(el) => [...el.querySelectorAll("*")].map((part) => {
    const s = getComputedStyle(part);
    const all = [s.fontFamily, s.color, s.lineHeight, s.justifyContent, s.textAlign];
    return [...all, s.borderRadius, s.borderTopWidth, s.boxShadow, s.backgroundColor].join();
}).join(";")"""


def put(page, label, to):
    """Sets a control of the panel, each time with a press of its own. Gives what it then shows."""
    if label is None:
        name, nth = to
        button = page.locator(".panel").get_by_role("button", name=name, exact=True).nth(nth)
        button.click()
        expect(button).to_have_class("on")
        return None
    control = field(page, label)
    if control.evaluate("el => el.tagName") == "SELECT":
        other = "el => [...el.options].find((o) => !o.selected && o.value).value"
        control.dispatch_event("pointerdown")
        control.select_option(to or control.evaluate(other))
    else:
        control.evaluate(SET, to)
    if to:
        expect(control).to_have_value(to)
    return control.input_value()


@pytest.mark.parametrize("kind, prop, label, away, back, stored", UNNAMED)
def test_a_block_set_away_from_what_it_shows_and_back_shows_it_again(
    editor, kind, prop, label, away, back, stored
):
    client = user()
    blocks = {
        "text": [box("a", "text", {**TEXT, "fill": "#ffff00", "stroke": "#222222"})],
        "shape": [box("a", "shape", {**RECT, "fill": "#ffff00"})],
        "table": [box("a", "table", TABLE)],
        "ruling": [box("a", "ruling", RULING)],
        "group": [
            box("a", "text", TEXT, w=40, group=["g"]),
            box("b", "text", TEXT, z=2, x=60, y=50, w=40, group=["g"]),
        ],
    }[kind]
    assert all(prop not in b["props"] for b in blocks)
    page = editor(*blocks, client=client)
    at(page, "a").click()
    expect_picked(page, *(b["id"] for b in blocks))
    drawn = at(page, "a").evaluate(LOOK)
    shown = put(page, label, away)
    assert steps(page) == 1
    assert at(page, "a").evaluate(LOOK) != drawn
    put(page, label, back)
    # Each of the two is a change, and the block is drawn as at first.
    assert steps(page) == 2
    assert at(page, "a").evaluate(LOOK) == drawn
    for b in saved(page, client):
        assert b["props"][prop] == stored
    # One step back the block has the value set first, and after the other it names none.
    page.get_by_label("Rückgängig", exact=True).click()
    assert at(page, "a").evaluate(LOOK) != drawn
    if shown:
        expect(field(page, label)).to_have_value(shown)
    page.get_by_label("Rückgängig", exact=True).click()
    assert at(page, "a").evaluate(LOOK) == drawn
    assert all(prop not in b["props"] for b in saved(page, client))


# The controls that find nothing to change before the sheet is asked: the block's kind, how the
# control is worked, its name, and which of that name it is.
GUARDED = [
    # The nudges go down, so the block stays at the left edge.
    ("text", "press", "Links", 1),
    ("text", "type", "X", 0),
    ("text", "type", "Drehung", 0),
    ("table", "press", "Eine Zeile weniger", 0),
    ("maths", "press", "+", 0),
    ("picture", "twice", "Zuschneiden", 0),
]
ACTIVE = "(el) => el === document.activeElement"
