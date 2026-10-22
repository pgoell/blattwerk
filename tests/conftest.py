import faulthandler
import gc
import json
import os
import signal
import sqlite3
import sys
import threading
import time
import traceback
from concurrent.futures import Future
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

import anyio
import pytest
from anyio.from_thread import BlockingPortal
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from playwright._impl._connection import Connection as PwConnection
from playwright.sync_api import expect, sync_playwright
from shards import split, times
from ui import BROWSER, serving, sheet, user

from blattwerk import auth, db

# Probe for #458: on CI a reply from Playwright's driver carried an id that waits for nothing, and
# dispatch raised KeyError. This says what was sent under that id, and then runs the real dispatch,
# so the KeyError still comes. Take it out once the cause is known.
_pw_send = PwConnection._send_message_to_server
_pw_dispatch = PwConnection.dispatch


def _pw_keep(book, key, value):
    book[key] = value
    if len(book) > 300:
        del book[next(iter(book))]


def _pw_sent(self, object, method, params, timeout, no_reply=False):
    sent = self.__dict__.setdefault("_probe_sent", {})
    thread = threading.current_thread()
    said = f"{method} on {object._guid} from {thread.name}"
    # The first catch on CI named a second thread as the sender (#463): such a send keeps its way.
    if thread is not threading.main_thread():
        said += " by\n" + "".join(traceback.format_stack(limit=25))
    # The id the send is about to take, as the driver answers it: `prefix@N` since 1.64.
    _pw_keep(sent, f"{self._call_id_prefix}@{self._last_id + 1}", said)
    return _pw_send(self, object, method, params, timeout, no_reply)


def _pw_answer(self, msg):
    sent = self.__dict__.setdefault("_probe_sent", {})
    answered = self.__dict__.setdefault("_probe_answered", {})
    id = msg.get("id")
    # After a close the real dispatch drops every reply, and no KeyError comes: nothing to say.
    if id and id not in self._callbacks and not self._closed_error:
        error = (msg.get("error") or {}).get("error") or {}
        print(
            f"playwright answered id {id} that waits for nothing: "
            f"{sent.get(id, 'never sent')}, answered before: {id in answered}, "
            f"reply error: {error.get('message')}, _closed_error: {self._closed_error!r}",
            file=sys.__stderr__,
            flush=True,
        )
    if id:
        _pw_keep(answered, id, True)
    _pw_dispatch(self, msg)


PwConnection._send_message_to_server = _pw_sent
PwConnection.dispatch = _pw_answer

