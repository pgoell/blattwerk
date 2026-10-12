"""Ganze Seite gives the same size after zooming in as before (issue 403)."""

import pytest
from playwright.sync_api import expect
from test_quer import fmt
from test_zoom import expect_fitted, fit, wheel, width
from ui import BROWSER, TEXT, box, sheet, user


@pytest.fixture
def shown(playwright, server):
    """Opens the editor on a sheet of the blocks, in a Chromium that draws its scrollbars.

    The fixture's Chromium hides them, and a desk with a bar along its bottom is what is tested.
    """
    if BROWSER != "chromium":
        pytest.skip("WebKit draws its scrollbars over the page, so the bar takes no room")
    browser = playwright.chromium.launch(ignore_default_args=["--hide-scrollbars"])
    try:

        def start(*blocks):
            client = user()
            context = browser.new_context(viewport={"width": 1280, "height": 1024})
            context.add_init_script("localStorage.setItem('tour', '1')")
            cookie = {"name": "session", "value": client.cookies["session"], "url": server}
            context.add_cookies([cookie])
            page = context.new_page()
            page.goto(f"{server}/blatt/{sheet(client, list(blocks))['id']}")
            expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
            return page

        yield start
    finally:
        browser.close()


def zoom_text(page):
    return page.locator("button.zoom").first.inner_text()


def bar(page):
    """Whether the desk has a scrollbar along its bottom."""
    return page.locator(".desk").evaluate("el => el.scrollWidth > el.clientWidth")


def bigger(page):
    """Clicks Größer and waits until the page is wider."""
    before = width(page)
    page.get_by_label("Größer", exact=True).first.click()
    page.wait_for_function(
        "(w) => document.querySelector('.sheet.on').getBoundingClientRect().width > w + 1",
        arg=before,
    )


def fit_zoom_fit(page, zoom_in, w, h):
    """Fits the page, zooms in so the desk scrolls, and fits again: same per cent, same width."""
    fit(page).click()
    expect_fitted(page, 0, w, h)
    first, wide = zoom_text(page), width(page)
    zoom_in()
    assert bar(page)
    fit(page).click()
    expect(page.locator("button.zoom").first).to_have_text(first)
    expect_fitted(page, 0, w, h)
    assert abs(width(page) - wide) < 0.5


def test_fit_gives_the_same_size_after_zooming_in(shown):
    """A1"""
    page = shown(box("a", "text", TEXT))
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    before, wide = zoom_text(page), width(page)
    # The per cent the sheet gets on this window: 77 % in the issue.
    print("percent before zooming in:", before)
    for _ in range(3):
        bigger(page)
    assert bar(page)
    fit(page).click()
    expect(page.locator("button.zoom").first).to_have_text(before)
    expect_fitted(page, 0, 210, 297)
    assert abs(width(page) - wide) < 0.5


def test_fit_is_the_same_on_a_page_on_its_side(shown):
    """I1 (a)"""
    page = shown(box("a", "text", TEXT))
    # Wide and low: on its side the height is what limits the page, as upright the width is.
    page.set_viewport_size({"width": 1700, "height": 900})
    fmt(page, "Quer")

    def zoom_in():
        for _ in range(3):
            bigger(page)

    fit_zoom_fit(page, zoom_in, 297, 210)


def test_fit_is_the_same_after_zooming_in_by_the_wheel(shown):
    """I1 (b)"""
    page = shown(box("a", "text", TEXT))

    def zoom_in():
        for _ in range(3):
            wheel(page, -100)

    fit_zoom_fit(page, zoom_in, 210, 297)


def test_a_second_fit_changes_neither_per_cent_nor_width(shown):
    """I1 (c)"""
    page = shown(box("a", "text", TEXT))
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    first, wide = zoom_text(page), width(page)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    expect(page.locator("button.zoom").first).to_have_text(first)
    assert abs(width(page) - wide) < 0.5
