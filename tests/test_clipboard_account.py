"""The block clipboard belongs to the account: the next one on the same browser gets none of it."""

import json
import re
from uuid import uuid4

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    all_of,
    blocks,
    button,
    chromium_only,
    clipboard_picture,
    every,
    expect_picture,
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
    copy_text,
    expect_picked,
    pick,
    reload,
    saved,
    sheet,
    track_writes,
    unpick,
    user,
    writes_landed,
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
        assert answer.value.ok
        # The session cookie is Secure and this server speaks http: Chromium keeps it for
        # 127.0.0.1 all the same, WebKit does not, so there it goes by hand. Till then the page's
        # calls get 401 and the form comes back after some ms (#727).
        if BROWSER == "webkit":
            value = answer.value.header_value("set-cookie").split(";")[0].split("=", 1)[1]
            page.context.add_cookies([{"name": "session", "value": value, "url": origin(page)}])
            # The login itself empties the store of copies: wait for that before the next page.
            page.wait_for_function("localStorage.getItem('clip') === null")
        else:
            expect(page.locator("#email")).to_have_count(0)
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
    unpick(page)
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


# The types on the system's clipboard.
TYPES = "async () => (await navigator.clipboard.read()).flatMap((item) => item.types)"


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


def copy_in_text(page):
    """Copies the whole line of the open text, as a user does: Enter, Home, Shift+End, Ctrl+C."""
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.press("Home")
    page.keyboard.press("Shift+End")
    page.keyboard.press("Control+c")
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")


def open_list(page):
    """Opens the Lernwörter panel with nothing picked and gives its field."""
    page.locator(".panel").get_by_role("button", name="Lernwörter", exact=True).click()
    return page.get_by_label("Lernwörter", exact=True)


def the_text_box():
    return box("t", "text", {**TEXT, "text": "Der Hund ist braun und klein"})


@pytest.mark.parametrize("by", ["keys", "button"])
def test_words_copied_in_an_open_text_paste_nothing_for_the_next_account(editor, by):
    """#757: the words of a copy in an open text stay on the system's clipboard after the logout."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    if by == "keys":
        field = open_list(page)
        field.press("Control+v")
        expect(field).to_have_value("")
    else:
        button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    # A paste still on its way, as the button's is while it reads the clipboard, would show here.
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


@chromium_only
def test_abmelden_empties_the_clipboard_of_words_copied_in_an_open_text(editor):
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == ""


def test_the_same_account_after_a_new_login_pastes_no_words_of_an_open_text(editor):
    a, email = someone()
    page = editor(the_text_box(), client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    copy_in_text(page)
    logout(page)
    login(page, email, mine, 1)
    assert a.post("/api/login", json={"email": email, "password": PASSWORD}).status_code == 200
    before = stored(page, a)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(1)
    assert stored(page, a) == before


def test_the_same_session_pastes_its_own_words_of_an_open_text_into_a_field(editor):
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    field = open_list(page)
    field.press("Control+v")
    expect(field).not_to_have_value("")
    assert "Hund" in field.input_value()


def test_the_same_session_pastes_its_own_words_of_an_open_text_on_the_sheet_as_a_text(editor):
    """Outside a field the words make a text block, as words copied elsewhere do."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    unpick(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    [new] = [b for b in saved(page, a) if b["id"] != "t"]
    assert (new["type"], new["props"]["text"]) == ("text", "Der Hund ist braun und klein")


CELLS = {"cells": [["Katze", "Maus"], ["", ""]], "cols": [1, 1], "size": 14, "align": "center"}


def in_b_sheet():
    return [
        box("x", "shape", RECT, w=40),
        box("t", "text", {**TEXT, "text": "Bleibt"}, z=2),
        box("c", "table", {**CELLS, "size": 14}, z=3, h=60),
    ]


