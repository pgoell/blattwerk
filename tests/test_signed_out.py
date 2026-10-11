"""A request that finds the session run out brings the login, on the address as it stands (issue
#337): a sheet, the list, the list's buttons, a picture, the PDF. After the login the page asked
for shows, and a change that was unsaved is saved. One teacher's kept change never goes to
another, and an answer about the session before does not sign the new one out. So does every
other call of the app (issue #347): templates, maths, feedback, photos, the admin and the account.

The session runs out when the test takes the cookie away. The cookie is Secure and this server
speaks http, so the login form's own cookie never arrives: the test puts it in by hand.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

import re

import pytest
from playwright.sync_api import expect
from test_admin import admin
from test_loading import READY, window  # noqa: F401
from test_saves import LEFT, NOTICE, answer, nudge, record, run, start, unsaved, x_of  # noqa: F401
from test_stale import FRAMES, GO, STATUS, TURNS, named
from ui import PASSWORD, TEXT, at, box, drop, maths, pick, png, sheet, user

WAITS = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
# Notes a failure page from here on, also one that stands for no longer than a turn.
WATCH = """() => {
    window.failed = false;
    new MutationObserver(() => {
        if (document.querySelector('[role=alert]')) window.failed = true;
    }).observe(document, { subtree: true, childList: true });
}"""


def expect_login(page, address):
    """The login stands on the address, and no failure page stood before it."""
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    expect(page).to_have_url(address)
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_have_count(0)


def expect_sheet(page):
    # Not `expect_ready`: the login stood in the app's frame on the sheet's address.
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(".block[data-id]")).to_have_count(1)


def login(page, server, client, password=PASSWORD):
    """Signs the client's teacher in at the login that stands."""
    if password == PASSWORD:
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(password)
    page.get_by_role("button", name="Anmelden").click()


def listed(page, server, client):
    """The list with one sheet on it. Gives the sheet's address."""
    made = sheet(client, [box("a", "text", TEXT)], title="a")
    page.goto(server)
    expect(page.locator(".sheets li")).to_have_count(1, timeout=10000)
    return f"{server}/blatt/{made['id']}"


@pytest.mark.parametrize("how", ["click", "address", "back"])
def test_a_sheet_asked_for_with_the_session_gone_brings_the_login_and_shows_after_it(
    window, server, how
):
    """A5"""
    page, client = window()
    address = listed(page, server, client)
    if how == "back":
        page.locator(".sheets a").click()
        expect_sheet(page)
        page.go_back()
        expect(page.locator(".sheets li")).to_have_count(1)
    page.evaluate(WATCH)
    page.context.clear_cookies()
    with page.expect_response(address.replace("/blatt/", "/api/sheets/")) as got:
        if how == "click":
            page.locator(".sheets a").click()
        elif how == "address":
            page.evaluate(GO, address)
        else:
            page.go_forward()
    assert got.value.status == 401
    expect_login(page, address)
    assert not page.evaluate("window.failed")
    login(page, server, client)
    expect_sheet(page)
    expect(at(page, "a")).to_contain_text("Hallo")
    expect(page).to_have_url(address)


def test_the_list_asked_for_with_the_session_gone_brings_the_login_and_shows_after_it(
    window, server
):
    """A6"""
    page, client = window()
    page.goto(listed(page, server, client))
    expect_sheet(page)
    page.evaluate(WATCH)
    page.context.clear_cookies()
    with page.expect_response(f"{server}/api/sheets") as got:
        page.get_by_label("Meine Blätter").click()
    assert got.value.status == 401
    expect_login(page, f"{server}/")
    assert not page.evaluate("window.failed")
    login(page, server, client)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page.locator(".sheets li strong")).to_have_text(["a"])


def gone(run, change=True):
    """On A, with a change that is not sent yet, the session runs out. Gives where the block
    shows, and the dialogs the page opens from here on."""
    page, gate = start(run)
    gate.keep = False
    asked = []
    page.on("dialog", lambda dialog: (asked.append(dialog.message), dialog.dismiss()))
    if change:
        nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    page.context.clear_cookies()
    return moved, asked


