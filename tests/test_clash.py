"""A clash stands until the teacher has chosen (issue #345), and a kept change goes only when its
owner's own session learns that the sheet is gone (issue #346).

In a clash the server holds another device's version, and nothing is sent over it: not after a
reload, a second or a third, not by a tab that shuts, a retry, the app's start or a second tab.
The browser's record keeps the version the change was made on, so each visit reads the clash
anew. And a record is one account's: a 404 that another account's session got says nothing
about the owner's sheet.

Built on test_saves.py: the sheet A, its gate, and a clock that stands until a test lets it run
for a reload or a new tab. The clash comes about in two ways: `left`, a change kept by a tab that
shut, which the next visit finds changed elsewhere, and `clash`, a save turned down in the window.

The docstrings name the lines of the checklist.
"""

# The fixtures `window` and `run` are imported, and each test names one as its argument.
# ruff: noqa: F811

from contextlib import contextmanager

import pytest
from playwright.sync_api import expect
from test_load_fails import ONLINE, expect_failed
from test_loading import READY, window  # noqa: F401
from test_other_version import expect_word, press
from test_saves import (  # noqa: F401
    CHOICES,
    LEFT,
    NOTICE,
    again,
    answer,
    asks_me,
    change,
    clash,
    elsewhere,
    kept_x,
    nudge,
    record,
    run,
    shut,
    start,
    to_list,
    unsaved,
    x_of,
)
from test_signed_out import expect_login, login
from test_stale import FRAMES, GO, STATUS, TURNS, Gate, named
from ui import at, pick, user

from blattwerk import sheets

LOAD, OVER = CHOICES
SAYS = "Dieses Blatt wurde auf einem anderen Gerät geändert."
LISTED = "„a“ wurde auf einem anderen Gerät geändert. Öffne das Blatt, um zu wählen."
WAITS = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
# Notes from here on whether the page said that the sheet is not there, for however short a time.
WATCH = """() => {
    window.missing = false;
    new MutationObserver(() => {
        const said = [...document.querySelectorAll('h1')].map((h) => h.textContent);
        if (said.includes('Blatt nicht gefunden')) window.missing = true;
    }).observe(document, { subtree: true, childList: true });
}"""
# Waits until the browser's record of the sheet holds the block at that x.
KEEPS = """([id, x]) => {
    const kept = JSON.parse(localStorage.getItem('unsaved:' + id));
    return kept?.doc.pages[0].blocks[0].x === x;
}"""
DROPPED = "(id) => localStorage.getItem('unsaved:' + id) === null"


