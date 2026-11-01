"""The app's bar on a sheet stays hidden when the stylesheet arrives after the module (#466).

The built page links the stylesheet after the module. WebKit runs the module first, so the
loading page can paint the bar, and the watch keeps that. Holding the stylesheet makes that
order every time.
"""

import json

import pytest
from conftest import WEBKIT
from playwright.sync_api import expect
from test_loading import SCRIPT, WATCH, expect_loading, expect_ready, hold
from ui import sheet, user


@pytest.fixture
def window(browser, server):
    """A signed-in page with the loading watch, as `window` in test_loading.py."""
    contexts = []

    def start(theme=None, dark=False):
        context = browser.new_context(
            viewport={"width": 1400, "height": 1000}, color_scheme="dark" if dark else "light"
        )
        contexts.append(context)
        context.add_init_script("localStorage.setItem('tour', '1')")
        if theme is not None:
            context.add_init_script(f"localStorage.setItem('theme', {json.dumps(theme)})")
        context.add_init_script(WATCH)
        client = user()
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        return context.new_page(), client

    yield start
    for context in contexts:
        context.close()


# Chromium runs the module after the stylesheet, so holding the file holds the module too and the
# bar never arrives. WebKit runs the module first: that is the flash (#466).
@pytest.mark.skipif(not WEBKIT, reason="Chromium waits for the stylesheet")
@pytest.mark.parametrize("theme", ["", None], ids=["plain", "blattform"])
def test_a_late_stylesheet_does_not_show_the_bar_on_a_sheet(window, server, theme):
    page, client = window(theme=theme, dark=True)
    late = []
    page.route("**/*.css", lambda route: late.append(route))
    go = hold(page, SCRIPT)
    page.goto(f"{server}/blatt/{sheet(client, [])['id']}", wait_until="commit")
    # Attached, not visible: the account has drawn the bar, and the rule has already hidden it.
    # The stylesheet is still held.
    page.wait_for_selector("#root > nav", state="attached", timeout=10000)
    assert page.evaluate("[...document.styleSheets].every((sheet) => !sheet.href)")
    assert not page.evaluate("window.bare || window.flash"), page.evaluate("window.seen")
    for route in late:
        route.continue_()
    expect_loading(page)
    go()
    expect_ready(page)
    expect(page.locator("#root > nav, #root > footer").locator("visible=true")).to_have_count(0)
