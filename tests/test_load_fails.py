"""A load that fails is not a sheet that is not there (issue #335): only a 404 says `Blatt nicht
gefunden`. Any other failure, and an answer that has not come after 20 s, says that the sheet
could not be loaded and offers another try, which also comes by itself when the network is back.
The list of sheets does the same.

Built on test_loading.py: the test fails or holds a load and goes to the address itself. For the
20 s the page's clock stands and the test moves it.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import json

import pytest
from playwright.sync_api import expect
from test_loading import BLANK, READY, SHEET, expect_loading, hold, window  # noqa: F401
from test_saves import (  # noqa: F401
    NOTICE,
    again,
    answer,
    elsewhere,
    leave,
    nudge,
    record,
    run,
    shut,
    start,
    x_of,
)
from test_stale import STATUS, TURNS
from ui import TEXT, at, box, sheet, user

FAILED = "Das Blatt konnte nicht geladen werden"
LIST_FAILED = "Die Blätter konnten nicht geladen werden"
AGAIN = "Erneut versuchen"
ONLINE = "dispatchEvent(new Event('online'))"


def fail(page, address, how=500):
    """Fails what the page reads from the address from now on: with the status, or "cut", where
    the line drops. Gives the loads that came."""
    came = []

    def refuse(route):
        if route.request.method != "GET":
            route.continue_()
            return
        came.append(route.request)
        if how == "cut":
            route.abort()
        else:
            route.fulfill(status=how)

    page.route(address, refuse)
    return came


def loads(page, address):
    """The loads the page asks of the address from now on."""
    asked = []
    page.on("request", lambda r: r.method == "GET" and r.url == address and asked.append(r))
    return asked


def expect_failed(page):
    """The failure page stands, told to a screen reader, and not as a sheet that is not there.
    Gives its button."""
    told = page.get_by_role("alert")
    expect(told.get_by_role("heading", name=FAILED)).to_be_visible(timeout=10000)
    expect(told).to_contain_text("Prüfe deine Verbindung.")
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_have_count(0)
    expect(page.locator("main.editor")).to_have_count(0)
    return told.get_by_role("button", name=AGAIN)


def expect_sheet(page, blocks=1):
    # Not `expect_ready`: the failure page stands in the app's frame, as the page of a sheet that
    # is not there does.
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(".block[data-id]")).to_have_count(blocks)
    expect(page.get_by_role("button", name=AGAIN)).to_have_count(0)


@pytest.mark.parametrize("how", [500, 503, "cut"])
def test_a_sheet_whose_load_fails_says_so_and_a_press_loads_it(window, server, how):
    """A1, A3; I7: the loading page stands while the try runs, and nothing starts a second."""
    page, client = window()
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    address = f"{server}/api/sheets/{sheet(client, [box('a', 'text', TEXT)])['id']}"
    fail(page, SHEET, how)
    page.goto(address.replace("/api/sheets/", "/blatt/"))
    press = expect_failed(page)
    page.unroute(SHEET)
    go = hold(page, SHEET)
    asked = loads(page, address)
    press.click()
    expect(page.locator(BLANK)).to_be_visible()
    expect(press).to_have_count(0)
    expect(page.get_by_role("alert")).to_have_count(0)
    page.evaluate(ONLINE)
    page.evaluate(TURNS)
    assert len(asked) == 1
    go()
    expect_sheet(page)
    assert len(asked) == 1
    assert not errors


@pytest.mark.parametrize("whose", ["nobody", "another-teacher"])
def test_a_sheet_that_is_not_there_or_is_another_teachers_is_not_found(window, server, whose):
    """A2"""
    page, _ = window()
    there = 987654 if whose == "nobody" else sheet(user(), [box("a", "text", TEXT)])["id"]
    with page.expect_response(f"{server}/api/sheets/{there}") as got:
        page.goto(f"{server}/blatt/{there}")
    assert got.value.status == 404
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_role("button", name=AGAIN)).to_have_count(0)


def test_a_failed_load_is_tried_again_when_the_network_is_back(window, server):
    """A4"""
    page, client = window()
    address = f"{server}/api/sheets/{sheet(client, [box('a', 'text', TEXT)])['id']}"
    fail(page, SHEET, "cut")
    page.goto(address.replace("/api/sheets/", "/blatt/"))
    expect_failed(page)
    page.unroute(SHEET)
    asked = loads(page, address)
    page.context.set_offline(True)
    page.evaluate(TURNS)
    assert not asked
    page.context.set_offline(False)
    expect_sheet(page)
    assert len(asked) == 1


def test_a_load_with_no_answer_counts_as_failed_after_20_s(window, server):
    """A5; I7: so does a try with no answer. Each is given up before the next one starts."""
    page, client = window()
    address = f"{server}/api/sheets/{sheet(client, [box('a', 'text', TEXT)])['id']}"
    held = []
    page.route(SHEET, lambda route: held.append(route))
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    with page.expect_request(address):
        page.goto(address.replace("/api/sheets/", "/blatt/"))
    for _ in range(2):
        page.clock.run_for(19999)
        page.evaluate(TURNS)
        expect_loading(page)
        assert not held[-1].request.failure
        with page.expect_event("requestfailed", lambda r: r.url == address):
            page.clock.run_for(1)
        press = expect_failed(page)
        # The try that follows: the first time with no answer either.
        page.unroute(SHEET)
        if len(held) == 1:
            page.route(SHEET, lambda route: held.append(route))
        with page.expect_request(address):
            press.click()
    assert len(held) == 2
    page.clock.resume()
    expect_sheet(page)


def test_a_kept_change_outlives_a_failed_load_and_shows_once_the_sheet_loads(window, server):
    """A6"""
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
    # The app's start asks for the sheet of a kept change too: that fails as well.
    came = fail(page, SHEET)
    with page.expect_response(lambda r: r.url == address and len(came) == 2):
        page.goto(address.replace("/api/sheets/", "/blatt/"))
    press = expect_failed(page)
    page.evaluate(TURNS)
    assert record(page, made["id"])["doc"]["pages"][0]["blocks"][0]["x"] == 77
    assert client.get(f"/api/sheets/{made['id']}").json() == made
    page.unroute(SHEET)
    press.click()
    expect_sheet(page)
    left = at(page, "a").evaluate("el => parseFloat(getComputedStyle(el).left)")
    assert left == pytest.approx(77 * 96 / 25.4, abs=0.01)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert client.get(f"/api/sheets/{made['id']}").json()["doc"]["pages"][0]["blocks"][0]["x"] == 77
    assert record(page, made["id"]) is None


def test_a_clash_notices_link_ends_on_the_failure_page_when_the_load_fails(run):
    """A7; A6: the kept change waits, and the try that loads the sheet asks which version stays."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    elsewhere(run, 40)
    page, _, sent = again(run, None)
    said = page.locator(NOTICE)
    expect(said).to_contain_text("wurde auf einem anderen Gerät geändert")
    address = f"**/api/sheets/{run.ids['a']}"
    fail(page, address)
    said.get_by_role("link", name="Öffne das Blatt").click()
    press = expect_failed(page)
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.unroute(address)
    press.click()
    expect_sheet(page)
    banner = page.locator(".clash")
    expect(banner.get_by_role("button", name="Andere Version laden")).to_be_visible()
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16


