"""Abmelden wipes the system clipboard, and a refused wipe still hides the copy from the next account."""

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    button,
    chromium_only,
)
from test_clipboard_account import (
    RECORD,
    copied,
    copy_all,
    copy_in_text,
    login,
    logout,
    next_list_paste_nothing,
    origin,
    someone,
    the_text_box,
    to_konto,
)
from ui import (
    RECT,
    box,
    copy_text,
    pick,
    sheet,
    track_writes,
    user,
    writes_landed,
)


@chromium_only
@pytest.mark.parametrize("way", ["reload", "tab", "address"])
@pytest.mark.parametrize("copy", ["blocks", "words", "key"])
def test_abmelden_on_a_page_that_did_not_copy_empties_the_clipboard_with_no_read_leave(
    editor, copy, way
):
    """#763: a page that did not make the copy empties the clipboard in the click, with no read
    and no permission query."""
    page, _ = copied(editor, copy)
    page = to_konto(page, way)
    page.context.clear_permissions()
    page.context.grant_permissions(["clipboard-write"])
    page.evaluate(RECORD)
    button(page, "Abmelden").click()
    expect(page.locator("#email")).to_be_visible()
    asked = page.evaluate("window.__asked")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    assert page.evaluate("navigator.clipboard.readText()") == ""
    assert asked == []
    next_list_paste_nothing(page)


@chromium_only
def test_a_copy_write_landing_after_abmelden_is_emptied_too(editor):
    """#763: a copy write still on its way at the logout lands on the clipboard; the wipe empties it
    then."""
    a = user()
    page = editor(the_text_box(), client=a)
    # Fault injection: the copy's write lands 1.5 s late.
    page.evaluate(
        """() => {
            const write = navigator.clipboard.write.bind(navigator.clipboard);
            navigator.clipboard.write = (...args) =>
                new Promise((done) => setTimeout(done, 1500)).then(() => write(...args));
        }"""
    )
    track_writes(page)
    pick(page, "t")
    page.keyboard.press("Control+c")
    page.evaluate(
        "history.pushState({}, '', '/konto'); dispatchEvent(new PopStateEvent('popstate'))"
    )
    button(page, "Abmelden").click()
    expect(page.locator("#email")).to_be_visible()
    writes_landed(page)
    page.wait_for_function("localStorage.getItem('copied') === null")
    assert page.evaluate("navigator.clipboard.readText()") == ""
    next_list_paste_nothing(page)


@chromium_only
def test_a_refused_wipe_keeps_the_marks_and_the_next_account_pastes_nothing(editor):
    """#763: when the wipe is refused the marks stay, so the words still on the clipboard paste
    nowhere."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    page.goto(f"{origin(page)}/konto")
    page.evaluate("() => { navigator.clipboard.writeText = () => Promise.reject(new Error()); }")
    button(page, "Abmelden").click()
    expect(page.locator("#email")).to_be_visible()
    assert page.evaluate("localStorage.getItem('typed-copy')") is not None
    next_list_paste_nothing(page)


@chromium_only
def test_abmelden_with_no_copy_stored_leaves_the_clipboard(editor):
    """#763: with no copy of Blattomat's stored, the logout leaves what another app copied."""
    a = user()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    assert page.evaluate(
        "[localStorage.getItem('copied'), localStorage.getItem('typed-copy')]"
    ) == [
        None,
        None,
    ]
    copy_text(page, "aus Word")
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == "aus Word"


@chromium_only
def test_after_a_wipe_a_later_abmelden_leaves_another_apps_copy(editor):
    """#763: the wipe takes the marks off, so the next logout leaves another app's copy alone."""
    a = user()
    page = editor(box("a", "shape", RECT), client=a)
    copy_all(page, 1)
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    page.evaluate("(words) => navigator.clipboard.writeText(words)", "aus Word")
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == "aus Word"
