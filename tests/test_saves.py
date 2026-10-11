"""A sheet's saver outlives its editor (issues #331, #329, #330): no load waits for a save, a save
that fails or never answers is tried again, and a change the server never got lies in the
browser's store until it is saved, on this visit or the next.

Built on test_stale.py: sheets A, B and C, each with one block that names it, and a gate at each
that holds its loads and its saves. Where time counts the page's clock stands and the test moves
it: 2 s from a change to its save, 20 s until a save with no answer is given up, 2 s doubling to
30 s between tries, 1 s until the notice.

The docstrings name the lines of the checklist.
"""

import json
import re
import threading
from contextlib import ExitStack, contextmanager

import pytest
from fastapi import HTTPException
from playwright.sync_api import expect
from test_loading import READY, expect_loading, expect_ready, window  # noqa: F401
from test_stale import GO, KEPT, STATUS, TURNS, Gate, Run, blocks, named
from ui import PASSWORD, TEXT, at, box, user

from blattwerk import sheets

NOTICE = "#root > .notice"
LEFT = "el => getComputedStyle(el).left"
# What a browser asks before a tab with an unsaved change shuts.
ASKS = ["beforeunload"]


def unsaved(name, then="Blattomat versucht es weiter."):
    return f"Die letzte Änderung an „{name}“ ist noch nicht gespeichert. {then}"


@pytest.fixture
def run(window, server):  # noqa: F811
    """On C, with a clock that stands."""
    page, client = window()
    return Run(page, client, server, clock=True)


def start(run, name="a"):
    """Opens the sheet. From then on its loads pass, and its saves are held."""
    run.go(name)
    run.land(name)
    run.gates[name].free = run.gates[name].keep = True
    return run.page, run.gates[name]


def nudge(run):
    """An unsaved change, which the saver has heard of."""
    run.nudge()
    run.page.evaluate(TURNS)


def change(run):
    """A change whose save has gone out, two seconds later. Gives that save."""
    gate = run.gates[run.here["name"]]
    nudge(run)
    with run.page.expect_request(gate.asks("PATCH")) as sent:
        run.page.clock.run_for(2000)
    run.page.evaluate(TURNS)
    return sent.value


def answer(run, name, how="ok"):
    """Answers the sheet's save that is held: "ok", as the server does; a status the test makes
    up; "lost", the server takes the save and the browser hears of a broken line; "cut", the
    save never arrives."""
    page, gate = run.page, run.gates[name]
    route = gate.saves.pop(0)
    if how in ("lost", "cut"):
        with page.expect_event("requestfailed", gate.asks("PATCH")):
            if how == "lost":
                assert route.fetch().status == 200
            route.abort()
    else:
        with page.expect_response(gate.answers("PATCH")) as got:
            if how == "ok":
                route.continue_()
            else:
                route.fulfill(status=how)
        if how == "ok":
            got.value.finished()
    page.evaluate(TURNS)


def give_up(run, name, arrives=False, out=0):
    """The sheet's save that is held gets no answer, and 20 s go by since it went, `out` ms of
    them already. With `arrives` the server took it."""
    page, gate = run.page, run.gates[name]
    route = gate.saves.pop(0)
    if arrives:
        assert route.fetch().status == 200
    page.clock.run_for(19999 - out)
    page.evaluate(TURNS)
    assert not route.request.failure
    # The page gives the save up by itself. WebKit tells the test nothing of that where the save
    # was one that may outlive the window: what follows shows it.
    page.clock.run_for(1)
    page.evaluate(TURNS)


def x_of(run, name):
    return run.held(name)["doc"]["pages"][0]["blocks"][0]["x"]


def to_list(run):
    """On to the list of sheets, which is asked for at once."""
    with run.page.expect_response(f"{run.server}/api/sheets") as got:
        run.page.get_by_label("Meine Blätter").click()
    got.value.finished()
    expect(run.page.get_by_role("heading", name="Meine Blätter")).to_be_visible()


def leave(run, how, to):
    """Changes A and goes on at once, so its save goes out as the teacher leaves: held, failed
    with a 500, or never answered. The next sheet, or the list, opens with the clock standing."""
    page, gate = start(run)
    nudge(run)
    with page.expect_request(gate.asks("PATCH")):
        if to == "sheet":
            run.go("b")
            run.land("b")
        else:
            to_list(run)
    page.evaluate(TURNS)
    if to == "list":
        expect(page.locator(".sheets li")).to_have_count(3)
    if how == "failed":
        answer(run, "a", 500)
    return page, gate


