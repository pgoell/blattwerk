"""A kept change that meets another version, a deleted sheet or a session that ran out."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from contextlib import suppress

import pytest
from playwright.sync_api import (
    Error,
    expect,
)
from test_loading import (
    READY,
    expect_ready,
    window,  # noqa: F401
)
from test_saves import (
    CHOICES,
    LEFT,
    NOTICE,
    again,
    answer,
    change,
    clash,
    down,
    elsewhere,
    give_up,
    kept_x,
    let_go,
    nudge,
    record,
    run,  # noqa: F401
    shut,
    start,
    unsaved,
    x_of,
)
from test_stale import (
    STATUS,
    TURNS,
)
from ui import (
    PASSWORD,
    at,
)


@pytest.mark.parametrize("state", ["held", "failed", "clash"])
def test_a_change_is_in_the_browsers_store_within_a_second_whatever_the_saver_does(run, state):
    """Review 1: also while a save is out, after one failed, and while a clash stands. A saver
    stopped by a session that ran out has no editor: the login stands in its place."""
    page, _ = start(run)
    if state == "clash":
        clash(run)
    else:
        change(run)
    if state == "failed":
        answer(run, "a", 500)
    assert kept_x(page, run) == 16
    nudge(run)
    page.clock.run_for(999)
    page.evaluate(TURNS)
    assert kept_x(page, run) == 16
    page.clock.run_for(1)
    page.evaluate(TURNS)
    assert kept_x(page, run) == 17


def test_a_save_given_up_that_arrives_after_a_reload_is_known_as_this_browsers_own(run):
    """Review 2: save X gets no answer for 20 s, change Y goes out, the tab is loaded anew, and X
    reaches the server before the new tab's Y: no banner, and the server ends with Y."""
    page, gate = start(run)
    first = change(run).post_data_json
    give_up(run, "a")
    nudge(run)
    with page.expect_request(gate.asks("PATCH")):
        page.clock.run_for(2000)
    page.evaluate(TURNS)
    assert record(page, run.ids["a"])["sent"]
    page.clock.resume()
    # No save of the tab that goes reaches the server.
    with down():
        page.reload()
        expect_ready(page, 1)
        expect(page.locator(STATUS)).to_have_text("Speichert …")
    assert x_of(run, "a") == 15
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=first).status_code == 200
    assert let_go(page, gate).status == 409
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 17
    assert run.held("a")["version"] == 3


def test_overwriting_sends_what_the_editor_shows_though_it_is_back_at_what_was_saved(run):
    """Review 3: a change, undone while its save is out; the save is turned down. While the
    clash stands the sheet is not saved, and `Mit dieser überschreiben` sends it."""
    page, gate = start(run)
    change(run)
    page.get_by_role("button", name="Rückgängig").click()
    page.evaluate(TURNS)
    elsewhere(run, 99)
    answer(run, "a")
    banner = page.locator(".clash")
    expect(banner).to_be_visible()
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    assert kept_x(page, run) == 15
    gate.keep = False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        banner.get_by_role("button", name="Mit dieser überschreiben").click()
    saved.value.finished()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 15
    assert run.held("a")["version"] == 3
    assert record(page, run.ids["a"]) is None


