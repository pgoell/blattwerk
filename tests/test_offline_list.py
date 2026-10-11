"""An action that needs the server and does not get it stays in the app and says so (issue #363):
a line above the page names the action and why, and its button tries the same again, with what
the teacher had typed. Here the buttons of Meine Blätter, of Konto and of Admin.

Each is tried with no connection and with a server that fails.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `admin_page` are imported, and each test names one as its argument.
# ruff: noqa: F811

import contextlib
import re

import pytest
from playwright.sync_api import expect
from test_admin import admin, admin_page  # noqa: F401
from test_loading import window  # noqa: F401
from test_stale import TURNS
from ui import TEXT, box, sheet, user

AGAIN = "Erneut versuchen"
WHY = {
    "offline": "Prüfe deine Verbindung und versuche es noch einmal.",
    500: "Blattomat hat gerade eine Störung. Versuche es gleich noch einmal.",
}
HOWS = ["offline", 500]
GONE = "Dieses Blatt wurde auf einem anderen Gerät gelöscht."
# The button of each action on the sheet "a", and what its line names.
ACTIONS = {
    "create": ("Neues Blatt", "Das neue Blatt konnte nicht angelegt werden."),
    "rename": ("a umbenennen", "Das Blatt konnte nicht umbenannt werden."),
    "duplicate": ("a duplizieren", "Das Blatt konnte nicht dupliziert werden."),
    "remove": ("a löschen", "Das Blatt konnte nicht gelöscht werden."),
}
API = "**/api/**"
# Notes whether the page ever says that a sheet was deleted, however briefly.
SEEN = """new MutationObserver(() => {
    if (document.body.textContent.includes('gelöscht.')) window.said = true;
}).observe(document.body, { subtree: true, childList: true, characterData: true })"""


def cut(page, how, loads=False):
    """Takes the server away from now on: no connection, or a fault for all the page sends, and
    with `loads` for all it reads too. Gives what brings the server back."""
    if how == "offline":
        page.context.set_offline(True)
        return lambda: page.context.set_offline(False)

    def refuse(route):
        if loads or route.request.method != "GET":
            route.fulfill(status=how)
        else:
            route.continue_()

    page.route(API, refuse)
    return lambda: page.unroute(API)


@contextlib.contextmanager
def failing(page, how):
    """Waits until a request of the page has failed, and the page has taken that in."""
    if how == "offline":
        failed = page.expect_event("requestfailed")
    else:
        failed = page.expect_response(lambda response: response.status == how)
    with failed:
        yield
    page.evaluate(TURNS)


def listed(page, server, client, *more):
    """The list with the sheet "a" on it, and those of `more`. Gives the id of "a"."""
    made = sheet(client, [box("a", "text", TEXT)], title="a")
    for title in more:
        sheet(client, [box("a", "text", TEXT)], title=title)
    page.goto(server)
    expect(page.locator(".sheets li")).to_have_count(1 + len(more), timeout=10000)
    return made["id"]


def titles(client):
    return sorted(s["title"] for s in client.get("/api/sheets").json())


@pytest.mark.parametrize("how", HOWS)
@pytest.mark.parametrize("action", ACTIONS)
def test_a_button_of_the_list_that_fails_says_so_and_a_try_does_it(window, server, action, how):
    """A12, A13, A14, A15; I4: a second failure takes the first one's place, and the line goes
    with the try that works."""
    page, client = window()
    listed(page, server, client)
    asked = []
    page.on("dialog", lambda d: (asked.append(d), d.accept("Neu" if d.type == "prompt" else None)))
    label, what = ACTIONS[action]
    line = page.get_by_role("alert")
    mend = cut(page, how)
    for _ in range(2):
        with failing(page, how):
            page.get_by_role("button", name=label).click()
        expect(line).to_have_count(1)
        expect(line).to_contain_text(f"{what} {WHY[how]}")
    # Nothing has changed, here or on the server.
    expect(page.locator(".sheets li strong")).to_have_text(["a"])
    assert titles(client) == ["a"]
    mend()
    questions = len(asked)
    line.get_by_role("button", name=AGAIN).click()
    if action == "create":
        expect(page).to_have_url(re.compile(r"/blatt/\d+$"))
        want = ["Unbenanntes Blatt", "a"]
    elif action == "rename":
        expect(page.locator(".sheets li strong")).to_have_text(["Neu"])
        want = ["Neu"]
    elif action == "duplicate":
        expect(page.locator(".sheets li")).to_have_count(2)
        want = ["a", "a (Kopie)"]
    else:
        expect(page.locator(".sheets li")).to_have_count(0)
        want = []
    expect(line).to_have_count(0)
    assert titles(client) == want
    # The try asked nothing again: it holds the title typed and the yes given.
    assert len(asked) == questions


@pytest.mark.parametrize("action", ["rename", "duplicate", "remove"])
def test_a_button_on_a_sheet_deleted_elsewhere_says_so_and_takes_the_row_away(
    window, server, action
):
    """A11: the server says 404, and no try would end otherwise, so the line has no such button."""
    page, client = window()
    there = listed(page, server, client, "b")
    page.on("dialog", lambda d: d.accept("Neu" if d.type == "prompt" else None))
    assert client.delete(f"/api/sheets/{there}").status_code == 200
    page.get_by_role("button", name=ACTIONS[action][0]).click()
    line = page.get_by_role("alert")
    expect(line).to_contain_text(GONE)
    expect(line.get_by_role("button", name=AGAIN)).to_have_count(0)
    expect(page.locator(".sheets li strong")).to_have_text(["b"])
    assert titles(client) == ["b"]
    line.get_by_role("button", name="Schließen").click()
    expect(line).to_have_count(0)


@pytest.mark.parametrize("action", ["rename", "duplicate", "remove"])
def test_a_button_pressed_under_another_accounts_session_calls_no_sheet_deleted(
    window, server, action
):
    """A10, review 1: another teacher signed in in another tab, so the server says 404 for a
    sheet that is still there. Nothing says that it was deleted, and the window goes on as that
    teacher."""
    page, client = window()
    listed(page, server, client)
    other = user()
    sheet(other, [box("a", "text", TEXT)], title="theirs")
    page.on("dialog", lambda d: d.accept("Neu" if d.type == "prompt" else None))
    page.context.clear_cookies()
    cookie = {"name": "session", "value": other.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.evaluate(SEEN)
    page.get_by_role("button", name=ACTIONS[action][0]).click()
    expect(page.locator(".sheets li strong")).to_have_text(["theirs"])
    assert not page.evaluate("window.said")
    expect(page.get_by_role("alert")).to_have_count(0)
    assert titles(client) == ["a"]


@pytest.mark.parametrize("action", ["create", "duplicate"])
def test_a_try_under_way_takes_no_second_press(window, server, action):
    """I1"""
    page, client = window()
    listed(page, server, client)
    held = []

    def came(route):
        if route.request.method == "POST":
            held.append(route)
        else:
            route.continue_()

    page.route(API, came)
    press = page.get_by_role("button", name=ACTIONS[action][0])
    with page.expect_request(lambda r: r.method == "POST"):
        press.click()
    press.click()
    page.evaluate(TURNS)
    assert len(held) == 1
    with page.expect_response(lambda r: r.request.method == "POST"):
        held[0].continue_()
    page.evaluate(TURNS)
    assert len(held) == 1
    assert len(titles(client)) == 2
    expect(page.get_by_role("alert")).to_have_count(0)


def test_the_line_is_told_and_its_try_is_reached_by_the_keys(window, server):
    """I2"""
    page, client = window()
    listed(page, server, client)
    mend = cut(page, 500)
    with failing(page, 500):
        page.get_by_role("button", name="a duplizieren").click()
    again = page.get_by_role("alert").get_by_role("button", name=AGAIN)
    expect(again).to_be_visible()
    mend()
    # Tab goes round the page's buttons and links: the line's is one of them.
    for _ in range(40):
        page.keyboard.press("Tab")
        if again.evaluate("(el) => el === document.activeElement"):
            break
    expect(again).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator(".sheets li")).to_have_count(2)
    expect(page.get_by_role("alert")).to_have_count(0)
    assert titles(client) == ["a", "a (Kopie)"]


def test_the_line_goes_with_a_press_on_close_and_with_the_page(window, server):
    """I4"""
    page, client = window()
    listed(page, server, client)
    cut(page, 500)
    line = page.get_by_role("alert")
    with failing(page, 500):
        page.get_by_role("button", name="a duplizieren").click()
    line.get_by_role("button", name="Schließen").click()
    expect(line).to_have_count(0)
    with failing(page, 500):
        page.get_by_role("button", name="a duplizieren").click()
    expect(line).to_have_count(1)
    page.get_by_role("link", name="Konto").click()
    expect(page.get_by_role("heading", name="Konto")).to_be_visible()
    expect(line).to_have_count(0)
    page.go_back()
    expect(page.locator(".sheets li")).to_have_count(1)
    expect(line).to_have_count(0)
    assert titles(client) == ["a"]


@pytest.mark.parametrize("how", HOWS)
@pytest.mark.parametrize("action", ["logout", "delete"])
def test_signing_out_or_deleting_the_account_that_fails_says_so_and_a_try_does_it(
    window, server, action, how
):
    """A23"""
    page, client = window()
    page.goto(f"{server}/konto")
    expect(page.get_by_role("heading", name="Konto")).to_be_visible()
    if action == "delete":
        page.get_by_role("button", name="Konto löschen …").click()
    label = "Abmelden" if action == "logout" else "Ja, endgültig löschen"
    what = (
        "Abmelden hat nicht geklappt."
        if action == "logout"
        else "Das Konto konnte nicht gelöscht werden."
    )
    mend = cut(page, how)
    with failing(page, how):
        page.get_by_role("button", name=label).click()
    line = page.get_by_role("alert")
    expect(line).to_contain_text(f"{what} {WHY[how]}")
    # The page stands as it stood, and the session is still there.
    expect(page.get_by_role("button", name=label)).to_be_visible()
    assert client.get("/api/me").status_code == 200
    mend()
    line.get_by_role("button", name=AGAIN).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    expect(line).to_have_count(0)
    assert client.get("/api/me").status_code == 401


@pytest.mark.parametrize("how", HOWS)
def test_the_admin_pages_loads_and_links_that_fail_say_so_and_a_try_does_them(admin_page, how):
    """A25"""
    page = admin_page(admin())
    rows = page.locator(".rows li")
    expect(rows).to_have_count(1)
    # The page is left and come back to with the server away: it asks for its two lists anew.
    page.get_by_role("link", name="Konto").click()
    mend = cut(page, how, loads=True)
    page.get_by_role("link", name="Admin").click()
    lines = page.get_by_role("alert")
    expect(lines).to_have_count(2)
    # In the order their answers failed to come.
    users = lines.filter(has_text=f"Die Konten konnten nicht geladen werden. {WHY[how]}")
    folders = f"Die nicht gelöschten Ordner konnten nicht geladen werden. {WHY[how]}"
    expect(users).to_have_count(1)
    expect(lines.filter(has_text=folders)).to_have_count(1)
    expect(rows).to_have_count(0)
    mend()
    with page.expect_response("**/api/admin/users"):
        users.get_by_role("button", name=AGAIN).click()
    expect(rows).to_have_text(["admin@example.com (Admin)Passwort-Link"])
    with page.expect_response("**/api/admin/leftovers") as got:
        lines.get_by_role("button", name=AGAIN).click()
    assert got.value.status == 200
    expect(lines).to_have_count(0)
    links = {
        "Einladung erstellen": ("Die Einladung konnte nicht erstellt werden.", "einladung"),
        "Passwort-Link": ("Der Passwort-Link konnte nicht erstellt werden.", "passwort"),
    }
    for label, (what, path) in links.items():
        mend = cut(page, how)
        with failing(page, how):
            page.get_by_role("button", name=label).click()
        expect(lines).to_contain_text(f"{what} {WHY[how]}")
        expect(page.locator(".link", has_text=f"/{path}/")).to_have_count(0)
        mend()
        lines.get_by_role("button", name=AGAIN).click()
        expect(page.locator(".link")).to_contain_text(f"/{path}/")
        expect(lines).to_have_count(0)
