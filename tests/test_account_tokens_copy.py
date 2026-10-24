"""Kopieren on a new key: the clipboard, a refused clipboard, and a second click.

The account fixture and the helpers live in test_account_tokens.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import time

from playwright.sync_api import expect
from test_account_tokens import (
    COPY_STUB,
    REFUSED_STUB,
    account,  # noqa: F401
    make,
)
from ui import user


def test_a7_kopieren_says_kopiert_and_puts_the_key_on_the_clipboard(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(COPY_STUB)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    assert page.evaluate("() => window.copiedKey") == key
    expect(box.get_by_role("button", name="Kopieren", exact=True)).to_be_visible()


def test_a8_a_refused_clipboard_says_so_and_marks_the_key(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(REFUSED_STUB)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Kopieren hat nicht geklappt")
    expect(box.get_by_role("button", name="Kopieren", exact=True)).to_be_visible()
    assert page.evaluate("() => String(getSelection())") == key


def test_i6_a_second_click_keeps_kopiert_and_the_key_stays(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(COPY_STUB)
    # The page's clock stands still and moves only by hand, so a slow machine cannot run the 2 s out.
    page.clock.install()
    page.clock.pause_at(int(time.time() * 1000) + 60_000)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    page.clock.run_for(1200)
    box.get_by_role("button", name="Kopiert", exact=True).click()
    page.clock.run_for(1200)
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    expect(box.locator("code")).to_have_text(key)
    page.clock.run_for(1000)
    expect(box.get_by_role("button", name="Kopieren", exact=True)).to_be_visible()


def test_i7_a_new_key_takes_the_failure_line_away(account):
    page = account(user())
    make(page, "Laptop")
    page.evaluate(REFUSED_STUB)
    page.get_by_test_id("new-token").get_by_role("button", name="Kopieren", exact=True).click()
    expect(page.get_by_role("alert")).to_have_count(1)
    make(page, "zweiter")
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(
        page.get_by_test_id("new-token").get_by_role("button", name="Kopieren", exact=True)
    ).to_be_visible()
