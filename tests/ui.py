"""What the tests share: users, sheets and blocks, the app on a port, and the editor's blocks.

One whole test of the editor. `editor` and `server` are fixtures in conftest.py:

    from playwright.sync_api import expect
    from ui import FIELD, TEXT, at, box, pick

    def test_enter_opens_a_text_and_typing_replaces_it(editor):
        page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
        pick(page, "a")
        page.keyboard.press("Enter")
        page.keyboard.type("du")
        expect(page.locator(FIELD)).to_have_text("du")
        expect(at(page, "b")).not_to_have_class("block sel")

Run one test: `mise run test:one -- tests/test_keys.py::test_name`. Wait with `expect`, never for
a fixed time. A probe, to try something out, goes in tests/probe_*.py, which git ignores.
"""

import struct
import threading
import time
import unicodedata
import zlib
from contextlib import contextmanager
from uuid import uuid4

import uvicorn
from fastapi.testclient import TestClient
from playwright.sync_api import expect

from blattwerk import auth, db
from blattwerk.app import STATIC, app

PASSWORD = "richtig-geheim"
MATHS = {"ops": ["+"], "max": 20, "count": 3, "seed": 7}
RED = b"\xff\x00\x00"
TEXT = {"text": "Hallo", "size": 14, "align": "left"}
RECT = {"kind": "rect", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
RULING = {"kind": "l4", "color": "#222222"}
TABLE = {"cells": [["H", "Z"], ["3", "7"]], "cols": [1, 1], "size": 14, "align": "center"}
LINE = {**RECT, "kind": "line"}
ITEM = {**TEXT, "text": "eins", "rich": [{"runs": [{"text": "eins"}], "list": "bullet"}]}
FIELD = ".block.sel .ProseMirror"


@contextmanager
def serving():
    """The app on a real port, for Chromium to call as it does in production. Gives its address."""
    assert (STATIC / "index.html").is_file(), "build the frontend first: mise run build"
    server = uvicorn.Server(uvicorn.Config(app, port=0, log_level="warning"))
    thread = threading.Thread(target=server.run)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
    finally:
        server.should_exit = True
        thread.join()


def user(email=None):
    """A client logged in as a new user. https, or the Secure cookie is not sent back.

    With no address each call makes one of its own, so no two tests meet in one account.
    """
    client = TestClient(app, base_url="https://testserver")
    email = email or f"{uuid4().hex}@example.com"
    body = {"token": auth.new_link(db.open_db()), "email": email, "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(colour=RED):
    """A picture a browser can draw: three by two pixels of one colour."""
    head = struct.pack(">IIBBBBB", 3, 2, 8, 2, 0, 0, 0)
    rows = zlib.compress((b"\x00" + colour * 3) * 2)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", rows) + chunk(b"IEND", b"")


def upload(client):
    return client.post("/api/uploads", files={"file": ("bild", png(), "image/png")}).json()["id"]


def block(kind, y, h, props):
    box = {"id": kind, "x": 15, "y": y, "w": 180, "h": h, "z": 1, "locked": False}
    return {**box, "type": kind, "props": props}


def picture(upload_id):
    return block("image", 150, 60, {"upload": upload_id, "ratio": 1.5, "cut": [0, 0, 0, 0]})


def sheet(client, *pages):
    doc = {"pages": [{"blocks": list(p)} for p in pages], "guides": {"x": [], "y": []}, "grid": 0}
    return client.post("/api/sheets", json={"title": "Plus bis 20", "doc": doc}).json()


def box(name, kind, props, z=1, **more):
    """A block with a name and a place of its own: 30 mm below the one before in z."""
    return {**block(kind, 20 + 30 * z, 20, props), "id": name, "z": z, **more}


def at(page, name):
    return page.locator(f'.block[data-id="{name}"]')


def pick(page, *names):
    """Selects the blocks by a click, with Shift for all after the first."""
    for i, name in enumerate(names):
        at(page, name).click(modifiers=["Shift"] if i else [])
    expect_picked(page, *names)


def picked(page):
    return page.eval_on_selector_all(".block.sel", "els => els.map((el) => el.dataset.id)")


def expect_picked(page, *names):
    """Waits until just these blocks are selected."""
    expect(page.locator(".block.sel")).to_have_count(len(names))
    for name in names:
        expect(at(page, name)).to_have_class("block sel")


def unpick(page):
    """A click on the empty corner of the page selects nothing."""
    page.locator(".sheet").click(position={"x": 5, "y": 5})
    expect_picked(page)


def stopped(page, keys):
    """Whether the page kept the keys from the browser."""
    page.evaluate("addEventListener('keydown', (e) => (window.pressed = e), true)")
    page.keyboard.press(keys)
    return page.evaluate("pressed.defaultPrevented")


def caret(page, word, offset):
    """Opens the text "a", of one paragraph, and puts the caret `offset` letters into its `word`."""
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Home")
    text = page.locator(FIELD).inner_text()
    # An arrow steps over a letter and the marks that combine with it as one.
    for ch in text[: text.index(word) + offset]:
        if not unicodedata.combining(ch):
            page.keyboard.press("ArrowRight")
