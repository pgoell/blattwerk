"""A press that changes nothing adds no undo step, as in PowerPoint."""

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    drag,
    expect_picked,
    maths,
    pick,
    picture,
    upload,
    user,
)

# A text and a shape that every setting of the panel names, small and in the page's corner: so
# each of the presses below asks for what the block has.
PLAIN = {"size": 8, "fill": "#ffff00", "stroke": "#222222"}
CORNER = {"x": 0, "y": 0}
# The fields for a place and a size, the buttons that put a block in front or behind, and what
# lines up with the page's left and upper edge: `nth` tells a button from one of the same name
# before it in the panel.
GEO = [("type", name, 0) for name in ("X", "Y", "Breite", "Höhe", "Drehung")]
ORDER = [
    ("press", name, 0)
    for name in ("Nach vorn", "Nach hinten", "Eine nach vorn", "Eine nach hinten")
]
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
# The lock is no part of the sheet.
LOCK = ("press", "Seitenverhältnis sperren", 0)
# What the bar holds that changes no block: a copy, the brush picked up and put down, the
# answers, and the zoom.
BAR = [
    ("bar", name, 0)
    for name in ("Kopieren", "Format übertragen", "Lösungen zeigen", "Größer", "Kleiner")
]
# Every control of the panel that can ask for what a block has already, by the block's kind:
# how it is worked, its name, and which of the buttons of that name it is.
CONTROLS = {
    "text": [*GEO, LOCK, *WORDS, ("press", "Links", 0), ("press", "Oben", 0), *FRAME, *ORDER],
    "shape": [
        *GEO,
        LOCK,
        *WORDS,
        # A shape's words stand in its middle, across and down, where it names no place.
        ("press", "Mitte", 0),
        ("press", "Mitte", 1),
        # A level box looks the same mirrored.
        ("press", "Horizontal spiegeln", 0),
        ("press", "Vertikal spiegeln", 0),
        *FRAME,
        *ORDER,
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
        *ORDER,
    ],
    "picture": [
        *GEO,
        ("press", "Keine", 0),
        ("press", "Links", 0),
        ("press", "Oben", 0),
        # Crop mode entered and left with the frame as it was.
        ("twice", "Zuschneiden", 0),
        *ORDER,
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
        # The table's own "Links" comes first.
        ("press", "Links", 1),
        ("press", "Oben", 0),
        *ORDER,
    ],
    "ruling": [
        *GEO,
        ("same", "Art der Lineatur", 0),
        ("same", "Farbe", 0),
        ("same", "Schriftart auf den Zeilen", 0),
        ("press", "Seitenbreite", 0),
        ("press", "Bis Seitenende", 0),
        ("press", "Keine", 0),
        *ORDER,
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
        *ORDER,
    ],
    "group": [
        *GEO[:2],
        *WORDS,
        ("press", "Links", 0),
        ("press", "Oben", 0),
        ("same", "Füllung", 0),
        ("same", "Rand", 0),
        *ORDER,
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
        "line": [box("a", "shape", LINE, **CORNER)],
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
    expect(page.locator(".panel output").first).to_have_text("1 Zeilen")
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
        for name in ("Alle Seiten", "Hoch", "Aus"):
            panel.get_by_role("button", name=name, exact=True).click()
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")


# Asked #238, A2


def test_seitenbreite_and_bis_seitenende_twice_are_one_step_each(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    undo = page.get_by_label("Rückgängig", exact=True)
    pick(page, "lines")
    for name, label, was, now in (
        ("Seitenbreite", "Breite", "80", "180"),
        ("Bis Seitenende", "Höhe", "20", "230"),
    ):
        for _ in range(2):
            page.get_by_role("button", name=name).click()
            expect(field(page, label)).to_have_value(now)
        page.keyboard.press("Control+z")
        expect(field(page, label)).to_have_value(was)
        expect(undo).to_be_disabled()


# Implied #238, I1


def test_a_press_that_changes_nothing_keeps_redo(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    wide = page.get_by_role("button", name="Seitenbreite")
    pick(page, "lines")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    wide.click()
    expect(field(page, "Breite")).to_have_value("180")
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    # Nothing to change: the only block is in front, has no number, and lies where it lies.
    for name in ("Nach vorn", "Keine"):
        page.get_by_role("button", name=name, exact=True).click()
    work(page, "same", "Art der Lineatur")
    work(page, "type", "X")
    expect(page.get_by_label("Wiederholen", exact=True)).to_be_enabled()
    page.keyboard.press("Control+y")
    expect(field(page, "Y")).to_have_value("51")
    page.keyboard.press("Control+y")
    expect(field(page, "Breite")).to_have_value("180")
    expect(page.get_by_label("Wiederholen", exact=True)).to_be_disabled()


# Implied #238, I2


def test_a_list_that_asks_for_nothing_new_swallows_no_step(editor):
    page = editor(box("a", "ruling", RULING))
    kind, undo = field(page, "Art der Lineatur"), page.get_by_label("Rückgängig", exact=True)
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    # The list opened by a press, left on the kind it shows, and then walked by the keys with no
    # press between: the new kind is a step of its own, not a part of the move before it.
    kind.dispatch_event("pointerdown")
    kind.select_option("l4")
    kind.select_option("l3")
    expect(field(page, "Höhe")).to_have_value("23")
    undo.click()
    expect(kind).to_have_value("l4")
    expect(field(page, "Höhe")).to_have_value("20")
    expect(field(page, "Y")).to_have_value("51")
    undo.click()
    expect(field(page, "Y")).to_have_value("50")
    expect(undo).to_be_disabled()


def test_a_drag_after_a_press_that_changes_nothing_is_one_step_of_its_own(editor):
    page = editor(box("a", "text", TEXT, x=0))
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    page.locator(".panel").get_by_role("button", name="Links", exact=True).nth(1).click()
    x, y = centre(at(page, "a"))
    drag(page, (x, y), (x + 40, y + 60), (x + 80, y + 120))
    expect(field(page, "Y")).not_to_have_value("51")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("51")
    expect(field(page, "X")).to_have_value("0")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_nudge_after_a_press_that_changes_nothing_is_its_own_step(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    # No press of the mouse comes between: the button is pressed as the keys press it.
    page.locator(".panel").get_by_role("button", name="Keine", exact=True).dispatch_event("click")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("52")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("51")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Implied #238, I3


def test_several_blocks_changed_in_part_are_one_step_and_none_changed_is_none(editor):
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", {**TEXT, "align": "right"}, z=2),
        box("c", "shape", RECT, z=3),
    )
    panel = page.locator(".panel")
    left = panel.get_by_role("button", name="Links", exact=True).first
    top = panel.get_by_role("button", name="Oben", exact=True).first
    pick(page, "a", "b", "c")
    left.click()
    expect(at(page, "b").locator(".frame")).to_have_css("text-align", "left")
    assert steps(page) == 1
    left.click()
    # A text stands at the top and a shape's words in its middle: "Oben" changes the shape alone.
    top.click()
    assert steps(page) == 2
    top.click()
    panel.get_by_role("button", name="Eckig", exact=True).click()
    assert steps(page) == 2
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect(at(page, "b").locator(".frame")).to_have_css("text-align", "right")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Implied #238, I4


@pytest.mark.parametrize(
    "how, label, nth",
    [
        ("same", "Schriftart", 0),
        ("press", "Links", 0),
        ("press", "Oben", 0),
        ("press", "Eckig", 0),
        ("press", "Keine", 0),
        ("press", "Nach vorn", 0),
    ],
)
def test_a_press_that_changes_nothing_while_a_text_is_written_keeps_the_caret(
    editor, how, label, nth
):
    page = editor(box("a", "text", TEXT))
    words = page.locator(FIELD)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    # The "l" is typed last, so the field knows where the caret is.
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("l")
    expect(words).to_have_text("Halllo")
    work(page, how, label, nth)
    expect(words).to_be_focused()
    page.keyboard.type("x")
    expect(words).to_have_text("Hallxlo")
    # A letter before the press and one after it: two steps, and the press is none.
    page.keyboard.press("Control+z")
    expect(words).to_have_text("Halllo")
    page.keyboard.press("Control+z")
    expect(words).to_have_text("Hallo")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Implied #238, I5


def test_a_press_that_changes_nothing_measures_no_text(editor):
    # Both texts are higher than their boxes, as a sheet made elsewhere can hold them.
    tall = {**TEXT, "text": "eins\nzwei\ndrei\nvier"}
    page = editor(box("a", "text", tall, h=5), box("b", "text", tall, z=2, h=5))
    pick(page, "a")
    page.locator(".panel").get_by_role("button", name="Links", exact=True).first.click()
    # The next drawing, of another selection, grows neither.
    pick(page, "b")
    expect(field(page, "Höhe")).to_have_value("5")
    pick(page, "a")
    expect(field(page, "Höhe")).to_have_value("5")
    assert page.locator("header [role=status]").inner_text() == "Gespeichert"
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_press_that_changes_nothing_sends_no_save(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    status = page.locator("header [role=status]")
    sent = []
    page.on("request", lambda r: r.method != "GET" and sent.append(r.url))
    save = "**/api/sheets/*"
    pick(page, "lines")
    with page.expect_response(save):
        page.get_by_role("button", name="Seitenbreite").click()
        expect(status).to_have_text("Speichert …")
    expect(status).to_have_text("Gespeichert")
    assert len(sent) == 1
    for name in ("Seitenbreite", "Nach vorn", "Keine"):
        page.get_by_role("button", name=name, exact=True).click()
        # At once, with no wait: the sheet was never anything else.
        assert status.inner_text() == "Gespeichert"
    # A change after them is the next thing sent: no save of theirs came in between.
    with page.expect_response(save):
        page.keyboard.press("ArrowDown")
    expect(status).to_have_text("Gespeichert")
    assert len(sent) == 2
