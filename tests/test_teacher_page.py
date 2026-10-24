"""The window of the session that only uses the app: scripts/teacher-page.py.

Each verb is called on the editor's page as the command line calls it, and the test sees what
came of it. The last test runs the command line itself, in a real window: start, a login by the
verbs alone, stop.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import expect
from ui import (
    BROWSER,
    RECT,
    TEXT,
    at,
    box,
    centre,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "teacher-page.py"
spec = importlib.util.spec_from_file_location("teacher_page", SCRIPT)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

# The tool opens Chromium and no other browser, so the WebKit lane has nothing to learn here.
pytestmark = pytest.mark.skipif(BROWSER != "chromium", reason="the tool's window is Chromium")

ONE = {**TEXT, "text": "Eins"}
TWO = {**TEXT, "text": "Zwei"}
RED = {**RECT, "fill": "#ff0000", "stroke": "none"}
POPUP = ".panel input[type=color]:open"


@pytest.fixture(autouse=True)
def folder(tmp_path, monkeypatch, server):
    """The tool writes into a folder of the test and knows the test's server as the app."""
    made = tmp_path / "teacher-run"
    made.mkdir()
    monkeypatch.setattr(tool, "STATE", made)
    monkeypatch.setattr(tool, "BASE", server)
    return made


def xy(found):
    """The middle of what the locator finds, as a TARGET of the command line."""
    x, y = centre(found)
    return f"{x:g},{y:g}"


def middle(found):
    """The same, as the tool prints a place it found by name: in whole px."""
    return ",".join(str(round(v)) for v in centre(found))


def slider(page):
    return page.locator(".panel").get_by_label("Randstärke", exact=True)


def shape(editor, client=None):
    """A picked shape, and its panel turned down to the border: the slider lies below the window."""
    page = editor(box("a", "shape", RECT), client=client)
    tool.click(page, xy(at(page, "a")))
    expect(slider(page)).to_have_value("0.5")
    assert tool.where(page, "Randstärke").endswith("(outside the window)")
    # A heading of the panel that lies in the window: the one over the border has moved below it.
    tool.wheel(page, "Schrift", "540")
    expect(slider(page)).to_be_in_viewport(ratio=1)
    return page


def size(path):
    return Image.open(path).size


def scrolled(page):
    return page.locator(".desk").evaluate("el => el.scrollTop")


def desk_at(page, across=10, down=10):
    """A point on the desk, px across and down from its top left corner, as a TARGET."""
    corner = page.locator(".desk").bounding_box()
    return f"{corner['x'] + across:g},{corner['y'] + down:g}"


def far(colour):
    """How far `#rrggbb` lies from the text's #222222, in its widest channel: 60 is plain to see."""
    return max(abs(int(colour[n : n + 2], 16) - 0x22) for n in (1, 3, 5))


def run(folder, server, *words, limit=120):
    """The command line, as `mise run teacher:page --` calls it. A call past `limit` s fails."""
    env = {**os.environ, "TEACHER_PAGE_DIR": str(folder), "TEACHER_PAGE_URL": server}
    return subprocess.run(
        [sys.executable, SCRIPT, *words], env=env, capture_output=True, text=True, timeout=limit
    )


def left(folder):
    """The processes that still name the folder: the browser has its profile there."""
    found = []
    for words in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            said = words.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if str(folder) in said:
            found.append(said[:200])
    return found


def below(page, name):
    """Pushes `name` in the panel below the window, under a tall spacer, and leaves the scroll at the top."""
    page.locator(".panel").get_by_label(name, exact=True).evaluate(
        """el => {
            const panel = el.closest(".panel");
            const spacer = document.createElement("div");
            spacer.style.height = "3000px";
            panel.insertBefore(spacer, panel.firstChild);
            panel.scrollTop = 0;
        }"""
    )
