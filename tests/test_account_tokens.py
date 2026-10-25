import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from ui import PASSWORD, reload, user

from blattwerk.app import app


@pytest.fixture
def account(browser, server):
    """Opens /konto logged in as the given client, and gives its page."""
    contexts = []

    def start(client):
        context = browser.new_context()
        contexts.append(context)
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        context.add_cookies([cookie])
        page = context.new_page()
        page.goto(f"{server}/konto")
        return page

    yield start
    for context in contexts:
        context.close()


def bearer(token):
    """A client with no cookie, asking as the key does."""
    client = TestClient(app, base_url="https://testserver")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def type_name(page, name):
    """Types the name and waits until the field shows it.

    fill() on WebKit sends insertText to whatever is focused, and that can miss this
    field. The letters never arrive, so waiting longer does not help (#749).
    """
    field = page.get_by_label("Name des Schlüssels")
    field.click()
    field.press_sequentially(name)
    expect(field).to_have_value(name)
    return field


def make(page, name):
    """Types the name and presses Enter, then gives the key as the page shows it."""
    type_name(page, name)
    page.keyboard.press("Enter")
    shown = page.locator("[data-testid=new-token] code")
    expect(shown).to_have_text(re.compile(r"^bt_"))
    return shown.inner_text()


def row(page, name):
    return page.get_by_role("listitem").filter(has_text=name)


def test_key_is_shown_once_and_never_stored(account):
    page = account(user())
    token = make(page, "Claude Desktop")
    expect(row(page, "Claude Desktop")).to_contain_text("zuletzt benutzt: noch nie")

    stored = page.evaluate("() => JSON.stringify([{...localStorage}, {...sessionStorage}])")
    assert token not in stored

    reload(page, page.url)
    expect(row(page, "Claude Desktop")).to_be_visible()
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(page.locator("body")).not_to_contain_text(token)


def test_revoke_takes_the_key_away(account):
    client = user()
    page = account(client)
    token = make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(page, "Laptop")).to_have_count(0)
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    assert bearer(token).get("/api/sheets").status_code == 401


def test_the_revoke_question_names_the_key_and_not_this_device(account):
    page = account(user())
    make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("„Laptop“")
    expect(dialog).not_to_contain_text("diesem Gerät")


def test_last_use_shows_on_the_list(account):
    client = user()
    page = account(client)
    token = make(page, "Schule")
    expect(row(page, "Schule")).to_contain_text("noch nie")
    assert bearer(token).get("/api/sheets").status_code == 200
    reload(page, page.url)
    expect(row(page, "Schule")).not_to_contain_text("noch nie")
    expect(row(page, "Schule")).to_contain_text("zuletzt benutzt")


def test_a_blank_name_makes_nothing(account):
    page = account(user())
    type_name(page, "   ")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(page.get_by_role("listitem")).to_have_count(0)


def test_a_list_that_fails_to_load_raises_no_alert(browser, server):
    context = browser.new_context()
    cookie = {"name": "session", "value": user().cookies["session"], "url": server}
    context.add_cookies([cookie])
    page = context.new_page()
    # Offline as the account page opens: the alert stays free for what the teacher does.
    page.route("**/api/tokens", lambda route: route.abort())
    page.goto(f"{server}/konto")
    expect(page.get_by_role("button", name="Abmelden")).to_be_visible()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("alert")).to_have_count(0)
    page.unroute("**/api/tokens")
    make(page, "Danach")
    expect(row(page, "Danach")).to_be_visible()
    context.close()


def test_newest_key_comes_first(account):
    page = account(user())
    make(page, "Erster")
    make(page, "Zweiter")
    rows = page.get_by_role("listitem")
    expect(rows).to_have_text([re.compile(r"^Zweiter"), re.compile(r"^Erster")])


def test_revoke_asks_first_and_abbrechen_keeps_the_key(account):
    page = account(user())
    make(page, "Laptop Schule")
    page.get_by_role("button", name="Widerrufen: Laptop Schule").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Schlüssel „Laptop Schule“ widerrufen?")
    dialog.get_by_role("button", name="Abbrechen").click()
    expect(dialog).not_to_be_visible()
    expect(row(page, "Laptop Schule")).to_be_visible()
    expect(page.get_by_role("button", name="Widerrufen: Laptop Schule")).to_be_focused()


def test_a_key_another_tab_already_revoked_leaves_the_list_quietly(account):
    page = account(user())
    make(page, "Laptop")
    other = page.context.new_page()
    other.goto(page.url)
    other.get_by_role("button", name="Widerrufen: Laptop").click()
    other.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(other, "Laptop")).to_have_count(0)
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(page, "Laptop")).to_have_count(0)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_a_revoke_that_finds_the_session_gone_is_said_after_the_login(account, server):
    client = user()
    page = account(client)
    make(page, "Laptop")
    page.context.clear_cookies()
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    said = "Der Schlüssel „Laptop“ ist noch nicht widerrufen"
    expect(page.get_by_role("status")).to_contain_text(said)
    expect(row(page, "Laptop")).to_be_visible()


def test_escape_keeps_the_key_and_gives_the_focus_back(account):
    page = account(user())
    make(page, "Laptop Schule")
    button = page.get_by_role("button", name="Widerrufen: Laptop Schule")
    button.click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(row(page, "Laptop Schule")).to_be_visible()
    expect(button).to_be_focused()