WEBKIT = BROWSER == "webkit"
# The headed lane, `mise run test:native`: a real window, where a list and a colour picker open.
NATIVE = os.environ.get("BLATTWERK_NATIVE") == "1"
IPAD = {"width": 834, "height": 1194}
TURNED = {"width": 1194, "height": 834}
# How long an `expect` waits for what it expects. It ends the moment the page has it, so the limit
# costs a passing test nothing: it only says when a test that waits has failed. Two seconds were
# right on an idle machine, and a runner with more workers than cores took longer now and then for
# a script or a font to come in (#419, #439). The headed lane presses a key again when a check
# fails (tests/test_native.py), so there the limit is a step of the test, and stays.
expect.set_options(timeout=2000 if NATIVE else 5000)
# The tests that take over 30 s on CI. A test has a minute (pyproject.toml); these have two.
SLOW = {
    "test_a_corpus_file_prints_as_it_shows",
    "test_full_run_fails_when_the_reloaded_editor_lacks_the_word",
    "test_a_block_on_its_way_finds_its_page_after_the_pages_change",
    "test_every_exercise_keeps_every_limit",
    # 13 to 23 s on an idle machine: with limits that allow no term the generator spends every
    # try (#447), and a runner is three times slower.
    "test_every_comparison_keeps_every_limit",
    "test_every_task_of_three_numbers_keeps_every_limit_and_its_result_is_right",
    # 22 s alone in WebKit, past 60 s at the end of a loaded shard (#608).
    "test_a_shrunk_table_agrees_on_screen_thumb_and_pdf",
}
# Whether the widest page fills the desk's width, as it does at a zoom of 100 % once the editor
# has measured the desk.
MEASURED = """() => {
    const desk = document.querySelector('.desk'), look = getComputedStyle(desk);
    const room = desk.clientWidth - parseFloat(look.paddingLeft) - parseFloat(look.paddingRight);
    const sheets = [...desk.querySelectorAll('.sheet')];
    const widest = Math.max(...sheets.map((el) => el.getBoundingClientRect().width));
    return Math.abs(widest - room) < 1;
}"""


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    """With SHARD=i/n, keeps the i-th of n shards: CI runs the shards side by side.

    The shards split by measured time (tests/shards.py). Each xdist worker collects the same list
    and reads the same variable, and the split is deterministic, so all agree.
    """

    for test in items:
        if getattr(test, "originalname", None) in SLOW:
            test.add_marker(pytest.mark.timeout(120))

    # A test marked native runs in the headed lane, and that lane runs nothing else.
    def other(test):
        return (test.get_closest_marker("native") is None) == NATIVE

    config.hook.pytest_deselected(items=[t for t in items if other(t)])
    items[:] = [t for t in items if not other(t)]
    if WEBKIT:
        # Only a test that opens the browser can differ there. Before the shards, so they split
        # what is left evenly.
        config.hook.pytest_deselected(items=[t for t in items if "browser" not in t.fixturenames])
        items[:] = [t for t in items if "browser" in t.fixturenames]
        for item in items:
            for mark in item.iter_markers("webkit_xfail"):
                issue, why = mark.args
                item.add_marker(pytest.mark.xfail(strict=True, reason=f"#{issue}: {why}"))
    shard = os.environ.get("SHARD")
    if not shard:
        return
    i, n = map(int, shard.split("/"))
    assert 1 <= i <= n, f"SHARD={shard}: want i/n with 1 <= i <= n"
    mine = set(split([t.nodeid for t in items], times(BROWSER), n)[i - 1])
    config.hook.pytest_deselected(items=[t for t in items if t.nodeid not in mine])
    items[:] = [t for t in items if t.nodeid in mine]


# Seconds without a finished test before the run counts as hung. The slowest tests have 120 s of
# their own (SLOW), and a report comes at each phase, so a run that is only slow never gets here.
HANG_AFTER = float(os.environ.get("BLATTWERK_HANG", "180"))
GUARD = None  # the Hang of the controller; None in a worker
SWEEP = []  # the browser test that runs now, where its leftovers are still to collect: see `swept`


class Hang:
    """Ends the run when no test has finished for HANG_AFTER seconds, and says where it sat."""

    def __init__(self, err):
        self.err = err  # the real stderr, as a file descriptor
        self.timer = None
        self.running = set()

    def say(self, line):
        os.write(self.err, f"{line}\n".encode())

    def restart(self):
        self.cancel()
        self.timer = threading.Timer(HANG_AFTER, self.fire)
        self.timer.daemon = True
        self.timer.start()

    def cancel(self):
        if self.timer:
            self.timer.cancel()

    def fire(self):
        self.say(
            f"No test has finished for {HANG_AFTER:g} s: the run hangs. "
            "The stacks of every process follow."
        )
        # A copy: the main thread may still add a test while this one reads.
        for node in sorted(tuple(self.running)):
            self.say(f"Started and not finished: {node}")
        # The workers are the children of this process; each prints its stacks on SIGUSR1. A child
        # is listed under the thread that started it, and execnet starts some from helper threads,
        # so the lists of all threads count.
        me = os.getpid()
        pids = set()
        try:
            for task in Path(f"/proc/{me}/task").iterdir():
                # A thread that ends while the lists are read takes its file along.
                with suppress(OSError):
                    pids.update(int(pid) for pid in (task / "children").read_text().split())
            # One at a time: two dumps written to the same pipe at once come out interleaved (#461).
            for pid in pids:
                # A child that had gone before its signal came does not keep the others from theirs.
                with suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGUSR1)
                    time.sleep(1)
            faulthandler.dump_traceback(file=self.err, all_threads=True)
            # A worker that hangs never ends by itself, and would keep the pipes of the job open.
            for pid in pids:
                with suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        finally:
            # Whatever went wrong above: a run that hangs must end.
            os._exit(1)


