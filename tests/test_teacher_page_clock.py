"""The teacher tool's clock: seconds since start, not the shell's date (#617)."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import sys
from contextlib import contextmanager
from urllib.parse import urlsplit

from test_teacher_page import (
    ONE,
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    tool,
)
from ui import box


def test_617_a_second_start_keeps_the_clock_and_a_verb_prints_it(editor, folder, monkeypatch):
    clocks = sys.modules["teacher_page_clock"]
    now = {"t": 1000.0}
    monkeypatch.setattr(clocks.time, "time", lambda: now["t"])
    tool.began()
    now["t"] = 2500.0
    tool.began()
    assert float((folder / "began").read_text()) == 1000.0
    assert tool.clock() == "The clock is 1500"
    page = editor(box("a", "text", ONE))

    @contextmanager
    def joined_here():
        yield page

    monkeypatch.setattr(tool, "joined", joined_here)
    lines = tool.verb("hover", ("Eins",), False).splitlines()
    assert lines[-2] == "The clock is 1500"
    assert lines[-1] == f"The page is {urlsplit(page.url).path}"


def test_617_with_no_start_the_clock_is_zero(folder):
    assert tool.clock() == "The clock is 0"
