import os
import sys
import threading
import traceback

import pytest
from fixtures.app import cheap as cheap
from fixtures.app import data_dir as data_dir
from fixtures.app import server as server
from fixtures.editor import IPAD as IPAD
from fixtures.editor import MEASURED as MEASURED
from fixtures.editor import NATIVE
from fixtures.editor import TURNED as TURNED
from fixtures.editor import WEBKIT as WEBKIT
from fixtures.editor import browser as browser
from fixtures.editor import editor as editor
from fixtures.editor import playwright as playwright
from fixtures.hang import pytest_configure as pytest_configure
from fixtures.hang import pytest_exception_interact as pytest_exception_interact
from fixtures.hang import pytest_runtest_logfinish as pytest_runtest_logfinish
from fixtures.hang import pytest_runtest_logreport as pytest_runtest_logreport
from fixtures.hang import pytest_runtest_logstart as pytest_runtest_logstart
from fixtures.hang import pytest_unconfigure as pytest_unconfigure
from fixtures.hang import swept as swept
from playwright._impl._connection import Connection as PwConnection
from playwright.sync_api import expect
from shards import split, times
from ui import BROWSER

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