def pytest_configure(config):
    """Each process prints its stacks on SIGUSR1, to the real stderr (capture moves fd 2)."""
    global GUARD
    err = os.dup(2)
    faulthandler.register(signal.SIGUSR1, file=err, all_threads=True)
    # Only the process that hands the tests to workers. A run with no workers may sit in a
    # debugger for as long as it likes.
    if not hasattr(config, "workerinput") and config.getoption("numprocesses", None):
        GUARD = Hang(err)


def pytest_unconfigure(config):
    if GUARD:
        GUARD.cancel()


def pytest_runtest_logstart(nodeid, location):
    if GUARD:
        GUARD.running.add(nodeid)


def pytest_runtest_logfinish(nodeid, location):
    if GUARD:
        GUARD.running.discard(nodeid)
    # Here and not in the fixture's own end: only now has pytest let go of the test's fixture
    # values, which may hold the routes of a gate.
    if SWEEP:
        SWEEP.clear()
        gc.collect()


def pytest_runtest_logreport(report):
    if GUARD:
        GUARD.restart()
        # On CI the trace comes at once: a job that is cancelled never prints its summary.
        if report.failed and os.environ.get("CI"):
            GUARD.say(f"FAILED {report.nodeid} ({report.when})\n{report.longreprtext}")


@pytest.hookimpl(trylast=True)
def pytest_exception_interact(node):
    """A failed test keeps its limit for its teardown.

    pytest-timeout ends its limit when a test fails, for a debugger that may open; pytest's own
    stack dump does the same. So a teardown that hung after a failure had no end, and the shard
    sat silent until the job's limit (#391). No debugger opens here: the limit starts anew.
    """
    # Asked for by name: the WebKit venv of a laptop may be older than the plugin (test-webkit.sh).
    limits = node.config.pluginmanager.getplugin("timeout")
    if limits and isinstance(node, pytest.Item):
        settings = limits._get_item_settings(node)
        if settings.timeout:
            node.config.pluginmanager.hook.pytest_timeout_set_timer(item=node, settings=settings)


def one_loop():
    """One event loop for every TestClient of the run. Left alone, a client starts a loop for each
    request and ends it after, and on CI such a loop now and then never ends (#340). This one is
    never ended: its thread is a daemon and goes with the process."""
    made = Future()

    async def run():
        async with BlockingPortal() as portal:
            made.set_result(portal)
            await portal.sleep_until_stopped()

    threading.Thread(target=anyio.run, args=[run], daemon=True).start()
    return made.result()


def unsynced():
    """sqlite3 as the app's database module sees it, with connections that do not wait for the disk.

    SQLite asks the disk to confirm each commit. That guards the data against a power cut, which
    no test is about, and it took most of a test's start: signing a user up was 38 ms on an idle
    machine and 520 ms with sixteen workers at one disk, 4 ms without. Only the app's own
    connections: a test that opens the file itself gets what SQLite gives.
    """

    def connect(*args, **more):
        con = sqlite3.connect(*args, **more)
        con.execute("PRAGMA synchronous = OFF")
        return con

    return SimpleNamespace(**{**vars(sqlite3), "connect": connect})


