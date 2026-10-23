import json
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_signed_out import login
from ui import user

from blattwerk.app import app

AUTH = (
    "/oauth/authorize?client_id=c&redirect_uri=https%3A%2F%2Fclaude.ai%2Fapi%2Fmcp%2Fauth_callback"
    "&response_type=code&code_challenge=x&code_challenge_method=S256&state=s"
)
CLIENT = {"client_name": "Claude", "redirect_host": "claude.ai", "loopback": False}
HEADING = "„Claude“ möchte sich mit deinem Blattomat-Konto verbinden"


@pytest.fixture
def signed_in(browser, server):
    """Opens a page of the app logged in as the given client, and gives the page."""
    contexts = []

    def start(client, path):
        context = browser.new_context()
        contexts.append(context)
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        context.add_cookies([cookie])
        page = context.new_page()
        page.goto(f"{server}{path}")
        return page

    yield start
    for context in contexts:
        context.close()


def stub_authorize(page, answer, status=200):
    def fulfill(route):
        route.fulfill(status=status, content_type="application/json", body=json.dumps(answer))

    page.route("**/api/oauth/authorize*", fulfill)


def stub_consent(page, server, sent):
    def fulfill(route):
        sent.append(json.loads(route.request.post_data))
        answer = {"redirect": f"{server}/ueber"}
        route.fulfill(content_type="application/json", body=json.dumps(answer))

    page.route("**/api/oauth/consent", fulfill)


def test_consent_page(signed_in, server):
    page = signed_in(user(), AUTH)
    stub_authorize(page, CLIENT)
    sent = []
    stub_consent(page, server, sent)
    page.reload()
    main = page.locator("main")
    expect(page.locator("h1")).to_have_text(HEADING)
    expect(main).to_contain_text("claude.ai")
    expect(main).to_contain_text("Was es darf")
    expect(main).to_contain_text("Unter „Konto“")
    expect(main).not_to_contain_text("läuft auf deinem Computer")
    page.get_by_role("button", name="Erlauben").click()
    expect(page).to_have_url(f"{server}/ueber")
    assert len(sent) == 1
    assert sent[0]["approve"] is True
    assert sent[0]["state"] == "s"
    assert sent[0]["code_challenge"] == "x"


def test_consent_deny(signed_in, server):
    page = signed_in(user(), AUTH)
    stub_authorize(page, CLIENT)
    sent = []
    stub_consent(page, server, sent)
    page.reload()
    expect(page.locator("h1")).to_have_text(HEADING)
    page.get_by_role("button", name="Ablehnen").click()
    expect(page).to_have_url(f"{server}/ueber")
    assert len(sent) == 1
    assert sent[0]["approve"] is False


def test_consent_loopback(signed_in):
    page = signed_in(user(), AUTH)
    stub_authorize(page, {**CLIENT, "redirect_host": "localhost", "loopback": True})
    page.reload()
    expect(page.locator("main")).to_contain_text("Dieses Programm läuft auf deinem Computer")


def test_consent_bad_client(signed_in):
    page = signed_in(user(), AUTH)
    stub_authorize(page, {"detail": "Dieses Programm ist Blattomat nicht bekannt."}, status=400)
    page.reload()
    expect(page.locator("main")).to_contain_text("Dieses Programm ist Blattomat nicht bekannt.")
    expect(page.get_by_role("button", name="Erlauben")).to_have_count(0)


def test_connections_list(signed_in):
    page = signed_in(user(), "/konto")
    row = {"id": 7, "name": "Claude", "created": "2026-10-01 10:00:00", "last_used": None}
    deleted = []

    def listed(route):
        route.fulfill(content_type="application/json", body=json.dumps([row]))

    def gone(route):
        deleted.append(route.request.url)
        route.fulfill(content_type="application/json", body="{}")

    page.route("**/api/connections", listed)
    page.route("**/api/connections/*", gone)
    page.reload()
    item = page.get_by_role("listitem").filter(has_text="Claude")
    expect(item).to_contain_text("zuletzt benutzt: noch nie")
    item.get_by_role("button", name="Trennen: Claude").click()
    dialog = page.locator("dialog[aria-labelledby=ask-unlink]")
    expect(dialog).to_contain_text("„Claude“ trennen?")
    assert deleted == []
    # The request is told before its route runs. The answer comes after that route has noted it.
    with page.expect_response(lambda res: res.request.method == "DELETE") as sent:
        dialog.get_by_role("button", name="Trennen", exact=True).click()
    assert sent.value.request.url.endswith("/api/connections/7")
    assert deleted == [sent.value.request.url]


def test_consent_after_the_login_with_the_real_server(window, server):  # noqa: F811
    """Logged out, the program's link brings the login, then the consent, then the code."""
    back = f"{server}/ueber"
    client = TestClient(app).post(
        "/oauth/register", json={"client_name": "Claude", "redirect_uris": [back]}
    )
    assert client.status_code == 201
    query = urlencode(
        {
            "client_id": client.json()["client_id"],
            "redirect_uri": back,
            "response_type": "code",
            "code_challenge": "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
            "code_challenge_method": "S256",
            "state": "s",
            "resource": f"{server}/mcp",
        }
    )
    page, teacher = window(signed=False)
    page.goto(f"{server}/oauth/authorize?{query}")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    login(page, server, teacher)
    expect(page.get_by_role("heading", name=HEADING)).to_be_visible()
    # The place the answer goes, so a teacher can tell a fake from claude.ai.
    expect(page.locator("main")).to_contain_text("127.0.0.1")
    page.get_by_role("button", name="Erlauben").click()
    page.wait_for_url(f"{back}?code=*")
    assert parse_qs(urlsplit(page.url).query)["state"] == ["s"]


def test_datenschutz_connector():
    text = TestClient(app).get("/datenschutz").text
    section = text.split('<h2 id="claude">9. ', 1)[1].split("<h2>10. ", 1)[0]
    assert "„/mcp“" in section
    assert "Trennen" in section
    connector = section.split("(b) Connector.", 1)[1]
    assert "Anthropic PBC" in connector
    assert "Rücksprungadresse" in connector
    # The tries lie in the database (attempts), not in memory.
    assert "im Arbeitsspeicher" not in text
    assert "die Anmeldungen von Programmen" in text
