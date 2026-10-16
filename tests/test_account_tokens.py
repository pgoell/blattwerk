import re

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


def make(page, name):
    """Types the name and presses Enter, then gives the key as the page shows it."""
    page.get_by_label("Name des Schlüssels").fill(name)
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
    expect(row(page, "Laptop")).to_have_count(0)
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    assert bearer(token).get("/api/sheets").status_code == 401


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
    page.get_by_label("Name des Schlüssels").fill("   ")
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
    page.get_by_label("Name des Schlüssels").fill("Danach")
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


def test_a_blank_name_says_so_beside_the_field(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("   ")
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description("Gib dem Schlüssel einen Namen.")
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    field.fill("x")
    expect(field).to_have_accessible_description("")


def test_a_name_already_in_the_list_says_so_beside_the_field(account):
    page = account(user())
    make(page, "Laptop")
    field = page.get_by_label("Name des Schlüssels")
    field.fill(" laptop ")
    page.keyboard.press("Enter")
    taken = "Diesen Namen hat schon ein Schlüssel. Gib jedem Gerät einen eigenen Namen."
    expect(field).to_have_accessible_description(taken)
    expect(page.get_by_role("listitem")).to_have_count(1)


def test_a_name_of_81_letters_stays_whole_and_says_so(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("x" * 81)
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description("Der Name ist zu lang: höchstens 80 Zeichen.")
    expect(field).to_have_value("x" * 81)
