"""Logout, a deleted account and a session that ends without Abmelden empty the block clipboard."""

import json

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    blocks,
    button,
    chromium_only,
    clipboard_picture,
    every,
    expect_picture,
    ready,
    stored,
)
from test_clipboard_account import (
    CLIP,
    TYPES,
    copy_all,
    leave,
    login,
    logout,
    origin,
    own,
    paste_both,
)
from ui import (
    RECT,
    TEXT,
    at,
    box,
    copy_picture,
    copy_text,
    expect_picked,
    pick,
    saved,
    sheet,
    user,
)


def test_a_clip_of_the_build_before_pastes_nothing_and_the_next_copy_heals_it(editor):
    """I1"""
    client = user()
    page = editor(box("x", "shape", RECT, w=40), client=client)
    old = json.dumps(every(client))
    # The copy leaves words on the system's clipboard, where another test may have left a picture.
    pick(page, "x")
    page.keyboard.press("Control+c")
    page.evaluate("(old) => localStorage.setItem('clip', old)", old)
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    assert page.evaluate(CLIP) == old
    assert len(own(page, client, 2)) == 2
    assert json.loads(page.evaluate(CLIP)).keys() == {"owner", "blocks"}


def test_a_session_that_ends_with_no_logout_leaves_nothing_to_paste(editor):
    """I2"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    leave(page)
    b = user()
    login(page, b, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


def test_the_next_account_pastes_its_own_copy_and_never_the_earlier_blocks(editor):
    """I3"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    copy_all(page, len(held))
    leave(page)
    b = user()
    login(page, b, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    assert len(own(page, b, 2)) == 2
    # Its copy lasts over a reload and reaches another sheet, as the earlier account's did.
    page.reload()
    ready(page, 2)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    login(page, b, sheet(b, [box("t", "text", TEXT, z=3)]), 1)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    assert sorted(b["type"] for b in saved(page, b)) == ["shape", "text"]
    # And the earlier account, back again, gets none of the next one's.
    leave(page)
    login(page, a, mine, len(held))
    paste_both(page)
    expect(blocks(page)).to_have_count(len(held))
    assert len(stored(page, a)) == len(held)


def test_deleting_the_account_empties_the_clipboard(editor):
    """I4"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    page.goto(f"{origin(page)}/konto")
    button(page, "Konto löschen …").click()
    button(page, "Ja, endgültig löschen").click()
    expect(page.locator("#email")).to_be_visible()
    assert page.evaluate(CLIP) is None
    b = user()
    login(page, b, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    assert len(own(page, b, 2)) == 2


def test_logout_in_one_tab_empties_the_clipboard_of_an_editor_open_in_another(editor):
    """I5"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    other = sheet(a, [box("x", "shape", RECT, w=40)])
    tab = page.context.new_page()
    tab.goto(f"{origin(page)}/blatt/{other['id']}")
    ready(tab, 1)
    page.bring_to_front()
    copy_all(page, len(held))
    logout(page)
    ready(tab, 1)
    assert tab.evaluate(CLIP) is None
    paste_both(tab)
    expect(blocks(tab)).to_have_count(1)
    # The button reads the system's clipboard first: its paste has run once it is free again.
    button(tab, "Einfügen").click()
    expect(blocks(tab)).to_have_count(1)


@pytest.mark.parametrize("by", ["keys", "button"])
def test_the_next_account_pastes_a_picture_from_another_app(editor, by):
    """I6"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    leave(page)
    b = user()
    login(page, b, sheet(b, [box("x", "text", TEXT)]), 1)
    copy_picture(page)
    page.keyboard.press("Control+v") if by == "keys" else button(page, "Einfügen").click()
    expect_picture(page, b, 2)


@pytest.mark.parametrize("clip", ["none", "another account's"])
def test_a_paste_that_finds_nothing_is_quiet(editor, clip):
    """I7"""
    client = user()
    page = editor(box("x", "shape", RECT, w=40), box("t", "text", TEXT, z=2), client=client)
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    # The copy leaves words on the system's clipboard, where another test may have left a picture.
    pick(page, "x")
    page.keyboard.press("Control+c")
    if clip == "none":
        page.evaluate("localStorage.removeItem('clip')")
    else:
        other = json.dumps({"owner": -1, "blocks": every(client)})
        page.evaluate("(other) => localStorage.setItem('clip', other)", other)
    pick(page, "t")
    page.keyboard.press("Delete")
    expect(blocks(page)).to_have_count(1)
    pick(page, "x")
    paste_both(page)
    expect_picked(page, "x")
    # Undo takes back the change before the paste: the paste made no step of its own.
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(2)
    expect(at(page, "t")).to_be_visible()
    assert sorted(b["id"] for b in saved(page, client)) == ["t", "x"]
    assert dialogs == []


@chromium_only
def test_abmelden_takes_the_copy_and_its_picture_off_the_system_clipboard(editor):
    """#139: at a shared computer the next one finds no picture of the sheets on the clipboard."""
    a = user()
    page = editor(box("a", "shape", RECT), client=a)
    copy_all(page, 1)
    clipboard_picture(page)
    logout(page)
    assert "image/png" not in page.evaluate(TYPES)
    assert page.evaluate("navigator.clipboard.readText()") == ""


@chromium_only
def test_abmelden_after_a_reload_takes_a_later_copy_of_another_app_too(editor):
    """#763: the price of the wipe that needs no read: a copy made after the copy goes as well."""
    a = user()
    page = editor(box("a", "shape", RECT), client=a)
    copy_all(page, 1)
    clipboard_picture(page)
    copy_text(page, "aus Word")
    # The way to Konto loads the page anew: it knows the copy only by its mark, and reads nothing.
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == ""


@chromium_only
def test_abmelden_in_the_same_page_takes_the_copy_off_without_reading(editor):
    """The page made the copy: the logout empties the clipboard in the click, as Safari wants."""
    a = user()
    page = editor(box("a", "shape", RECT), client=a)
    copy_all(page, 1)
    clipboard_picture(page)
    # Another app looked at in between, and no leave to read the clipboard: it knows by itself.
    page.evaluate("dispatchEvent(new Event('blur'))")
    page.context.clear_permissions()
    page.context.grant_permissions(["clipboard-write"])
    page.evaluate(
        "history.pushState({}, '', '/konto'); dispatchEvent(new PopStateEvent('popstate'))"
    )
    button(page, "Abmelden").click()
    expect(page.locator("#email")).to_be_visible()
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    assert "image/png" not in page.evaluate(TYPES)
    assert page.evaluate("navigator.clipboard.readText()") == ""
