"""The zoom buttons and Ganze Seite stop where the wheel stops, and fit the page in use."""

import re

import pytest
from playwright.sync_api import expect
from test_pages import expect_in_use
from test_zoom import (
    INSIDE,
    expect_fitted,
    expect_percent,
    expect_width,
    fit,
    page_width,
    roomy,
    settled,
    wheel,
    width,
)
from ui import BROWSER, LINE, TEXT, box, sheet, thumb, user


def test_fit_shows_the_whole_page(editor):
    """A4"""
    page = editor(box("a", "text", TEXT))
    # Right after the percent button.
    assert fit(page).evaluate("el => !!el.previousElementSibling?.classList.contains('zoom')")
    assert not page.evaluate(INSIDE, 0)
    wide = width(page)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    expect_percent(page)
    # The list still sets the width. The fit works from a zoom that overflows both ways.
    page_width(page)
    expect_width(page, wide)
    assert not page.evaluate(INSIDE, 0)
    roomy(page)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)


def test_fit_takes_the_page_in_use(editor):
    """I8"""
    rest = [
        {"blocks": [box("b", "text", TEXT)], "landscape": True},
        {"blocks": [box("c", "text", TEXT)]},
    ]
    page = editor(box("a", "text", TEXT), pages=rest, theme="")
    for n, (w, h) in ((1, (297, 210)), (2, (210, 297)), (0, (210, 297))):
        thumb(page, n).click()
        expect_in_use(page, n)
        fit(page).click()
        expect_fitted(page, n, w, h)
        # No other page has room beside it.
        assert [m for m in range(3) if page.evaluate(INSIDE, m)] == [n]


def test_the_buttons_stop_where_the_wheel_stops(editor):
    """I4"""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    ends = (("Größer", "Kleiner", -100, 4, 1.25**6), ("Kleiner", "Größer", 100, 0.25, 1.25**-6))
    for on, back, delta, stop, step in ends:
        page_width(page)
        expect_width(page, wide)
        for notch in range(1, 8):
            wheel(page, delta)
            expect_width(page, wide * min(4, max(0.25, 1.25 ** (-notch * delta / 100))))
        # At the stop the button that leads on does nothing, and the other takes the next step back.
        page.get_by_label(on, exact=True).first.click()
        settled(page)
        assert width(page) == pytest.approx(wide * stop, abs=2)
        page.get_by_label(back, exact=True).first.click()
        expect_width(page, wide * step)
        expect_percent(page)


def test_the_buttons_step_cleanly_where_the_scrollbar_comes_and_goes(browser, playwright, server):
    """12, 13"""
    # The fixture's Chromium hides the scrollbars, so Chromium starts its own. WebKit on Linux
    # draws scrollbars over the page, so there the test passes with nothing to prove, on the
    # fixture's browser.
    own = BROWSER == "chromium"
    if own:
        browser = playwright.chromium.launch(ignore_default_args=["--hide-scrollbars"])
    context = browser.new_context(viewport={"width": 1700, "height": 900})
    try:
        context.add_init_script("localStorage.setItem('tour', '1')")
        client = user()
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        context.add_cookies([cookie])
        page = context.new_page()
        page.goto(f"{server}/blatt/{sheet(client, [box('a', 'shape', LINE)])['id']}")
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
        # A browser that does not know scrollbar-gutter (Safari before 18.2).
        page.add_style_tag(content=".desk { scrollbar-gutter: auto !important }")
        desk = page.locator(".desk")
        start = width(page)
        left = page.locator(".sheet.on").evaluate("el => el.getBoundingClientRect().left")

        def expect_exact(wide):
            """Waits until the page in use is this wide, to half a pixel."""
            page.wait_for_function(
                "(w) => Math.abs(document.querySelector('.sheet.on')"
                ".getBoundingClientRect().width - w) < 0.5",
                arg=wide,
            )

        # Chromium draws the scrollbar while the sheet overflows the desk, and not when it fits.
        assert desk.evaluate("el => el.scrollHeight > el.clientHeight")
        for n in range(1, 6):
            page.get_by_label("Kleiner", exact=True).first.click()
            expect_exact(start / 1.25**n)
            # The start's percent is Chromium's: WebKit lays the same sheet out a little larger.
            if n == 1 and own:
                expect(page.locator("button.zoom").first).to_have_text(re.compile(r"113\s*%"))
        assert desk.evaluate("el => el.scrollHeight <= el.clientHeight")
        for n in range(4, -1, -1):
            page.get_by_label("Größer", exact=True).first.click()
            expect_exact(start / 1.25**n)
        now = page.locator(".sheet.on").evaluate("el => el.getBoundingClientRect().left")
        assert now == pytest.approx(left, abs=0.5)
    finally:
        context.close()
        if own:
            browser.close()
