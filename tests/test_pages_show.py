"""Undo and redo show the page the change was on.

The helpers live in test_pages.py.
"""

import pytest
from playwright.sync_api import expect
from test_clipboard import button
from test_pages import (
    PICKED,
    PICKER,
    copy,
    expect_in_use,
    expect_order,
    left,
    three,
)
from ui import (
    RECT,
    at,
    box,
    copy_picture,
    order,
    pick,
    thumb,
)

# What changes the pages with "b", the second of three, in use: how many pages there are then,
# which is in use, where a block asked for on "b" lands and how many blocks the sheet then has.
# With "b" deleted the block lands on the page in use.
CHANGES = {
    "new": (lambda page: button(page, "Neue Seite").click(), 4, 2, 1, 4),
    "deleted": (lambda page: button(page, "Seite löschen").click(), 2, 1, 1, 3),
    "moved": (lambda page: page.keyboard.press("Control+ArrowUp"), 3, 0, 0, 4),
    "copied": (lambda page: copy(page).click(), 4, 2, 1, 5),
}


def change_pages(page, how):
    """Changes the pages and waits for it. Gives the page in use from then on."""
    run, count, after, _, _ = CHANGES[how]
    thumb(page, 1).focus()
    run(page)
    expect(page.locator(".sheet[data-page]")).to_have_count(count)
    expect_in_use(page, after)
    return after


def expect_shown(page, n):
    """Waits until page n is in use and the desk has scrolled to it."""
    expect_in_use(page, n)
    expect(page.locator(f'.sheet[data-page="{n}"]')).to_be_in_viewport(ratio=0.5)


@pytest.mark.parametrize("how", CHANGES)
def test_undo_and_redo_of_a_page_change_show_the_page_it_changed(editor, how):
    """#155: undo shows the page in use before the change, redo the one in use after it."""
    page = three(editor)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    after = change_pages(page, how)
    away = 0 if after else 2
    thumb(page, away).click()
    expect_shown(page, away)
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    expect_shown(page, 1)
    thumb(page, 2 - away).click()
    expect_shown(page, 2 - away)
    page.keyboard.press("Control+y")
    expect(page.locator(".sheet[data-page]")).to_have_count(CHANGES[how][1])
    expect_shown(page, after)


def test_undo_and_redo_of_a_block_change_show_its_page(editor):
    """#155"""
    page = three(editor)
    pick(page, "b")
    before = left(page, "b")
    page.keyboard.press("ArrowRight")
    expect(at(page, "b")).not_to_have_css("left", before)
    thumb(page, 0).click()
    expect_shown(page, 0)
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_css("left", before)
    expect_shown(page, 1)
    thumb(page, 2).click()
    expect_shown(page, 2)
    page.keyboard.press("Control+y")
    expect(at(page, "b")).not_to_have_css("left", before)
    expect_shown(page, 1)


def test_undo_of_a_change_on_the_page_in_use_keeps_the_selection(editor):
    """#155: the selection stays when the undo is for the page in use."""
    page = three(editor)
    pick(page, "b")
    before = left(page, "b")
    page.keyboard.press("ArrowRight")
    expect(at(page, "b")).not_to_have_css("left", before)
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_css("left", before)
    expect_in_use(page, 1)
    expect(at(page, "b")).to_have_class("block sel")


# What asks the server for a block, and the request that waits.
SOURCES = {
    "maths": ("**/api/maths", lambda page: button(page, "Rechnen").click()),
    "ctrl v": ("**/api/uploads", lambda page: page.keyboard.press("Control+v")),
    "einfügen": ("**/api/uploads", lambda page: button(page, "Einfügen").click()),
    "picker": ("**/api/uploads", lambda page: page.locator(PICKER).set_input_files(PICKED)),
}
# #775: now and then Playwright sees neither the route nor the request of a picture's upload,
# which the page sends and the server answers. So the page holds that answer itself.
HOLD_UPLOAD = """() => {
    const real = window.fetch;
    window.fetch = (...args) => {
        if (!String(args[0]).endsWith("/api/uploads")) return real(...args);
        window.uploading = true;
        return new Promise((go) => (window.release = go)).then(() => real(...args));
    };
}"""


