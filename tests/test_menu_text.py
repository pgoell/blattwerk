"""The right click's entry Text bearbeiten: it opens a block for writing, as F2 does."""

import pytest
from playwright.sync_api import expect
from test_menu import item, menu, right
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
    maths,
    pick,
    picture,
    upload,
    user,
)

# A shape with words of its own, a table and a Lineatur, each with text in its first place.
WRITERS = {
    "text": ("text", TEXT),
    "shape": ("shape", {**RECT, "text": "Hallo"}),
    "table": ("table", TABLE),
    "ruling": ("ruling", {**RULING, "text": "abc"}),
}


def written(page, kind):
    """Where the text is typed: the editor's field, the table's cell or the ruling's line."""
    if kind == "table":
        return at(page, "a").locator("textarea")
    if kind == "ruling":
        return at(page, "a").locator("textarea.written")
    return page.locator(FIELD)


@pytest.mark.parametrize("kind", list(WRITERS))
def test_text_bearbeiten_opens_the_block_with_all_its_text_picked(editor, kind):
    """A test that types over the old text: it must be all picked, as F2 picks it."""
    made, props = WRITERS[kind]
    page = editor(box("a", made, props))
    right(page, "a")
    item(page, "Text bearbeiten").click()
    expect(menu(page)).to_have_count(0)
    expect(written(page, kind)).to_be_focused()
    page.keyboard.type("x")
    if kind in ("text", "shape"):
        expect(written(page, kind)).to_have_text("x")
    else:
        expect(written(page, kind)).to_have_value("x")


@pytest.mark.parametrize("kind", list(WRITERS))
def test_text_bearbeiten_is_disabled_on_a_locked_block(editor, kind):
    made, props = WRITERS[kind]
    page = editor(box("a", made, props, locked=True))
    right(page, "a")
    expect(item(page, "Text bearbeiten")).to_be_disabled()


def test_text_bearbeiten_is_offered_on_points_and_on_a_name_block(editor):
    page = editor(box("p", "points", {"max": 10}), box("n", "name", {}, z=2))
    right(page, "p")
    item(page, "Text bearbeiten").click()
    expect(at(page, "p").locator("input")).to_be_focused()
    page.keyboard.press("Escape")
    right(page, "n")
    expect(item(page, "Text bearbeiten")).to_be_enabled()
    item(page, "Text bearbeiten").click()
    expect(at(page, "n").locator("input").first).to_be_focused()


def test_text_bearbeiten_is_absent_for_a_picture_a_line_maths_a_group_and_two_blocks(editor):
    client = user()
    page = editor(
        box("bild", "image", picture(upload(client))["props"]),
        box("linie", "shape", LINE, z=2),
        box("rechnung", "maths", maths(client), z=3),
        box("g1", "text", TEXT, z=4, group=["g"]),
        box("g2", "text", TEXT, z=5, group=["g"]),
        box("x", "text", TEXT, z=6),
        box("y", "text", TEXT, z=7),
    )
    for name in ("bild", "linie", "rechnung", "g1"):
        right(page, name)
        expect(item(page, "Text bearbeiten")).to_have_count(0)
        page.keyboard.press("Escape")
    pick(page, "x", "y")
    right(page, "x")
    expect(item(page, "Text bearbeiten")).to_have_count(0)


def test_text_bearbeiten_on_the_second_cell_puts_the_caret_there(editor):
    page = editor(box("t", "table", TABLE))
    right(page, "t")
    page.mouse.click(*centre(at(page, "t").locator('[data-cell="1"]')), button="right")
    expect(menu(page)).to_be_visible()
    item(page, "Text bearbeiten").click()
    expect(menu(page)).to_have_count(0)
    page.keyboard.type("x")
    expect(at(page, "t").locator("textarea")).to_have_value("x")
    page.keyboard.press("Escape")
    expect(at(page, "t").locator('[data-cell="0"]')).to_have_text("H")
    expect(at(page, "t").locator('[data-cell="1"]')).to_have_text("x")


