"""A later login wipes the previous account's copy and keeps the same account's."""

import pytest
from playwright.sync_api import expect
from test_clipboard import chromium_only
from test_clipboard_account import (
    CLIPBOARD_LOG,
    ITEM_LOG,
    copy_in_text,
    form_login,
    login,
    run_out,
    someone,
    the_text_box,
)
from ui import (
    RECT,
    box,
    copy_text,
    pick,
    sheet,
    user,
)


@chromium_only
def test_a_session_that_runs_out_then_another_login_takes_the_copy_off_the_clipboard(editor):
    """#772, checklist A1: a login after a run-out save empties the clipboard."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.context.clear_cookies()
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.type("x")
    expect(page.locator("#email")).to_be_visible()
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    assert page.evaluate("navigator.clipboard.readText()") == ""


@chromium_only
def test_a_session_left_by_reload_then_another_login_takes_the_copy_off_the_clipboard(editor):
    """#772, checklist A2: a login after a run-out reload empties the clipboard."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    run_out(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    assert page.evaluate("navigator.clipboard.readText()") == ""


@chromium_only
def test_the_same_account_signing_in_again_keeps_its_copy_on_the_clipboard(editor):
    """#772, checklist A3: the account's own login leaves its copy on the system's clipboard."""
    a, email = someone()
    page = editor(the_text_box(), client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    copy_in_text(page)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    words = page.evaluate("navigator.clipboard.readText()")
    assert words
    run_out(page)
    login(page, email, mine, 1)
    assert page.evaluate("navigator.clipboard.readText()") == words


@chromium_only
def test_another_apps_copy_survives_a_login_when_blattomat_stored_no_copy(editor):
    """#772, checklist I6: with no copy stored, a login leaves another app's copy alone."""
    a = user()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    copy_text(page, "aus Word")
    page.context.clear_cookies()
    page.reload()
    expect(page.locator("#email")).to_be_visible()
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    assert page.evaluate("navigator.clipboard.readText()") == "aus Word"


def test_another_accounts_login_writes_an_empty_clipboard_over_the_copy(editor):
    """#772, checklist W: another account's form login writes "" to the clipboard."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    run_out(page)
    page.evaluate(CLIPBOARD_LOG)
    _, email = someone()
    form_login(page, email)
    assert "" in page.evaluate("window.wrote")


@pytest.mark.parametrize("same", [False, True])
def test_the_login_click_itself_begins_the_wipe(editor, same):
    """#772, A1 and A3: the write starts in the login's own submit, as Safari wants; it empties
    the clipboard for another account and writes nothing for the same one."""
    a, mine = someone()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    run_out(page)
    page.evaluate(ITEM_LOG)
    form_login(page, mine if same else someone()[1])
    page.wait_for_function("window.items.length === 1 && 'text' in window.items[0]")
    assert page.evaluate("window.items") == [{"event": "submit", "text": "refused" if same else ""}]


@chromium_only
def test_the_same_account_signing_in_a_second_time_keeps_the_clipboard(editor):
    """#772, A3: a second login of the same account wipes nothing either, not another app's copy."""
    a, mine = someone()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    run_out(page)
    form_login(page, mine)
    copy_text(page, "aus Word")
    run_out(page)
    page.evaluate(ITEM_LOG)
    form_login(page, mine)
    page.wait_for_function("window.items.length === 1 && 'text' in window.items[0]")
    assert page.evaluate("window.items")[0]["text"] == "refused"
    assert page.evaluate("navigator.clipboard.readText()") == "aus Word"


def test_the_same_account_signing_in_again_writes_no_clipboard(editor):
    """#772, checklist W: the account's own form login writes nothing to the clipboard."""
    a, email = someone()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    run_out(page)
    page.evaluate(CLIPBOARD_LOG)
    form_login(page, email)
    assert page.evaluate("window.wrote") == []
