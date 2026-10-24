"""A late answer for the account before, and a 404 that names nobody, drops nothing."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_clash import (
    WAITS,
    loads_of,
    swap,
    x_at,
)
from test_loading import (
    READY,
    window,  # noqa: F401
)
from test_saves import (
    LEFT,
    NOTICE,
    answer,
    asks_me,
    change,
    record,
    run,  # noqa: F401
    start,
    to_list,
    x_of,
)
from test_signed_out import (
    expect_login,
    login,
)
from test_stale import (
    GO,
    STATUS,
    TURNS,
    Gate,
    named,
)
from ui import (
    at,
    pick,
    user,
)


def test_two_answers_served_for_another_account_ask_who_is_signed_in_once(run):
    """Issue #353, I1: the list is B's, and B's sheet is opened and changed before the window
    has heard who is signed in. One request asks, and its answer starts the editor over once,
    for the account is another now: the change shows on, and is saved."""
    page, _ = start(run)
    b = user()
    d = named(b, "d")
    gate = Gate(page, d)
    gate.free = True
    held = []
    page.route("**/api/me", lambda route: held.append(route))
    loads = loads_of(page, gate)
    swap(page, run.server, b)
    to_list(run)
    page.locator(".sheets a").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    pick(page, "d")
    page.keyboard.press("ArrowRight")
    page.evaluate(TURNS)
    moved = at(page, "d").evaluate(LEFT)
    assert len(held) == 1
    with page.expect_response(gate.answers("GET")) as anew:
        held[0].continue_()
    anew.value.finished()
    page.evaluate(TURNS)
    expect(at(page, "d")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_at(b, d) == 16
    assert len(held) == 1
    assert len(loads) == 2


def test_a_late_answer_served_for_the_account_before_leaves_the_editor_as_it_is(run):
    """Issue #353, I1: A's list has no answer yet when B signs in in another tab, and B's sheet
    makes the window B's. Then the list's answer comes, served for A. The window asks who is
    signed in and hears nothing new: the editor does not start over, an undo step stays, and
    the change is saved as ever."""
    page, _ = start(run)
    b = user()
    d = named(b, "d")
    gate = Gate(page, d)
    listed, lists = f"{run.server}/api/sheets", []
    page.route(listed, lambda route: lists.append(route))
    with page.expect_request(listed):
        page.get_by_label("Meine Blätter").click()
    page.evaluate(TURNS)
    late = lists.pop()
    for_a = late.fetch()
    swap(page, run.server, b)
    with page.expect_request(gate.asks("GET")):
        page.evaluate(GO, f"/blatt/{d}")
    page.evaluate(TURNS)
    # The sheet's answer names B: the window asks who, and as B's it asks for the sheet anew.
    with page.expect_request(gate.asks("GET")), page.expect_response("**/api/me") as me:
        gate.loads.pop().continue_()
    me.value.finished()
    page.evaluate(TURNS)
    with page.expect_response(gate.answers("GET")) as anew:
        gate.loads.pop().continue_()
    anew.value.finished()
    page.evaluate(TURNS)
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    pick(page, "d")
    page.keyboard.press("ArrowRight")
    page.evaluate(TURNS)
    moved = at(page, "d").evaluate(LEFT)
    undo = page.get_by_role("button", name="Rückgängig")
    expect(undo).to_be_enabled()
    gate.free = True
    loads = loads_of(page, gate)
    with page.expect_response("**/api/me") as me:
        late.fulfill(response=for_a)
    me.value.finished()
    page.evaluate(TURNS)
    expect(undo).to_be_enabled()
    expect(at(page, "d")).to_have_css("left", moved)
    assert loads == []
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.clock.run_for(2000)
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_at(b, d) == 16
    assert record(page, d) is None
    assert len(run.sent) == 1


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
