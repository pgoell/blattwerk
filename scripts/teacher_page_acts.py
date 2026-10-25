"""Verbs of scripts/teacher-page.py: the mouse, the files, and the window that stays open.

The tests patch names on the teacher-page module (STATE, point, joined). These functions
read those names through teacher_page_ns, which that module binds to its own globals.
"""

import base64
import json
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from playwright.sync_api import Error, Page, sync_playwright
from playwright.sync_api import TimeoutError as Late
from teacher_page_name import read_value
from teacher_page_ns import g

# A PDF button. `click` on it used to return before the file arrived, and the browser then
# wrote that file into Downloads (#617). `pdf` waits and saves it into the run folder.
PRINTS = """([x, y]) => {
    const el = document.elementFromPoint(x, y)?.closest("button");
    const name = (el?.innerText ?? "").replace(/\\s+/g, " ").trim();
    return name === "PDF" || name === "Lösungen";
}"""


def click(page: Page, target: str) -> str:
    x, y = g("point")(page, target)
    grey = g("greyed")(page, x, y)
    if not grey and page.evaluate(PRINTS, [x, y]):
        return pdf(page, target)
    page.mouse.click(x, y)
    return g("shown")(page, f"clicked at {x:g},{y:g}{grey}")


def double_click(page: Page, target: str) -> str:
    x, y = g("point")(page, target)
    grey = g("greyed")(page, x, y)
    page.mouse.dblclick(x, y)
    return g("shown")(page, f"double-clicked at {x:g},{y:g}{grey}")


def shift_click(page: Page, target: str) -> str:
    x, y = g("point")(page, target)
    grey = g("greyed")(page, x, y)
    page.keyboard.down("Shift")
    page.mouse.click(x, y)
    page.keyboard.up("Shift")
    return g("shown")(page, f"shift-clicked at {x:g},{y:g}{grey}")


def hover(page: Page, target: str) -> str:
    x, y = g("point")(page, target)
    page.mouse.move(x, y)
    return g("shown")(page, f"mouse at {x:g},{y:g}")


