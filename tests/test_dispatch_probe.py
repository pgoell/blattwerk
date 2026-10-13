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
