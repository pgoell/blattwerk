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
from test_loading import READY, window  # noqa: F401
from test_saves import LEFT, NOTICE, answer, nudge, record, run, start, unsaved, x_of  # noqa: F401
from test_stale import FRAMES, GO, TURNS
from ui import PASSWORD, TEXT, at, box, png, sheet

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
    button = page.get_by_role("button", name="Anmelden")
    button.click()
    if password != PASSWORD:
        return
    # WebKit once left this form standing, the fields filled and no fault said, so the editor
    # never came (shard 19 on the merge of #999). The same test had passed on the commit before.
    # The cause is not proven. The click goes again when the form stays.
    try:
        expect(button).to_be_hidden()
    except AssertionError:
        button.click()


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


TYPED = "Die Lineatur fehlt mir."
PHOTO = {"name": "blatt.png", "mimeType": "image/png", "buffer": png()}


def written(page):
    page.get_by_role("button", name="Feedback").click()
    page.locator("dialog.feedback textarea").fill(TYPED)
    page.locator("dialog.feedback input[type=file]").set_input_files(PHOTO)


def photographed(page):
    page.locator("input[type=file]").set_input_files(PHOTO)
    page.get_by_label("Was ist das?").fill("Mathe Kl. 3")
    page.get_by_label("Was gefällt dir daran?").fill(TYPED)
