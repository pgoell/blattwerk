"""What a held route leaves behind (#458, #463): why the fixture `swept` collects in the test's thread."""

import asyncio
import gc
import threading

import pytest


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
    """The cause of the KeyError (#458, #463). The coroutine of a held route never ends. Up to
    Playwright 1.64, when the collector ended it, a `finally` in `Page._on_route` started a task
    that sent to the driver, on the loop of whatever thread collected, and the reply came back
    before its callback was kept. Since 1.65 `_on_route` has no such `finally`, so a collector in
    another thread starts nothing, whether or not the test's thread collected first (`swept`).
    Should a later Playwright bring the send back, this fails and says which task it started."""
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
        assert found == []
    finally:
        gc.enable()
