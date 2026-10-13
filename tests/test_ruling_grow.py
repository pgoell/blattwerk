"""A Lineatur or a Karo grows by whole rows for the text typed into it."""

import pytest
from playwright.sync_api import expect
from ui import RULING, at, box, saved, user

# The rows of each kind, in mm: a block of two rows is this high.
ROW = {"l1": 20, "l3": 11.5, "l4": 10, "k5": 5, "k7": 7}
# The Ctrl+z presses that typing takes: the whole writing is one step.
UNDO_STEPS = 1


def height(page, client, name="l"):
    return next(b for b in saved(page, client) if b["id"] == name)["h"]


@pytest.mark.parametrize("kind", ["l1", "l3", "l4"])
def test_text_past_the_last_row_grows_a_lineatur_by_whole_rows(editor, kind):
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": kind}, z=2, h=2 * ROW[kind]), client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma " * 40)
    field = at(page, "l").locator("textarea")
    h = height(page, client)
    rows = round(h / ROW[kind], 6)
    assert rows == int(rows) and rows > 2
    assert field.evaluate("e => e.scrollHeight <= e.clientHeight + 1")


@pytest.mark.parametrize("kind", ["k5", "k7"])
def test_text_past_the_last_square_grows_a_karo(editor, kind):
    client = user()
    karo = box("l", "ruling", {**RULING, "kind": kind}, z=2, w=50, h=2 * ROW[kind])
    page = editor(karo, client=client)
    at(page, "l").dblclick()
    page.keyboard.type("Oma" * 15)
    # Each letter is a square's character; a space or a line break is drawn as none.
    expect(at(page, "l").locator("svg text")).to_have_count(45)
    h = height(page, client)
    rows = round(h / ROW[kind], 6)
    assert rows == int(rows) and rows > 2


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
    page.keyboard.type("Oma " * 40)
    expect(at(page, "l").locator("textarea")).not_to_have_value("")
    assert height(page, client) > 40
    page.keyboard.press("Escape")
    # The steps that typing alone takes: UNDO_STEPS, as a text that fits shows.
    for _ in range(UNDO_STEPS):
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
