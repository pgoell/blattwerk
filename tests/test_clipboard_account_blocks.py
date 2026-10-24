"""The next account on the same browser pastes none of the previous account's blocks."""

import json

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    blocks,
    button,
    every,
    ready,
    stored,
)
from test_clipboard_account import (
    CLIP,
    copy_all,
    leave,
    login,
    logout,
    origin,
    own,
    paste_both,
    someone,
)
from ui import (
    PASSWORD,
    RECT,
    box,
    copy_text,
    pick,
    saved,
    sheet,
    user,
)

from blattwerk import db


def test_after_logout_nothing_pastes_for_the_same_account_back_again(editor):
    """A1"""
    a, email = someone()
    held = every(a)
    page = editor(*held, client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    copy_all(page, len(held))
    logout(page)
    assert page.evaluate(CLIP) is None
    login(page, email, mine, len(held))
    paste_both(page)
    expect(blocks(page)).to_have_count(len(held))
    # The click on Abmelden ended the session the client had.
    assert a.post("/api/login", json={"email": email, "password": PASSWORD}).status_code == 200
    assert len(stored(page, a)) == len(held)
    # Only its own new copy pastes.
    pick(page, "b1")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(len(held) + 1)
    assert len(saved(page, a)) == len(held) + 1


def test_the_next_account_pastes_nothing_of_the_one_before(editor):
    """A2"""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


@pytest.mark.parametrize("by", ["keys", "button"])
def test_the_next_account_pastes_no_words_of_the_one_before(editor, by):
    """#138: the copy's words still lie on the system's clipboard, and make no text block."""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    logout(page)
    # The logout took the words off the clipboard, and their mark with them (#763).
    kept = page.evaluate("JSON.stringify(localStorage)")
    assert "copied" not in kept and "Hallo" not in kept and "eins" not in kept
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    page.keyboard.press("Control+v") if by == "keys" else button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    # A paste still on its way, as the button's is while it reads the clipboard, would show here.
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


@pytest.mark.parametrize("by", ["keys", "button"])
def test_words_from_another_app_paste_as_a_text_block_for_the_next_account(editor, by):
    """#138: copied after the logout, they are no one's in the editor."""
    a = user()
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    copy_text(page, "Wort")
    page.keyboard.press("Control+v") if by == "keys" else button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(2)
    [new] = [b for b in saved(page, b) if b["id"] != "x"]
    assert (new["type"], new["props"]["text"]) == ("text", "Wort")


def test_an_account_with_the_id_of_a_deleted_one_pastes_nothing_of_it(editor):
    """A2"""
    a = user()
    gone = a.get("/api/me").json()["id"]
    held = every(a)
    page = editor(*held, client=a)
    copy_all(page, len(held))
    leave(page)
    # Deleted on another device: this browser's store still holds the copy.
    assert a.delete("/api/me").status_code == 200
    # The database never hands an id out again. One that was lost and made anew would.
    db.open_db().execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'users'")
    b, email = someone()
    assert b.get("/api/me").json()["id"] == gone
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


def test_a_copy_in_a_tab_left_open_over_the_logout_does_not_outlast_the_next_login(editor):
    """A1, I5"""
    a, email = someone()
    held = every(a)
    page = editor(*held, client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    tab = page.context.new_page()
    tab.goto(f"{origin(page)}/blatt/{sheet(a, [box('x', 'shape', RECT, w=40)])['id']}")
    ready(tab, 1)
    page.bring_to_front()
    logout(page)
    # The other tab's editor still stands, and copies as the account that left.
    ready(tab, 1)
    pick(tab, "x")
    tab.keyboard.press("Control+c")
    assert json.loads(tab.evaluate(CLIP))["blocks"]
    page.bring_to_front()
    login(page, email, mine, len(held))
    paste_both(page)
    expect(blocks(page)).to_have_count(len(held))
    assert a.post("/api/login", json={"email": email, "password": PASSWORD}).status_code == 200
    assert len(stored(page, a)) == len(held)
    pick(page, "b1")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(len(held) + 1)
    assert len(saved(page, a)) == len(held) + 1


@pytest.mark.parametrize(
    "junk", [[{}], [None], "abc", [{"id": "q", "type": "text"}], [], ...], ids=str
)
def test_the_accounts_own_clip_that_holds_no_whole_blocks_pastes_nothing(editor, junk):
    """A stored clip of this account with broken blocks harms neither the editor nor the sheet."""
    client = user()
    page = editor(box("x", "shape", RECT, w=40), client=client)
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    # The copy leaves words on the system's clipboard, where another test may have left a picture.
    pick(page, "x")
    page.keyboard.press("Control+c")
    clip = {"owner": client.get("/api/me").json()["id"]}
    # The last one has no blocks at all.
    if junk is not ...:
        clip["blocks"] = junk
    page.evaluate("(clip) => localStorage.setItem('clip', clip)", json.dumps(clip))
    paste_both(page)
    expect(blocks(page)).to_have_count(1)
    # The next copy heals it.
    assert len(own(page, client, 2)) == 2
    assert errors == []
