"""Who has the keys after a press in the format panel, and what Escape does to a selection."""

import re

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
    expect_picked,
    maths,
    pick,
    picture,
    upload,
    user,
)

OPEN = ".ProseMirror, .block textarea:not([readonly])"
# Every select and colour input the panel shows for a block, by its label.
CONTROLS = {
    "text": ["Schriftart", "Farbe", "Füllung", "Rand"],
    "shape": ["Schriftart", "Farbe", "Füllung", "Rand"],
    "line": ["Füllung", "Rand"],
    "ruling": ["Art der Lineatur", "Farbe", "Schriftart auf den Zeilen"],
    "table": ["Schriftart der Tabelle", "Farbe", "Linien"],
}
KINDS = {
    "text": ("text", TEXT),
    "shape": ("shape", RECT),
    "line": ("shape", LINE),
    "ruling": ("ruling", RULING),
    "table": ("table", TABLE),
}
LABEL = "(el) => el.getAttribute('aria-label') ?? el.closest('label').firstChild.textContent.trim()"


def choose(page, label):
    """Picks another font or colour in a control of the panel, as the mouse does.

    No test can press in an open list or a colour picker, so the press is a pointerdown made by
    hand and the focus is given, as a real press gives it. A colour's `input` comes while its
    picker is dragged and its `change` when the picker closes.
    """
    control = page.locator(".panel").get_by_label(label, exact=True)
    control.dispatch_event("pointerdown")
    control.focus()
    if control.evaluate("el => el.tagName") == "SELECT":
        other = "el => [...el.options].find((o) => !o.selected && o.value).value"
        control.select_option(control.evaluate(other))
    else:
        # React hears only of a value set as the browser sets it.
        control.evaluate(
            """(el) => {
                const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
                own.set.call(el,el.value === "#ff0000" ? "#00ff00" : "#ff0000");
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
            }"""
        )
    return control


def everything(client):
    """One block of every type, two of them a group, and a text behind them all."""
    group = {"group": ["g"]}
    return [
        box("text", "text", TEXT),
        box("shape", "shape", RECT, z=2),
        box("line", "shape", LINE, z=3),
        {**picture(upload(client)), "id": "picture", "y": 230, "h": 20, "z": 4},
        box("table", "table", TABLE, z=5, x=110, y=20, w=80),
        box("ruling", "ruling", RULING, z=6, x=110, y=50, w=80),
        box("maths", "maths", maths(client), z=7, x=110, y=80, w=80),
        box("one", "text", TEXT, z=8, x=110, y=110, w=40, **group),
        box("two", "text", TEXT, z=9, x=155, y=110, w=40, **group),
    ]


# Asked #98


def test_a_panel_button_leaves_the_caret_in_a_text(editor):
    page = editor(box("a", "text", TEXT))
    field, bigger = page.locator(FIELD), page.get_by_label("Schrift größer")
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    bigger.click()
    expect(field).to_be_focused()
    # 16 pt. WebKit writes one more digit of it than Chromium does.
    expect(field).to_have_css("font-size", re.compile(r"^21\.3333\d*px$"))
    page.keyboard.type("x")
    expect(field).to_have_text("Hallox")
    bigger.click()
    page.keyboard.press("Backspace")
    expect(field).to_have_text("Hallo")
    bigger.click()
    page.keyboard.press("Enter")
    expect(field.locator("p")).to_have_count(2)
    for key in ("F2", "Escape"):
        bigger.click()
        expect(field).to_be_focused()
        page.keyboard.press(key)
        expect(page.locator(".ProseMirror")).to_have_count(0)
        expect_picked(page, "a")
        page.keyboard.press("Enter")
    expect(field).to_be_focused()


def test_a_panel_button_leaves_the_caret_in_a_ruling(editor):
    page = editor(box("lines", "ruling", RULING))
    written, more = (
        at(page, "lines").locator("textarea.written"),
        page.get_by_label("Eine Zeile mehr"),
    )
    pick(page, "lines")
    page.keyboard.press("Enter")
    page.keyboard.type("abc")
    more.click()
    expect(page.locator(".panel output").first).to_have_text("3 Zeilen")
    expect(written).to_be_focused()
    page.keyboard.type("x")
    expect(written).to_have_value("abcx")
    more.click()
    page.keyboard.press("Backspace")
    expect(written).to_have_value("abc")
    more.click()
    page.keyboard.press("Enter")
    expect(written).to_have_value("abc\n")
    for key in ("F2", "Escape"):
        more.click()
        expect(written).to_be_focused()
        page.keyboard.press(key)
        expect(written).not_to_be_editable()
        expect_picked(page, "lines")
        page.keyboard.press("Enter")
    expect(written).to_be_focused()


