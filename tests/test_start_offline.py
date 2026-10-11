"""A start whose account check fails says that the server cannot be reached (issue #370). It is not
the login: only a 401 says the session is gone.

Built on test_load_fails.py: `fail` refuses the address, and the page's own try is the button.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import json

import pytest
from playwright.sync_api import expect
from test_load_fails import AGAIN, ONLINE, fail
from test_loading import ME, READY, SHEET, window  # noqa: F401
from test_saves import record
from test_stale import STATUS, TURNS
from ui import TEXT, box, sheet

UNREACHED = "Blattomat erreicht den Server nicht"
LOGIN = "input[type=password]"


def expect_unreached(page):
    """The failure page stands, told to a screen reader, and not the login. Gives its button."""
    told = page.get_by_role("alert")
    expect(told.get_by_role("heading", name=UNREACHED)).to_be_visible(timeout=10000)
    expect(page.locator(LOGIN)).to_have_count(0)
    return told.get_by_role("button", name=AGAIN)


@pytest.mark.parametrize("how", [500, "cut"])
def test_a_start_whose_account_check_fails_says_the_server_is_not_reached(window, server, how):
    """15: a 500, and no connection at all."""
    page, _ = window()
    fail(page, ME, how)
    page.goto(server)
    press = expect_unreached(page)
    expect(press).to_be_visible()


def test_the_press_opens_the_app_as_signed_in(window, server):
    """16: the press asks again, and the app shows once the account is known."""
    page, _ = window()
    fail(page, ME, "cut")
    page.goto(server)
    press = expect_unreached(page)
    page.unroute(ME)
    press.click()
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_the_network_coming_back_opens_the_app_as_signed_in(window, server):
    """16: the online event asks again in place of the press."""
    page, _ = window()
    fail(page, ME, "cut")
    page.goto(server)
    expect_unreached(page)
    page.unroute(ME)
    page.evaluate(ONLINE)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_a_session_that_ran_out_still_shows_the_login(window, server):
    """16: a 401 is signed out, not an unreachable server: the login shows, and no failure page."""
    page, _ = window()
    fail(page, ME, 401)
    page.goto(server)
    expect(page.locator(LOGIN)).to_be_visible(timeout=10000)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_a_kept_change_is_saved_once_the_account_check_comes_back(window, server):
    """17: a change the browser kept waits through the failed start, and is saved after it."""
    page, client = window()
    made = sheet(client, [box("a", "text", TEXT)])
    address = f"{server}/api/sheets/{made['id']}"
    doc = json.loads(json.dumps(made["doc"]))
    doc["pages"][0]["blocks"][0]["x"] = 77
    kept = {"owner": client.get("/api/me").json()["id"], "base": made["version"], "doc": doc}
    page.context.add_init_script(
        f"localStorage.getItem('seeded') || localStorage.setItem('unsaved:{made['id']}', "
        f"{json.dumps(json.dumps(kept))}); localStorage.setItem('seeded', '1')"
    )
    fail(page, ME, "cut")
    page.goto(address.replace("/api/sheets/", "/blatt/"))
    press = expect_unreached(page)
    page.evaluate(TURNS)
    assert record(page, made["id"])["doc"]["pages"][0]["blocks"][0]["x"] == 77
    assert client.get(f"/api/sheets/{made['id']}").json() == made
    page.unroute(ME)
    press.click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert client.get(f"/api/sheets/{made['id']}").json()["doc"]["pages"][0]["blocks"][0]["x"] == 77
    assert record(page, made["id"]) is None


@pytest.mark.parametrize("address", ["/ueber", "/passwort/abc"])
def test_a_page_that_needs_no_account_shows_when_the_account_check_fails(window, server, address):
    """I8: the pages that need no account take the login's place; the failure page is not theirs."""
    page, _ = window()
    fail(page, ME, 500)
    page.goto(server + address)
    expect(page.get_by_role("heading", name=UNREACHED)).to_have_count(0)
    if address == "/ueber":
        expect(page.get_by_role("heading", name="Über Blattomat")).to_be_visible(timeout=10000)
    else:
        expect(page.locator("#password")).to_be_visible(timeout=10000)


def test_a_print_page_does_not_show_the_account_failure(window, server):
    """I8: a sheet's print page needs no account; the failure page does not stand on it."""
    page, client = window()
    made = sheet(client, [box("a", "text", TEXT)])
    fail(page, ME, 500)
    page.goto(f"{server}/druck/{made['id']}")
    expect(page.get_by_role("heading", name=UNREACHED)).to_have_count(0)
