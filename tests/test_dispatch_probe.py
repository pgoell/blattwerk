"""The probe of tests/conftest.py for #458: a reply that waits for nothing says so, then raises."""

import io
import sys
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