HOW = ["held", "failed", "never"]
TO = ["sheet", "list"]


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


@contextmanager
def down(saves=0):
    """The server takes no save meanwhile, and so many reach it in vain before it is back.

    The server's own doing: a save sent as a tab goes outlives the tab, and no route of the test
    holds it then.
    """
    came = threading.Semaphore(0)

    def refuse(*_):
        came.release()
        raise HTTPException(503)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sheets, "touch_stored", refuse)
        yield
        for _ in range(saves):
            assert came.acquire(timeout=5)


@contextmanager
def stalled():
    """The server takes a save and does not answer it: under way for good, with no route of the
    test in between. Gives what tells that a save has reached it. In the end it takes none."""
    came, over = threading.Semaphore(0), threading.Event()

    def stall(*_):
        came.release()
        over.wait(30)
        raise HTTPException(503)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sheets, "touch_stored", stall)
        try:
            yield came
        finally:
            over.set()


def shut(page, saves=0, gates=False):
    """Shuts the tab as a teacher does, with a server that takes none of the `saves` the tab
    sends as it goes. Gives what the browser asked first, each answered yes."""
    asked = []
    page.on("dialog", lambda dialog: (asked.append(dialog.type), dialog.accept()))
    # A save sent as the tab goes passes no gate: whether one that a gate holds dies with the tab
    # or goes on is the browser's to say. With `gates` they stay, for a save they hold already.
    if not gates:
        page.unroute_all()
    # The clock is the browser's, and runs again for the next visit: WebKit has none to set on a
    # tab that is on no address yet.
    page.clock.resume()
    with down(saves), page.expect_event("close"):
        page.close(run_before_unload=True)
    return asked


def again(run, name="a", keep=False, client=None):
    """The next visit: a new tab of the same browser on the sheet, or with no name on the list.
    Gives the tab, the sheet's gate there, which holds no load, and the saves the tab sends."""
    context = run.page.context
    if client:
        context.clear_cookies()
        cookie = {"name": "session", "value": client.cookies["session"], "url": run.server}
        context.add_cookies([cookie])
    page = context.new_page()
    sent = []
    page.on("request", lambda r: r.method == "PATCH" and sent.append(r))
    if not name:
        page.goto(run.server)
        expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
        return page, None, sent
    gate = Gate(page, run.ids[name])
    gate.free, gate.keep = True, keep
    page.goto(f"{run.server}/blatt/{run.ids[name]}")
    return page, gate, sent


def record(page, sheet_id):
    """What the browser keeps of the sheet's unsaved change."""
    return page.evaluate("(id) => JSON.parse(localStorage.getItem('unsaved:' + id))", sheet_id)


def let_go(page, gate):
    """Lets the sheet's last held save reach the server, and waits for the answer."""
    gate.keep = False
    with page.expect_response(gate.answers("PATCH")) as saved:
        gate.saves.pop().continue_()
    saved.value.finished()
    return saved.value


