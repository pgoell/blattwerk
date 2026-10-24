"""Two tabs that hold the same deleted sheet, or two different ones.

The helpers live in test_deleted.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import re

from playwright.sync_api import expect
from test_deleted import (
    DROP,
    KEEP,
    LINE,
    deleted,
    expect_choice,
    expect_list,
    expect_new,
    press,
)
from test_saves import NOTICE, kept_x, run  # noqa: F401
from test_stale import STATUS


def test_a_keep_in_one_tab_ends_the_choice_in_the_other_that_holds_the_same_work(run):
    """1: tab 2 holds what tab 1 kept, so its choice ends, and it opens the new sheet. One sheet
    is made."""
    page, _, _ = deleted(run)
    other = page.context.new_page()
    other.goto(f"{run.server}/blatt/{run.ids['a']}")
    expect_choice(other.locator(NOTICE), LINE)
    press(page.locator(".clash"), KEEP)
    expect_new(run, page)
    new = page.url.rsplit("/", 1)[1]
    expect(other).to_have_url(f"{run.server}/blatt/{new}")
    expect(other.locator(NOTICE)).to_have_count(0)
    assert len(run.client.get("/api/sheets").json()) == 3


def test_another_tab_with_other_work_keeps_its_choice_and_its_record(run):
    """3: tab 2 holds a change other than the one tab 1 kept, so its choice stands and its record
    is written back."""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    other = page.context.new_page()
    other.add_init_script(
        f"const k = JSON.parse(localStorage.getItem('unsaved:{a}') ?? 'null');"
        f"if (k) {{"
        f" k.doc.pages[0].blocks[0].x = 17;"
        f" localStorage.setItem('unsaved:{a}', JSON.stringify(k));"
        f" }}"
    )
    other.goto(f"{run.server}/blatt/{a}")
    expect_choice(other.locator(NOTICE), LINE)
    press(page.locator(".clash"), KEEP)
    expect(page).not_to_have_url(re.compile(rf"/blatt/{a}$"))
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert len(run.client.get("/api/sheets").json()) == 3
    other.wait_for_function(f"(localStorage.getItem('unsaved:{a}') ?? '').includes('\"x\":17')")
    expect_choice(other.locator(NOTICE), LINE)
    assert kept_x(other, run) == 17


def test_a_tab_writes_its_record_back_when_another_tab_takes_it_out(run):
    """CI: the other tab's removal of the record may reach the store after this tab wrote it back.
    A tab with unsaved work writes its record again whenever another tab takes it out."""
    page, _, _ = deleted(run)
    a = run.ids["a"]
    other = page.context.new_page()
    other.goto(f"{run.server}/blatt/{a}")
    expect_choice(other.locator(NOTICE), LINE)
    page.evaluate(f"() => localStorage.removeItem('unsaved:{a}')")
    other.wait_for_function(f"localStorage.getItem('unsaved:{a}') !== null")
    expect_choice(other.locator(NOTICE), LINE)


def test_a_drop_in_one_tab_ends_the_choice_in_the_other_that_holds_the_same_work(run):
    """2: tab 2 holds what tab 1 dropped, so its choice ends, and it goes to the list."""
    page, _, _ = deleted(run)
    other = page.context.new_page()
    other.goto(f"{run.server}/blatt/{run.ids['a']}")
    expect_choice(other.locator(NOTICE), LINE)
    press(page.locator(".clash"), DROP)
    expect_list(page)
    expect_list(other)
    expect(other).not_to_have_url(re.compile(rf"/blatt/{run.ids['a']}$"))
