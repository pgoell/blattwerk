"""A save that fails or never answers is tried again, and the notice names the sheet."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_loading import (
    expect_loading,
    window,  # noqa: F401
)
from test_saves import (
    HOW,
    LEFT,
    NOTICE,
    TO,
    answer,
    change,
    give_up,
    leave,
    nudge,
    run,  # noqa: F401
    start,
    unsaved,
    x_of,
)
from test_stale import (
    STATUS,
    TURNS,
)
from ui import at


@pytest.mark.parametrize("to", TO)
@pytest.mark.parametrize("how", HOW)
def test_the_next_sheet_and_the_list_open_at_once_whatever_the_save_of_the_sheet_left_does(
    run, how, to
):
    """A1: no time has gone by when B, or the list, stands."""
    page, _ = leave(run, how, to)
    if how == "never":
        give_up(run, "a")
        expect(page.locator(NOTICE)).to_have_text(unsaved("a"))
    if to == "sheet":
        run.check()
        # B is saved as ever.
        with page.expect_response(run.gates["b"].answers("PATCH")) as saved:
            run.nudge()
            page.clock.run_for(2000)
        assert saved.value.status == 200
    assert x_of(run, "a") == 15


@pytest.mark.parametrize("to", TO)
@pytest.mark.parametrize("how", HOW)
def test_a_notice_names_the_sheet_whose_save_is_out_from_a_second_on_until_it_lands(run, how, to):
    """A2"""
    page, gate = leave(run, how, to)
    said = page.locator(NOTICE)
    if how == "failed":
        # A save that failed says so at once.
        expect(said).to_have_text(unsaved("a"))
    else:
        page.clock.run_for(999)
        page.evaluate(TURNS)
        expect(said).to_have_count(0)
        page.clock.run_for(1)
        expect(said).to_have_text(unsaved("a"))
    expect(said).to_have_attribute("role", "status")
    if to == "sheet":
        # It lies over the editor's bar, not on it, and B still shows.
        low = said.bounding_box()
        assert low["y"] + low["height"] <= page.locator("main.editor > header").bounding_box()["y"]
        run.check()
    if how == "never":
        give_up(run, "a", out=1000)
        expect(said).to_have_text(unsaved("a"))
    if how != "held":
        # The next try, two seconds after the failure.
        with page.expect_request(gate.asks("PATCH")):
            page.clock.run_for(2000)
        page.evaluate(TURNS)
    answer(run, "a")
    expect(said).to_have_count(0)
    assert x_of(run, "a") == 16


def test_no_notice_stands_on_the_sheet_itself_nor_on_a_loading_page_with_nothing_to_say(run):
    """A2: the loading page stays as its own tests need it."""
    page, _ = start(run)
    change(run)
    page.clock.run_for(5000)
    expect(page.locator(STATUS)).to_have_text("Speichert …")
    expect(page.locator(NOTICE)).to_have_count(0)
    # On B's loading page the notice shows, above the page, and the loading page is whole.
    run.go("b")
    expect(page.locator(NOTICE)).to_have_text(unsaved("a"))
    expect_loading(page)
    answer(run, "a")
    expect(page.locator(NOTICE)).to_have_count(0)
    expect(page.get_by_role("status")).to_have_count(1)
    expect_loading(page)


def test_a_save_with_no_answer_after_20_s_counts_as_failed_and_is_tried_again(run):
    """A3"""
    page, gate = start(run)
    change(run)
    expect(page.locator(STATUS)).to_have_text("Speichert …")
    give_up(run, "a")
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    page.clock.run_for(1999)
    page.evaluate(TURNS)
    assert not gate.saves
    with page.expect_request(gate.asks("PATCH")):
        page.clock.run_for(1)
    page.evaluate(TURNS)
    answer(run, "a")
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16


@pytest.mark.parametrize("gone", [False, True], ids=["editor-open", "editor-gone"])
def test_a_failed_save_is_tried_again_after_2_s_doubling_to_30_s_and_when_the_network_is_back(
    run, gone
):
    """A3, and A8 where the teacher has left the sheet: the tries go on."""
    page, gate = start(run)
    change(run)
    if gone:
        run.go("b")
        run.land("b")
    answer(run, "a", 500)
    for wait in (2, 4, 8, 16, 30, 30):
        page.clock.run_for(wait * 1000 - 1)
        page.evaluate(TURNS)
        assert not gate.saves, wait
        with page.expect_request(gate.asks("PATCH")):
            page.clock.run_for(1)
        page.evaluate(TURNS)
        answer(run, "a", "cut" if wait == 8 else 503)
    assert x_of(run, "a") == 15
    # The network is back: at once, not in half a minute.
    with page.expect_request(gate.asks("PATCH")):
        page.evaluate("dispatchEvent(new Event('online'))")
    page.evaluate(TURNS)
    answer(run, "a")
    assert x_of(run, "a") == 16
    expect(page.locator(NOTICE)).to_have_count(0)
    if not gone:
        expect(page.locator(STATUS)).to_have_text("Gespeichert")
    # Nothing more goes.
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert not gate.saves


def test_a_save_that_fails_after_the_teacher_left_the_sheet_is_tried_again(run):
    """A8"""
    page, gate = leave(run, "failed", "sheet")
    assert x_of(run, "a") == 15
    with page.expect_request(gate.asks("PATCH")) as again:
        page.clock.run_for(2000)
    assert again.value.post_data_json["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.evaluate(TURNS)
    answer(run, "a")
    assert x_of(run, "a") == 16
    assert run.held("a")["version"] == 2
    assert [run.whose(request) for request in run.sent] == ["a", "a"]
    run.check()


@pytest.mark.parametrize("how", ["held", "lost", "timeout", "cut", "never"])
def test_a_sheet_opened_again_before_its_save_landed_shows_the_change_and_never_clashes(run, how):
    """A4, A5: A is left with its save out and opened again. The load holds the old document, and
    the change shows. The next save lands whether the first one's answer came, was lost on a
    broken line or after 20 s with the server holding the save, or the save never arrived."""
    page, gate = start(run)
    was = at(page, "a").evaluate(LEFT)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    assert moved != was
    with page.expect_request(gate.asks("PATCH")):
        run.go("b")
    gate.free = False
    run.go("a", back=True)
    # The server has not heard of the change when it answers the load.
    assert len(gate.saves) == 1
    run.land("a")
    gate.free = True
    expect(at(page, "a")).to_have_css("left", moved)
    if how == "held":
        expect(page.locator(STATUS)).to_have_text("Speichert …")
        answer(run, "a")
    elif how in ("lost", "cut"):
        answer(run, "a", how)
    else:
        give_up(run, "a", arrives=how == "timeout")
    expect(page.locator(STATUS)).to_have_text(
        "Gespeichert" if how == "held" else "Nicht gespeichert"
    )
    assert x_of(run, "a") == (15 if how in ("cut", "never") else 16)
    # The next change. After a failure the save in between goes first, 2 s after it failed; where
    # the server holds that one already it turns this one down, and the editor finds its own
    # document there.
    gate.keep = False
    nudge(run)
    expect(at(page, "a")).not_to_have_css("left", moved)
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.clock.run_for(2000)
        if how in ("lost", "timeout"):
            expect(page.locator(STATUS)).to_have_text("Speichert …")
            page.clock.run_for(2000)
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 17
    version = 3 if how in ("held", "lost", "timeout") else 2
    assert run.held("a")["version"] == version
    for request in run.sent:
        assert run.whose(request) == "a"
