"""The block clipboard belongs to the account: the next one on the same browser gets none of it."""

import json
from uuid import uuid4

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    all_of,
    blocks,
    button,
    every,
    expect_picture,
    no_picture,
    ready,
    stored,
)
from ui import (
    BROWSER,
    PASSWORD,
    RECT,
    TEXT,
    at,
    box,
    copy_picture,
    expect_picked,
    pick,
    saved,
    sheet,
    user,
)

from blattwerk import db

CLIP = "localStorage.getItem('clip')"


def someone():
    """A new user and the address to log in with."""
    email = f"{uuid4().hex}@example.com"
    return user(email), email


def origin(page):
    return "/".join(page.url.split("/", 3)[:3])


def copy_all(page, count):
    all_of(page, count)
    page.keyboard.press("Control+c")
    assert json.loads(page.evaluate(CLIP))["blocks"]


def logout(page):
    """The click on Abmelden, which ends the session on the server too."""
    page.goto(f"{origin(page)}/konto")
    button(page, "Abmelden").click()
    expect(page.locator("#email")).to_be_visible()


def leave(page):
    """The session ends with no logout, as when it runs out: the copied blocks stay in the store."""
    page.context.clear_cookies()
    page.reload()
    expect(page.locator("#email")).to_be_visible()
    assert page.evaluate(CLIP)


def login(page, who, on, count):
    """Logs in on the login page, with the form for an address or else with the client's cookie,
    and opens the sheet `on` of `count` blocks."""
    if isinstance(who, str):
        page.fill("#email", who)
        page.fill("#password", PASSWORD)
        with page.expect_response("**/api/login") as answer:
            button(page, "Anmelden").click()
        expect(page.locator("#email")).to_have_count(0)
        # The session cookie is Secure and this server speaks http: Chromium keeps it for
        # 127.0.0.1 all the same, WebKit does not, so there it goes by hand.
        if BROWSER == "webkit":
            value = answer.value.header_value("set-cookie").split(";")[0].split("=", 1)[1]
            page.context.add_cookies([{"name": "session", "value": value, "url": origin(page)}])
    else:
        cookie = {"name": "session", "value": who.cookies["session"], "url": origin(page)}
        page.context.add_cookies([cookie])
    page.goto(f"{origin(page)}/blatt/{on['id']}")
    ready(page, count)


def paste_both(page):
    """Ctrl+V and the button Einfügen, one after the other."""
    page.keyboard.press("Control+v")
    button(page, "Einfügen").click()


def own(page, client, count):
    """Copies and pastes the shape "x" and gives the sheet as saved: a paste still on its way
    from before would show in it."""
    pick(page, "x")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(count)
    return saved(page, client)


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


@no_picture
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