def left(run):
    """A is changed here, the tab shuts with the change kept and unsent, and another device
    moves the block to 40. Gives where the block showed here, and the sheet as the other device
    left it."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    return moved, elsewhere(run, 40)


def safe(run, page, sent, theirs, n=0, x=16, base=None):
    """Nothing went over the other device's sheet: `n` saves were sent so far and none more, the
    server holds the other device's sheet, and the browser the kept change with the version it
    was made on."""
    page.evaluate(TURNS)
    assert len(sent) == n
    assert run.held("a") == theirs
    kept = record(page, run.ids["a"])
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == x
    assert kept["base"] == (base or theirs["version"] - 1)


def stands(run, page, sent, theirs, moved, **more):
    """The clash stands on the page: the banner with both choices, the kept change in the
    editor, the status that says it is not saved, and all of `safe`."""
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    banner = page.locator(".clash")
    expect(banner).to_contain_text(SAYS)
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_enabled()
    expect(banner).not_to_contain_text("Lädt …")
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    safe(run, page, sent, theirs, **more)


def swap(page, server, client):
    """The browser's session becomes the client's, as a login in another tab does it: this
    tab hears nothing of it."""
    page.context.clear_cookies()
    page.context.add_cookies(
        [{"name": "session", "value": client.cookies["session"], "url": server}]
    )


@contextmanager
def reached():
    """Gives the saves of a document that reach the server meanwhile, whoever sent them: one
    sent as a tab goes passes no route and no listener of the test."""
    came, real = [], sheets.touch_stored

    def count(con, sheet_id, user):
        came.append(sheet_id)
        real(con, sheet_id, user)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sheets, "touch_stored", count)
        yield came


def test_a_clash_stands_through_every_reload_and_nothing_is_sent(run):
    """A1, I1, I2: at the first visit, and after a first, a second and a third reload."""
    moved, theirs = left(run)
    page, _, sent = again(run)
    stands(run, page, sent, theirs, moved)
    for _ in range(3):
        page.reload()
        stands(run, page, sent, theirs, moved)


def test_a_clash_that_arose_in_this_window_stands_through_every_reload(run):
    """A2, I2: a save turned down, and then three reloads."""
    page, _ = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    stands(run, page, run.sent, theirs, moved, n=1)
    page.clock.resume()
    for _ in range(3):
        page.reload()
        stands(run, page, run.sent, theirs, moved, n=1)


def test_a_change_made_in_a_clash_is_kept_on_the_version_the_first_one_was_made_on(run):
    """I1: the editor shows it after each reload, and the record still tells the clash."""
    moved, theirs = left(run)
    page, _, sent = again(run)
    page.reload()
    stands(run, page, sent, theirs, moved)
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    further = at(page, "a").evaluate(LEFT)
    assert further != moved
    # The store has it within a second, by the page's own clock.
    page.wait_for_function(KEEPS, arg=[run.ids["a"], 17])
    stands(run, page, sent, theirs, further, x=17)
    for _ in range(2):
        page.reload()
        stands(run, page, sent, theirs, further, x=17)


def test_a_tab_shut_in_a_clash_sends_nothing_and_the_next_visit_shows_the_clash(run):
    """A3: shut and visited twice over. A tab that goes sends what is unsaved on every other
    road, so the server itself is asked what reached it."""
    moved, theirs = left(run)
    with reached() as came:
        for _ in range(2):
            page, _, sent = again(run)
            stands(run, page, sent, theirs, moved)
            # A change in this tab too, so the tab that shuts has one of its own to send.
            pick(page, "a")
            page.keyboard.press("ArrowLeft")
            page.keyboard.press("ArrowRight")
            page.on("dialog", lambda dialog: dialog.accept())
            with page.expect_event("close"):
                page.close(run_before_unload=True)
        page, _, sent = again(run)
        stands(run, page, sent, theirs, moved)
        assert came == []


def test_no_retry_sends_in_a_clash_though_minutes_go_by_and_the_network_is_back(run):
    """A4: a save failed first, so the saver has a try to take up when the network is back. Then
    its next try is turned down, and from there on nothing goes: in this window and after a
    reload."""
    page, gate = start(run)
    change(run)
    answer(run, "a", 500)
    theirs = elsewhere(run, 99)
    with page.expect_request(gate.asks("PATCH")):
        page.clock.run_for(2000)
    page.evaluate(TURNS)
    answer(run, "a")
    moved = at(page, "a").evaluate(LEFT)

    def waits():
        for _ in range(3):
            page.clock.run_for(5 * 60000)
            page.evaluate(ONLINE)
            page.evaluate(TURNS)

    stands(run, page, run.sent, theirs, moved, n=2)
    waits()
    stands(run, page, run.sent, theirs, moved, n=2)
    page.clock.resume()
    for _ in range(2):
        page.reload()
        stands(run, page, run.sent, theirs, moved, n=2)
        waits()
        stands(run, page, run.sent, theirs, moved, n=2)


def test_a_reload_with_the_server_out_of_reach_shows_the_clash_at_the_next_try(run):
    """A5: the load's failure first, with the kept change safe, then the clash, and again after
    the reloads that follow."""
    moved, theirs = left(run)
    page, _, sent = again(run)
    stands(run, page, sent, theirs, moved)
    page.reload()
    stands(run, page, sent, theirs, moved)
    address = f"{run.server}/api/sheets/{run.ids['a']}"

    def cut(route):
        # The line drops for the sheet's loads, the start's and the editor's.
        if route.request.method == "GET":
            route.abort()
        else:
            route.fallback()

    page.route(address, cut)
    page.reload()
    retry = expect_failed(page)
    safe(run, page, sent, theirs)
    page.unroute(address, cut)
    retry.click()
    stands(run, page, sent, theirs, moved)
    page.reload()
    stands(run, page, sent, theirs, moved)


def test_a_save_turned_down_whose_check_of_the_servers_sheet_fails_never_lands(run):
    """A5: the saver cannot tell yet whose document the server holds. It tries again on the
    version it had, is turned down again, and shows the clash once the server says what it
    holds."""
    page, gate = start(run)
    theirs = elsewhere(run, 99)
    change(run)
    moved = at(page, "a").evaluate(LEFT)
    gate.free = False
    with page.expect_request(gate.asks("GET")):
        answer(run, "a")
    page.evaluate(TURNS)
    with page.expect_response(gate.answers("GET")):
        gate.loads.pop().fulfill(status=500)
    banner = page.locator(".clash")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(banner).to_have_count(0)
    safe(run, page, run.sent, theirs, n=1)
    with page.expect_request(gate.asks("PATCH")) as second:
        page.clock.run_for(2000)
    page.evaluate(TURNS)
    assert second.value.post_data_json["version"] == theirs["version"] - 1
    gate.free = True
    answer(run, "a")
    stands(run, page, run.sent, theirs, moved, n=2)
    page.clock.resume()
    for _ in range(2):
        page.reload()
        stands(run, page, run.sent, theirs, moved, n=2)


def test_the_start_on_the_list_sends_no_kept_change_in_a_clash_at_any_start(run):
    """A6, I2: the sheet is not opened. The notice names the clash at the first start, the
    second and the third, and leads to the sheet with both choices."""
    moved, theirs = left(run)
    page, _, sent = again(run, None)
    said = page.locator(NOTICE)
    for start_ in range(3):
        if start_:
            page.reload()
        expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
        expect(said).to_have_text(LISTED)
        safe(run, page, sent, theirs)
    said.get_by_role("link", name="Öffne das Blatt").click()
    stands(run, page, sent, theirs, moved)
    expect(said).to_have_count(0)
    # Back on the list after a reload of the sheet, the notice stands again.
    page.reload()
    stands(run, page, sent, theirs, moved)
    page.goto(run.server)
    expect(said).to_have_text(LISTED)
    safe(run, page, sent, theirs)


@pytest.mark.parametrize("found", ["by-a-choice", "by-a-reload"])
def test_a_clash_stands_after_the_session_ran_out_the_login_and_reloads(run, found):
    """A7: the session is found gone by a choice, or by a reload. After the login the clash
    stands, and after each reload that follows."""
    page, _ = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    address = f"{run.server}/blatt/{run.ids['a']}"
    page.clock.resume()
    page.reload()
    stands(run, page, run.sent, theirs, moved, n=1)
    page.context.clear_cookies()
    if found == "by-a-choice":
        page.locator(".clash").get_by_role("button", name=LOAD).click()
        expect_login(page, address)
        expect(page.locator(NOTICE)).to_have_text(WAITS)
    else:
        page.reload()
        expect_login(page, address)
    safe(run, page, run.sent, theirs, n=1)
    login(page, run.server, run.client)
    stands(run, page, run.sent, theirs, moved, n=1)
    for _ in range(3):
        page.reload()
        stands(run, page, run.sent, theirs, moved, n=1)


@pytest.mark.parametrize("choice", CHOICES)
def test_after_three_reloads_either_choice_still_does_what_it_says(run, choice):
    """A8, I4: the other device saves once more before the press. `Andere Version laden` shows
    that sheet and drops the kept change; `Mit dieser überschreiben` saves this one once, on
    the version the server holds at the press."""
    moved, first = left(run)
    page, _, sent = again(run)
    for _ in range(3):
        page.reload()
        stands(run, page, sent, first, moved)
    theirs = elsewhere(run, 70)
    assert theirs["version"] == first["version"] + 1
    banner = page.locator(".clash")
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)

    def chosen():
        if choice == LOAD:
            expect(at(page, "a")).not_to_have_css("left", moved)
            assert not sent
            assert run.held("a") == theirs
        else:
            expect(at(page, "a")).to_have_css("left", moved)
            assert [save.post_data_json["version"] for save in sent] == [theirs["version"]]
            assert x_of(run, "a") == 16
            assert run.held("a")["version"] == theirs["version"] + 1
        assert record(page, run.ids["a"]) is None

    chosen()
    # The choice holds: the next visit has nothing to ask and nothing to send.
    page.reload()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(banner).to_have_count(0)
    page.evaluate(TURNS)
    chosen()


def test_a_second_tab_on_a_sheet_in_a_clash_shows_the_clash_and_sends_nothing(run):
    """I3: neither tab sends, whichever is loaded anew."""
    page, _ = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    page.clock.resume()
    page.reload()
    stands(run, page, run.sent, theirs, moved, n=1)
    second, _, sent = again(run)
    stands(run, second, sent, theirs, moved)
    second.reload()
    stands(run, second, sent, theirs, moved)
    stands(run, page, run.sent, theirs, moved, n=1)
    page.reload()
    stands(run, page, run.sent, theirs, moved, n=1)
    second.reload()
    stands(run, second, sent, theirs, moved)


@pytest.mark.parametrize("choice", CHOICES)
def test_a_choice_answered_404_under_another_accounts_session_keeps_the_change_for_its_owner(
    run, choice
):
    """A10, I5: another teacher signed in in another tab, so the owner's sheet is not there for
    the session. The login shows, the record stays, and after the owner's login the clash stands
    with both choices, which then do what they say. #353 A5: the 404 names that teacher, and
    nobody is asked who is signed in."""
    page, gate = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    a = run.ids["a"]
    kept = record(page, a)
    page.evaluate(WATCH)
    other, asked = user(), asks_me(page)
    swap(page, run.server, other)
    with page.expect_response(gate.answers("GET")) as got:
        page.locator(".clash").get_by_role("button", name=choice).click()
    assert got.value.status == 404
    assert got.value.headers["x-user"] == str(other.get("/api/me").json()["id"])
    expect_login(page, f"{run.server}/blatt/{a}")
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    assert not page.evaluate("window.missing")
    assert record(page, a) == kept
    safe(run, page, run.sent, theirs, n=1)
    assert asked == []
    # The owner signs in again.
    page.clock.resume()
    login(page, run.server, run.client)
    stands(run, page, run.sent, theirs, moved, n=1)
    assert not page.evaluate("window.missing")
    gate.keep = False
    banner = page.locator(".clash")
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert x_of(run, "a") == (99 if choice == LOAD else 16)
    assert len(run.sent) == (1 if choice == LOAD else 2)
    assert record(page, a) is None


@pytest.mark.parametrize("choice", CHOICES)
def test_a_choice_answered_404_with_no_word_on_who_is_signed_in_says_so_and_stands_again(
    run, choice
):
    """A10, #353 I3: the 404 names nobody, so whose session it came from is not known. Nothing
    is dropped, nobody is signed out and nobody is asked. The banner says that it did not work,
    and the next press goes through."""
    page, gate = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    kept = record(page, run.ids["a"])
    page.evaluate(WATCH)
    asked = asks_me(page)
    load = press(run, choice)
    with page.expect_response(gate.answers("GET")):
        load.fulfill(status=404)
    page.evaluate(TURNS)
    expect_word(page)
    assert not page.evaluate("window.missing")
    assert record(page, run.ids["a"]) == kept
    stands(run, page, run.sent, theirs, moved, n=1)
    assert asked == []
    gate.free, gate.keep = True, False
    banner = page.locator(".clash")
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert x_of(run, "a") == (99 if choice == LOAD else 16)


@pytest.mark.parametrize("whose", ["another-accounts", "the-owners"])
def test_the_start_drops_a_kept_change_whose_sheet_is_gone_only_under_its_owners_session(
    run, whose
):
    """A12: the start asks for the sheet of a kept change, and the answer is a 404. Under the
    owner's own session the sheet was deleted, and the record goes. Where another teacher signed
    in in another tab while the sheet was asked for, the record stays, and the owner's next
    start saves the change. #353 A5: the 404 names whom it was served for, and the tab asks who
    is signed in once, as it starts."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    a = run.ids["a"]
    if whose == "the-owners":
        assert run.client.delete(f"/api/sheets/{a}").status_code == 200
    page = run.page.context.new_page()
    sent, asked = [], asks_me(page)
    page.on("request", lambda r: r.method == "PATCH" and sent.append(r))
    gate = Gate(page, a)
    with page.expect_request(gate.asks("GET")):
        page.goto(run.server)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    if whose == "another-accounts":
        swap(page, run.server, user())
    with page.expect_response(gate.answers("GET")) as got:
        gate.loads.pop().continue_()
    assert got.value.status == 404
    page.evaluate(FRAMES)
    assert not sent
    if whose == "the-owners":
        page.wait_for_function(DROPPED, arg=a)
        assert len(asked) == 1
        return
    assert len(asked) == 1
    assert record(page, a) == kept
    assert x_of(run, "a") == 15
    page.close()
    page, _, sent = again(run, None, client=run.client)
    page.wait_for_function(DROPPED, arg=a)
    assert x_of(run, "a") == 16
    assert len(sent) == 1


