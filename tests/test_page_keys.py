"""Delete on a focused page thumbnail deletes its page; page keys steer the page in use."""

import re

from playwright.sync_api import expect
from test_pages import expect_order, three, write
from ui import TEXT, at, bar, box, doc, pick, thumb, user

ON = re.compile(r"\bon\b")


def test_delete_on_a_focused_thumbnail_deletes_its_page_and_undo_brings_it_back(editor):
    page = three(editor)
    thumb(page, 1).focus()
    page.keyboard.press("Delete")
    expect_order(page, "ac")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "ac")


def test_the_last_page_is_not_deleted(editor):
    page = editor(box("a", "text", TEXT), theme="")
    thumb(page, 0).focus()
    page.keyboard.press("Delete")
    expect_order(page, "a")


def test_delete_in_a_text_does_not_touch_the_page(editor):
    page = three(editor)
    write(page, "b", "du")
    page.keyboard.press("Delete")
    page.keyboard.press("Backspace")
    expect_order(page, "abc")


def test_backspace_on_a_thumbnail_deletes_its_page(editor):
    page = three(editor)
    thumb(page, 2).focus()
    page.keyboard.press("Backspace")
    expect_order(page, "ab")


def test_after_a_delete_the_focus_goes_to_the_page_now_in_its_place(editor):
    page = three(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Delete")
    expect_order(page, "bc")
    expect(thumb(page, 0)).to_be_focused()
    page.keyboard.press("Delete")
    expect_order(page, "c")


def test_with_a_block_picked_delete_on_a_thumbnail_deletes_the_page_not_the_block(editor):
    page = three(editor)
    pick(page, "a")
    thumb(page, 1).focus()
    page.keyboard.press("Delete")
    expect_order(page, "ac")


def test_delete_on_a_thumbnail_of_another_page_keeps_the_page_in_use(editor):
    page = three(editor)
    thumb(page, 2).click()
    thumb(page, 0).focus()
    page.keyboard.press("Delete")
    expect_order(page, "bc")
    # The page in use is still "c", now the second page: a new text lands there.
    expect(thumb(page, 1)).to_have_class(ON)


def test_deleting_the_page_in_use_puts_the_page_in_use_on_the_one_in_its_place(editor):
    """Extra case: the page in use is deleted, so the page now in its place is in use."""
    page = three(editor)
    thumb(page, 1).click()
    thumb(page, 1).focus()
    page.keyboard.press("Delete")
    expect_order(page, "ac")
    expect(thumb(page, 1)).to_have_class(ON)


def test_shift_or_ctrl_delete_on_a_thumbnail_does_nothing_new(editor):
    """Extra case: a modifier with Delete leaves the pages alone."""
    page = three(editor)
    thumb(page, 1).focus()
    page.keyboard.press("Shift+Delete")
    page.keyboard.press("Control+Delete")
    page.keyboard.press("Alt+Delete")
    expect_order(page, "abc")


def desk_bottom(page):
    return page.locator(".desk").evaluate(
        "el => el.scrollTop + el.clientHeight >= el.scrollHeight - 2"
    )


def scroll_to_page(page, key, want, limit=12):
    """Presses the key until the desk is at its bottom, the view of the last page."""
    for _ in range(limit):
        if want():
            return
        page.keyboard.press(key)
        page.wait_for_timeout(150)


def click_desk_beside_pages(page):
    box_ = page.locator(".desk").bounding_box()
    page.mouse.click(box_["x"] + 8, box_["y"] + box_["height"] / 2)


def test_page_down_makes_the_page_in_view_the_page_in_use(editor):
    page = three(editor)
    click_desk_beside_pages(page)
    scroll_to_page(page, "PageDown", lambda: desk_bottom(page))
    expect(thumb(page, 2)).to_have_class(ON)


def test_end_and_home_make_the_page_in_view_the_page_in_use(editor):
    page = three(editor)
    click_desk_beside_pages(page)
    page.keyboard.press("End")
    page.wait_for_timeout(800)
    expect(thumb(page, 2)).to_have_class(ON)
    click_desk_beside_pages(page)
    page.keyboard.press("Home")
    page.wait_for_timeout(800)
    expect(thumb(page, 0)).to_have_class(ON)


def test_the_arrows_make_the_page_in_view_the_page_in_use(editor):
    page = three(editor)
    click_desk_beside_pages(page)
    scroll_to_page(page, "ArrowDown", lambda: desk_bottom(page), limit=80)
    page.wait_for_timeout(800)
    expect(thumb(page, 2)).to_have_class(ON)


def test_an_arrow_with_a_block_picked_nudges_the_block_and_does_not_steer(editor):
    page = three(editor)
    pick(page, "a")
    before = at_top(page, "a")
    page.keyboard.press("ArrowDown")
    expect(at_top_locator(page, "a")).not_to_have_css("top", before)
    page.locator(".desk").evaluate("el => el.scrollTo(0, el.scrollHeight)")
    page.wait_for_timeout(800)
    page.keyboard.press("ArrowDown")
    expect(thumb(page, 0)).to_have_class(ON)


def at_top(page, name):
    return at_top_locator(page, name).evaluate("el => getComputedStyle(el).top")


def at_top_locator(page, name):
    return at(page, name)


def on_page(page, n):
    """The thumbnail of page n is the one in use."""
    expect(thumb(page, n)).to_have_class(ON)


def test_a_block_added_after_page_down_lands_on_page_3(editor):
    client = user()
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    page = editor(box("a", "text", TEXT), client=client, pages=rest, theme="")
    click_desk_beside_pages(page)
    scroll_to_page(page, "PageDown", lambda: desk_bottom(page))
    on_page(page, 2)
    page.locator(".dock, .insert").get_by_label("Text", exact=True).click()
    saved_pages = doc(page, client)["pages"]
    assert [len(p["blocks"]) for p in saved_pages] == [1, 1, 2]


def test_a_text_being_written_keeps_its_page_in_use(editor):
    page = three(editor)
    write(page, "b", "du")
    on_page(page, 1)
    page.keyboard.press("PageDown")
    page.wait_for_timeout(800)
    on_page(page, 1)


def test_a_number_field_with_the_focus_keeps_the_page_in_use(editor):
    page = three(editor)
    pick(page, "a")
    page.locator("input.mm").first.focus()
    on_page(page, 0)
    page.keyboard.press("PageDown")
    page.wait_for_timeout(800)
    on_page(page, 0)


def test_delete_in_a_number_field_does_not_touch_the_page(editor):
    page = three(editor)
    pick(page, "a")
    page.locator("input.mm").first.focus()
    page.keyboard.press("Delete")
    expect_order(page, "abc")
    expect(page.locator(".block.sel")).to_have_count(1)


def test_tab_reaches_a_thumbnail_and_delete_removes_its_page(editor):
    page = three(editor)
    pick(page, "a")
    bar(page, "left").focus()
    for _ in range(40):
        if thumb(page, 1).evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(thumb(page, 1)).to_be_focused()
    page.keyboard.press("Delete")
    expect_order(page, "ac")
