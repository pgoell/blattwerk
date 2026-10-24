"""A sheet's saver outlives its editor (issues #331, #329, #330): no load waits for a save, a save
that fails or never answers is tried again, and a change the server never got lies in the
browser's store until it is saved, on this visit or the next.

Built on test_stale.py: sheets A, B and C, each with one block that names it, and a gate at each
that holds its loads and its saves. Where time counts the page's clock stands and the test moves
it: 2 s from a change to its save, 20 s until a save with no answer is given up, 2 s doubling to
30 s between tries, 1 s until the notice.

The docstrings name the lines of the checklist.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import threading
from contextlib import contextmanager

import pytest
from fastapi import HTTPException
from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_stale import (
    STATUS,  # noqa: F401
    TURNS,
    Gate,
    Run,
)
from ui import unpick

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
    """An unsaved change, which the saver has heard of. Unpicks first: a click on a block that is
    already picked alone opens it for writing, and the arrow must reach the block."""
    unpick(run.page)
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


def asks_me(page):
    """The requests of the page that ask who is signed in, from here on."""
    asked = []
    page.on("request", lambda r: r.url.endswith("/api/me") and asked.append(r))
    return asked


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


CHOICES = ["Andere Version laden", "Mit dieser überschreiben"]
