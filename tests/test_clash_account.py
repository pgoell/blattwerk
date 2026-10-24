"""A 404 or a save answered under another account's session says nothing about the owner's sheet."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_clash import (
    DROPPED,
    LOAD,
    WAITS,
    WATCH,
    safe,
    stands,
    swap,
    x_at,
)
from test_loading import (
    READY,
    window,  # noqa: F401
)
from test_other_version import (
    expect_word,
    press,
)
from test_saves import (
    CHOICES,
    LEFT,
    NOTICE,
    again,
    answer,
    asks_me,
    change,
    clash,
    nudge,
    record,
    run,  # noqa: F401
    shut,
    start,
    to_list,
    x_of,
)
from test_signed_out import (
    expect_login,
    login,
)
from test_stale import (
    FRAMES,
    GO,
    STATUS,
    TURNS,
    Gate,
    named,
)
from ui import (
    at,
    reload,
    user,
)


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
def test_the_start_takes_a_kept_changes_sheet_for_deleted_only_under_its_owners_session(run, whose):
    """A12: the start asks for the sheet of a kept change, and the answer is a 404. Under the
    owner's own session the sheet was deleted: the record stays (#360), and a line asks what
    becomes of the change. Where another teacher signed in in another tab while the sheet was
    asked for, the record stays with no such line, and the owner's next start saves the change.
    #353 A5: the 404 names whom it was served for, and the tab asks who is signed in once, as it
    starts."""
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
        said = page.locator(NOTICE)
        expect(said).to_contain_text("„a“ wurde auf einem anderen Gerät gelöscht.")
        assert record(page, a) == kept
        assert len(asked) == 1
        said.page.once("dialog", lambda dialog: dialog.accept())
        said.get_by_role("button", name="Verwerfen").click()
        page.wait_for_function(DROPPED, arg=a)
        assert not sent
        return
    assert len(asked) == 1
    expect(page.locator(NOTICE)).to_have_count(0)
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
    reload(page, f"{run.server}/api/sheets")
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
    reload(page, f"{run.server}/api/sheets")
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
