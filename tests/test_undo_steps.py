"""Each pick in a list of the panel is an undo step, and a gesture back at its start is none."""

import pytest
from playwright.sync_api import expect
from test_undo_same import field, steps
from ui import LINE, RECT, RULING, TABLE, TEXT, box, drag, expect_picked, maths, pick, saved, user

# A text and a shape that name all a gesture changes, each slider at its lower end: a press on a
# slider's left end then asks for what the block has.
NAMED = {
    "color": "#0000ff",
    "spacing": 1,
    "fill": "#ffff00",
    "stroke": "#222222",
    "strokeWidth": 0.25,
    "opacity": 1,
}
PROPS = {
    "text": {**TEXT, **NAMED},
    "shape": {**RECT, **NAMED},
    "line": {**LINE, "fill": "#ffff00", "strokeWidth": 0.25},
    "ruling": RULING,
    "table": {**TABLE, "color": "#222222", "line": "#222222"},
}
# Every list of the panel, by the block's kind: its name, the key that walks it, and the two values
# the key picks after the one the block has.
LISTS = [
    ("text", "Schriftart", "ArrowDown", ("andika", "grund", "va")),
    ("shape", "Schriftart", "ArrowDown", ("andika", "grund", "va")),
    ("ruling", "Art der Lineatur", "ArrowUp", ("l4", "l3", "l2")),
    ("ruling", "Schriftart auf den Zeilen", "ArrowDown", ("andika", "grund", "va")),
    ("table", "Schriftart der Tabelle", "ArrowDown", ("andika", "grund", "va")),
    ("maths", "Zahlenraum", "ArrowDown", ("20", "100", "1000")),
    ("maths", "E von", "ArrowDown", ("0", "1", "2")),
    ("maths", "Z bis", "ArrowUp", ("9", "8", "7")),
]
# Every colour and slider of the panel, by the block's kind.
FRAME = ["Füllung", "Transparenz", "Rand", "Randstärke"]
GESTURES = [
    *(("text", label) for label in ["Farbe", "Zeilenabstand", *FRAME]),
    *(("shape", label) for label in ["Farbe", "Zeilenabstand", *FRAME]),
    *(("line", label) for label in ["Füllung", "Rand", "Randstärke"]),
    ("ruling", "Farbe"),
    ("table", "Farbe"),
    ("table", "Linien"),
]
COLOURS = ["#ff0000", "#00ff00"]
PRESS = """(el) => el.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }))"""
INPUT = """(el, to) => {
    const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
    own.set.call(el, to);
    el.dispatchEvent(new Event("input", { bubbles: true }));
}"""


def opened(editor, kind, n=1):
    """The editor on `n` blocks of the kind, all selected. Gives the page and the user."""
    client = user()
    props = maths(client, count=12) if kind == "maths" else PROPS[kind]
    names = "ab"[:n]
    kind = "shape" if kind == "line" else kind
    page = editor(*(box(name, kind, props, z=z) for z, name in enumerate(names, 1)), client=client)
    pick(page, *names)
    return page, client


def walk(page, label, key):
    """Picks the next value of a list with an arrow key, and waits until the sheet has it."""
    status = page.locator("header [role=status]")
    # A maths block's limit asks the server, and the list shows the value before the answer is on
    # the sheet: only the sheet no longer saved tells that it is.
    expect(status).to_have_text("Gespeichert", timeout=5000)
    field(page, label).focus()
    page.keyboard.press(key)
    expect(status).not_to_have_text("Gespeichert")


def gesture(page, label, *stops):
    """Works a colour or a slider in one go, with one press: through the stops and no letting go.

    Stop 0 is the value the control has, 1 and 2 are two others.
    """
    control = field(page, label)
    if control.get_attribute("type") == "color":
        to = [control.input_value(), *COLOURS]
        control.evaluate(PRESS)
        for stop in stops:
            control.evaluate(INPUT, to[stop])
        return
    # A slider at its lower end: the press on its left end changes nothing.
    control.scroll_into_view_if_needed()
    place = control.bounding_box()
    y = place["y"] + place["height"] / 2
    xs = [place["x"] + 1, place["x"] + place["width"] / 2, place["x"] + place["width"] - 1]
    drag(page, (xs[0], y), *((xs[stop], y) for stop in stops))


# Asked #257, A11