def test_text_bearbeiten_from_the_keys_puts_the_caret_in_the_first_cell(editor):
    """Shift+F10 knows no cell: the first gets the caret, also after a right click on another."""
    page = editor(box("t", "table", TABLE))
    page.mouse.click(*centre(at(page, "t").locator('[data-cell="1"]')), button="right")
    expect(item(page, "Text bearbeiten")).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    page.keyboard.press("Shift+F10")
    expect(item(page, "Text bearbeiten")).to_be_visible()
    item(page, "Text bearbeiten").focus()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.type("x")
    page.keyboard.press("Escape")
    expect(at(page, "t").locator('[data-cell="0"]')).to_have_text("x")
    expect(at(page, "t").locator('[data-cell="1"]')).not_to_have_text("x")


def test_opening_by_the_entry_adds_no_undo_step_and_escape_ends_the_writing(editor):
    page = editor(box("a", "text", TEXT))
    right(page, "a")
    item(page, "Text bearbeiten").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()


def test_a_frame_right_click_ends_an_open_text_and_offers_the_entry(editor):
    """The frame's right click ends the writing first, so the entry is offered for the text shut."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("F2")
    expect(page.locator(FIELD)).to_be_focused()
    # The block's frame, a little in from its corner: the text itself takes the browser's own menu.
    corner = at(page, "a").bounding_box()
    page.mouse.click(corner["x"] + 1, corner["y"] + 1, button="right")
    expect(menu(page)).to_be_visible()
    expect(page.locator(FIELD)).to_have_count(0)
    item(page, "Text bearbeiten").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("x")


def test_an_empty_rectangle_gets_the_entry_and_opens_with_a_caret(editor):
    """Extra case: an empty rectangle counts as a shape with words, as in PowerPoint."""
    page = editor(box("a", "shape", RECT))
    right(page, "a")
    item(page, "Text bearbeiten").click()
    expect(page.locator(FIELD)).to_be_focused()


def test_a_right_click_on_another_text_offers_the_entry_for_that_text(editor):
    """Extra case: the right click picks the text it lands on, and the entry goes to that text."""
    page = editor(box("a", "text", TEXT), box("b", "text", {**TEXT, "text": "Welt"}, z=2))
    pick(page, "a")
    right(page, "b")
    item(page, "Text bearbeiten").click()
    expect(page.locator(FIELD)).to_have_text("Welt")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("x")


# Each block that Text bearbeiten opens, where its text is typed, and the key typed (#640).
AT_ONCE = {
    "text": (box("a", "text", TEXT), lambda page: page.locator(FIELD), "x"),
    "shape": (box("a", "shape", {**RECT, "text": "Hallo"}), lambda page: page.locator(FIELD), "x"),
    "first cell": (box("a", "table", TABLE), lambda page: at(page, "a").locator("textarea"), "x"),
    "second cell": (box("a", "table", TABLE), lambda page: at(page, "a").locator("textarea"), "x"),
    "ruling": (
        box("a", "ruling", {**RULING, "text": "abc"}),
        lambda page: at(page, "a").locator("textarea.written"),
        "x",
    ),
    "points": (box("a", "points", {"max": 10}), lambda page: at(page, "a").locator("input"), "7"),
    "name": (box("a", "name", {}), lambda page: at(page, "a").locator("input").first, "x"),
}


@pytest.mark.parametrize("kind", list(AT_ONCE))
def test_a_key_typed_at_once_after_text_bearbeiten_lands_in_the_block(editor, kind):
    """The entry opens its block a moment later. A key typed in that moment goes there all the
    same, over the picked text, and into the cell the right click named. The clock stands still
    between the click and the key, so the key always comes first."""
    made, field, key = AT_ONCE[kind]
    page = editor(made)
    if kind == "second cell":
        page.mouse.click(*centre(at(page, "a").locator('[data-cell="1"]')), button="right")
    else:
        right(page, "a")
    expect(item(page, "Text bearbeiten")).to_be_enabled()
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    item(page, "Text bearbeiten").click()
    page.keyboard.type(key)
    page.clock.run_for(100)
    page.clock.resume()
    page.keyboard.type(key)
    if kind in ("text", "shape"):
        expect(field(page)).to_have_text(key * 2)
    else:
        expect(field(page)).to_have_value(key * 2)
    page.keyboard.press("Escape")
    if kind == "first cell":
        expect(at(page, "a").locator('[data-cell="0"]')).to_have_text("xx")
        expect(at(page, "a").locator('[data-cell="1"]')).to_have_text("Z")
    if kind == "second cell":
        expect(at(page, "a").locator('[data-cell="0"]')).to_have_text("H")
        expect(at(page, "a").locator('[data-cell="1"]')).to_have_text("xx")
