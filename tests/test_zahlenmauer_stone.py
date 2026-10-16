"""A Zahlenmauer stone on the sheet: a double click opens its number field, as a table cell does.

The docstrings name the lines of the checklist that each test proves.
"""

import pytest
from playwright.sync_api import expect
from test_words import undo
from ui import at, box, doc, pick, unpick, user

WALL = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
# The top stone of the second wall: row 2 of a base of 3, stone 5 of the wall.
TOP_OF_SECOND = '.wall[data-wall="1"] .stone[data-stone="5"]'


@pytest.fixture
def editor(editor):
    """The editor without a theme, as the Zahlenmauer tests of the format panel have it."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def props_of(stored):
    """The props of the one Zahlenmauer of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlenmauer"]
    return block["props"]


def number_field(page):
    return at(page, "w").locator("input[inputmode=numeric]")


def test_double_click_on_a_stone_opens_a_field_that_stores_the_number(editor):
    """Z7: a double click on a stone opens its number field on the sheet; 25 typed is stored."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    pick(page, "w")
    at(page, "w").locator(TOP_OF_SECOND).dblclick()
    expect(number_field(page)).to_be_focused()
    page.keyboard.type("25")
    expect(number_field(page)).to_have_value("25")
    assert props_of(doc(page, client))["typed"] == [[1, 5, 25]]


@pytest.mark.parametrize("end", ["Enter", "Escape", "click"])
def test_enter_escape_or_a_click_elsewhere_ends_the_field(editor, end):
    """Z7: Enter, Escape or a click elsewhere closes the field and keeps the number."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    pick(page, "w")
    at(page, "w").locator(TOP_OF_SECOND).dblclick()
    expect(number_field(page)).to_be_focused()
    page.keyboard.type("25")
    if end == "click":
        unpick(page)
    else:
        page.keyboard.press(end)
    expect(number_field(page)).to_have_count(0)
    assert props_of(doc(page, client))["typed"] == [[1, 5, 25]]


def test_one_ctrl_z_after_takes_the_typed_number_back(editor):
    """Z7: the two digits of 25 are one undo step; one Ctrl+Z removes the stone's number."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    pick(page, "w")
    at(page, "w").locator(TOP_OF_SECOND).dblclick()
    expect(number_field(page)).to_be_focused()
    page.keyboard.type("25")
    page.keyboard.press("Enter")
    expect(number_field(page)).to_have_count(0)
    assert props_of(doc(page, client))["typed"] == [[1, 5, 25]]
    undo(page)
    assert "typed" not in props_of(doc(page, client))


def test_only_digits_go_into_the_field(editor):
    """Z7: a letter is refused as in the panel's field; 2a5 shows 25."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    pick(page, "w")
    at(page, "w").locator(TOP_OF_SECOND).dblclick()
    expect(number_field(page)).to_be_focused()
    page.keyboard.type("2a5")
    expect(number_field(page)).to_have_value("25")
    page.keyboard.press("Enter")
    assert props_of(doc(page, client))["typed"] == [[1, 5, 25]]
