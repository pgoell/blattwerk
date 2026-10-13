"""A Lineatur or a Karo grows by whole rows for the text typed into it."""

import pytest
from playwright.sync_api import expect
from ui import RULING, at, box, saved, user

# The rows of each kind, in mm: a block of two rows is this high.
ROW = {"l1": 20, "l3": 11.5, "l4": 10, "k5": 5, "k7": 7}
# A mm on the screen at 100 %, as the editor scales its page (sheet.tsx, K).
PX = 96 / 25.4


def height(page, client, name="l"):
    return next(b for b in saved(page, client) if b["id"] == name)["h"]


def needs_every_row(field, kind):
    """The field holds the text, and one row less would not: the text takes every row."""
    assert field.evaluate("e => e.scrollHeight <= e.clientHeight + 1")
    # Shorter by one row, the field would scroll.
    script = (
        "(e, px) => { const h = e.clientHeight - px; e.style.height = h + 'px';"
        " return e.scrollHeight > h + 1; }"
    )
    less = field.evaluate(script, ROW[kind] * PX)
    assert less


@pytest.mark.parametrize("kind", ["l1", "l3", "l4"])
def test_text_past_the_last_row_grows_a_lineatur_by_whole_rows(editor, kind):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": kind}, z=2, h=2 * ROW[kind]), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma " * 40)
    h = height(page, client)
    rows = round(h / ROW[kind])
    assert rows > 2 and h == pytest.approx(rows * ROW[kind], abs=0.01)
    needs_every_row(at(page, "l").locator("textarea"), kind)


@pytest.mark.parametrize("kind", ["l1", "l3", "l4"])
def test_three_typed_lines_take_three_rows(editor, kind):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": kind}, z=2, h=2 * ROW[kind]), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("a")
    page.keyboard.press("Enter")
    page.keyboard.type("b")
    page.keyboard.press("Enter")
    page.keyboard.type("c")
    expect(at(page, "l").locator("textarea")).to_have_value("a\nb\nc")
    assert height(page, client) == pytest.approx(3 * ROW[kind], abs=0.01)


@pytest.mark.parametrize("kind", ["k5", "k7"])
def test_text_past_the_last_square_grows_a_karo(editor, kind):
    client = user()
    karo = box("l", "ruling", {**RULING, "kind": kind}, z=2, w=50, h=2 * ROW[kind])
    page = editor(karo, client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma" * 15)
    # Each letter is a square's character; a space or a line break is drawn as none.
    expect(at(page, "l").locator("svg text")).to_have_count(45)
    # The block's 50 mm hold 7 squares a row for Karo 7 and 10 for Karo 5.
    cols = int(50 // ROW[kind])
    rows = -(-45 // cols)
    assert height(page, client) == pytest.approx(rows * ROW[kind], abs=0.01)


def test_text_that_fits_leaves_the_height_alone(editor):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": "l1"}, z=2, h=40), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma")
    expect(at(page, "l").locator("textarea")).to_have_value("Oma")
    assert height(page, client) == 40


def test_the_block_does_not_grow_past_the_foot_of_the_page(editor):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": "l1"}, z=2, y=250, h=40), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma " * 60)
    expect(at(page, "l").locator("textarea")).not_to_have_value("")
    block = next(b for b in saved(page, client) if b["id"] == "l")
    assert block["y"] + block["h"] <= 297


def test_growth_and_typing_undo_together(editor):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": "l1"}, z=2, h=40), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma")
    expect(at(page, "l").locator("textarea")).to_have_value("Oma")
    page.keyboard.press("Escape")
    # Typing that fits takes one Control+z to empty the text.
    page.keyboard.press("Control+z")
    expect(at(page, "l").locator("textarea")).to_have_value("")
    assert height(page, client) == 40
    # Writing that grows takes the same single press, and the height goes back with the text.
    at(page, "l").dblclick()
    page.keyboard.type("Oma " * 40)
    expect(at(page, "l").locator("textarea")).not_to_have_value("")
    assert height(page, client) > 40
    page.keyboard.press("Escape")
    page.keyboard.press("Control+z")
    expect(at(page, "l").locator("textarea")).to_have_value("")
    assert height(page, client) == 40


def test_the_grown_block_prints_all_its_text(editor):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": "l1"}, z=2, h=40), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma " * 40)
    block = next(b for b in saved(page, client) if b["id"] == "l")
    assert block["h"] > 40
    assert block["props"]["text"] == "Oma " * 40
