"""The block clipboard belongs to the account: the next one on the same browser gets none of it."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import json
import re
from uuid import uuid4

from playwright.sync_api import expect
from test_clipboard import (
    all_of,
    blocks,
    button,
    ready,
    stored,
)
from ui import (
    BROWSER,
    PASSWORD,
    RECT,
    TEXT,
    box,
    pick,
    reload,
    saved,
    sheet,
    track_writes,
    unpick,
    user,
    writes_landed,
)

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
        # The wipe starts in the click and ends after the form has gone. The next line leaves
        # this page: a navigation before that write lands drops it, and the previous account's
        # words stay on the clipboard (#772).
        if BROWSER != "webkit":
            track_writes(page)
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
            writes_landed(page)
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


# The types on the system's clipboard.
TYPES = "async () => (await navigator.clipboard.read()).flatMap((item) => item.types)"


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


CELLS = {"cells": [["Katze", "Maus"], ["", ""]], "cols": [1, 1], "size": 14, "align": "center"}


def in_b_sheet():
    return [
        box("x", "shape", RECT, w=40),
        box("t", "text", {**TEXT, "text": "Bleibt"}, z=2),
        box("c", "table", {**CELLS, "size": 14}, z=3, h=60),
    ]


def next_list_paste_nothing(page):
    """Logs in as the next account, pastes into its Lernwörter list; its sheet stays as it was."""
    b, email = someone()
    login(page, email, sheet(b, in_b_sheet()), 3)
    before = stored(page, b)
    field = open_list(page)
    field.press("Control+v")
    expect(field).to_have_value("")
    assert stored(page, b) == before


GAPPED = {
    **TEXT,
    "text": "Der Hund bellt",
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
}


def copy_key(page):
    """Makes a key on Konto and copies it with its button; gives the key."""
    page.get_by_label("Name des Schlüssels").fill("Kopie")
    page.keyboard.press("Enter")
    shown = page.locator("[data-testid=new-token] code")
    expect(shown).to_have_text(re.compile(r"^bt_"))
    page.get_by_test_id("new-token").get_by_role("button", name="Kopieren").click()
    return shown.inner_text()


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
