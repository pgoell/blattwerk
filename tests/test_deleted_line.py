"""The choice for a deleted sheet when its editor is not the open page.

The helpers live in test_deleted.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_deleted import (
    DROP,
    KEEP,
    LINE,
    OLD,
    delete,
    deleted,
    expect_choice,
    expect_list,
    expect_new,
    left,
    press,
    tab_to,
)
from test_loading import window  # noqa: F401
from test_saves import (
    NOTICE,
    again,
    kept_x,
    nudge,
    record,
    run,  # noqa: F401
    shut,
    start,
)


def test_the_list_asks_anew_when_a_save_finds_its_sheet_deleted(run):
    """A11: the list showed the sheet, and its row goes with no reload."""
    page = left(run)
    expect(page.locator(".sheets li")).to_have_count(2)
    expect(page.locator(".sheets li strong")).to_have_text(["c", "b"], ignore_case=False)


@pytest.mark.parametrize("choice", [KEEP, DROP])
def test_a_save_that_finds_the_delete_with_the_editor_gone_asks_above_the_list(run, choice):
    """A6"""
    page = left(run)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    assert kept_x(page, run) == 16
    press(line, choice)
    if choice == KEEP:
        expect_new(run, page)
    else:
        expect_list(page)
        assert record(page, run.ids["a"]) is None
    assert len(run.sent) == 1


@pytest.mark.parametrize("choice", [KEEP, DROP])
@pytest.mark.parametrize("kept", ["named", "from-before-names"])
def test_the_start_with_a_kept_change_of_a_deleted_sheet_asks_above_the_list(run, choice, kept):
    """A7: also for a record written before it kept the sheet's name."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    delete(run)
    if kept != "named":
        run.page.context.add_init_script(OLD)
    page, _, sent = again(run, None)
    line = page.locator(NOTICE)
    expect_choice(line, LINE if kept == "named" else LINE.replace("a", "Unbenanntes Blatt", 1))
    expect(page.locator(".sheets li")).to_have_count(2)
    assert kept_x(page, run) == 16
    press(line, choice)
    if choice == KEEP:
        expect_new(run, page, title="a" if kept == "named" else "Unbenanntes Blatt")
    else:
        expect_list(page)
        assert record(page, run.ids["a"]) is None
    assert not sent


@pytest.mark.parametrize("choice", [KEEP, DROP])
def test_a_reload_on_the_dead_sheets_address_shows_the_choice_there(run, choice):
    """A8"""
    page, _, _ = deleted(run)
    page.clock.resume()
    page.reload()
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible(timeout=10000)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    press(line, choice)
    if choice == KEEP:
        expect_new(run, page)
    else:
        expect_list(page)
        assert record(page, run.ids["a"]) is None


def test_the_lines_buttons_are_reached_by_tab_and_pressed_by_enter(run):
    """I2"""
    page = left(run)
    line = page.locator(NOTICE)
    expect_choice(line, LINE)
    tab_to(page, line.get_by_role("button", name=KEEP))
    page.keyboard.press("Tab")
    expect(line.get_by_role("button", name=DROP)).to_be_focused()
    page.keyboard.press("Shift+Tab")
    page.keyboard.press("Enter")
    expect_new(run, page)