@pytest.mark.parametrize("target", ["list", "text", "cell", "sheet", "key"])
def test_the_next_account_pastes_no_words_of_the_one_before_into_any_target(editor, target):
    """#757: a copy's words stay on the clipboard; no field of the next account takes them."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, in_b_sheet()), 3)
    before = stored(page, b)
    if target == "list":
        field = open_list(page)
        field.press("Control+v")
        expect(field).to_have_value("")
    elif target == "text":
        pick(page, "t")
        page.keyboard.press("Enter")
        page.keyboard.press("End")
        page.keyboard.press("Control+v")
    elif target == "cell":
        pick(page, "c")
        at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
        expect(at(page, "c").locator("textarea")).to_be_focused()
        page.keyboard.press("Control+v")
    elif target == "sheet":
        unpick(page)
        page.keyboard.press("Control+v")
    else:
        page.goto(f"{origin(page)}/konto")
        field = page.get_by_label("Name des Schlüssels")
        field.click()
        field.press("Control+v")
        expect(field).to_have_value("")
        page.go_back()
        ready(page, 3)
    if target != "key":
        expect(blocks(page)).to_have_count(3)
    assert stored(page, b) == before


def next_list_paste_nothing(page):
    """Logs in as the next account, pastes into its Lernwörter list; its sheet stays as it was."""
    b, email = someone()
    login(page, email, sheet(b, in_b_sheet()), 3)
    before = stored(page, b)
    field = open_list(page)
    field.press("Control+v")
    expect(field).to_have_value("")
    assert stored(page, b) == before


def test_a_cut_in_an_open_text_pastes_nothing_for_the_next_account(editor):
    """#757: a cut is a copy too."""
    a, _ = someone()
    page = editor(the_text_box(), client=a)
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.press("Home")
    page.keyboard.press("Shift+End")
    page.keyboard.press("Control+x")
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    logout(page)
    next_list_paste_nothing(page)


def test_two_table_cells_copied_paste_nothing_for_the_next_account(editor):
    """#757: the cells' text, copied as a whole, is the editor's copy too."""
    a, _ = someone()
    page = editor(box("c", "table", CELLS), client=a)
    pick(page, "c")
    at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
    expect(at(page, "c").locator("textarea")).to_be_focused()
    at(page, "c").locator('.table > div[data-cell="1"]').click(modifiers=["Shift"])
    expect(at(page, "c").locator(".table > div.picked")).to_have_count(2)
    page.keyboard.press("Control+c")
    assert page.evaluate("navigator.clipboard.readText()") == "Katze\tMaus"
    logout(page)
    next_list_paste_nothing(page)


def test_words_picked_in_the_list_field_paste_nothing_for_the_next_account(editor):
    """#757: a copy in the side panel's Lernwörter field is a copy in a field of the editor."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    field = open_list(page)
    field.fill("Hund\nKatze")
    field.press("Control+a")
    field.press("Control+c")
    logout(page)
    next_list_paste_nothing(page)


GAPPED = {
    **TEXT,
    "text": "Der Hund bellt",
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
}


def test_a_text_with_a_gap_copied_whole_pastes_nothing_for_the_next_account(editor):
    """#757: the words of a Lückentext's copy are the copy's words, as the editor's own."""
    a, _ = someone()
    page = editor(box("t", "text", GAPPED), client=a)
    copy_in_text(page)
    logout(page)
    next_list_paste_nothing(page)


@chromium_only
def test_a_word_copied_then_again_in_another_app_pastes_as_a_text_block(editor):
    """#757: after the logout the copy's mark is gone: a word from another app is a text again."""
    a = user()
    page = editor(box("t", "text", {**TEXT, "text": "Hund"}), client=a)
    copy_in_text(page)
    logout(page)
    # Another app's copy, on the login page: no sheet to unpick.
    page.evaluate("(words) => navigator.clipboard.writeText(words)", "Hund")
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    [new] = [b for b in saved(page, b) if b["id"] != "x"]
    assert (new["type"], new["props"]["text"]) == ("text", "Hund")