def ends(page: Page, start: str, end: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """FROM and TO in px. The page may turn to TO, so FROM is read again: both must show at once."""
    x, y = g("point")(page, start)
    to = g("point")(page, end)
    if g("NOTES"):
        # The page turned to TO, so FROM stands elsewhere now. Both must be in the window at once.
        g("NOTES").clear()
        x, y = g("point")(page, start)
        if g("NOTES"):
            raise g("Refused")(f'"{start}" and "{end}" are not in the window together: give X,Y')
        g("NOTES").append("turned the page to it")
    return (x, y), to


def drag(page: Page, start: str, end: str) -> str:
    (x, y), to = ends(page, start, end)
    page.mouse.move(x, y)
    page.mouse.down()
    # The editor follows the moves between the two, not a jump.
    page.mouse.move(*to, steps=10)
    page.mouse.up()
    return g("shown")(page, f"dragged from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


def middle_drag(page: Page, start: str, end: str) -> str:
    (x, y), to = ends(page, start, end)
    page.mouse.move(x, y)
    page.mouse.down(button="middle")
    page.mouse.move(*to, steps=10)
    page.mouse.up(button="middle")
    return g("shown")(page, f"middle-dragged from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


def swipe(page: Page, start: str, end: str) -> str:
    """A finger over the browser's debugging line: Playwright's touchscreen only taps."""
    (x, y), to = ends(page, start, end)
    session = page.context.new_cdp_session(page)
    try:
        session.send(
            "Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x, "y": y}]}
        )
        steps = 10
        for n in range(1, steps + 1):
            at = [{"x": x + (to[0] - x) * n / steps, "y": y + (to[1] - y) * n / steps}]
            session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": at})
        session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    finally:
        session.detach()
    return g("shown")(page, f"swiped from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


def wheel(page: Page, target: str, dy: str) -> str:
    x, y = g("point")(page, target)
    page.mouse.move(x, y)
    page.mouse.wheel(0, g("number")(dy, float))
    return g("shown")(page, f"wheel turned by {dy} at {x:g},{y:g}")


def where(page: Page, name: str) -> str:
    found = g("places")(page, name, part=True)
    return "\n".join(
        f"{one.shown} at {one.x},{one.y}"
        + ("" if g("inside")(page, one.x, one.y) else " (outside the window)")
        for one in found
    )


def value(page: Page, name: str) -> str:
    """What a field holds, or which button under a heading of that name is on."""
    return read_value(page, name)


def wanted() -> list[int]:
    """The size the holder keeps the window at: what `resize` wrote last, else VIEW."""
    try:
        size = json.loads((g("STATE") / "size.json").read_text())
        return [size["width"], size["height"]]
    except OSError, ValueError, KeyError:
        return [g("VIEW")["width"], g("VIEW")["height"]]


def holder_since(moment: float) -> None:
    """Waits until the holder has put the size back after `moment`, for up to 3 s. Reads no page,
    so a box that is open does not hold it.
    """
    late = time.monotonic() + 3
    while time.monotonic() < late:
        with suppress(OSError, ValueError):
            if float((g("STATE") / "fit").read_text()) >= moment:
                return
        time.sleep(0.05)


def resize(page: Page, wide: str, high: str) -> str:
    # The holder owns the size: a verb's connection that ends clears the page's own size.
    # Written once the browser took it: a size it refuses would stop the holder.
    w, h = g("number")(wide), g("number")(high)
    page.set_viewport_size({"width": w, "height": h})
    (g("STATE") / "size.json").write_text(json.dumps({"width": w, "height": h}))
    return g("shown")(page, f"window is {wide} x {high}")


def screenshot(page: Page, name: str = "screen") -> str:
    if not re.fullmatch(r"[\w,-]+", name):
        raise g("Refused")(f'"{name}" is no name for a file: letters, digits, commas, - and _ only')
    path = g("STATE") / f"{name}.png"
    # The window and no more: its px are the px a TARGET is given in.
    page.screenshot(path=path)
    return str(path)


# The clash bar's words: it waits for one of its two buttons, which makes the file.
WAITS = "Danach kommt dein PDF"

CHOICES = ("Andere Version laden", "Mit dieser überschreiben")

WAIT_REFUSAL = (
    'the PDF waits for a choice in the clash bar: pdf "Andere Version laden" or '
    'pdf "Mit dieser überschreiben" makes it and saves the file'
)


def pdf(page: Page, target: str = "PDF") -> str:
    x, y = g("point")(page, target)
    had = page.evaluate_handle("document.activeElement")
    downloads: list = []

    def keep(download) -> None:
        downloads.append(download)

    # Once the bar says it waits, only one of its two buttons is a choice that makes the file.
    waiting = page.locator(".clash", has_text=WAITS).is_visible()
    if waiting and target not in CHOICES:
        raise g("Refused")(WAIT_REFUSAL)
    page.on("download", keep)
    try:
        page.mouse.click(x, y)
        late = time.monotonic() + 60
        while not downloads:
            # In a clash the PDF waits for the bar's choice: no file comes until one is made.
            if not waiting and page.locator(".clash", has_text=WAITS).is_visible():
                raise g("Refused")(WAIT_REFUSAL)
            if time.monotonic() > late:
                raise g("Refused")(f"no file came down after the click at {x:g},{y:g}")
            page.wait_for_timeout(100)
    finally:
        page.remove_listener("download", keep)
    coming = downloads[0]
    path = g("STATE") / Path(coming.suggested_filename).name
    coming.save_as(path)
    # The click gave the focus to the bar's button: a slider that had it takes the next key again.
    had.evaluate("el => el.focus()")
    return str(path)


DROP = """([x, y, name, type, b64]) => {
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(new File([bytes], name, { type }));
    const under = document.elementFromPoint(x, y);
    const init = { dataTransfer, clientX: x, clientY: y, bubbles: true, cancelable: true };
    for (const kind of ["dragenter", "dragover", "drop"]) {
        under.dispatchEvent(new DragEvent(kind, init));
    }
}"""


def drop(page: Page, file: str, target: str) -> str:
    """Drops a file of the run folder on the page, as a file dragged from the desktop is dropped."""
    # Playwright cannot drag a file from outside the browser: the bytes go in by the page instead.
    path = (g("STATE") / file).resolve()
    if not path.is_relative_to(g("STATE").resolve()):
        raise g("Refused")(
            f'"{file}" is outside the run folder {g("STATE")}: only its files can be dropped'
        )
    if not path.is_file():
        raise g("Refused")(f'there is no file "{file}" in {g("STATE")}')
    x, y = g("point")(page, target)
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode()
    page.evaluate(DROP, [x, y, path.name, kind, data])
    return g("shown")(page, f"dropped {path.name} at {x:g},{y:g}")


def upload(page: Page, file: str, target: str) -> str:
    """Clicks the target and picks a file of the run folder in the file box it opens."""
    path = (g("STATE") / file).resolve()
    if not path.is_relative_to(g("STATE").resolve()):
        raise g("Refused")(
            f'"{file}" is outside the run folder {g("STATE")}: only its files can be picked'
        )
    if not path.is_file():
        raise g("Refused")(f'there is no file "{file}" in {g("STATE")}')
    x, y = g("point")(page, target)
    try:
        with page.expect_file_chooser(timeout=3000) as chooser:
            # The browser learns of the listener on its own time: one call to the page first, or
            # the click may come before it and the file box opens past Playwright.
            page.evaluate("0")
            page.mouse.click(x, y)
    except Late:
        raise g("Refused")(
            f'"{target}" opened no file box: click the button that does, such as "Bild"'
        ) from None
    chooser.value.set_files(path)
    return g("shown")(page, f"uploaded {path.name} by the file box of {x:g},{y:g}")


# What a paste brings: the clipboard's types and words, and each file with its type and size, and
# its px where it is a picture.
RECORD = """() => {
    window.took = null;
    document.getElementById("field").addEventListener("paste", async (e) => {
        // Chromium empties the clipboard's data once this handler's first part ends: read it now.
        const data = e.clipboardData;
        const types = [...data.types];
        const words = data.getData("text/plain");
        const files = [...data.files];
        const pictures = [];
        try {
            for (const file of files) {
                const picture = { type: file.type, size: file.size };
                const img = new Image();
                img.src = URL.createObjectURL(file);
                try {
                    await img.decode();
                    picture.width = img.naturalWidth;
                    picture.height = img.naturalHeight;
                } catch (error) {
                    // Not a picture: the file is named by its type and size alone.
                }
                pictures.push(picture);
            }
        } finally {
            window.took = { types, words, pictures };
        }
    });
}"""


def close_tabs(page: Page) -> list[str]:
    """Closes each tab of the window that is not the app's page, and names each one it closed."""
    lines = []
    for other in page.context.pages:
        if other is not page and not other.is_closed():
            lines.append(
                f"A new tab opened on {other.url}; the tool closed it, the window stays on the app."
            )
            other.close()
    return lines


def paste_elsewhere(page: Page) -> str:
    """Pastes the clipboard into a field of another app, a second page of the browser, and says
    what the field took. The app's page keeps its focus."""
    other = page.context.new_page()
    try:
        other.set_content('<div id="field" contenteditable="true"></div>')
        other.evaluate(RECORD)
        other.focus("#field")
        other.keyboard.press("Control+v")
        with suppress(Late):
            other.wait_for_function("window.took !== null", timeout=2000)
        empty = {"types": [], "words": "", "pictures": []}
        took: dict = other.evaluate("window.took") or empty
    finally:
        other.close()
    page.bring_to_front()
    parts = []
    if took["words"]:
        parts.append(f'the words "{took["words"]}"')
    for picture in took["pictures"]:
        if "width" in picture:
            parts.append(f"a picture of {picture['width']} x {picture['height']} px")
        else:
            parts.append(f"a file of {picture['type'] or 'unknown type'}, {picture['size']} bytes")
    if parts:
        return f"another app's field took {' and '.join(parts)}"
    if took["types"]:
        return f"another app's field took only {', '.join(took['types'])}"
    return "another app's field took nothing: the clipboard is empty"


def expire(page: Page) -> str:
    """Ends the window's sign-in, as if its session had run out. The page stays as it is."""
    page.context.clear_cookies()
    return g("shown")(page, "the session has run out: the next action meets Anmelden")


def answered(page: Page, yes: bool) -> list[tuple[str, str]]:
    """Answers each box that opens on the page, yes or no. Returns what each asked: its kind and
    its words. A verb answers the boxes it meets; the holder answers those no verb met in time.
    """
    asked: list[tuple[str, str]] = []

    def answer(dialog) -> None:
        asked.append((dialog.type, dialog.message))
        if yes:
            dialog.accept()
        else:
            dialog.dismiss()

    page.on("dialog", answer)
    return asked


def remember(waiting: list) -> Callable[..., None]:
    """The holder's handler: keeps each box that opens, with the time it was seen."""

    def keep(dialog) -> None:
        waiting.append((dialog, time.monotonic()))

    return keep


def overdue(waiting: list, now: float) -> None:
    """Dismisses each box that has waited PATIENCE seconds, and drops it from the list. A box a
    verb answered first is answered already: the second answer raises, and that is no error.
    """
    for item in [item for item in waiting if now - item[1] >= g("PATIENCE")]:
        waiting.remove(item)
        with suppress(Error):
            item[0].dismiss()


def hold() -> None:
    """Keeps the window open until `stop` asks it to go. Runs under xvfb-run, started by `start`."""
    # A profile of its own each time: no login of an earlier run is left in it.
    profile = g("STATE") / "profile"
    shutil.rmtree(profile, ignore_errors=True)
    with sync_playwright() as p:
        # The profile's own context, the one a verb sees when it joins over the port.
        context = p.chromium.launch_persistent_context(
            profile,
            headless=False,
            viewport=g("VIEW"),
            device_scale_factor=1,
            accept_downloads=True,
            args=["--remote-debugging-port=0"],
        )
        # A teacher's Einfügen reads the clipboard: the window may do it without a question.
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        # A test that must still be unsaved after the next verbs says how long to wait. It is read
        # as the page is made, before the app's own scripts.
        if delay := os.environ.get("TEACHER_SAVE_AFTER"):
            context.add_init_script(f"window.saveAfter = {int(delay)}")
        # A box waits for the verb that meets it. The holder keeps each one and says no to any
        # that no verb answers within PATIENCE seconds.
        waiting: list = []
        context.on("dialog", remember(waiting))
        page = context.pages[0]
        page.goto(g("BASE"))
        # Chromium picked a free port and wrote it down.
        port = (profile / "DevToolsActivePort").read_text().split()[0]
        # From here on `stop` knows whom to ask, and its signal waits until it is read.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        state = {"pid": os.getpid(), "group": os.getpgid(0), "endpoint": f"http://127.0.0.1:{port}"}
        (g("STATE") / "page.tmp").write_text(json.dumps(state))
        (g("STATE") / "page.tmp").replace(g("STATE") / "page.json")
        # Playwright gets the browser's news only while one of its calls runs. So each second the
        # holder makes a call that does not touch the page, then says no to what is overdue.
        while signal.sigtimedwait({signal.SIGTERM}, 1.0) is None:
            context.cookies()
            overdue(waiting, time.monotonic())
            fit(page)
        context.close()


def fit(page: Page) -> None:
    """Puts the window back at its size, as each second does: a verb's connection ending clears it.
    Then it stamps the time, so a verb that joined before knows the size is back.
    """
    size = wanted()
    # A page that crashed says so to the next verb; the holder and its window stay.
    with suppress(Error):
        page.set_viewport_size({"width": size[0], "height": size[1]})
    (g("STATE") / "fit").write_text(str(time.time()))


def stop() -> bool:
    """Ends the holder, its browser and its xvfb. Says whether one ran."""
    state = g("running")()
    if not state:
        return False
    (g("STATE") / "page.json").unlink(missing_ok=True)
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
    g("STATE").mkdir(parents=True, exist_ok=True)
    (g("STATE") / "size.json").unlink(missing_ok=True)
    with (g("STATE") / "log").open("w") as log:
        # A session of its own: the window outlives this call and the shell that made it.
        child = subprocess.Popen(
            # A screen with room for the window on its side and upright: `resize 820 1180`.
            # The holder is this script's main, not this module: `running` knows it by that name.
            [
                "xvfb-run",
                "-a",
                "-s",
                "-screen 0 1920x1400x24",
                sys.executable,
                Path(__file__).resolve().parent / "teacher-page.py",
                "hold",
            ],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    late = time.monotonic() + 60
    while not (g("STATE") / "page.json").exists():
        if child.poll() is not None or time.monotonic() > late:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            said = (g("STATE") / "log").read_text().strip()[-2000:]
            raise g("Refused")(f"the window did not open on {g('BASE')}:\n{said}")
        time.sleep(0.1)
    g("began")()
    return f"started: a window of {g('VIEW')['width']} x {g('VIEW')['height']} on {g('BASE')}"
