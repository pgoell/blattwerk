"""How a Suchsel is drawn: the rings of the answer key, the squares, and the keys in the words field.

The helpers live in test_suchsel.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_fields import enter
from test_suchsel import (
    LIST8,
    ON_SHEET,
    SUCHSEL,
    editor,  # noqa: F401
    grid,
    rings,
    sq,
    suchsel_props,
)
from ui import at, doc, expect_picked, pick, tool, user

MIDDLE = """el => {
    const b = el.getBoundingClientRect();
    return [b.x + b.width / 2, b.y + b.height / 2];
}"""
BOX = "el => { const b = el.getBoundingClientRect(); return [b.x, b.y, b.right, b.bottom]; }"


def squares_fit(page, name, cols, rows):
    """The squares are square and three letters centred. Gives the square's side."""
    edge = at(page, name).locator("rect.edge").bounding_box()
    side = edge["width"] / cols
    assert side == pytest.approx(edge["height"] / rows, abs=0.5)
    for col, row in ((0, 0), (cols // 2, rows // 2), (cols - 1, rows - 1)):
        # Measured in the page: WebKit gives Playwright another box for a letter of an SVG.
        x, y = at(page, name).locator(f'text[data-at="{col},{row}"]').evaluate(MIDDLE)
        # The box around a letter is as wide as its glyph is set, which lies a hair off its ink.
        assert x - (edge["x"] + (col + 0.5) * side) == pytest.approx(0, abs=0.05 * side)
        assert abs(y - (edge["y"] + (row + 0.5) * side)) <= 0.2 * side
    return side


def test_the_answer_key_rings_each_hidden_word(editor):
    """A12: no ring until "Lösungen zeigen" is on, then one ring per hidden word."""
    page = editor(sq("s", SUCHSEL))
    expect(at(page, "s").locator("rect.ring")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(6)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_each_ring_lies_around_its_word(editor, seed):
    """A12: each ring lies over its word, its middle between its first and last square's."""
    props = {**SUCHSEL, "ways": "back", "cols": 12, "rows": 12, "words": LIST8, "seed": seed}
    page = editor(sq("s", props))
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(len(LIST8))
    edge = at(page, "s").locator("rect.edge").bounding_box()
    side = edge["width"] / 12

    def middle(col, row):
        return (edge["x"] + (col + 0.5) * side, edge["y"] + (row + 0.5) * side)

    ringed = rings(at(page, "s"))
    shapes = at(page, "s").locator("rect.ring.answer").all()
    for ring, shape in zip(ringed, shapes, strict=True):
        last = (ring["n"] - 1) * ring["dc"], (ring["n"] - 1) * ring["dr"]
        first = middle(ring["col"], ring["row"])
        end = middle(ring["col"] + last[0], ring["row"] + last[1])
        # The SVG rounds each rect to its own pixels: a few tenths of a pixel, one of them 1.1 px.
        middle_of_ends = ((first[0] + end[0]) / 2, (first[1] + end[1]) / 2)
        assert shape.evaluate(MIDDLE) == pytest.approx(middle_of_ends, abs=0.05 * side)
        left, top, right, bottom = shape.evaluate(BOX)
        for x, y in (first, end):
            assert left - 1 <= x <= right + 1 and top - 1 <= y <= bottom + 1
    # A ring straight to the right or down tells nothing of the turn: one must be diagonal or back.
    assert any(r["dc"] * r["dr"] != 0 or min(r["dc"], r["dr"]) < 0 for r in ringed)


def test_the_squares_scale_stay_square_and_centred(editor):
    """A13: the squares fill the room the box leaves and stay square and centred, and grow."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    small = squares_fit(page, "s", 10, 10)
    enter(page, "Breite", "200")
    enter(page, "Höhe", "240")
    expect(page.locator(".geo").get_by_label("Breite", exact=True)).to_have_value("200")
    assert squares_fit(page, "s", 10, 10) > small


def test_a_wide_low_box_keeps_the_grid_and_its_list_inside(editor):
    """A13: when the height is the limit the squares shrink; grid and list stay in the box."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    enter(page, "Breite", "180")
    enter(page, "Höhe", "70")
    expect(page.locator(".geo").get_by_label("Höhe", exact=True)).to_have_value("70")
    squares_fit(page, "s", 10, 10)
    block = at(page, "s").bounding_box()
    edge = at(page, "s").locator("rect.edge").bounding_box()
    assert edge["x"] >= block["x"] - 1
    assert edge["x"] + edge["width"] <= block["x"] + block["width"] + 1
    assert edge["y"] >= block["y"] - 1
    assert edge["y"] + edge["height"] <= block["y"] + block["height"] + 1
    found = at(page, "s").locator(".found").bounding_box()
    assert found["y"] >= edge["y"] + edge["height"] - 1
    assert found["y"] + found["height"] <= block["y"] + block["height"] + 1


def test_keys_in_the_words_field_edit_the_text_only(editor):
    """I1: Backspace, Delete, arrows and Ctrl+A act in the field; the block stays picked."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client)
    pick(page, "s")
    place = doc(page, client)["pages"][0]["blocks"][0]
    field = page.get_by_label("Wörter des Suchsels")
    field.click()
    page.keyboard.type("Hund")
    for key in ("Backspace", "ArrowLeft", "Delete", "Control+a"):
        page.keyboard.press(key)
    expect(field).to_be_focused()
    expect_picked(page, "s")
    now = doc(page, client)["pages"][0]["blocks"][0]
    assert (now["x"], now["y"]) == (place["x"], place["y"])


def test_ctrl_z_and_ctrl_y_in_the_words_field_undo_and_redo(editor):
    """I2: Ctrl+Z empties the typed words, Ctrl+Y brings them back, as in the Lernwörter."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client)
    pick(page, "s")
    field = page.get_by_label("Wörter des Suchsels")
    field.click()
    page.keyboard.type("Hund")
    expect(field).to_have_value("Hund")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("")
    assert suchsel_props(doc(page, client))["words"] == []
    page.keyboard.press("Control+y")
    expect(field).to_have_value("Hund")
    assert suchsel_props(doc(page, client))["words"] == ["Hund"]


@pytest.mark.parametrize("keys", [("Control+c", "Control+v"), ("Control+d",)])
def test_a_copy_shows_the_grid_of_its_source(editor, keys):
    """I4: a pasted or duplicated Suchsel shows the same grid as its source."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    for key in keys:
        page.keyboard.press(key)
    expect(page.locator(ON_SHEET)).to_have_count(2)
    source, copy = page.locator(ON_SHEET).all()
    expect(copy.locator("text[data-at]")).to_have_count(100)
    assert grid(copy) == grid(source)
