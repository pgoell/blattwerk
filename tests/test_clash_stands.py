"""A clash stands through reloads, retries, a shut tab and either choice."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_clash import (
    KEEPS,
    LISTED,
    LOAD,
    WAITS,
    left,
    reached,
    safe,
    stands,
)
from test_load_fails import (
    ONLINE,
    expect_failed,
)
from test_loading import (
    READY,
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
    elsewhere,
    record,
    run,  # noqa: F401
    start,
    x_of,
)
from test_signed_out import (
    expect_login,
    login,
)
from test_stale import (
    STATUS,
    TURNS,
)
from ui import (
    at,
    pick,
)


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