def hold(page, url):
    """Holds the server's answer to the next request of url: gives what lets it go on."""
    if url.endswith("uploads"):
        page.evaluate(HOLD_UPLOAD)
        return lambda: page.evaluate("window.release()")
    waiting = []
    page.route(url, lambda route: waiting.append(route))
    return lambda: waiting.pop().continue_()


def asked(page, url, ask):
    """Asks and waits until the request is on its way."""
    if url.endswith("uploads"):
        ask(page)
        page.wait_for_function("window.uploading === true")
        return
    with page.expect_request(url):
        ask(page)


@pytest.mark.parametrize("how", CHANGES)
@pytest.mark.parametrize("source", SOURCES)
def test_a_block_on_its_way_finds_its_page_after_the_pages_change(editor, source, how):
    """#156: it lands on the page in use when it was asked for, wherever that page is by then."""
    page = three(editor)
    url, ask = SOURCES[source]
    if url.endswith("uploads"):
        copy_picture(page)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    # The server's answer waits until the pages have changed.
    release = hold(page, url)
    asked(page, url, ask)
    change_pages(page, how)
    _, _, _, n, count = CHANGES[how]
    release()
    expect(page.locator(".block[data-id]")).to_have_count(count)
    expect(page.locator(f'.sheet[data-page="{n}"] .block[data-id]')).to_have_count(2)
    expect(page.locator(f'.sheet[data-page="{n}"] .block.sel')).to_have_count(1)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect_in_use(page, n)
    assert "b" in order(page)[n] or how == "deleted"


def test_undo_of_a_brush_stroke_on_another_page_shows_that_page(editor):
    """The press that paints also visits the page: the paint comes off where it went on."""
    red = box("a", "shape", {**RECT, "fill": "#ff0000"})
    page = editor(red, more=[box("b", "shape", RECT)], theme="")
    pick(page, "a")
    page.get_by_label("Format übertragen", exact=True).click()
    was = at(page, "b").inner_html()
    same = "([was, same]) => (document.querySelector('[data-id=b]').innerHTML === was) === same"
    at(page, "b").click()
    expect_in_use(page, 1)
    page.wait_for_function(same, arg=[was, False])
    page.keyboard.press("Control+z")
    page.wait_for_function(same, arg=[was, True])
    expect_shown(page, 1)


def test_undo_of_a_block_from_the_server_shows_the_page_it_landed_on(editor):
    page = three(editor)
    waiting = []
    page.route("**/api/maths", lambda route: waiting.append(route))
    with page.expect_request("**/api/maths"):
        button(page, "Rechnen").click()
    thumb(page, 2).click()
    expect_shown(page, 2)
    [route] = waiting
    route.continue_()
    expect(page.locator('.sheet[data-page="0"] .block[data-id]')).to_have_count(2)
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    expect_shown(page, 0)


def nudged(page):
    """Three pages with "a" moved by a key. Gives the page and where "a" was before."""
    page = three(page)
    pick(page, "a")
    before = left(page, "a")
    page.keyboard.press("ArrowRight")
    expect(at(page, "a")).not_to_have_css("left", before)
    return page, before


def test_undo_scrolls_to_the_page_in_use_when_it_is_out_of_view(editor):
    page, before = nudged(editor)
    page.locator(".desk").evaluate("el => el.scrollTo(0, el.scrollHeight)")
    expect(page.locator('.sheet[data-page="0"]')).not_to_be_in_viewport()
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    expect_shown(page, 0)


def test_undo_leaves_the_desk_where_it_is_while_its_page_is_in_view(editor):
    page, before = nudged(editor)
    page.locator(".desk").evaluate("el => el.scrollTo(0, 50)")
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    # A scroll would have begun by the second frame after the undo.
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
    assert page.locator(".desk").evaluate("el => el.scrollTop") == 50