def test_a_key_not_made_when_the_session_ran_out_is_said_after_the_login(account, server):
    client = user()
    page = account(client)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    type_name(page, "Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    said = "Der Schlüssel „Danach“ wurde nicht erstellt"
    expect(page.get_by_role("status")).to_contain_text(said)
    expect(page.get_by_label("Name des Schlüssels")).to_have_value("Danach")
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(row(page, "Danach")).to_have_count(0)


def test_the_note_of_one_teacher_never_shows_to_the_next_one_at_that_login(account, server):
    page = account(user())
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    type_name(page, "Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    other = user()
    cookie = {"name": "session", "value": other.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(other.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_label("Name des Schlüssels")).to_have_value("")
    expect(page.get_by_role("status")).to_have_count(0)


def test_the_note_shows_once_and_a_reload_takes_it_away(account, server):
    client = user()
    page = account(client)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    type_name(page, "Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.get_by_role("status")).to_contain_text("wurde nicht erstellt")
    reload(page, page.url)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_role("status")).to_have_count(0)


def test_a_double_press_on_erstellen_makes_one_key_and_no_more_words(account):
    page = account(user())
    field = type_name(page, "Doppelt")
    page.get_by_role("button", name="Schlüssel erstellen").dblclick()
    expect(page.locator("[data-testid=new-token] code")).to_have_text(re.compile(r"^bt_"))
    page.wait_for_timeout(500)
    expect(row(page, "Doppelt")).to_have_count(1)
    # The hint beside the field, and no complaint after it.
    expect(field).to_have_accessible_description(HINT)


def test_enter_pressed_twice_makes_one_key_and_no_more_words(account):
    page = account(user())
    field = type_name(page, "Doppelt")
    made = []
    page.on(
        "request", lambda r: r.method == "POST" and r.url.endswith("/api/tokens") and made.append(r)
    )
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    expect(page.locator("[data-testid=new-token] code")).to_have_text(re.compile(r"^bt_"))
    # The row comes with the list asked for after the first make: a second make went out before it.
    expect(row(page, "Doppelt")).to_have_count(1)
    assert len(made) == 1
    expect(field).to_have_accessible_description(HINT)


# What WebKit's fill did on the failed run: the name is in the DOM, and React was not told.
SET_DOM = """(value) => {
  const el = document.getElementById("key-name");
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, value);
}"""


def test_a_name_in_the_field_stays_when_the_key_list_arrives(browser, server):
    """The list's answer must not clear a name the field already shows (#749).

    WebKit's fill once wrote that name into the field and not into React. The list
    then drew the empty state over it, Enter made no key, and the test sat out the
    5 s waiting for one that was never asked for.
    """
    client = user()
    context = browser.new_context()
    held = []

    def hold(route):
        if route.request.method == "GET":
            held.append(route)
        else:
            route.continue_()

    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.route("**/api/tokens", hold)
    context.route("**/api/connections", hold)
    page = context.new_page()
    try:
        # The effect asks for both lists after the first paint. Wait until those two are
        # held, or a slow one arrives after we let go and the test waits on it forever.
        with (
            page.expect_request(lambda r: r.method == "GET" and "/api/tokens" in r.url),
            page.expect_request(lambda r: r.method == "GET" and "/api/connections" in r.url),
        ):
            page.goto(f"{server}/konto")
        field = page.get_by_label("Name des Schlüssels")
        expect(field).to_be_visible()
        page.evaluate(SET_DOM, "Laptop")
        expect(field).to_have_value("Laptop")
        with (
            page.expect_response(lambda r: "/api/tokens" in r.url and r.request.method == "GET"),
            page.expect_response(
                lambda r: "/api/connections" in r.url and r.request.method == "GET"
            ),
        ):
            for route in held:
                route.continue_()
        context.unroute("**/api/tokens", hold)
        context.unroute("**/api/connections", hold)
        # Both answers have been drawn. The name that was already in the field stays.
        page.evaluate(
            "() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))"
        )
        expect(field).to_have_value("Laptop")
        field.press("Enter")
        expect(page.locator("[data-testid=new-token] code")).to_have_text(re.compile(r"^bt_"))
        expect(row(page, "Laptop")).to_be_visible()
    finally:
        context.close()


def test_a_name_typed_while_the_list_loads_makes_its_key(account):
    """Review of #934: the guard against a double press lets go once the teacher types."""
    page = account(user())
    held = []
    page.route(
        "**/api/tokens", lambda r: held.append(r) if r.request.method == "GET" else r.continue_()
    )
    field = type_name(page, "Erster")
    page.keyboard.press("Enter")
    expect(page.locator("[data-testid=new-token] code")).to_have_text(re.compile(r"^bt_"))
    expect(field).to_have_value("")
    type_name(page, "Zweiter")
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/api/tokens")):
        page.keyboard.press("Enter")
    for route in held:
        route.continue_()
    page.unroute("**/api/tokens")
    expect(row(page, "Zweiter")).to_have_count(1)


def test_enter_on_the_question_keeps_the_key(account):
    page = account(user())
    make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    expect(page.get_by_role("dialog").get_by_role("button", name="Abbrechen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(row(page, "Laptop")).to_be_visible()


DOCS = Path(__file__).resolve().parents[1] / "docs" / "okf"


LABEL = "Name des Schlüssels, z. B. Laptop Schule"
HINT = "Gib jedem Schlüssel einen eigenen Namen, einen je Gerät."


COPY_STUB = "() => { window.copiedKey = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: (t) => { window.copiedKey = t; return Promise.resolve(); }}}); }"
REFUSED_STUB = "() => { Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError'))}}); }"
