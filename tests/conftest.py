import faulthandler
import json
import os
import signal
import threading
import time
from concurrent.futures import Future
from pathlib import Path

import anyio
import pytest
from anyio.from_thread import BlockingPortal
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright
from shards import split, times
from ui import BROWSER, serving, sheet, user

from blattwerk import auth, db

WEBKIT = BROWSER == "webkit"
# The headed lane, `mise run test:native`: a real window, where a list and a colour picker open.
NATIVE = os.environ.get("BLATTWERK_NATIVE") == "1"
IPAD = {"width": 834, "height": 1194}
TURNED = {"width": 1194, "height": 834}
expect.set_options(timeout=2000)
# The tests that take over 30 s on CI. A test has a minute (pyproject.toml); these have two.
SLOW = {
    "test_a_corpus_file_prints_as_it_shows",
    "test_full_run_fails_when_the_reloaded_editor_lacks_the_word",
    "test_a_block_on_its_way_finds_its_page_after_the_pages_change",
    "test_every_exercise_keeps_every_limit",
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
        for node in sorted(self.running):
            self.say(f"Started and not finished: {node}")
        # The workers are the children of this process; each prints its stacks on SIGUSR1.
        me = os.getpid()
        children = Path(f"/proc/{me}/task/{me}/children")
        pids = [int(pid) for pid in children.read_text().split()] if children.is_file() else []
        for pid in pids:
            os.kill(pid, signal.SIGUSR1)
        time.sleep(2)
        faulthandler.dump_traceback(file=self.err, all_threads=True)
        # A worker that hangs never ends by itself, and would keep the pipes of the job open.
        for pid in pids:
            os.kill(pid, signal.SIGKILL)
        os._exit(1)


def pytest_configure(config):
    """Each process prints its stacks on SIGUSR1, to the real stderr (capture moves fd 2)."""
    global GUARD
    err = os.dup(2)
    faulthandler.register(signal.SIGUSR1, file=err, all_threads=True)
    if not hasattr(config, "workerinput"):
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


@pytest.fixture(scope="session", autouse=True)
def cheap(tmp_path_factory):
    with pytest.MonkeyPatch.context() as patch:
        # The real hash takes 64 MiB and a fifth of a second, and every test signs a user up.
        patch.setattr(auth, "hasher", PasswordHasher(time_cost=1, memory_cost=8, parallelism=1))
        # Between two tests too, no request may reach the data folder of the checkout.
        patch.setattr(db, "DATA_DIR", tmp_path_factory.mktemp("between"))
        patch.setattr(TestClient, "portal", one_loop())
        yield


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

    def start(*blocks, client=None, more=(), pages=(), theme=None, touch=False):
        """`more` holds the blocks of a second page. With `touch` the window takes fingers too,
        and with `touch="landscape"` the iPad lies on its side.

        `pages` holds the pages after the first, each a whole page: its blocks and, where it has
        them, its own guides, grid and landscape. `theme` is the one picked on the account page:
        "" opens the panel Seiten, none is Blattform, which starts with that panel shut.
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
        page.goto(f"{server}/blatt/{sheet(client, blocks, *rest)['id']}")
        # The editor listens for keys once the sheet has loaded.
        # The first load of a cold browser takes more than the 2 s of every other wait when the
        # machine has more workers than cores.
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
        # A thumbnail draws blocks too, with no name.
        count = len(blocks) + len(more) + sum(len(p["blocks"]) for p in pages)
        expect(page.locator(".block[data-id]")).to_have_count(count)
        # The editor fits the sheet to the desk as it opens, and the desk's observer may set the
        # width anew a frame later. A place read before then is not where the block ends up.
        page.wait_for_function(MEASURED, timeout=10000)
        return page

    yield start
    # Leaving the editor saves. A save that comes in late finds no such session in the next
    # test's data and changes nothing.
    for context in contexts:
        context.close()