def test_a_panel_button_leaves_the_caret_in_a_cell(editor):
    page = editor(box("table", "table", TABLE))
    cell, below = at(page, "table").locator("textarea"), page.get_by_text("Zeile darunter")
    pick(page, "table")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    below.click()
    expect(at(page, "table").locator("[data-cell]")).to_have_count(6)
    expect(cell).to_be_focused()
    page.keyboard.type("x")
    expect(cell).to_have_value("Hx")
    below.click()
    page.keyboard.press("Backspace")
    expect(cell).to_have_value("H")
    below.click()
    page.keyboard.press("Enter")
    expect(cell).to_have_value("H\n")
    for key in ("F2", "Escape"):
        below.click()
        expect(cell).to_be_focused()
        page.keyboard.press(key)
        expect(cell).to_have_count(0)
        expect_picked(page, "table")
        page.keyboard.press("Enter")
    expect(cell).to_be_focused()


# Asked #99


@pytest.mark.parametrize("name, label", [(n, c) for n, cs in CONTROLS.items() for c in cs])
def test_a_pick_with_the_mouse_gives_the_keys_back_to_the_sheet(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    # The list above names every control there is, so a new one fails here until it is tested.
    found = page.locator(".panel select, .panel input[type=color]").evaluate_all(
        f"els => els.map({LABEL})"
    )
    assert found == CONTROLS[name]

    control = choose(page, label)
    expect(control).not_to_be_focused()
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")

    choose(page, label)
    page.keyboard.press("Tab")
    expect_picked(page, "z")

    # A line holds no text to open.
    if name != "line":
        pick(page, name)
        choose(page, label)
        page.keyboard.press("Enter")
        expect(page.locator(OPEN)).to_be_focused()


def test_a_pick_in_a_select_of_a_maths_block_gives_the_keys_back(editor):
    client = user()
    page = editor(box("z", "text", TEXT), box("maths", "maths", maths(client), z=2), client=client)
    pick(page, "maths")
    expect(choose(page, "Zahlenraum")).not_to_be_focused()
    page.keyboard.press("Tab")
    expect_picked(page, "z")


def test_who_walks_a_select_with_the_keys_keeps_the_focus(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    # The last press was in the panel, but the select is reached without one.
    page.get_by_label("Schrift größer").click()
    font = page.get_by_label("Schriftart")
    font.focus()
    was = font.input_value()
    page.keyboard.press("ArrowDown")
    expect(font).not_to_have_value(was)
    expect(font).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(font).to_be_focused()
    # Tab stays the browser's and goes on to the next field of the panel.
    page.keyboard.press("Tab")
    expect(font).not_to_be_focused()
    assert page.evaluate("!!document.activeElement.closest('.panel')")
    expect_picked(page, "a")


# Asked #101


def test_a_ruling_is_a_tab_stop_only_while_written_in(editor):
    page = editor(box("lines", "ruling", RULING))
    written = at(page, "lines").locator("textarea.written")
    expect(written).to_have_js_property("tabIndex", -1)
    pick(page, "lines")
    page.keyboard.press("Enter")
    expect(written).to_be_focused()
    expect(written).to_have_js_property("tabIndex", 0)
    page.keyboard.press("Escape")
    expect(written).to_have_js_property("tabIndex", -1)


# Asked #102

SELECTIONS = [
    ["text"],
    ["shape"],
    ["line"],
    ["picture"],
    ["table"],
    ["ruling"],
    ["maths"],
    ["one", "two"],
    ["text", "shape", "picture"],
]


@pytest.mark.parametrize("names", SELECTIONS, ids="+".join)
def test_escape_selects_nothing(editor, names):
    client = user()
    page = editor(*everything(client), client=client)
    # A click on a block of a group picks the whole group.
    for i, name in enumerate(names if names != ["one", "two"] else ["one"]):
        at(page, name).click(modifiers=["Shift"] if i else [])
    expect_picked(page, *names)
    page.keyboard.press("Escape")
    expect_picked(page)
    # Escape is no step to undo.
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    page.keyboard.press("Control+z")
    expect(page.locator(".block")).to_have_count(9)
    expect(page.locator(OPEN)).to_have_count(0)


# Implied 1


@pytest.mark.parametrize("kind, props", [("text", TEXT), ("shape", RECT)])
def test_a_pick_with_the_mouse_gives_the_keys_back_to_an_open_text(editor, kind, props):
    page = editor(box("a", kind, props), box("b", "text", TEXT, z=2))
    field = page.locator(FIELD)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Wort")
    for label, letter, text in (("Schriftart", "x", "Wortx"), ("Farbe", "y", "Wortxy")):
        choose(page, label)
        expect(field).to_be_focused()
        # The key right after the pick is the field's.
        page.keyboard.type(letter)
        expect(field).to_have_text(text)
    choose(page, "Schriftart")
    page.keyboard.press("Backspace")
    expect(field).to_have_text("Wortx")
    expect_picked(page, "a")


# Implied 3


def test_an_escape_that_ends_something_else_keeps_the_selection(editor):
    client = user()
    page = editor(*everything(client), client=client)
    undo = page.get_by_label("Rückgängig", exact=True)

    def then_none(name):
        expect_picked(page, name)
        page.keyboard.press("Escape")
        expect_picked(page)

    # A crop.
    at(page, "picture").dblclick()
    expect(page.locator(".crop")).to_have_count(1)
    page.keyboard.press("Escape")
    expect(page.locator(".crop")).to_have_count(0)
    then_none("picture")

    # The brush.
    brush = page.get_by_label("Format übertragen", exact=True)
    pick(page, "shape")
    brush.click()
    expect(brush).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Escape")
    expect(brush).to_have_attribute("aria-pressed", "false")
    then_none("shape")

    # The right click's menu.
    page.mouse.click(*centre(at(page, "shape")), button="right")
    expect(page.get_by_role("menu")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("menu")).to_have_count(0)
    then_none("shape")

    # A text, a cell and a Lineatur being written in.
    for name in ("text", "table", "ruling"):
        pick(page, name)
        page.keyboard.press("Enter")
        expect(page.locator(OPEN)).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.locator(OPEN)).to_have_count(0)
        then_none(name)
    expect(undo).to_be_disabled()


# Implied 4


def test_escape_in_a_field_of_the_panel_or_in_the_title_keeps_the_selection(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    x = page.get_by_label("X", exact=True)
    x.click()
    page.keyboard.type("99")
    page.keyboard.press("Escape")
    # The field drops what was typed and keeps the focus.
    expect(x).to_have_value("15")
    expect(x).to_be_focused()
    expect_picked(page, "a")
    title = page.get_by_label("Titel")
    title.focus()
    page.keyboard.press("Escape")
    expect(title).to_be_focused()
    expect_picked(page, "a")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    # With nothing to undo Ctrl+Z leaves the sheet as it is.
    title.blur()
    page.keyboard.press("Control+z")
    expect(x).to_have_value("15")
    expect_picked(page, "a")


def test_a_disabled_panel_button_leaves_the_caret_too(editor):
    page = editor(box("a", "text", TEXT), box("table", "table", TABLE, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    # A text with no fill has nothing to take away.
    off = page.locator(".panel button:disabled", has_text="Keine Füllung")
    page.mouse.click(*centre(off))
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Hallox")
    page.keyboard.press("Backspace")
    expect(page.locator(FIELD)).to_have_text("Hallo")
    # A table never turns.
    pick(page, "table")
    page.keyboard.press("Enter")
    cell = at(page, "table").locator("textarea")
    expect(cell).to_be_focused()
    page.mouse.click(*centre(page.locator(".panel button:disabled").first))
    expect(cell).to_be_focused()
    page.keyboard.press("Backspace")
    expect(page.locator(".block")).to_have_count(2)


def test_a_panel_button_leaves_a_draft_in_a_number_field(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    x = page.get_by_label("X", exact=True)
    x.click()
    page.keyboard.type("40")
    page.locator(".panel button.bold").click()
    expect(x).to_be_focused()
    # Backspace is the number's, not the block's.
    page.keyboard.press("Backspace")
    expect(x).to_have_value("4")
    expect(page.locator(".block")).to_have_count(2)
