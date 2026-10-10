"""A real window with a real mouse, for the session that only uses the app (docs/teacher-run.md).

    mise -C /home/pascal/Code/blattwerk run teacher:page -- <verb> [args]

    start                  opens the window, 1280 x 1024, on the stage; a second start replaces it
    stop                   shuts the window
    open PATH              goes to a path of the app: / or /blatt/12, never /admin
    click TARGET           also: double-click TARGET, shift-click TARGET, hover TARGET
    drag FROM TO           presses the mouse at FROM, moves it to TO and lets go
    wheel TARGET DY        turns the wheel over TARGET by DY px; less than 0 is up
    key KEYS [N]           presses a key or a chord N times: Escape, ArrowRight, Control+z
    type TEXT              types the text where the focus is
    where NAME             prints where the name is on the page; changes nothing
    resize W H             sets the window's size
    screenshot [NAME]      writes the window to NAME.png, `screen` if none
    pdf [TARGET]           clicks the bar's `PDF`, or `Lösungen`, and saves what comes down

A TARGET is `X,Y`, in px of the window, which are the px of the screenshot, or a name: the words
on a control, its label, or what a hover or a screen reader says of it. A name must be on the page
once. Every verb that acts also writes the window to last.png and prints that path.

One process, `hold`, keeps the window under xvfb-run, and each verb joins it over Chromium's
debugging port. Python's Playwright has no `launch_server`, and a context that a client makes
ends with that client: so the holder owns the page, and the mouse stays where a verb left it.

The files lie in /tmp/teacher-run, or where TEACHER_PAGE_DIR says. The window opens on the stage,
http://127.0.0.1:8220; TEACHER_PAGE_URL names another server, for the tests only.
"""

import inspect
import json
import os
import posixpath
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import Error, Page, sync_playwright
from playwright.sync_api import TimeoutError as Late

STATE = Path(os.environ.get("TEACHER_PAGE_DIR", "/tmp/teacher-run"))
BASE = os.environ.get("TEACHER_PAGE_URL", "http://127.0.0.1:8220")
VIEW = {"width": 1280, "height": 1024}
XY = re.compile(r"(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)")
# Of the matches of a name, which stay: one that holds another match, or is the label of one,
# gives way to it. So a label and its field are one place, the field's.
KEPT = """(found) => found.map((el) =>
    !found.some((other) => other !== el && (el.contains(other) || el.control === other)))"""


class Refused(Exception):
    """What the caller asked for cannot be done; the words say why."""


def running() -> dict | None:
    """What the holder wrote of itself, or nothing where no holder runs."""
    try:
        state = json.loads((STATE / "page.json").read_text())
        # The pid may be another process's by now: only a holder of this script counts.
        words = Path(f"/proc/{state['pid']}/cmdline").read_bytes().split(b"\0")
    except FileNotFoundError, ProcessLookupError:
        return None
    return state if __file__.encode() in words and b"hold" in words else None


def places(page: Page, name: str) -> list[tuple[int, int]]:
    """The middle of each visible thing of that name, by what a user reads or hears only."""
    found = page.get_by_label(name, exact=True)
    for by in (page.get_by_text, page.get_by_title, page.get_by_placeholder, page.get_by_alt_text):
        found = found.or_(by(name, exact=True))
    found = found.filter(visible=True)
    try:
        found.first.wait_for(timeout=3000)
    except Late:
        raise Refused(f'nothing on the page is called "{name}"') from None
    handles = [one.element_handle() for one in found.all()]
    kept = page.evaluate(KEPT, handles)
    boxes = [el.bounding_box() for el, keep in zip(handles, kept, strict=True) if keep]
    return [(round(b["x"] + b["width"] / 2), round(b["y"] + b["height"] / 2)) for b in boxes if b]


def inside(page: Page, x: float, y: float) -> bool:
    wide, high = page.evaluate("[innerWidth, innerHeight]")
    return 0 <= x < wide and 0 <= y < high


