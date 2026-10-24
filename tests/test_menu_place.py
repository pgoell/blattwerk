"""Where the editor's menu sits, and the keys that walk its entries.

The helpers live in test_menu.py.
"""

import pytest
from playwright.sync_api import expect
from test_menu import (
    item,
    left,
    menu,
    right,
    texts,
)
from ui import (
    order,
)


def test_the_arrows_walk_the_enabled_entries_and_enter_runs_one(editor):
    """I3"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    expect(item(page, "Ausschneiden")).to_be_focused()
    # "a" lies at the back, so the two backward entries are grey.
    page.keyboard.press("ArrowUp")
    expect(item(page, "Eine Ebene nach vorn")).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(item(page, "Ausschneiden")).to_be_focused()
    for name in ("Kopieren", "Einfügen", "Text bearbeiten", "Duplizieren", "Löschen", "Sperren"):
        page.keyboard.press("ArrowDown")
        expect(item(page, name)).to_be_focused()
    # Neither Gruppieren nor Gruppierung aufheben can do anything for one block.
    page.keyboard.press("ArrowDown")
    expect(item(page, "In den Vordergrund")).to_be_focused()
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowUp")
    expect(item(page, "Löschen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(page.locator(".block[data-id]")).to_have_count(1)
    assert order(page) == [["b"]]


@pytest.mark.parametrize(
    "keys",
    ["Delete", "Backspace", "Control+x", "Control+d", "ArrowRight", "Shift+F10", "ContextMenu"],
)
def test_the_sheets_keys_do_not_reach_it_while_the_menu_is_open(editor, keys):
    """I3"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    before = left(page, "a")
    page.keyboard.press(keys)
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    # Nothing to undo: the key made no step.
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    assert order(page) == [["a", "b"]]
    assert left(page, "a") == before


def test_a_menu_higher_than_the_window_scrolls(editor):
    """I7"""
    # "b" lies over "a", so the last entry can take it to the back.
    page = editor(*texts(*"ab"))
    # Wide enough for Blattform's layout: in a narrower window the dock lies over the block.
    page.set_viewport_size({"width": 1100, "height": 320})
    right(page, "b")
    box = menu(page).bounding_box()
    assert box["y"] >= 0 and box["y"] + box["height"] <= 320
    item(page, "In den Hintergrund").click()
    expect(menu(page)).to_be_hidden()


def test_the_menu_stays_inside_the_window(editor):
    """I7"""
    page = editor(*texts("a"))
    # Wide enough for Blattform's layout, whose bar of insert tools leaves the desk's corner free.
    heard = "new Promise((done) => addEventListener('resize', done, { once: true }))"
    page.evaluate(f"() => {{ window.heard = {heard} }}")
    page.set_viewport_size({"width": 1100, "height": 500})
    # A window hears of its new size with its next frame, and a menu shuts when it does: one opened
    # before then is gone again.
    page.evaluate("window.heard")
    desk = page.locator(".desk").bounding_box()
    # The desk's scroll bars lie at its very edge.
    x, y = desk["x"] + desk["width"] - 30, desk["y"] + desk["height"] - 30
    page.mouse.click(x, y, button="right")
    expect(menu(page)).to_be_visible()
    shown = menu(page).bounding_box()
    assert shown["x"] + shown["width"] <= 1100
    assert shown["y"] + shown["height"] <= 500
    assert shown["x"] >= 0
    assert shown["y"] >= 0
    # It did move: it would not fit below and right of the click.
    assert shown["x"] < x
    assert shown["y"] < y