def back(run, moved, saved=True):
    """After the login A shows as it was left, and the change is saved."""
    page = run.page
    page.clock.resume()
    login(page, run.server, run.client)
    expect_sheet(page)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert x_of(run, "a") == (16 if saved else 15)
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("how", ["drop", "button"])
def test_a_picture_that_finds_the_session_gone_brings_the_login_and_the_change_is_saved_after_it(
    run, how
):
    """A8: no dialog says that the picture could not be uploaded."""
    moved, asked = gone(run)
    page = run.page
    address = f"{run.server}/blatt/{run.ids['a']}"
    with page.expect_response(f"{run.server}/api/uploads") as got:
        if how == "drop":
            held = page.locator('.sheet[data-page="0"]').bounding_box()
            point = held["x"] + held["width"] / 2, held["y"] + held["height"] / 2
            drop(page, *point, ("bild.png", "image/png", png()))
        else:
            file = {"name": "bild.png", "mimeType": "image/png", "buffer": png()}
            page.locator("input[type=file]").set_input_files(file)
    assert got.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    back(run, moved)
    assert asked == []


@pytest.mark.parametrize("change", [True, False], ids=["unsaved", "saved"])
def test_a_pdf_that_finds_the_session_gone_brings_the_login_and_stays_in_the_app(run, change):
    """A9: nothing goes to the PDF's address, and an unsaved change is saved after the login."""
    moved, asked = gone(run, change)
    page = run.page
    address = f"{run.server}/blatt/{run.ids['a']}"
    left = []
    page.on("request", lambda r: "/pdf" in r.url and left.append(r.url))
    page.on("download", lambda download: left.append(download))
    page.on("framenavigated", lambda frame: left.append(frame.url))
    with page.expect_response(f"{run.server}/api/me") as got:
        page.get_by_role("button", name="PDF", exact=True).click()
    assert got.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text([WAITS] if change else [])
    page.evaluate(TURNS)
    assert left == []
    back(run, moved, saved=change)
    assert left == []
    assert asked == []


