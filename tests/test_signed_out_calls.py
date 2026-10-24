"""A call other than the sheet that finds the session gone, and what was typed before it.

The helpers live in test_signed_out.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import re

import pytest
from playwright.sync_api import expect
from test_admin import admin
from test_loading import READY, window  # noqa: F401
from test_saves import LEFT, NOTICE, answer, nudge, record, run, start, unsaved, x_of  # noqa: F401
from test_signed_out import (
    TYPED,
    WATCH,
    expect_login,
    expect_sheet,
    login,
    photographed,
    written,
)
from test_stale import FRAMES
from ui import TEXT, box, maths, pick, sheet, user

# Every other call of the app (issue #347): templates, maths, feedback, photos, the admin page and
# the account page.
SHEET = "the sheet"
NO_MATHS = "Die Aufgaben konnten nicht erzeugt werden. Blattomat hat gerade eine Störung."
NO_FEEDBACK = "Das hat nicht geklappt. Dein Feedback ist noch da, versuch es gleich nochmal."
HEADS = {
    "/": "Meine Blätter",
    "/admin": "Admin",
    "/konto": "Konto",
    "/feedback/fotos": "Fotos von Blättern",
}


def click(name):
    return lambda page: page.get_by_role("button", name=name, exact=True).first.click()


def templates(page):
    """The panel of the templates, with a name typed for a new one."""
    page.get_by_role("tab", name="Vorlagen").click()
    page.get_by_label("Name der Vorlage").fill("Neu")


def limits(page):
    pick(page, "a")
    expect(page.locator(".panel").get_by_label("Eine Aufgabe mehr")).to_be_visible()


def to_sheet(page):
    page.locator(".sheets a").click()


def to_admin(page):
    page.get_by_role("link", name="Admin").click()


# Each call: where the teacher starts, what is made ready before the session runs out, the click,
# and the request it sends.
CALLS = {
    "templates load": ("/", None, to_sheet, "GET", "/templates"),
    "template store": (SHEET, templates, click("Dieses Blatt als Vorlage"), "POST", "/templates"),
    "template delete": (
        SHEET,
        templates,
        click("Vorlage Alt löschen"),
        "DELETE",
        r"/templates/\d+",
    ),
    "maths block": (SHEET, None, click("Rechnen"), "POST", "/maths"),
    "maths limit": (SHEET, limits, click("Eine Aufgabe mehr"), "POST", "/maths"),
    "feedback": ("/", written, click("Abschicken"), "POST", "/feedback"),
    "photos": ("/feedback/fotos", photographed, click("Abschicken"), "POST", "/feedback"),
    "admin users": ("/", None, to_admin, "GET", "/admin/users"),
    "admin leftovers": ("/", None, to_admin, "GET", "/admin/leftovers"),
    "admin invite": ("/admin", None, click("Einladung erstellen"), "POST", "/admin/invites"),
    "admin password link": (
        "/admin",
        None,
        click("Passwort-Link"),
        "POST",
        r"/admin/users/\d+/reset",
    ),
    "logout": ("/konto", None, click("Abmelden"), "POST", "/logout"),
    "account delete": (
        "/konto",
        click("Konto löschen …"),
        click("Ja, endgültig löschen"),
        "DELETE",
        "/me",
    ),
}
# The page asks these as it opens, each beside a call that brings the login too. So the session
# stays and this call alone is told that it is gone: once, for the page asks again after the login.
# The click leads to another address, and the login must stand on that one.
ALONE = {"templates load": SHEET, "admin users": "/admin", "admin leftovers": "/admin"}


def tell(page, call, status, **how):
    """The call is answered with the status, whatever the server would say."""
    page.route(re.compile(f"/api{CALLS[call][4]}$"), lambda r: r.fulfill(status=status), **how)


def shown(page, server, address):
    """The page of the address shows."""
    path = address.removeprefix(server)
    if path.startswith("/blatt/"):
        return expect_sheet(page)
    expect(page.get_by_role("heading", name=HEADS[path], exact=True)).to_be_visible(timeout=10000)
    if path == "/admin":
        expect(page.get_by_text("admin@example.com (Admin)")).to_be_visible()


def before(window, server, call):
    """The teacher is where the call is made, with all ready for it. Gives the page, the
    teacher's client, the address the login must stand on, what answers the call, and the alerts
    the page opens from here on."""
    start, ready, _, method, path = CALLS[call]
    on = ALONE.get(call, start)
    page, client = window()
    if "admin" in call:
        client = admin()
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        page.context.clear_cookies()
        page.context.add_cookies([cookie])
    block = box("a", "maths", maths(client)) if "maths" in call else box("a", "text", TEXT)
    made = sheet(client, [block], title="a")
    assert client.post("/api/templates", json={"name": "Alt", "doc": made["doc"]}).is_success
    start, on = (server + (f"/blatt/{made['id']}" if to == SHEET else to) for to in (start, on))
    alerts = []
    page.on("dialog", lambda d: (d.type == "alert" and alerts.append(d.message), d.accept()))
    # A failure nobody caught counts as one: the call's own catch must take the 401.
    page.on("pageerror", lambda error: alerts.append(str(error)))
    if start == server + "/konto":
        # Konto loads its keys and programs after its heading shows. A load still out when the
        # test takes the cookies finds the session gone and brings the login before the call.
        with (
            page.expect_response(re.compile("/api/tokens$")),
            page.expect_response(re.compile("/api/connections$")),
        ):
            page.goto(start)
    else:
        page.goto(start)
    shown(page, server, start)
    if ready:
        ready(page)
    page.evaluate(WATCH)

    def answers(response):
        return response.request.method == method and re.search(f"/api{path}$", response.url)

    return page, client, on, answers, alerts


@pytest.mark.parametrize("call", CALLS)
def test_a_call_that_finds_the_session_gone_brings_the_login_and_its_page_shows_after_it(
    window, server, call
):
    """A17: no alert and no failure page stand before the login."""
    page, client, on, answers, alerts = before(window, server, call)
    if call in ALONE:
        tell(page, call, 401, times=1)
    else:
        page.context.clear_cookies()
    with page.expect_response(answers) as got:
        CALLS[call][2](page)
    # The server signs out whoever asks, also who has no session.
    assert got.value.status == (200 if call == "logout" else 401)
    expect_login(page, on)
    assert not page.evaluate("window.failed")
    assert alerts == []
    login(page, server, client)
    shown(page, server, on)
    expect(page).to_have_url(on)
    assert alerts == []


@pytest.mark.parametrize("who", ["same", "other"])
@pytest.mark.parametrize("call", ["feedback", "photos"])
def test_what_was_entered_when_the_session_ran_out_waits_for_its_teacher_and_nobody_else(
    window, server, call, who
):
    """I6: the login takes the form away. After it the teacher finds the text and the picture
    again, on the photos' page at once and in the feedback form opened again, and sends them;
    another teacher who signs in there finds an empty form."""
    page, client, on, answers, _ = before(window, server, call)
    page.context.clear_cookies()
    with page.expect_response(answers) as got:
        click("Abschicken")(page)
    assert got.value.status == 401
    expect_login(page, on)
    login(page, server, client if who == "same" else user())
    if call == "feedback":
        click("Feedback")(page)
    form = page.locator("dialog.feedback" if call == "feedback" else "main form")

    def holds(text, pictures):
        expect(form.locator("textarea")).to_have_value(text)
        expect(form.locator("figure")).to_have_count(pictures)
        if call == "photos":
            expect(form.get_by_label("Was ist das?")).to_have_value(text and "Mathe Kl. 3")

    if who == "other":
        return holds("", 0)
    holds(TYPED, 1)
    with page.expect_response(answers) as got:
        click("Abschicken")(page)
    assert got.value.ok
    expect(form.get_by_role("status")).to_contain_text("Danke! Ist angekommen.")
    holds("", 0)


@pytest.mark.parametrize("call", ["maths block", "maths limit", "feedback"])
def test_a_call_that_fails_for_another_reason_says_so_as_before_and_brings_no_login(
    window, server, call
):
    """I7"""
    page, _, on, answers, alerts = before(window, server, call)
    tell(page, call, 500)
    with page.expect_response(answers) as got:
        CALLS[call][2](page)
    assert got.value.status == 500
    if call in ("maths block", "maths limit"):
        # Since #363 a line above the page says so, and no box of the browser.
        expect(page.locator(".notice.fault")).to_contain_text(NO_MATHS)
        expect(page.locator(".block[data-id]")).to_have_count(1)
        assert alerts == []
    else:
        form = page.locator("dialog.feedback")
        expect(form.get_by_role("status")).to_have_text(NO_FEEDBACK)
        expect(form.locator("textarea")).to_have_value(TYPED)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    expect(page).to_have_url(on)


def test_templates_asked_for_before_a_login_and_turned_down_after_it_sign_nobody_out(
    window, server
):
    """I8: the sheet's templates get no answer, the session runs out, the list brings the login
    and the teacher signs in. Then the templates are answered: the session is gone."""
    page, client, _, answers, _ = before(window, server, "templates load")
    held = []
    page.route(re.compile("/api/templates$"), lambda route: held.append(route))
    with page.expect_request(re.compile("/api/templates$")):
        to_sheet(page)
    expect_sheet(page)
    page.context.clear_cookies()
    with page.expect_response(f"{server}/api/sheets") as got:
        page.get_by_label("Meine Blätter").click()
    assert got.value.status == 401
    expect_login(page, f"{server}/")
    login(page, server, client)
    shown(page, server, f"{server}/")
    with page.expect_response(answers) as late:
        held[0].fulfill(status=401)
    assert late.value.status == 401
    page.evaluate(FRAMES)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    shown(page, server, f"{server}/")
