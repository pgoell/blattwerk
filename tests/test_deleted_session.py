"""Who may answer the deleted-sheet choice, and what a missing PDF says.

The helpers live in test_deleted.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_clash import swap
from test_deleted import (
    DROP,
    KEEP,
    LINE,
    PDF_GONE,
    SAYS,
    WORD,
    delete,
    deleted,
    expect_choice,
    expect_list,
    expect_new,
    press,
)
from test_saves import (
    NOTICE,
    answer,
    change,
    record,
    run,  # noqa: F401
    start,
)
from test_signed_out import login
from test_stale import TURNS
from ui import user


def test_a_choice_that_finds_the_session_gone_brings_the_login_and_stands_after_it(run):
    """I5"""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    kept = record(page, a)
    page.context.clear_cookies()
    page.locator(".clash").get_by_role("button", name=KEEP).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    expect(page).to_have_url(f"{run.server}/blatt/{a}")
    assert record(page, a) == kept
    page.clock.resume()
    login(page, run.server, run.client)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    expect(line).not_to_contain_text(WORD)
    assert record(page, a) == kept
    line.get_by_role("button", name=KEEP).click()
    expect_new(run, page)


def test_a_choice_under_another_accounts_session_makes_no_sheet_there(run):
    """A10: another teacher signed in in another tab. The login shows, that teacher gets no
    sheet of this one, and the change stays for its owner, who then chooses."""
    page, _, _ = deleted(run)
    a, other = run.ids["a"], user()
    kept = record(page, a)
    swap(page, run.server, other)
    page.locator(".clash").get_by_role("button", name=KEEP).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    page.evaluate(TURNS)
    assert other.get("/api/sheets").json() == []
    assert record(page, a) == kept
    page.clock.resume()
    login(page, run.server, run.client)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    line.get_by_role("button", name=KEEP).click()
    expect_new(run, page)
    assert other.get("/api/sheets").json() == []


@pytest.mark.parametrize("session", ["none", "another teacher's"])
def test_dropping_needs_the_owners_own_session(run, session):
    """A10, review 2: with the session gone, or another teacher's, `Verwerfen` drops nothing.
    The login shows, the change stays for its owner, and after the owner's login it goes."""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    kept = record(page, a)
    if session == "none":
        page.context.clear_cookies()
    else:
        swap(page, run.server, user())
    press(page.locator(".clash"), DROP)
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    page.evaluate(TURNS)
    assert record(page, a) == kept
    page.clock.resume()
    login(page, run.server, run.client)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    assert record(page, a) == kept
    press(line, DROP)
    expect_list(page)
    assert record(page, a) is None


def test_dropping_asks_once_more_and_a_no_keeps_all(run):
    """Review 3: what shows is the only copy, so one press alone drops nothing."""
    page, _ = start(run)
    asked = []
    page.on("dialog", lambda d: (asked.append(d.message), d.dismiss()))
    change(run)
    delete(run)
    answer(run, "a")
    banner = page.locator(".clash")
    kept = record(page, run.ids["a"])
    banner.get_by_role("button", name=DROP).click()
    page.evaluate(TURNS)
    assert asked == ["Was von „a“ noch da ist, endgültig verwerfen?"]
    expect_choice(banner, SAYS)
    assert record(page, run.ids["a"]) == kept


def test_dropping_with_no_connection_says_so_and_the_choice_stands(run):
    """Review 2: who is signed in cannot be asked, so nothing is dropped."""
    page, _, _ = deleted(run)
    kept = record(page, run.ids["a"])
    page.context.set_offline(True)
    banner = page.locator(".clash")
    press(banner, DROP)
    expect(banner).to_contain_text(WORD)
    assert record(page, run.ids["a"]) == kept
    page.context.set_offline(False)
    press(banner, DROP)
    expect_list(page)


@pytest.mark.parametrize("button", ["PDF", "Lösungen"], ids=["pdf", "key"])
def test_a_pdf_of_a_sheet_deleted_elsewhere_says_so_and_offers_no_try(run, button):
    """14"""
    page, _, _ = deleted(run)
    page.get_by_role("button", name=button, exact=True).click()
    line = page.locator(".notice.fault")
    expect(line).to_contain_text(PDF_GONE)
    expect(line.get_by_role("button", name="Erneut versuchen")).to_have_count(0)
    expect_choice(page.locator(".clash"), SAYS)
