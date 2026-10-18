"""#708: a sheet list served for another account turns the tab to that account, and Konto shows
nothing of the one before. A's key, shown once, and A's key list do not reach the page once the
tab is B's.

Tab 1 is A's on /konto with a key made. Tab 2 signs B in, which replaces the cookie of the shared
context. Tab 1 goes in-app to the sheet list, which is served for B, and back to Konto.
"""

import re

from playwright.sync_api import expect
from test_account_tokens import make, row
from ui import sheet, user


def test_konto_shows_nothing_of_a_after_the_tab_turns_to_b(browser, server):
    a = user()
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": a.cookies["session"], "url": server}])
    page = context.new_page()
    page.goto(f"{server}/konto")
    token = make(page, "Nur-A-Schlüssel")
    expect(row(page, "Nur-A-Schlüssel")).to_be_visible()

    # Tab 2 signs B in: the shared cookie is B's from now on. B has a sheet, so the list has one.
    b = user()
    sheet(b, [])
    b_email = b.get("/api/me").json()["email"]
    context.clear_cookies()
    context.add_cookies([{"name": "session", "value": b.cookies["session"], "url": server}])

    # Tab 1 goes in-app to the sheet list, which the server serves for B, then back to Konto.
    page.get_by_role("link", name="Blattomat").click()
    expect(page.get_by_role("link", name="Konto")).to_be_visible()
    expect(page).to_have_url(f"{server}/")
    page.get_by_role("link", name="Konto").click()
    expect(page).to_have_url(re.compile(r"/konto$"))

    # Tab 1 is B's now: Konto shows B, and nothing of A.
    expect(page.get_by_text(b_email)).to_be_visible(timeout=10000)
    body = page.locator("body")
    expect(body).not_to_contain_text(token)
    expect(body).not_to_contain_text(token[:8])
    expect(body).not_to_contain_text("Nur jetzt sichtbar")
    expect(row(page, "Nur-A-Schlüssel")).to_have_count(0)
    context.close()