@chromium_only
def test_words_copied_in_a_table_cell_paste_nothing_for_the_next_account(editor):
    """#757: a table cell's copy counts as the editor's: the next account's list gets none."""
    a = user()
    page = editor(box("c", "table", CELLS), client=a)
    pick(page, "c")
    at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
    expect(at(page, "c").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    assert page.evaluate("navigator.clipboard.readText()") == "Katze"
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    field = open_list(page)
    field.press("Control+v")
    expect(field).to_have_value("")
    assert stored(page, b) == before


def test_words_copied_on_the_login_page_paste_there_and_in_the_sheet(editor):
    """With no one signed in a copy is no account's: it pastes as any other words do."""
    a, email = someone()
    page = editor(the_text_box(), client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    logout(page)
    page.fill("#email", email)
    page.locator("#email").select_text()
    page.keyboard.press("Control+c")
    page.fill("#email", "")
    page.locator("#email").press("Control+v")
    expect(page.locator("#email")).to_have_value(email)
    login(page, email, mine, 1)
    unpick(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)


def copy_key(page):
    """Makes a key on Konto and copies it with its button; gives the key."""
    page.get_by_label("Name des Schlüssels").fill("Kopie")
    page.keyboard.press("Enter")
    shown = page.locator("[data-testid=new-token] code")
    expect(shown).to_have_text(re.compile(r"^bt_"))
    page.get_by_test_id("new-token").get_by_role("button", name="Kopieren").click()
    return shown.inner_text()


@chromium_only
def test_abmelden_empties_the_clipboard_of_a_key_copied_on_konto(editor):
    """#760: the key copied on Konto leaves the system clipboard at Abmelden."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    token = copy_key(page)
    assert page.evaluate("navigator.clipboard.readText()") == token
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == ""


def test_the_next_account_pastes_no_key_copied_on_konto(editor):
    """#760: the next account pastes no key copied on Konto."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    copy_key(page)
    logout(page)
    next_list_paste_nothing(page)


def test_the_same_session_pastes_its_own_key_into_a_field(editor):
    """#760: the account that copied a key on Konto pastes it back there."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    token = copy_key(page)
    field = page.get_by_label("Name des Schlüssels")
    field.fill("")
    field.focus()
    # The copy's mark is set once the clipboard has taken the key: wait for it before the paste.
    assert page.evaluate("navigator.clipboard.readText()") == token
    page.keyboard.press("Control+v")
    expect(field).to_have_value(token)


def copied(editor, copy):
    """A copy of the kind on the system clipboard, made on its page by its account."""
    if copy == "blocks":
        a = user()
        page = editor(box("a", "shape", RECT), client=a)
        copy_all(page, 1)
    elif copy == "words":
        a = user()
        page = editor(the_text_box(), client=a)
        copy_in_text(page)
    else:
        a, _ = someone()
        page = editor(box("x", "shape", RECT, w=40), client=a)
        page.goto(f"{origin(page)}/konto")
        token = copy_key(page)
        # The clipboard takes the key after the click: a navigation before that cuts it off.
        assert page.evaluate("navigator.clipboard.readText()") == token
    return page, a


def to_konto(page, way):
    """Gets the page to Konto the way named: a reload, a new tab, or the address typed in."""
    konto = f"{origin(page)}/konto"
    if way == "reload":
        reload(page, page.url)
        page.goto(konto)
    elif way == "tab":
        page = page.context.new_page()
        page.goto(konto)
    else:
        page.goto(konto)
    return page


# Records each read of the clipboard and each permission query the page makes from now on.
RECORD = """() => {
    window.__asked = [];
    const clipboard = navigator.clipboard;
    const readText = clipboard.readText.bind(clipboard);
    const read = clipboard.read.bind(clipboard);
    clipboard.read = (...args) => {
        window.__asked.push("read");
        return read(...args);
    };
    const permissions = navigator.permissions;
    const query = permissions.query.bind(permissions);
    clipboard.readText = (...args) => {
        window.__asked.push("readText");
        return readText(...args);
    };
    permissions.query = (...args) => {
        window.__asked.push("query");
        return query(...args);
    };
}"""


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


def run_out(page):
    """The session ends with no logout, and the login form comes back. No clip is needed."""
    page.context.clear_cookies()
    page.reload()
    expect(page.locator("#email")).to_be_visible()


def form_login(page, email):
    """Logs in on the form and waits for the login's clipboard step, before any navigation."""
    page.fill("#email", email)
    page.fill("#password", PASSWORD)
    with page.expect_response("**/api/login") as answer:
        button(page, "Anmelden").click()
    assert answer.value.ok
    if BROWSER == "webkit":
        value = answer.value.header_value("set-cookie").split(";")[0].split("=", 1)[1]
        page.context.add_cookies([{"name": "session", "value": value, "url": origin(page)}])
    page.wait_for_function("localStorage.getItem('clip') === null")


CLIPBOARD_LOG = """() => {
    window.wrote = [];
    const real = navigator.clipboard.writeText.bind(navigator.clipboard);
    navigator.clipboard.writeText = (t) => (window.wrote.push(t), real(t).catch(() => {}));
}"""


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


# Keeps each clipboard write of whole items: the event it was begun in, and what its text came to.
ITEM_LOG = """() => {
    window.items = [];
    const real = navigator.clipboard.write.bind(navigator.clipboard);
    navigator.clipboard.write = (items) => {
        const seen = { event: window.event?.type };
        window.items.push(seen);
        items[0].getType("text/plain").then((b) => b.text()).then(
            (t) => (seen.text = t),
            () => (seen.text = "refused"),
        );
        return real(items);
    };
}"""


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