def test_one_teachers_kept_change_never_goes_to_the_teacher_who_signs_in_at_that_login(run):
    """A10: B signs in at the login A's save brought, on A's sheet. B sees and saves nothing of
    A's, and A gets the change back."""
    moved, _ = gone(run)
    page, gate, a = run.page, run.gates["a"], run.ids["a"]
    address = f"{run.server}/blatt/{a}"
    with page.expect_response(gate.answers("PATCH")) as turned_down:
        page.clock.run_for(2000)
    assert turned_down.value.status == 401
    expect_login(page, address)
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.clock.resume()
    other = user()
    d = named(other, "d")
    asked = []
    page.on("request", lambda r: r.url.endswith(f"/api/sheets/{a}") and asked.append(r.method))
    login(page, run.server, other)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()

    def untouched():
        expect(page.locator(".notice, .clash")).to_have_count(0)
        page.evaluate(FRAMES)
        # The address asks for the sheet once, and is told that it is not there. No save goes.
        assert asked == ["GET"]
        assert len(run.sent) == 1
        assert record(page, a) == kept
        assert x_of(run, "a") == 15

    untouched()
    # A sheet of B's own shows as B left it.
    page.evaluate(GO, f"/blatt/{d}")
    expect_sheet(page)
    expect(at(page, "d")).to_contain_text("Blatt D")
    expect(at(page, "a")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    untouched()
    # B's session runs out, and A signs in on A's sheet.
    page.context.clear_cookies()
    page.evaluate(GO, address)
    expect_login(page, address)
    back(run, moved)


ACTIONS = {
    "create": "Neues Blatt",
    "rename": "a umbenennen",
    "duplicate": "a duplizieren",
    "remove": "a löschen",
}


@pytest.mark.parametrize("action", ACTIONS)
def test_a_button_of_the_list_that_finds_the_session_gone_brings_the_login(window, server, action):
    """I5"""
    page, client = window()
    listed(page, server, client)
    page.on("dialog", lambda dialog: dialog.accept("Neu" if dialog.type == "prompt" else None))
    page.context.clear_cookies()
    with page.expect_response(re.compile(r"/api/sheets")) as got:
        page.get_by_role("button", name=ACTIONS[action]).click()
    assert got.value.status == 401
    assert got.value.request.method != "GET"
    expect_login(page, f"{server}/")
    login(page, server, client)
    expect(page.locator(".sheets li strong")).to_have_text(["a"])


def test_an_answer_about_the_session_before_does_not_sign_the_new_one_out(run):
    """I6: B is asked for and gets no answer, the session runs out, a save of A brings the login
    and the teacher signs in. Then B's first load is answered: the session is gone."""
    gone(run)
    page, gate = run.page, run.gates["b"]
    address = f"{run.server}/blatt/{run.ids['b']}"
    with page.expect_response(run.gates["a"].answers("PATCH")) as turned_down:
        page.evaluate(GO, address)
    assert turned_down.value.status == 401
    expect_login(page, address)
    page.clock.resume()
    with page.expect_request(gate.asks("GET")):
        login(page, run.server, run.client)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    late, now = gate.loads
    with page.expect_response(gate.answers("GET")):
        late.fulfill(status=401)
    page.evaluate(FRAMES)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    now.continue_()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(at(page, "b")).to_contain_text("Blatt B")
    # A's change went with the login.
    expect(page.locator(NOTICE)).to_have_count(0)
    assert x_of(run, "a") == 16


def test_a_save_sent_before_the_login_and_turned_down_after_it_is_tried_again(run):
    """I6: A's save is out with no answer, the session runs out, B's load brings the login and
    the teacher signs in. Then the save is told that the session is gone: no login shows, and
    the saver's next try saves the change with the new session."""
    page, gate = start(run)
    nudge(run)
    with page.expect_request(gate.asks("PATCH")):
        page.clock.run_for(2000)
    page.evaluate(TURNS)
    page.context.clear_cookies()
    run.gates["b"].free = True
    address = f"{run.server}/blatt/{run.ids['b']}"
    with page.expect_response(run.gates["b"].answers("GET")) as got:
        page.evaluate(GO, address)
    assert got.value.status == 401
    expect_login(page, address)
    page.clock.resume()
    login(page, run.server, run.client)
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(NOTICE)).to_have_text(unsaved("a"))
    gate.keep = False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok, timeout=10000) as saved:
        answer(run, "a", 401)
        expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    saved.value.finished()
    expect(page.locator(NOTICE)).to_have_count(0)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    expect(at(page, "b")).to_contain_text("Blatt B")
    assert len(run.sent) == 2
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


def test_a_wrong_password_at_the_login_says_so_and_the_right_one_signs_in(window, server):
    """I8"""
    page, client = window()
    address = listed(page, server, client)
    page.context.clear_cookies()
    page.locator(".sheets a").click()
    expect_login(page, address)
    with page.expect_response(f"{server}/api/login") as got:
        login(page, server, client, "falsch-geheim")
    assert got.value.status == 401
    expect(page.get_by_role("status")).to_have_text("E-Mail oder Passwort stimmt nicht.")
    expect_login(page, address)
    login(page, server, client)
    expect_sheet(page)
    expect(page).to_have_url(address)


# Every other call of the app (issue #347): templates, maths, feedback, photos, the admin page and
# the account page.
SHEET = "the sheet"
TYPED = "Die Lineatur fehlt mir."
PHOTO = {"name": "blatt.png", "mimeType": "image/png", "buffer": png()}
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


def written(page):
    page.get_by_role("button", name="Feedback").click()
    page.locator("dialog.feedback textarea").fill(TYPED)
    page.locator("dialog.feedback input[type=file]").set_input_files(PHOTO)


def photographed(page):
    page.locator("input[type=file]").set_input_files(PHOTO)
    page.get_by_label("Was ist das?").fill("Mathe Kl. 3")
    page.get_by_label("Was gefällt dir daran?").fill(TYPED)


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