def test_a_sheet_deleted_on_the_list_takes_its_clash_notice_and_its_kept_change_along(run):
    """Review 4"""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    elsewhere(run, 40)
    page, _, _ = again(run, None)
    expect(page.locator(NOTICE)).to_contain_text("wurde auf einem anderen Gerät geändert")
    page.on("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name="a löschen").click()
    expect(page.locator(".sheets li")).to_have_count(2)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert record(page, run.ids["a"]) is None


def test_overwriting_that_cannot_ask_the_server_leaves_the_banner_for_another_try(run):
    """Review 5"""
    page, gate = start(run)
    clash(run)
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    banner = page.locator(".clash")
    gate.free = False
    with page.expect_response(gate.answers("GET")):
        banner.get_by_role("button", name="Mit dieser überschreiben").click()
        page.evaluate(TURNS)
        gate.loads.pop().fulfill(status=500)
    page.evaluate(TURNS)
    expect(banner).to_be_visible()
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    assert not errors
    assert len(run.sent) == 1
    # The network is back.
    gate.free, gate.keep = True, False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        banner.get_by_role("button", name="Mit dieser überschreiben").click()
    saved.value.finished()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16


def test_the_other_version_that_answers_after_the_teacher_overwrote_it_changes_nothing(run):
    """Review 6: `Andere Version laden`, its answer held, then `Mit dieser überschreiben`. While
    the load is under way neither choice takes a press (#338), so it is given up first."""
    page, gate = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    banner = page.locator(".clash")
    gate.free = False
    with page.expect_request(gate.asks("GET")):
        banner.get_by_role("button", name="Andere Version laden").click()
    page.evaluate(TURNS)
    late = gate.loads.pop()
    page.clock.run_for(20000)
    gate.free, gate.keep = True, False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        banner.get_by_role("button", name="Mit dieser überschreiben").click()
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    # The answer to the first press, as the server stood then. Where the browser has let the
    # request go, there is no way left for it.
    with suppress(Error):
        late.fulfill(json=theirs)
    page.evaluate(TURNS)
    expect(at(page, "a")).to_have_css("left", moved)
    assert x_of(run, "a") == 16
    with page.expect_response(gate.answers("PATCH")) as next_save:
        nudge(run)
        page.clock.run_for(2000)
    assert next_save.value.status == 200
    expect(banner).to_have_count(0)
    assert x_of(run, "a") == 17


def test_an_undone_change_whose_save_arrives_after_a_reload_is_undone_on_the_server_too(run):
    """Second review 1: the save of a change gets no answer for 20 s, the teacher undoes the
    change, the tab is loaded anew, and then that save reaches the server. The editor's
    document is sent again, as the tab before would have: the server ends with what shows."""
    page, gate = start(run)
    first = change(run).post_data_json
    give_up(run, "a")
    page.get_by_role("button", name="Rückgängig").click()
    page.evaluate(TURNS)
    page.clock.run_for(1000)
    page.evaluate(TURNS)
    kept = record(page, run.ids["a"])
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 15
    assert [doc["pages"][0]["blocks"][0]["x"] for doc in kept["sent"]] == [16]
    page.clock.resume()
    with down():
        page.reload()
        expect_ready(page, 1)
        expect(page.locator(STATUS)).to_have_text("Speichert …")
    assert x_of(run, "a") == 15
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=first).status_code == 200
    assert let_go(page, gate).status == 409
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 15
    assert run.held("a")["version"] == 3
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("choice", CHOICES)
def test_a_clash_whose_sheet_was_deleted_elsewhere_ends_in_the_deleted_sheets_choice(run, choice):
    """Second review 2, and #360 A9: either choice finds the sheet gone. The clash is over, the
    change stays in the editor and in the store, and the banner asks what becomes of it."""
    page, _ = start(run)
    clash(run)
    moved = at(page, "a").evaluate(LEFT)
    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200
    banner = page.locator(".clash")
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_contain_text("Dieses Blatt wurde auf einem anderen Gerät gelöscht.")
    expect(banner).to_have_count(1)
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_have_count(0)
    expect(banner.get_by_role("button", name="Als neues Blatt behalten")).to_be_enabled()
    expect(banner).not_to_contain_text("Lädt …")
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_have_count(0)
    expect(at(page, "a")).to_have_css("left", moved)
    assert kept_x(page, run) == 16
    assert len(run.sent) == 1
    banner.page.once("dialog", lambda dialog: dialog.accept())
    banner.get_by_role("button", name="Verwerfen").click()
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    expect(page.locator(".sheets li")).to_have_count(2)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert record(page, run.ids["a"]) is None
    assert shut(page) == []


@pytest.mark.parametrize("choice", CHOICES)
def test_a_clash_with_the_session_gone_brings_the_login_and_stands_again_after_it(run, choice):
    """Second review 3"""
    page, _ = start(run)
    clash(run)
    moved = at(page, "a").evaluate(LEFT)
    email = run.client.get("/api/me").json()["email"]
    page.context.clear_cookies()
    page.locator(".clash").get_by_role("button", name=choice).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    said = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
    expect(page.locator(NOTICE)).to_have_text(said)
    assert kept_x(page, run) == 16
    page.clock.resume()
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"name": "session", "value": run.client.cookies["session"], "url": run.server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    banner = page.locator(".clash")
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_visible()
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    assert x_of(run, "a") == 99
    assert len(run.sent) == 1