def point(page: Page, target: str) -> tuple[float, float]:
    """The place in the window that the target names."""
    if at := XY.fullmatch(target):
        return float(at[1]), float(at[2])
    found = places(page, target)
    seen = [p for p in found if inside(page, *p)]
    listed = ", ".join(f"{x},{y}" for x, y in seen or found)
    if not seen:
        raise Refused(f'"{target}" lies outside the window, at {listed}: scroll to it')
    if len(seen) > 1:
        raise Refused(f'"{target}" is on the page {len(seen)} times, at {listed}: give one as X,Y')
    return seen[0]


def number(text: str, kind: Callable = int):
    try:
        return kind(text)
    except ValueError:
        raise Refused(f'"{text}" is not a number') from None


def shown(page: Page, did: str) -> str:
    """Writes the window to last.png, so the call that acts also shows what came of it."""
    path = STATE / "last.png"
    page.screenshot(path=path)
    return f"{did}: {path}"


def go(page: Page, path: str) -> str:
    # A browser reads `//host` and `/\\host` as another host, and drops a tab or a line break.
    if not re.fullmatch(r"/(?![/\\])[^\s\\]*", path):
        raise Refused(f'"{path}" is not a path of the app: give one like / or /blatt/12')
    # As the browser will ask for it: `/x/../admin` is the admin page too.
    way = posixpath.normpath(unquote(urlsplit(path).path)).lower()
    if way == "/admin" or way.startswith("/admin/"):
        raise Refused("the admin page is not a teacher's")
    # A teacher sees pages, not what the pages ask the server.
    if way == "/api" or way.startswith("/api/"):
        raise Refused("a path under /api is no page of the app")
    page.goto(BASE + path)
    return shown(page, f"opened {path}")


def click(page: Page, target: str) -> str:
    x, y = point(page, target)
    page.mouse.click(x, y)
    return shown(page, f"clicked at {x:g},{y:g}")


def double_click(page: Page, target: str) -> str:
    x, y = point(page, target)
    page.mouse.dblclick(x, y)
    return shown(page, f"double-clicked at {x:g},{y:g}")


def shift_click(page: Page, target: str) -> str:
    x, y = point(page, target)
    page.keyboard.down("Shift")
    page.mouse.click(x, y)
    page.keyboard.up("Shift")
    return shown(page, f"shift-clicked at {x:g},{y:g}")


def hover(page: Page, target: str) -> str:
    x, y = point(page, target)
    page.mouse.move(x, y)
    return shown(page, f"mouse at {x:g},{y:g}")


