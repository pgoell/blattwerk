"""The keys on a page thumbnail: move by one, jump to an end, and leave a text alone.

The helpers live in test_pages.py.
"""

from playwright.sync_api import expect
from test_pages import (
    expect_order,
    three,
    write,
)
from ui import (
    FIELD,
    thumb,
)


def test_ctrl_and_an_arrow_on_a_thumbnail_move_its_page_by_one_place(editor):
    """I7"""
    page = three(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "bac")
    expect(thumb(page, 1)).to_be_focused()
    # The focus went with the page, so the same key moves it on.
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "bca")
    expect(thumb(page, 2)).to_be_focused()
    page.keyboard.press("Control+ArrowUp")
    expect_order(page, "bac")
    expect(thumb(page, 1)).to_be_focused()


def test_ctrl_shift_and_an_arrow_on_a_thumbnail_move_its_page_to_the_start_or_the_end(editor):
    """I7"""
    page = three(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Control+Shift+ArrowDown")
    expect_order(page, "bca")
    expect(thumb(page, 2)).to_be_focused()
    page.keyboard.press("Control+Shift+ArrowUp")
    expect_order(page, "abc")
    expect(thumb(page, 0)).to_be_focused()


def test_in_a_text_the_page_keys_stay_the_texts(editor):
    """I7"""
    page = three(editor)
    write(page, "a", "du")
    for keys in ("ArrowDown", "ArrowUp", "Shift+ArrowDown", "Shift+ArrowUp", "d"):
        page.keyboard.press(f"Control+{keys}")
        expect(page.locator(FIELD)).to_have_text("du")
        expect_order(page, "abc")
