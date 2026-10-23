"""Teilen on the list opens a preview that sets no cookie.

The fixture `window` is imported, and the test names it as its argument.
"""

# ruff: noqa: F811

import re

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from ui import TEXT, block, picture, sheet, upload


def test_teilen_opens_a_preview_without_a_cookie(window, server, browser):
    """The owner switches the link on. A visitor without an account sees the sheet and no cookie."""
    page, client = window()
    sheet(client, [block("text", 20, 20, TEXT), picture(upload(client))], title="Sachaufgaben")
    page.goto(server + "/")
    expect(page.get_by_role("button", name="Sachaufgaben teilen")).to_be_visible()
    page.get_by_role("button", name="Sachaufgaben teilen").click()
    page.get_by_role("button", name="Link einschalten").click()
    link = page.locator("dialog .link")
    expect(link).to_contain_text("/teilen/")
    url = link.inner_text().strip()
    fresh = browser.new_context()
    guest = fresh.new_page()
    try:
        set_cookie = []
        guest.on(
            "response",
            lambda res: set_cookie.append(res.url) if res.headers.get("set-cookie") else None,
        )
        guest.goto(url)
        expect(guest.get_by_role("heading", name="Sachaufgaben")).to_be_visible()
        expect(guest.get_by_text("Hallo")).to_be_visible()
        img = guest.locator(".paper img")
        expect(img).to_have_attribute("src", re.compile(r"/api/shares/[^/]+/uploads/\d+$"))
        guest.wait_for_function(
            "() => { const img = document.querySelector('.paper img');"
            " return !!img && img.complete && img.naturalWidth > 0 }"
        )
        expect(guest.get_by_role("button", name="Kopie in meine Blätter")).to_be_visible()
        guest.get_by_role("button", name="Kopie in meine Blätter").click()
        expect(guest.get_by_role("heading", name="Anmelden")).to_be_visible()
        assert set_cookie == []
    finally:
        fresh.close()
