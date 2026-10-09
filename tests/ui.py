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

import base64
import math
import re
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


def maths(client, **more):
    """A maths block's props as the editor makes them: three sums in a row, 12 mm high at 14 pt."""
    digits = [[0, 9], [0, 9]]
    limits = {**MATHS, "a": digits, "b": digits, "carry": "either", "rest": False, "format": "row"}
    limits = {**limits, **{key: more[key] for key in more if key in limits}}
    made = client.post("/api/maths", json=limits).json()
    return {**limits, **made, "columns": 3, "size": 14, **more}


def sheet(client, *pages):
    """A sheet of the pages: each the list of its blocks, or a whole page with what is its own."""
    pages = [p if isinstance(p, dict) else {"blocks": list(p)} for p in pages]
    doc = {"pages": pages, "guides": {"x": [], "y": []}, "grid": 0}
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


def copy_picture(page, colour=RED):
    """Puts a picture on the system clipboard, as a copy in another app does."""
    # The browser lets a page write the clipboard only while it has the focus.
    unpick(page)
    page.evaluate(
        """async (b64) => {
            const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
            const blob = new Blob([bytes], { type: "image/png" });
            await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })]);
        }""",
        base64.b64encode(png(colour)).decode(),
    )


def drop(page, x, y, *files, text=None):
    """Drops files on the point of the window, as a drag from the file manager ends there.

    A file is its name, its type and its bytes; `text` is what a file manager adds, the file's
    address. Gives whether the page kept each of the two events from the browser.
    """
    # The point must lie in the window: scroll what is dropped on into view first.
    held = [(name, kind, base64.b64encode(data).decode()) for name, kind, data in files]
    kept = page.evaluate(
        """([x, y, files, text]) => {
            const dataTransfer = new DataTransfer();
            for (const [name, type, b64] of files) {
                const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
                dataTransfer.items.add(new File([bytes], name, { type }));
            }
            if (text) dataTransfer.setData("text/plain", text);
            const under = document.elementFromPoint(x, y);
            const init = { dataTransfer, clientX: x, clientY: y, bubbles: true, cancelable: true };
            return ["dragover", "drop"].map((kind) => {
                const event = new DragEvent(kind, init);
                under.dispatchEvent(event);
                return event.defaultPrevented;
            });
        }""",
        [x, y, held, text],
    )
    return dict(zip(("dragover", "drop"), kept, strict=True))


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


def saved(page, client):
    """The first page's blocks as the server holds them, once the editor has saved a change."""
    # The editor saves two seconds after the last change.
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert", timeout=5000)
    sheet_id = page.url.rsplit("/", 1)[1]
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]


def doc(page, client):
    """The whole sheet as the server holds it, once the editor has saved a change."""
    saved(page, client)
    return client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()["doc"]


def thumb(page, n):
    """Page n's thumbnail in the panel Seiten."""
    return page.locator(f'.pages button[data-thumb="{n}"]')


def order(page):
    """The names of the blocks on each page of the desk, page by page."""
    named = "(el) => [...el.querySelectorAll('.block[data-id]')].map((b) => b.dataset.id)"
    return page.eval_on_selector_all(".sheet[data-page]", f"els => els.map({named})")


def angle(page, name):
    """The degrees the block is turned by, clockwise, as its own style says: 0 with no turn."""
    found = re.search(
        r"rotate\((-?[\d.]+)deg\)", at(page, name).evaluate("el => el.style.transform")
    )
    return float(found[1]) if found else 0


def mirror(page, name):
    """How the block's picture or symbol is drawn across and down: -1 when flipped, else 1."""
    drawn = at(page, name).evaluate(
        "el => getComputedStyle(el.querySelector(':scope > .picture, :scope > img')).transform"
    )
    # A matrix holds the scale across first and the scale down fourth.
    parts = re.findall(r"-?[\d.]+", drawn)
    return (round(float(parts[0])), round(float(parts[3]))) if parts else (1, 1)


def centre(locator):
    """The middle on the screen of what the locator finds: of the level box around a turned one."""
    box = locator.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def arc(start, about, degrees, steps=12):
    """The points of the way from `start` clockwise around `about`, for a drag or a swipe."""
    dx, dy = start[0] - about[0], start[1] - about[1]
    turns = [math.radians(degrees * i / steps) for i in range(steps + 1)]
    return [
        (
            about[0] + dx * math.cos(t) - dy * math.sin(t),
            about[1] + dx * math.sin(t) + dy * math.cos(t),
        )
        for t in turns
    ]


def drag(page, *points, keys=()):
    """Presses the mouse at the first point, moves it through the others and lets go."""
    # The keys are down before the press, as a hand holds Shift.
    page.mouse.move(*points[0])
    for key in keys:
        page.keyboard.down(key)
    page.mouse.down()
    # Moveable follows the moves between two points, not a jump.
    for point in points[1:]:
        page.mouse.move(*point, steps=5)
    page.mouse.up()
    for key in keys:
        page.keyboard.up(key)


def grow(page, by):
    """Drags the selection's handle at its lower right corner away from the upper left one."""
    start, end = (centre(page.locator(f".moveable-control.moveable-{c}")) for c in ("nw", "se"))
    far = math.dist(start, end)
    drag(page, end, tuple(e + (e - s) * by / far for s, e in zip(start, end, strict=True)))


def swipe(page, *points):
    """Puts a finger down at the first point, moves it through the others and lifts it."""
    # Playwright's own touchscreen only taps, so the browser is told of each touch by hand.
    session = page.context.new_cdp_session(page)
    for i, (x, y) in enumerate(points):
        kind = "touchMove" if i else "touchStart"
        session.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [{"x": x, "y": y}]})
    session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    session.detach()


@contextmanager
def finger(page, start):
    """A finger down at the start for as long as the block runs. Gives the way to send touches."""
    session = page.context.new_cdp_session(page)

    def touch(kind, *at):
        touched = [{"x": x, "y": y} for x, y in at]
        session.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": touched})

    touch("touchStart", start)
    yield touch
    touch("touchEnd")
    session.detach()


def jitter(held, start, *by):
    """Tells `held` that the finger on it lies off the start by each of `by`, in px."""
    # Chrome keeps a finger's moves from the page until it is more than 15 px from where it came
    # down. Safari on an iPad does not, so the page is told by hand, as it is there.
    for dx, dy in by:
        held.evaluate(
            """(el, [clientX, clientY]) => {
                const touches = [new Touch({ identifier: 0, target: el, clientX, clientY })];
                const init = { touches, bubbles: true, cancelable: true };
                el.dispatchEvent(new TouchEvent("touchmove", init));
            }""",
            [start[0] + dx, start[1] + dy],
        )


def outlast(page):
    """Waits until a hold would be over."""
    # A hold that was called off shows nothing on the page, so only the clock tells that none comes.
    page.wait_for_timeout(700)


def hold_drag(page, held, start, *points, by=(), shows="drag"):
    """Holds a finger on `held` at the start until it lifts off for a drag, then moves and lifts.

    The finger jitters by each of `by` during the hold. `shows` is the class `held` gets when the
    hold is over.
    """
    with finger(page, start) as touch:
        jitter(held, start, *by)
        # The hold is over when the page says so, however long it asks for.
        expect(held).to_have_class(re.compile(rf"\b{shows}\b"))
        for point in points:
            touch("touchMove", point)