@pytest.fixture(scope="session", autouse=True)
def cheap(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        # The real hash takes 64 MiB and a fifth of a second, and every test signs a user up.
        patch.setattr(auth, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
        # Between two tests too, no request may reach the data folder of the checkout.
        patch.setattr(db, "DATA_DIR", tmp_path_factory.mktemp("between"))
        patch.setattr(TestClient, "portal", one_loop())
        patch.setattr(db, "sqlite3", unsynced())
        yield


@pytest.fixture(autouse=True)
def swept(request):
    """Collects what a browser test leaves, in the test's own thread, once its pages are shut.

    A route that a test held leaves a coroutine of Playwright's that never ends. When the garbage
    collector ends it, its `finally` starts a task that sends `setNetworkInterceptionPatterns`
    (`Page._on_route`), on the loop of whatever thread the collector runs in. In the server's
    thread, which has a loop of its own, the send goes out there, and the reply reaches the test's
    thread before its callback is kept: `KeyError` in `dispatch`, and the worker ends (#458, #463).
    Collected in the test's thread, the task runs on Playwright's own loop, as every send does.
    This only asks for it: `pytest_runtest_logfinish` collects, once the test is let go whole.
    """
    if "playwright" in request.fixturenames:
        SWEEP.append(request.node.nodeid)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture(scope="session")
def server():
    """The app on a real port, for Chromium to call as it does in production.

    One for the whole run: the app looks up the data folder with each request, so each test still
    has its own.
    """
    with serving() as url:
        yield url


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright):
    browser = getattr(playwright, BROWSER).launch(headless=not NATIVE)
    yield browser
    browser.close()


@pytest.fixture
def editor(browser, server, playwright):
    """Opens the editor on a sheet of the given blocks, as a new user, and gives its page."""
    contexts = []

    def start(
        *blocks, client=None, more=(), pages=(), theme=None, touch=False, words=None, wait=1100
    ):
        """`more` holds the blocks of a second page. With `touch` the window takes fingers too,
        and with `touch="landscape"` the iPad lies on its side.

        `pages` holds the pages after the first, each a whole page: its blocks and, where it has
        them, its own guides, grid and landscape. `theme` is the one picked on the account page:
        "" opens the panel Seiten, none is Blattform, which starts with that panel shut. `words`
        are the sheet's Lernwörter. `wait` is the time in ms from a change to its save: a test
        that counts on a change being unsaved for a while asks for a teacher's 2000.
        """
        window = {"viewport": {"width": 1400, "height": 1000}, "has_touch": bool(touch)}
        if touch:
            # Fingers mean an iPad, and its own window: 834 by 1194, or on its side.
            window["viewport"] = TURNED if touch == "landscape" else IPAD
        if WEBKIT and touch:
            # In WebKit its sharp screen and its name too.
            window = {**playwright.devices["iPad Pro 11"], "viewport": window["viewport"]}
        context = browser.new_context(**window)
        contexts.append(context)
        # The tests save 1.1 s after a change; a teacher's page waits 2 s (saves.ts). Not less: a
        # test that waits for "Speichert …" looks at most 1 s apart, and must not look past it.
        context.add_init_script(f"window.saveAfter = {wait}")
        # A copy stamps the system clipboard and a paste reads it; headless Chromium asks no one.
        # WebKit knows no leave to write, and lets the page write without one.
        context.grant_permissions(["clipboard-read", *([] if WEBKIT else ["clipboard-write"])])
        # The tour would open on the first visit and lie over the sheet.
        context.add_init_script("localStorage.setItem('tour', '1')")
        if theme is not None:
            context.add_init_script(f"localStorage.setItem('theme', {json.dumps(theme)})")
        client = client or user()
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        context.add_cookies(
            [{"name": "session", "value": client.cookies["session"], "url": server}]
        )
        page = context.new_page()
        rest = [*([more] if more else []), *pages]
        page.goto(f"{server}/blatt/{sheet(client, blocks, *rest, words=words)['id']}")
        # The editor listens for keys once the sheet has loaded.
        # The first load of a cold browser takes more than the 5 s of every other wait when the
        # machine has more workers than cores.
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
        # A thumbnail draws blocks too, with no name.
        count = len(blocks) + len(more) + sum(len(p["blocks"]) for p in pages)
        expect(page.locator(".block[data-id]")).to_have_count(count)
        # A font that comes in late moves what stands in it, and the editor measures anew then. A
        # place read or a click sent before that is not where the text ends up (#419, #436).
        page.evaluate("document.fonts.ready.then(() => 0)")
        # The editor fits the sheet to the desk as it opens, and the desk's observer may set the
        # width anew a frame later. A place read before then is not where the block ends up.
        page.wait_for_function(MEASURED, timeout=10000)
        # One browser serves the whole run, and every context shares its clipboard. Empty it
        # before the test uses the page, or a picture an earlier test left there pastes here (#182).
        page.bring_to_front()
        page.evaluate("navigator.clipboard.writeText('')")
        return page

    yield start
    # Leaving the editor saves. A save that comes in late finds no such session in the next
    # test's data and changes nothing.
    for context in contexts:
        context.close()