def drag(page: Page, start: str, end: str) -> str:
    x, y = point(page, start)
    to = point(page, end)
    page.mouse.move(x, y)
    page.mouse.down()
    # The editor follows the moves between the two, not a jump.
    page.mouse.move(*to, steps=10)
    page.mouse.up()
    return shown(page, f"dragged from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


def wheel(page: Page, target: str, dy: str) -> str:
    x, y = point(page, target)
    page.mouse.move(x, y)
    page.mouse.wheel(0, number(dy, float))
    return shown(page, f"wheel turned by {dy} at {x:g},{y:g}")


def key(page: Page, keys: str, times: str = "1") -> str:
    for _ in range(number(times)):
        page.keyboard.press(keys)
    return shown(page, f"pressed {keys} {times} times")


def type_(page: Page, text: str) -> str:
    page.keyboard.type(text)
    return shown(page, f"typed {len(text)} letters")


def where(page: Page, name: str) -> str:
    found = places(page, name)
    return "\n".join(
        f"{name} at {x},{y}" + ("" if inside(page, x, y) else " (outside the window)")
        for x, y in found
    )


def resize(page: Page, wide: str, high: str) -> str:
    page.set_viewport_size({"width": number(wide), "height": number(high)})
    return shown(page, f"window is {wide} x {high}")


def screenshot(page: Page, name: str = "screen") -> str:
    if not re.fullmatch(r"[\w-]+", name):
        raise Refused(f'"{name}" is no name for a file: letters, digits, - and _ only')
    path = STATE / f"{name}.png"
    # The window and no more: its px are the px a TARGET is given in.
    page.screenshot(path=path)
    return str(path)


def pdf(page: Page, target: str = "PDF") -> str:
    x, y = point(page, target)
    try:
        with page.expect_download(timeout=60000) as coming:
            page.mouse.click(x, y)
    except Late:
        raise Refused(f"no file came down after the click at {x:g},{y:g}") from None
    path = STATE / Path(coming.value.suggested_filename).name
    coming.value.save_as(path)
    return str(path)


VERBS: dict[str, Callable[..., str]] = {
    "open": go,
    "click": click,
    "double-click": double_click,
    "shift-click": shift_click,
    "hover": hover,
    "drag": drag,
    "wheel": wheel,
    "key": key,
    "type": type_,
    "where": where,
    "resize": resize,
    "screenshot": screenshot,
    "pdf": pdf,
}


def hold() -> None:
    """Keeps the window open until `stop` asks it to go. Runs under xvfb-run, started by `start`."""
    # A profile of its own each time: no login of an earlier run is left in it.
    profile = STATE / "profile"
    shutil.rmtree(profile, ignore_errors=True)
    with sync_playwright() as p:
        # The profile's own context, the one a verb sees when it joins over the port.
        context = p.chromium.launch_persistent_context(
            profile,
            headless=False,
            viewport=VIEW,  # ty: ignore[invalid-argument-type]
            device_scale_factor=1,
            accept_downloads=True,
            args=["--remote-debugging-port=0"],
        )
        context.pages[0].goto(BASE)
        # Chromium picked a free port and wrote it down.
        port = (profile / "DevToolsActivePort").read_text().split()[0]
        # From here on `stop` knows whom to ask, and its signal waits until it is read.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        state = {"pid": os.getpid(), "group": os.getpgid(0), "endpoint": f"http://127.0.0.1:{port}"}
        (STATE / "page.tmp").write_text(json.dumps(state))
        (STATE / "page.tmp").replace(STATE / "page.json")
        signal.sigwait({signal.SIGTERM})
        context.close()


def stop() -> bool:
    """Ends the holder, its browser and its xvfb. Says whether one ran."""
    state = running()
    (STATE / "page.json").unlink(missing_ok=True)
    if not state:
        return False
    # The holder shuts the browser itself, and xvfb-run then ends its screen.
    os.kill(state["pid"], signal.SIGTERM)
    try:
        for _ in range(100):
            os.killpg(state["group"], 0)
            time.sleep(0.1)
        os.killpg(state["group"], signal.SIGKILL)
    except ProcessLookupError:
        pass
    return True


def start() -> str:
    stop()
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "log").open("w") as log:
        # A session of its own: the window outlives this call and the shell that made it.
        child = subprocess.Popen(
            # A screen with room for the window on its side and upright: `resize 820 1180`.
            ["xvfb-run", "-a", "-s", "-screen 0 1920x1400x24", sys.executable, __file__, "hold"],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    late = time.monotonic() + 60
    while not (STATE / "page.json").exists():
        if child.poll() is not None or time.monotonic() > late:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            said = (STATE / "log").read_text().strip()[-2000:]
            raise Refused(f"the window did not open on {BASE}:\n{said}")
        time.sleep(0.1)
    return f"started: a window of {VIEW['width']} x {VIEW['height']} on {BASE}"


@contextmanager
def joined():
    """The holder's page, for one verb."""
    state = running()
    if not state:
        raise Refused("no page is running: start it first, with the verb `start`")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(state["endpoint"])
        yield browser.contexts[0].pages[0]


def main(name: str = "", *args: str) -> str:
    if name == "hold":
        hold()
        return ""
    if name == "start":
        return start()
    if name == "stop":
        return "stopped" if stop() else "no page was running"
    if name not in VERBS:
        known = ", ".join(["start", "stop", *VERBS])
        raise Refused(f'no verb "{name}": there are {known}')
    try:
        inspect.signature(VERBS[name]).bind(None, *args)
    except TypeError:
        takes = " ".join(list(inspect.signature(VERBS[name]).parameters)[1:]).upper()
        raise Refused(f"{name} takes: {takes}") from None
    with joined() as page:
        return VERBS[name](page, *args)


if __name__ == "__main__":
    try:
        print(main(*sys.argv[1:]))
    except Refused as error:
        sys.exit(str(error))
    except Error as error:
        # Playwright's own words, without its log of calls.
        sys.exit(error.message.splitlines()[0])
