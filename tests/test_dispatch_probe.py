"""The probe of tests/conftest.py for #458: a reply that waits for nothing says so, then raises."""

import asyncio
import gc
import io
import sys
import threading
from types import SimpleNamespace
from typing import Any

import pytest
from playwright._impl._connection import Connection


def test_a_reply_that_waits_for_nothing_says_what_it_answers_and_still_raises(monkeypatch):
    err = io.StringIO()
    monkeypatch.setattr(sys, "__stderr__", err)
    fake = SimpleNamespace(_callbacks={}, _closed_error=None)
    dispatch: Any = Connection.dispatch  # a stand-in connection, not a real one
    with pytest.raises(KeyError):
        dispatch(fake, {"id": 7, "error": {"error": {"message": "closed"}}})
    assert err.getvalue() == (
        "playwright answered id 7 that waits for nothing: never sent, answered before: False, "
        "reply error: closed, _closed_error: None\n"
    )


def test_a_second_reply_names_what_was_sent_under_its_id(browser, monkeypatch):
    # On the real connection: what a call sent is kept under the id the driver answers.
    connection: Any = browser._impl_obj._connection
    context = browser.new_context()
    context.close()
    last = connection._last_id
    assert max(connection._probe_sent) == last
    err = io.StringIO()
    monkeypatch.setattr(sys, "__stderr__", err)
    with pytest.raises(KeyError):
        connection.dispatch({"id": last, "error": {"error": {"message": "closed"}}})
    said = err.getvalue()
    assert said.startswith(f"playwright answered id {last} that waits for nothing: close on ")
    assert "from MainThread, answered before: True, reply error: closed" in said


def started_in_a_loop_thread():
    """Runs the collector in a thread with an event loop, as the server's thread has one. Gives
    the tasks that the collector started on that loop, and ends them before they run."""
    found = []

    async def collect():
        gc.collect()
        for task in asyncio.all_tasks() - {asyncio.current_task()}:
            found.append(repr(task.get_coro()))
            task.cancel()

    other = threading.Thread(target=lambda: asyncio.run(collect()), name="loop")
    other.start()
    other.join()
    return found


@pytest.mark.parametrize("first", [False, True], ids=["left", "collected"])
def test_what_a_held_route_leaves_sends_from_the_thread_that_collects_it(browser, server, first):
    """The cause of the KeyError (#458, #463). The coroutine of a held route never ends; when the
    collector ends it, Playwright's `finally` starts a task that sends to the driver, on the loop
    of whatever thread collects. Collected first in the test's own thread, as the fixture `swept`
    asks for, nothing is left for another thread."""
    gc.collect()
    gc.disable()
    try:
        context = browser.new_context()
        page = context.new_page()
        kept = []
        # ruff takes the `del` below for the name's end; the handler runs before it.
        page.route("**/api/me", lambda route: kept.append(route))  # noqa: F821
        page.goto(server)
        # The page waits for its account; the handler has the route once the request is out.
        while not kept:
            page.wait_for_timeout(20)
        page.unroute("**/api/me")
        context.close()
        del page, context, kept
        if first:
            gc.collect()
        found = started_in_a_loop_thread()
        assert any("Connection.wrap_api_call" in coro for coro in found) is not first, found
    finally:
        gc.enable()


def test_a_send_from_a_second_thread_keeps_the_way_it_came(monkeypatch):
    # What the first catch on CI showed (#463): the sender was not the test's thread.
    from conftest import _pw_sent

    fake: Any = SimpleNamespace(_last_id=4, __dict__={})
    thing = SimpleNamespace(_guid="page@1")
    monkeypatch.setattr("conftest._pw_send", lambda *args: None)
    other = threading.Thread(target=lambda: _pw_sent(fake, thing, "route", {}, 0), name="other")
    other.start()
    other.join()
    said = fake._probe_sent[5]
    assert said.startswith("route on page@1 from other by\n")
    assert "test_dispatch_probe.py" in said