@pytest.mark.parametrize("arrived", [False, True], ids=["save-never-arrived", "save-arrived"])
def test_a_tab_shut_with_a_save_under_way_keeps_the_newer_change_for_the_next_visit(run, arrived):
    """A6, I3: the change behind the save under way is not sent beside it. The browser keeps it,
    and the next visit shows and saves it, whether the save under way arrived or not."""
    page, gate = start(run)
    with ExitStack() as server:
        if arrived:
            change(run)
            assert gate.saves.pop().fetch().status == 200
        else:
            came = server.enter_context(stalled())
            gate.keep = False
            change(run)
            assert came.acquire(timeout=5)
        nudge(run)
        moved = at(page, "a").evaluate(LEFT)
        asked = shut(page, gates=arrived)
    assert asked == ASKS
    assert [run.whose(request) for request in run.sent] == ["a"]
    assert x_of(run, "a") == (16 if arrived else 15)
    page, gate, sent = again(run, keep=True)
    expect_ready(page, 1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Speichert …")
    assert let_go(page, gate).status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash")).to_have_count(0)
    assert x_of(run, "a") == 17
    assert record(page, run.ids["a"]) is None
    assert len(sent) == 1


@pytest.mark.parametrize("how", ["reload", "shut"])
def test_a_change_whose_save_failed_is_saved_on_the_next_visit(run, how):
    """A7"""
    page, gate = start(run)
    change(run)
    answer(run, "a", 500)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    moved = at(page, "a").evaluate(LEFT)
    assert record(page, run.ids["a"])["base"] == 1
    # The tab tries once more as it goes, and the next visit tries at once: both in vain.
    gate.keep = False
    with down(2):
        if how == "reload":
            page.clock.resume()
            page.reload()
        else:
            shut(page)
            page, gate, _ = again(run)
        expect_ready(page, 1)
        expect(at(page, "a")).to_have_css("left", moved)
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
        assert x_of(run, "a") == 15
    # The server is back.
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.evaluate("dispatchEvent(new Event('online'))")
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


def test_a_large_sheets_last_change_is_saved_on_the_next_visit(run):
    """A7: the browser sends no save over 64 KiB from a tab that shuts."""
    was = run.held("a")
    heavy = [box(f"x{n}", "text", {**TEXT, "text": "schwer " * 20}) for n in range(300)]
    doc = {**was["doc"], "pages": [*was["doc"]["pages"], {"blocks": heavy}]}
    assert len(json.dumps(doc)) > 64 * 1024
    large = {"doc": doc, "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=large).status_code == 200
    page, gate = start(run)
    page.evaluate(KEPT)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    assert page.evaluate("window.kept") == []
    # Whether that save leaves the tab at all is the browser's to say: the server is down until
    # the next visit stands, so it is surely not what saves the change.
    with down():
        shut(page)
        page, gate, _ = again(run, keep=True)
        expect_ready(page, 301)
        expect(at(page, "a")).to_have_css("left", moved)
        expect(page.locator(STATUS)).to_have_text("Speichert …")
        assert x_of(run, "a") == 15
    assert let_go(page, gate).status == 200
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


@pytest.mark.parametrize("choice", ["Andere Version laden", "Mit dieser überschreiben"])
def test_a_kept_change_of_a_sheet_changed_elsewhere_asks_which_version_stays(run, choice):
    """I1: nothing is overwritten unasked."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    # Another device moves the block far to the right meanwhile.
    was = run.held("a")
    was["doc"]["pages"][0]["blocks"][0]["x"] = 40
    other = {"doc": was["doc"], "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    page, _, sent = again(run)
    expect_ready(page, 1)
    banner = page.locator(".clash")
    expect(banner).to_contain_text("Dieses Blatt wurde auf einem anderen Gerät geändert.")
    for name in ("Andere Version laden", "Mit dieser überschreiben"):
        expect(banner.get_by_role("button", name=name)).to_be_visible()
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    banner.get_by_role("button", name=choice).click()
    expect(banner).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    if choice == "Andere Version laden":
        expect(at(page, "a")).not_to_have_css("left", moved)
        assert not sent
    else:
        expect(at(page, "a")).to_have_css("left", moved)
    assert x_of(run, "a") == (40 if choice == "Andere Version laden" else 16)
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_belongs_to_its_account(run):
    """I2: another account in the same browser neither sees nor saves it, and its owner still
    gets it later."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    a = run.ids["a"]
    other = user()
    d = named(other, "d")
    run.ids["d"] = d
    # The owner's sheet is not there for the other account.
    page, _, sent = again(run, client=other)
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    kept = record(page, a)
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    # Nor does the record show on a sheet of the other account, should it lie under that one's id.
    page.evaluate(f"localStorage.setItem('unsaved:{d}', localStorage.getItem('unsaved:{a}'))")
    page.close()
    page, _, sent = again(run, "d")
    expect_ready(page, 1)
    expect(at(page, "d")).to_contain_text("Blatt D")
    expect(at(page, "a")).to_have_count(0)
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    expect(page.locator(".clash, .notice")).to_have_count(0)
    page.evaluate(TURNS)
    assert not sent
    assert record(page, a) == kept
    assert record(page, d) == kept
    assert blocks(other.get(f"/api/sheets/{d}").json()["doc"]) == [("d", "Blatt D")]
    assert x_of(run, "a") == 15
    page.close()
    # The owner comes back.
    page, _, sent = again(run, client=run.client)
    expect_ready(page, 1)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    assert x_of(run, "a") == 16
    assert record(page, a) is None


def test_a_changed_title_is_kept_and_tried_again_like_a_changed_sheet(run):
    """I4"""
    page, gate = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    page.evaluate(TURNS)
    for how in (500, "cut"):
        with page.expect_request(gate.asks("PATCH")) as sent:
            page.clock.run_for(2000)
        assert sent.value.post_data_json["title"] == "Neu"
        page.evaluate(TURNS)
        answer(run, "a", how)
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    assert record(page, run.ids["a"])["title"] == "Neu"
    assert run.held("a")["title"] == "a"
    page.clock.resume()
    gate.keep = False
    with down(2):
        page.reload()
        expect_ready(page, 1)
        expect(page.get_by_label("Titel", exact=True)).to_have_value("Neu")
        expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        page.evaluate("dispatchEvent(new Event('online'))")
    assert saved.value.request.post_data_json["title"] == "Neu"
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert run.held("a")["title"] == "Neu"
    assert record(page, run.ids["a"]) is None


def test_the_browser_asks_before_the_tab_shuts_while_a_change_is_unsaved(run):
    """A9"""
    page, _ = start(run)
    nudge(run)
    assert shut(page, 1) == ASKS


def test_the_browser_does_not_ask_when_all_is_saved(run):
    """A9"""
    page, gate = start(run)
    gate.keep = False
    with page.expect_response(gate.answers("PATCH")) as saved:
        nudge(run)
        page.clock.run_for(2000)
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    assert shut(page) == []
    assert x_of(run, "a") == 16


def test_a_sheet_deleted_meanwhile_drops_its_kept_change_and_its_notice(run):
    """I5"""
    page, gate = leave(run, "held", "sheet")
    page.clock.run_for(1000)
    expect(page.locator(NOTICE)).to_have_text(unsaved("a"))
    assert record(page, run.ids["a"])
    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200
    with page.expect_response("**/api/me"):
        answer(run, "a")
    expect(page.locator(NOTICE)).to_have_count(0)
    assert record(page, run.ids["a"]) is None
    # Nothing more is tried, and the app goes on.
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert not gate.saves
    assert [run.whose(request) for request in run.sent] == ["a"]
    run.check()
    to_list(run)
    expect(page.locator(".sheets li")).to_have_count(2)


def test_pdf_goes_on_once_a_save_that_never_answers_is_given_up(run):
    """I6"""
    page, gate = start(run)
    nudge(run)
    got, asked = [], []
    page.on("download", lambda download: got.append(download))
    page.on("dialog", lambda dialog: (asked.append(dialog.type), dialog.accept()))
    with page.expect_request(gate.asks("PATCH")):
        page.get_by_role("button", name="PDF", exact=True).click()
    page.evaluate(TURNS)
    gate.saves.pop()
    page.clock.run_for(19999)
    page.evaluate(TURNS)
    assert not got
    with page.expect_download(timeout=20000) as download:
        page.clock.run_for(1)
    assert download.value.suggested_filename == "a.pdf"
    # A download leaves the page where it is: the browser has nothing to ask.
    assert asked == []
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")


def test_the_list_shows_a_sheet_as_it_was_left_once_its_late_save_lands(run):
    """I7"""
    page, gate = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    page.evaluate(TURNS)
    with page.expect_request(gate.asks("PATCH")):
        to_list(run)
    names = page.locator(".sheets li strong")
    expect(names).to_have_text(["c", "b", "a"])
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        answer(run, "a")
    listed.value.finished()
    expect(names.filter(has_text="Neu")).to_have_count(1)
    expect(names.filter(has_text=re.compile("^a$"))).to_have_count(0)


@pytest.mark.parametrize("reload", [False, True], ids=["at-once", "after-a-reload"])
def test_a_change_made_when_the_session_ran_out_is_kept_and_saved_after_the_login(run, reload):
    """I8: the save that finds the session gone brings the login, which says what waits; after
    the login the change is saved, with no reload, and after one too."""
    page, gate = start(run)
    gate.keep = False
    email = run.client.get("/api/me").json()["email"]
    page.context.clear_cookies()
    with page.expect_response(gate.answers("PATCH")) as turned_down:
        nudge(run)
        moved = at(page, "a").evaluate(LEFT)
        page.clock.run_for(2000)
    assert turned_down.value.status == 401
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    said = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
    expect(page.locator(NOTICE)).to_have_text(said)
    # Nothing is tried while nobody is signed in.
    page.clock.run_for(60000)
    page.evaluate(TURNS)
    assert len(run.sent) == 1
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16
    page.clock.resume()
    if reload:
        page.reload()
        expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    # The session cookie is Secure and this server speaks http, so it goes by hand.
    cookie = {"name": "session", "value": run.client.cookies["session"], "url": run.server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(email)
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Gespeichert", timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert x_of(run, "a") == 16
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_is_saved_from_the_list_with_its_sheet_not_opened(run):
    """A7: the teacher who comes back to the list is not left with a change that sits."""
    page, _ = start(run)
    page.get_by_label("Titel", exact=True).fill("Neu")
    change(run)
    answer(run, "a", 500)
    shut(page, 1)
    assert x_of(run, "a") == 15
    page, _, sent = again(run, None)
    names = page.locator(".sheets li strong")
    expect(names.filter(has_text="Neu")).to_have_count(1, timeout=5000)
    expect(page.locator(NOTICE)).to_have_count(0)
    assert len(sent) == 1
    assert sent[0].url.endswith(f"/api/sheets/{run.ids['a']}")
    assert x_of(run, "a") == 16
    assert run.held("a")["title"] == "Neu"
    assert record(page, run.ids["a"]) is None


def test_a_kept_change_of_a_sheet_changed_elsewhere_says_so_on_the_list(run):
    """I1: nothing is sent; the notice leads to the sheet, which asks which version stays."""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    was = run.held("a")
    was["doc"]["pages"][0]["blocks"][0]["x"] = 40
    other = {"doc": was["doc"], "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    page, _, sent = again(run, None)
    said = page.locator(NOTICE)
    expect(said).to_have_text(
        "„a“ wurde auf einem anderen Gerät geändert. Öffne das Blatt, um zu wählen."
    )
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    said.get_by_role("link", name="Öffne das Blatt").click()
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    banner = page.locator(".clash")
    for name in ("Andere Version laden", "Mit dieser überschreiben"):
        expect(banner.get_by_role("button", name=name)).to_be_visible()
    expect(said).to_have_count(0)
    page.evaluate(TURNS)
    assert not sent
    assert x_of(run, "a") == 40
    assert record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"] == 16


def test_another_accounts_kept_change_is_neither_sent_nor_removed_at_the_start(run):
    """I2"""
    page, _ = start(run)
    nudge(run)
    shut(page, 1)
    page, _, sent = again(run, None, client=user())
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    kept = record(page, run.ids["a"])
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == 16
    # Once more, with all that the tab asks for in view.
    with page.expect_response(f"{run.server}/api/sheets") as listed:
        page.reload()
    listed.value.finished()
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible()
    page.evaluate(TURNS)
    assert not sent
    assert not [url for url in asked if url.endswith(f"/api/sheets/{run.ids['a']}")]
    assert record(page, run.ids["a"]) == kept
    assert x_of(run, "a") == 15


def elsewhere(run, x):
    """Another device moves A's block there and saves."""
    was = run.held("a")
    was["doc"]["pages"][0]["blocks"][0]["x"] = x
    other = {"doc": was["doc"], "version": was["version"]}
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    return run.held("a")


def clash(run):
    """A is changed here and elsewhere, and this editor's save is turned down: the banner stands.
    Gives the sheet as the other device left it."""
    theirs = elsewhere(run, 99)
    change(run)
    answer(run, "a")
    expect(run.page.locator(".clash")).to_be_visible()
    return theirs


def kept_x(page, run):
    return record(page, run.ids["a"])["doc"]["pages"][0]["blocks"][0]["x"]


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
    """Review 6: `Andere Version laden`, its answer held, then `Mit dieser überschreiben`."""
    page, gate = start(run)
    theirs = clash(run)
    moved = at(page, "a").evaluate(LEFT)
    banner = page.locator(".clash")
    gate.free = False
    with page.expect_request(gate.asks("GET")):
        banner.get_by_role("button", name="Andere Version laden").click()
    page.evaluate(TURNS)
    late = gate.loads.pop()
    gate.free, gate.keep = True, False
    with page.expect_response(lambda r: gate.answers("PATCH")(r) and r.ok) as saved:
        banner.get_by_role("button", name="Mit dieser überschreiben").click()
    saved.value.finished()
    expect(page.locator(STATUS)).to_have_text("Gespeichert")
    # The answer to the first press, as the server stood then.
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


CHOICES = ["Andere Version laden", "Mit dieser überschreiben"]


@pytest.mark.parametrize("choice", CHOICES)
def test_a_clash_whose_sheet_was_deleted_elsewhere_ends_at_either_choice(run, choice):
    """Second review 2"""
    page, _ = start(run)
    clash(run)
    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200
    page.locator(".clash").get_by_role("button", name=choice).click()
    expect(page.get_by_role("heading", name="Blatt nicht gefunden")).to_be_visible()
    page.evaluate(GO, "/")
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
