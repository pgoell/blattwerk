"""Ends a run that has finished no test for too long, and collects a browser test's leftovers."""

import faulthandler
import gc
import os
import signal
import threading
import time
from contextlib import suppress
from pathlib import Path

import pytest

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