def test_another_accounts_record_survives_a_start_a_sheet_opened_and_a_delete_on_the_list(run):
    """A13: the other teacher's start asks for no sheet of the record, the sheet opened shows
    nothing of it, and the delete on the list leaves it, also where it lies under the id of the
    sheet deleted. No sheet id is given twice, so that last one is made up."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    a, other = run.ids["a"], user()
    d = named(other, "d")
    page, _, sent = again(run, None, client=other)
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    assert kept["owner"] == run.client.get("/api/me").json()["id"]
    page.evaluate(f"localStorage.setItem('unsaved:{d}', localStorage.getItem('unsaved:{a}'))")
    asked = []
    of_a_record = (f"/api/sheets/{a}", f"/api/sheets/{d}")
    page.on("request", lambda r: r.url.endswith(of_a_record) and asked.append(r.method))

    def untouched():
        expect(page.locator(".notice, .clash")).to_have_count(0)
        page.evaluate(FRAMES)
        assert not sent
        assert record(page, a) == kept
        assert record(page, d) == kept
        assert x_of(run, "a") == 15

    # The start, with both records there.
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        page.reload()
    listed.value.finished()
    expect(page.locator(".sheets li strong")).to_have_text(["d"])
    untouched()
    assert asked == []
    # The sheet opened.
    page.locator(".sheets a").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(at(page, "d")).to_contain_text("Blatt D")
    expect(at(page, "a")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    untouched()
    assert asked == ["GET"]
    # The delete on the list.
    page.go_back()
    expect(page.locator(".sheets li strong")).to_have_text(["d"])
    page.on("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="d löschen").click()
    expect(page.locator(".sheets li")).to_have_count(0)
    untouched()
    assert asked == ["GET", "DELETE"]


def x_at(client, sheet_id):
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["x"]


@pytest.mark.parametrize("me", ["answers", "fails"])
def test_a_change_kept_by_a_window_that_holds_another_account_carries_the_sheets_owner(run, me):
    """Issue #353, A1, A2, A3, A5: the window holds A, and B signs in in another tab. On the
    list, with no reload, B's sheet is opened and changed while no save lands, and the tab shuts.
    The record names B, as the sheet's answer does, also where the window cannot ask who is
    signed in. A's next start leaves it alone, and B's sends it."""
    page, _ = start(run)
    b = user()
    d = run.ids["d"] = named(b, "d")
    gate = run.gates["d"] = Gate(page, d)
    gate.free = gate.keep = True
    if me == "fails":
        page.route("**/api/me", lambda route: route.fulfill(status=500))
    swap(page, run.server, b)
    to_list(run)
    expect(page.locator(".sheets li strong")).to_have_text(["d"])
    page.locator(".sheets a").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    run.here = {"name": "d", "state": "in"}
    change(run)
    answer(run, "d", 500)
    kept = record(page, d)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    assert kept["owner"] == b.get("/api/me").json()["id"]
    shut(page, 1)
    # A's next start.
    page, _, sent = again(run, None, client=run.client)
    assert record(page, d) == kept
    asked = []
    page.on("request", lambda r: r.url.endswith(f"/api/sheets/{d}") and asked.append(r.method))
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        page.reload()
    listed.value.finished()
    expect(page.locator(".sheets li")).to_have_count(3)
    page.evaluate(FRAMES)
    assert not sent
    assert asked == []
    assert record(page, d) == kept
    assert x_at(b, d) == 15
    page.close()
    # B's next visit.
    page, _, sent = again(run, None, client=b)
    page.wait_for_function(DROPPED, arg=d)
    assert x_at(b, d) == 16
    assert len(sent) == 1


def test_a_window_that_hears_an_answer_served_for_another_account_goes_on_as_that_one(run):
    """Issue #353, I1: B signed in in another tab, and the list this window asks for is B's.
    The window asks who is signed in, once, and goes on as at B's login: no login shows, the
    clipboard is emptied, and A's saver leaves with its change kept, which A's next start saves."""
    page, gate = start(run)
    a, b = run.ids["a"], user()
    named(b, "d")
    page.evaluate("localStorage.setItem('clip', '{}')")
    nudge(run)
    asked = asks_me(page)
    swap(page, run.server, b)
    with page.expect_request(gate.asks("PATCH")), page.expect_response("**/api/me") as me:
        to_list(run)
    me.value.finished()
    page.evaluate(TURNS)
    expect(page.locator(".sheets li strong")).to_have_text(["d"])
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert page.evaluate("localStorage.getItem('clip')") is None
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    assert kept["owner"] == run.client.get("/api/me").json()["id"]
    # The save that went as A's sheet was left is answered under B's session: nobody hears it.
    with page.expect_response(gate.answers("PATCH")) as got:
        gate.saves.pop().continue_()
    assert got.value.status == 404
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    assert record(page, a) == kept
    assert x_of(run, "a") == 15
    assert len(run.sent) == 1
    assert len(asked) == 1
    page.evaluate(GO, "/konto")
    expect(page.get_by_text(f"Angemeldet als {b.get('/api/me').json()['email']}")).to_be_visible()
    # Nothing of B's is unsaved, so the browser has nothing to ask.
    assert shut(page) == []
    page, _, sent = again(run, None, client=run.client)
    page.wait_for_function(DROPPED, arg=a)
    assert x_of(run, "a") == 16
    assert len(sent) == 1


def test_a_save_answered_404_under_another_accounts_session_keeps_the_change_for_its_owner(run):
    """Issue #353, I2, A5: the window stays on A's sheet while B signs in in another tab, and
    A's change is sent. The 404 names B: nothing is dropped, nothing is saved, and nobody is
    asked who is signed in. The login shows, and A's login saves the change."""
    page, gate = start(run)
    a, b = run.ids["a"], user()
    asked = asks_me(page)
    change(run)
    moved = at(page, "a").evaluate(LEFT)
    kept = record(page, a)
    swap(page, run.server, b)
    with page.expect_response(gate.answers("PATCH")) as got:
        gate.saves.pop().continue_()
    assert got.value.status == 404
    assert got.value.headers["x-user"] == str(b.get("/api/me").json()["id"])
    page.evaluate(TURNS)
    expect_login(page, f"{run.server}/blatt/{a}")
    expect(page.locator(NOTICE)).to_have_text(WAITS)
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert record(page, a) == kept
    assert x_of(run, "a") == 15
    assert b.get("/api/sheets").json() == []
    assert len(run.sent) == 1
    assert asked == []
    page.clock.resume()
    gate.keep = False
    login(page, run.server, run.client)
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert x_of(run, "a") == 16
    assert record(page, a) is None


def test_a_save_answered_404_that_names_nobody_drops_nothing_and_is_tried_again(run):
    """Issue #353, I3: whose session the 404 came from is not known. The change stays in the
    editor and in the store, no login shows, and the next try saves it."""
    page, gate = start(run)
    a = run.ids["a"]
    asked = asks_me(page)
    change(run)
    kept = record(page, a)
    answer(run, "a", 404)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    expect(page.get_by_role("button", name="Anmelden")).to_have_count(0)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_have_count(0)
    assert record(page, a) == kept
    assert asked == []
    gate.keep = False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.clock.run_for(2000)
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16
    assert record(page, a) is None
