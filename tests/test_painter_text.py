"""The brush taken from an open text paints that text, and Escape ends it."""

from playwright.sync_api import expect
from test_painter import (
    FINE,
    brush,
    expect_brush,
    held,
)
from ui import (
    FIELD,
    TEXT,
    at,
    box,
    expect_picked,
    pick,
    stopped,
    user,
)


def test_the_brush_works_from_an_open_text(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "color": "#ff0000"}),
        box("b", "text", {**TEXT, "text": "du"}, z=2),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    # In the field Ctrl+Shift+C copies the look of the caret's word, not the browser's.
    assert stopped(page, "Control+Shift+C")
    expect_brush(page, False)
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("Hallo")
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect_picked(page, "b")
    expect_brush(page, False)
    b = held(page, client)["b"]
    # The block's colour and the picked words' bold, both for the whole of the target.
    assert b == {**TEXT, "text": "du", "color": "#ff0000", "bold": True}


def test_a_paint_from_an_open_text_that_changes_nothing_adds_no_step(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT), box("b", "text", {**TEXT, "text": "du"}, z=2), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect_brush(page, False)
    # Words that are not bold look as a block does that says nothing of bold.
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert held(page, client)["b"] == {**TEXT, "text": "du"}


def test_the_brush_by_key_takes_no_words_of_an_earlier_press(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("Hallo")
    # The brush goes on by the mouse with bold words picked, and off again.
    brush(page).click()
    expect_brush(page, True)
    brush(page).click()
    expect_brush(page, False)
    pick(page, "c")
    brush(page).focus()
    page.keyboard.press("Space")
    expect_brush(page, True)
    at(page, "b").click()
    expect_brush(page, False)
    assert held(page, client)["b"] == TEXT


def test_escape_in_an_open_text_ends_the_brush(editor):
    page = editor(box("a", "text", FINE), box("b", "text", TEXT, z=2))
    pick(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    at(page, "b").click()
    expect_picked(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    # Ctrl+Shift+V in the field gives the caret's word the look, and is not the browser's.
    assert stopped(page, "Control+Shift+V")
    page.keyboard.press("Escape")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect_brush(page, False)