@pytest.mark.parametrize("kind, label, key, values", LISTS)
def test_each_value_picked_in_a_list_with_the_arrows_is_its_own_undo_step(
    editor, kind, label, key, values
):
    page, _ = opened(editor, kind)
    undo = page.get_by_label("Rückgängig", exact=True)
    expect(field(page, label)).to_have_value(values[0])
    for value in values[1:]:
        walk(page, label, key)
        expect(field(page, label)).to_have_value(value)
    undo.click()
    expect(field(page, label)).to_have_value(values[1])
    expect(undo).to_be_enabled()
    undo.click()
    expect(field(page, label)).to_have_value(values[0])
    expect(undo).to_be_disabled()


# Asked #258, A12


@pytest.mark.parametrize("kind, label", GESTURES)
def test_a_colour_or_a_slider_moved_away_and_back_in_one_go_adds_no_undo_step(editor, kind, label):
    page, _ = opened(editor, kind)
    was = field(page, label).input_value()
    gesture(page, label, 1, 2, 0)
    expect(field(page, label)).to_have_value(was)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    # The next change is one step.
    page.get_by_label("Duplizieren", exact=True).click()
    assert steps(page) == 1


# Implied #258, I1


@pytest.mark.parametrize("kind, label", GESTURES)
def test_a_gesture_back_at_its_start_keeps_redo_and_leaves_the_sheet_saved(editor, kind, label):
    page, _ = opened(editor, kind)
    redo = page.get_by_label("Wiederholen", exact=True)
    status = page.locator("header [role=status]")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    page.get_by_label("Rückgängig", exact=True).click()
    expect(field(page, "Y")).to_have_value("50")
    expect(status).to_have_text("Gespeichert")
    gesture(page, label, 1, 0)
    # At once, with no wait: the sheet is the one that was saved.
    assert status.inner_text() == "Gespeichert"
    expect(redo).to_be_enabled()
    redo.click()
    expect(field(page, "Y")).to_have_value("51")
    expect(redo).to_be_disabled()


# Implied #258, I2


@pytest.mark.parametrize("stops", [(1, 2), (1, 0, 2)])
@pytest.mark.parametrize("kind, label", GESTURES)
def test_a_gesture_that_ends_elsewhere_is_one_step(editor, kind, label, stops):
    page, _ = opened(editor, kind)
    undo = page.get_by_label("Rückgängig", exact=True)
    was = field(page, label).input_value()
    # A step before the gesture, which the gesture leaves alone.
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    gesture(page, label, *stops)
    expect(field(page, label)).not_to_have_value(was)
    undo.click()
    expect(field(page, label)).to_have_value(was)
    expect(field(page, "Y")).to_have_value("51")
    undo.click()
    expect(field(page, "Y")).to_have_value("50")
    expect(undo).to_be_disabled()


# Implied #257, I3


@pytest.mark.parametrize("kind, label, key, values", LISTS)
def test_undo_and_redo_walk_the_picks_of_a_list_one_by_one(editor, kind, label, key, values):
    page, _ = opened(editor, kind)
    undo, redo = (page.get_by_label(name, exact=True) for name in ("Rückgängig", "Wiederholen"))
    for _ in values[1:]:
        walk(page, label, key)
    expect(field(page, label)).to_have_value(values[2])
    for value in (values[1], values[0]):
        undo.click()
        expect(field(page, label)).to_have_value(value)
    expect(undo).to_be_disabled()
    for value in values[1:]:
        redo.click()
        expect(field(page, label)).to_have_value(value)
    expect(redo).to_be_disabled()


# Implied #257, I4


@pytest.mark.parametrize(
    "kind, label, key, prop, values",
    [
        ("ruling", "Art der Lineatur", "ArrowUp", "kind", ("l4", "l3", "l2")),
        ("text", "Schriftart", "ArrowDown", "font", (None, "grund", "va")),
    ],
)
def test_a_pick_in_a_list_is_one_step_for_all_the_selected_blocks(
    editor, kind, label, key, prop, values
):
    page, client = opened(editor, kind, 2)
    undo = page.get_by_label("Rückgängig", exact=True)
    for _ in values[1:]:
        walk(page, label, key)
    for value in reversed(values):
        assert [b["props"].get(prop) for b in saved(page, client)] == [value, value]
        expect_picked(page, "a", "b")
        if value != values[0]:
            undo.click()
    expect(undo).to_be_disabled()
