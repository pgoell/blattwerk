import re

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from ui import reload, user

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