def test_the_failure_is_told_and_its_button_is_reached_by_tab_and_pressed_by_enter(window, server):
    """I8"""
    page, client = window()
    fail(page, SHEET)
    page.goto(f"{server}/blatt/{sheet(client, [box('a', 'text', TEXT)])['id']}")
    press = expect_failed(page)
    # The alert is the failure and what to do about it, and the button waits for Enter at once.
    expect(press).to_be_focused()
    assert press.evaluate("el => el.tagName") == "BUTTON"
    page.evaluate("document.activeElement.blur()")
    expect(press).not_to_be_focused()
    for _ in range(12):
        page.keyboard.press("Tab")
        if press.evaluate("el => el === document.activeElement"):
            break
    expect(press).to_be_focused()
    page.unroute(SHEET)
    page.keyboard.press("Enter")
    expect_sheet(page)


def expect_list_failed(page):
    told = page.get_by_role("alert")
    expect(told).to_contain_text(LIST_FAILED, timeout=10000)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page.locator(".sheets li")).to_have_count(0)
    return told.get_by_role("button", name=AGAIN)


@pytest.mark.parametrize("how", [500, "cut"])
def test_the_list_whose_load_fails_says_so_and_a_press_loads_it(window, server, how):
    """A8, I8"""
    page, client = window()
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    sheet(client, [box("a", "text", TEXT)])
    address = f"{server}/api/sheets"
    fail(page, address, how)
    page.goto(server)
    press = expect_list_failed(page)
    expect(press).to_be_focused()
    expect(page.locator("main")).not_to_contain_text("Noch kein Blatt")
    page.unroute(address)
    asked = loads(page, address)
    page.keyboard.press("Enter")
    expect(page.locator(".sheets li")).to_have_count(1)
    expect(page.get_by_role("alert")).to_have_count(0)
    assert len(asked) == 1
    assert not errors


def test_the_list_is_asked_for_again_when_the_network_is_back(window, server):
    """A8"""
    page, client = window()
    sheet(client, [box("a", "text", TEXT)])
    address = f"{server}/api/sheets"
    fail(page, address, "cut")
    page.goto(server)
    expect_list_failed(page)
    page.unroute(address)
    page.context.set_offline(True)
    page.context.set_offline(False)
    expect(page.locator(".sheets li")).to_have_count(1)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_the_list_with_no_answer_counts_as_failed_after_20_s(window, server):
    """A8"""
    page, client = window()
    sheet(client, [box("a", "text", TEXT)])
    address = f"{server}/api/sheets"
    held = []
    page.route(address, lambda route: held.append(route))
    page.clock.install()
    page.clock.pause_at(page.evaluate("Date.now()") + 1000)
    with page.expect_request(address):
        page.goto(server)
    page.clock.run_for(19999)
    page.evaluate(TURNS)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page.get_by_role("alert")).to_have_count(0)
    assert not held[0].request.failure
    page.clock.run_for(1)
    press = expect_list_failed(page)
    page.unroute(address)
    page.clock.resume()
    press.click()
    expect(page.locator(".sheets li")).to_have_count(1)


def test_a_failed_refresh_leaves_the_list_that_stands(run):
    """I6: the list asks anew when a save lands; that load fails, and nothing changes."""
    page, _ = leave(run, "held", "list")
    address = f"{run.server}/api/sheets"
    came = fail(page, address)
    with page.expect_response(address) as got:
        answer(run, "a")
    assert got.value.status == 500
    page.evaluate(TURNS)
    assert len(came) == 1
    expect(page.locator(".sheets li")).to_have_count(3)
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_role("button", name=AGAIN)).to_have_count(0)
