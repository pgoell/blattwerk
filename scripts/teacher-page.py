"""A real window with a real mouse, for the session that only uses the app (docs/teacher-run.md).

    mise -C /home/pascal/Code/blattwerk run teacher:page -- <verb> [args]

    start                  opens the window, 1280 x 1024, on the stage; a second start replaces it
    stop                   shuts the window
    open PATH              goes to a path of the app: / or /blatt/12, never /admin
    click TARGET           also: double-click TARGET, shift-click TARGET, hover TARGET
    drag FROM TO           presses the mouse at FROM, moves it to TO and lets go
    middle-drag FROM TO    the same with the middle button held: it pans the desk
    swipe FROM TO          a finger put down at FROM, moved to TO and lifted; from an edge it
                           opens a drawer, upright only
    wheel TARGET DY        turns the wheel over TARGET by DY px; less than 0 is up
    key KEYS [N]           presses a key or a chord N times: Escape, ArrowRight, Control+z
    type TEXT              types the text where the focus is
    drop FILE TARGET       drops a file of the run folder on the page at TARGET, as from the desktop
    upload FILE TARGET     clicks TARGET and picks a file of the run folder in the file box it opens
    paste-elsewhere        pastes the clipboard into another app's field; says what it took
    where NAME             prints where the name is on the page, or what holds it; changes nothing
    value NAME             prints what the field of that name holds: a colour, a slider's number
    resize W H             sets the window's size
    screenshot [NAME]      writes the window to NAME.png, `screen` if none
    pdf [TARGET]           clicks the bar's `PDF`, or `Lösungen`, and saves what comes down; the
                           focus stays where it was
    expire                 ends the window's sign-in, as if the session had run out; the page stays
    box yes VERB [ARGS]    runs VERB and answers the box it meets with yes; `box no` answers no
    tidy                   deletes each TR*.pdf and blattomat*.mcpb in ~/Downloads and each PDF
                           in the folder, and names each with its folder; needs no window

A box that a verb meets is answered no unless `box yes` asks yes, and the output names its words.

A TARGET is `X,Y`, in px of the window, which are the px of the screenshot, or a name: the words
on a control, its label, or what a hover or a screen reader says of it. A name must be on the page
once, or once as a control beside plain text of that name. A name below or above the window turns
the page to it when it is that one place, and a heading of the same name does not stop the turn.
A control in an open dialog is taken over one of the same name that the dialog covers. Every verb
that acts also writes the window to last.png and prints that path. Every verb of the window prints
the page's path, `The page is /blatt/12`.

One process, `hold`, keeps the window under xvfb-run, and each verb joins it over Chromium's
debugging port. Python's Playwright has no `launch_server`, and a context that a client makes
ends with that client: so the holder owns the page, and the mouse stays where a verb left it.

The files lie in /tmp/teacher-run, or where TEACHER_PAGE_DIR says. The window opens on the stage,
http://127.0.0.1:8220; TEACHER_PAGE_URL names another server, for the tests only. TEACHER_SAVE_AFTER
is how long, in ms, a change waits before it is saved. A teacher's page has none and waits 2 s.
"""

import base64
import inspect
import json
import mimetypes
import os
import posixpath
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

from playwright.sync_api import ElementHandle, Error, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as Late

STATE = Path(os.environ.get("TEACHER_PAGE_DIR", "/tmp/teacher-run"))
BASE = os.environ.get("TEACHER_PAGE_URL", "http://127.0.0.1:8220")
VIEW = {"width": 1280, "height": 1024}
XY = re.compile(r"(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)")
# Seconds a box may wait for the verb that meets it. Then the holder says no, and the page is free.
PATIENCE = 3.0
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
    # A file that is cut short or holds something else names no holder either.
    except OSError, ValueError, KeyError, TypeError:
        return None
    # By the script's name, not its path: another checkout's holder is one too.
    script = Path(__file__).name.encode()
    return state if any(w.endswith(script) for w in words) and b"hold" in words else None


# What an element is called, each with its spaces made one: its label, title, placeholder and alt
# text, the words of the <label> that names it, and last its own words.
CALLED = """el => [
    ...["aria-label", "title", "placeholder", "alt"].map((a) => el.getAttribute(a) ?? ""),
    ...[...(el.labels ?? [])].map((l) => l.textContent ?? ""),
    el.tagName === "SELECT" ? "" : el.textContent ?? "",
].map((s) => s.split(/\\s+/).filter(Boolean).join(" "))"""
# The things a teacher clicks: a click on one of them is the control the name means.
CONTROLS = (
    "button, input, select, textarea, summary, a[href], [role=button], [role=tab], [role=switch], "
    "[role=checkbox], [role=radio], [role=combobox], [role=slider], [role=option], [role=menuitem]"
)
# Where a verb turned the page to a name that lay below or above the window.
NOTES: list[str] = []


class Found(NamedTuple):
    """A place of a name: its middle in px, the name it shows, whether it is a control."""

    x: int
    y: int
    shown: str
    control: bool
    el: ElementHandle


def named(page: Page, name: str | re.Pattern) -> Locator:
    """Each visible thing of that name, by what a user reads or hears only."""
    found = page.get_by_label(name, exact=True)
    for by in (page.get_by_title, page.get_by_placeholder, page.get_by_alt_text):
        found = found.or_(by(name, exact=True))
    # A select's text is its options run together: a text is never a select or an option.
    texts = page.get_by_text(name, exact=True).and_(page.locator(":not(select, option)"))
    return found.or_(texts).filter(visible=True)


def pattern(name: str) -> re.Pattern:
    """The name as Playwright writes it into a selector: its slash, quote and backslash escaped."""
    return re.compile(re.escape(name).replace("/", r"\/").replace('"', r"\""))


def places(page: Page, name: str, part: bool = False) -> list[Found]:
    """The middle of each visible thing of that name, and the name it shows. With `part`, and
    where no whole name matches, of each thing whose text holds it, shown as that text with
    capitals as written.
    """
    whole = named(page, name)
    found = whole.or_(named(page, pattern(name))) if part else whole
    try:
        found.first.wait_for(timeout=3000)
    except Late:
        # A narrow bar folds its commands away.
        more = ': it may lie under "Mehr"' if named(page, "Mehr").count() else ""
        raise Refused(f'nothing on the page is called "{name}"{more}') from None
    matched_whole = whole.count() > 0
    if matched_whole:
        found = whole
    handles = [one.element_handle() for one in found.all()]
    kept = page.evaluate(KEPT, handles)
    out = []
    for el in [el for el, keep in zip(handles, kept, strict=True) if keep]:
        box = el.bounding_box()
        if not box:
            continue
        # A control is called by its label, its title or its placeholder, a text by its words: the
        # first of them that holds the name is what the user reads there.
        shown = name if matched_whole else next((s for s in el.evaluate(CALLED) if name in s), name)
        control = el.evaluate("(el, sel) => el.matches(sel)", CONTROLS)
        middle = (round(box["x"] + box["width"] / 2), round(box["y"] + box["height"] / 2))
        out.append(Found(*middle, shown, control, el))
    return out


def inside(page: Page, x: float, y: float) -> bool:
    wide, high = page.evaluate("[innerWidth, innerHeight]")
    return 0 <= x < wide and 0 <= y < high


def in_dialog(found: Found) -> bool:
    """Whether the place lies in an open modal dialog, the layer a click can hit."""
    return found.el.evaluate(
        """el => {
            const dialog = el.closest("dialog");
            return !!dialog && dialog.open && dialog.matches(":modal");
        }"""
    )


def meant(spots: list[Found]) -> Found | None:
    """The place a name means, or nothing where several stay.

    The only control wins over a heading of the same name, wherever it lies. Failing that, the
    only control in an open modal dialog wins over one the dialog covers. A lone text is taken.
    Two controls with no dialog between them, or two texts, are not one place.
    """
    controls = [spot for spot in spots if spot.control]
    if len(controls) == 1:
        return controls[0]
    dialog = [spot for spot in controls if in_dialog(spot)]
    if len(dialog) == 1:
        return dialog[0]
    if len(spots) == 1:
        return spots[0]
    return None


def point(page: Page, target: str) -> tuple[float, float]:
    """The place in the window that the target names."""
    if at := XY.fullmatch(target):
        return float(at[1]), float(at[2])
    spots = places(page, target)
    choice = meant(spots)
    if choice is not None and not inside(page, choice.x, choice.y):
        # The one place lies below or above the window: the page turns to it. A heading of the
        # same name does not make it two places, so the turn still happens.
        choice.el.evaluate("el => el.scrollIntoView({block: 'center'})")
        NOTES.append("turned the page to it")
        spots = places(page, target)
        choice = meant(spots)
    seen = [spot for spot in spots if inside(page, spot.x, spot.y)]
    if choice is not None and inside(page, choice.x, choice.y):
        return choice.x, choice.y
    listed = ", ".join(f"{s.x},{s.y}" for s in seen or spots)
    if choice is not None or not seen:
        raise Refused(f'"{target}" lies outside the window, at {listed}: scroll to it')
    if len(seen) > 1:
        # A bar's button and a panel's heading may share a name, as "Text" does with a text picked.
        # Two controls, or none, stay a refusal: the caller gives one as X,Y.
        raise Refused(f'"{target}" is on the page {len(seen)} times, at {listed}: give one as X,Y')
    return seen[0].x, seen[0].y


def number(text: str, kind: Callable = int):
    try:
        return kind(text)
    except ValueError:
        raise Refused(f'"{text}" is not a number') from None


def shown(page: Page, did: str) -> str:
    """Writes the window to last.png, so the call that acts also shows what came of it."""
    path = STATE / "last.png"
    page.screenshot(path=path)
    turned = " (turned the page to it)" if NOTES else ""
    NOTES.clear()
    return f"{did}: {path}{turned}"


# The control at a place, when it is greyed out: a mouse still clicks it, and nothing happens.
GREYED = """([x, y]) => {
    const near = "button, input, select, textarea, [aria-disabled]";
    const el = document.elementFromPoint(x, y)?.closest(near);
    return !!el && (el.disabled === true || el.getAttribute("aria-disabled") === "true");
}"""


def greyed(page: Page, x: float, y: float) -> str:
    """What the click says of a greyed control at its place, or nothing."""
    return ", on a greyed control: nothing happens" if page.evaluate(GREYED, [x, y]) else ""


def here(page: Page) -> str:
    """The path and query of the page, so `open` can go back to it."""
    way = urlsplit(page.url)
    return f"The page is {way.path}" + (f"?{way.query}" if way.query else "")


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
    grey = greyed(page, x, y)
    page.mouse.click(x, y)
    return shown(page, f"clicked at {x:g},{y:g}{grey}")


def double_click(page: Page, target: str) -> str:
    x, y = point(page, target)
    grey = greyed(page, x, y)
    page.mouse.dblclick(x, y)
    return shown(page, f"double-clicked at {x:g},{y:g}{grey}")


def shift_click(page: Page, target: str) -> str:
    x, y = point(page, target)
    grey = greyed(page, x, y)
    page.keyboard.down("Shift")
    page.mouse.click(x, y)
    page.keyboard.up("Shift")
    return shown(page, f"shift-clicked at {x:g},{y:g}{grey}")


def hover(page: Page, target: str) -> str:
    x, y = point(page, target)
    page.mouse.move(x, y)
    return shown(page, f"mouse at {x:g},{y:g}")


def ends(page: Page, start: str, end: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """FROM and TO in px. The page may turn to TO, so FROM is read again: both must show at once."""
    x, y = point(page, start)
    to = point(page, end)
    if NOTES:
        # The page turned to TO, so FROM stands elsewhere now. Both must be in the window at once.
        NOTES.clear()
        x, y = point(page, start)
        if NOTES:
            raise Refused(f'"{start}" and "{end}" are not in the window together: give X,Y')
        NOTES.append("turned the page to it")
    return (x, y), to


def drag(page: Page, start: str, end: str) -> str:
    (x, y), to = ends(page, start, end)
    page.mouse.move(x, y)
    page.mouse.down()
    # The editor follows the moves between the two, not a jump.
    page.mouse.move(*to, steps=10)
    page.mouse.up()
    return shown(page, f"dragged from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


def middle_drag(page: Page, start: str, end: str) -> str:
    (x, y), to = ends(page, start, end)
    page.mouse.move(x, y)
    page.mouse.down(button="middle")
    page.mouse.move(*to, steps=10)
    page.mouse.up(button="middle")
    return shown(page, f"middle-dragged from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


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
    return shown(page, f"swiped from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


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
    found = places(page, name, part=True)
    return "\n".join(
        f"{one.shown} at {one.x},{one.y}"
        + ("" if inside(page, one.x, one.y) else " (outside the window)")
        for one in found
    )


def value(page: Page, name: str) -> str:
    """What a field holds: a colour as `#rrggbb`, a slider's or a number field's number."""
    found = page.get_by_label(name, exact=True).filter(visible=True)
    try:
        return f"{name} is {found.input_value(timeout=3000)}"
    # No field of that name, several, or a button that holds nothing.
    except Error:
        raise Refused(f'no field on the page is called "{name}"') from None


def wanted() -> list[int]:
    """The size the holder keeps the window at: what `resize` wrote last, else VIEW."""
    try:
        size = json.loads((STATE / "size.json").read_text())
        return [size["width"], size["height"]]
    except OSError, ValueError, KeyError:
        return [VIEW["width"], VIEW["height"]]


def holder_since(moment: float) -> None:
    """Waits until the holder has put the size back after `moment`, for up to 3 s. Reads no page,
    so a box that is open does not hold it.
    """
    late = time.monotonic() + 3
    while time.monotonic() < late:
        with suppress(OSError, ValueError):
            if float((STATE / "fit").read_text()) >= moment:
                return
        time.sleep(0.05)


def resize(page: Page, wide: str, high: str) -> str:
    # The holder owns the size: a verb's connection that ends clears the page's own size.
    # Written once the browser took it: a size it refuses would stop the holder.
    w, h = number(wide), number(high)
    page.set_viewport_size({"width": w, "height": h})
    (STATE / "size.json").write_text(json.dumps({"width": w, "height": h}))
    return shown(page, f"window is {wide} x {high}")


def screenshot(page: Page, name: str = "screen") -> str:
    if not re.fullmatch(r"[\w,-]+", name):
        raise Refused(f'"{name}" is no name for a file: letters, digits, commas, - and _ only')
    path = STATE / f"{name}.png"
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
    x, y = point(page, target)
    had = page.evaluate_handle("document.activeElement")
    downloads: list = []

    def keep(download) -> None:
        downloads.append(download)

    # Once the bar says it waits, only one of its two buttons is a choice that makes the file.
    waiting = page.locator(".clash", has_text=WAITS).is_visible()
    if waiting and target not in CHOICES:
        raise Refused(WAIT_REFUSAL)
    page.on("download", keep)
    try:
        page.mouse.click(x, y)
        late = time.monotonic() + 60
        while not downloads:
            # In a clash the PDF waits for the bar's choice: no file comes until one is made.
            if not waiting and page.locator(".clash", has_text=WAITS).is_visible():
                raise Refused(WAIT_REFUSAL)
            if time.monotonic() > late:
                raise Refused(f"no file came down after the click at {x:g},{y:g}")
            page.wait_for_timeout(100)
    finally:
        page.remove_listener("download", keep)
    coming = downloads[0]
    path = STATE / Path(coming.suggested_filename).name
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
    path = (STATE / file).resolve()
    if not path.is_relative_to(STATE.resolve()):
        raise Refused(f'"{file}" is outside the run folder {STATE}: only its files can be dropped')
    if not path.is_file():
        raise Refused(f'there is no file "{file}" in {STATE}')
    x, y = point(page, target)
    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = base64.b64encode(path.read_bytes()).decode()
    page.evaluate(DROP, [x, y, path.name, kind, data])
    return shown(page, f"dropped {path.name} at {x:g},{y:g}")


def upload(page: Page, file: str, target: str) -> str:
    """Clicks the target and picks a file of the run folder in the file box it opens."""
    path = (STATE / file).resolve()
    if not path.is_relative_to(STATE.resolve()):
        raise Refused(f'"{file}" is outside the run folder {STATE}: only its files can be picked')
    if not path.is_file():
        raise Refused(f'there is no file "{file}" in {STATE}')
    x, y = point(page, target)
    try:
        with page.expect_file_chooser(timeout=3000) as chooser:
            # The browser learns of the listener on its own time: one call to the page first, or
            # the click may come before it and the file box opens past Playwright.
            page.evaluate("0")
            page.mouse.click(x, y)
    except Late:
        raise Refused(
            f'"{target}" opened no file box: click the button that does, such as "Bild"'
        ) from None
    chooser.value.set_files(path)
    return shown(page, f"uploaded {path.name} by the file box of {x:g},{y:g}")


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
    return shown(page, "the session has run out: the next action meets Anmelden")


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
    for item in [item for item in waiting if now - item[1] >= PATIENCE]:
        waiting.remove(item)
        with suppress(Error):
            item[0].dismiss()


def tidy() -> str:
    """Deletes each TR*.pdf and blattomat*.mcpb directly in the downloads folder and each PDF in
    the tool's folder, and names each one it deleted with its folder.
    """
    downloads = Path(os.environ.get("TEACHER_PAGE_DOWNLOADS", Path.home() / "Downloads"))
    found = sorted(path for path in downloads.glob("TR*.pdf") if path.is_file())
    found += sorted(path for path in downloads.glob("blattomat*.mcpb") if path.is_file())
    found += sorted(path for path in STATE.glob("*.pdf") if path.is_file())
    for path in found:
        path.unlink()
    if not found:
        return "nothing to delete"
    return "\n".join(f"deleted {path.parent.name}/{path.name}" for path in found)


VERBS: dict[str, Callable[..., str]] = {
    "open": go,
    "click": click,
    "double-click": double_click,
    "shift-click": shift_click,
    "hover": hover,
    "drag": drag,
    "middle-drag": middle_drag,
    "swipe": swipe,
    "wheel": wheel,
    "key": key,
    "type": type_,
    "drop": drop,
    "upload": upload,
    "paste-elsewhere": paste_elsewhere,
    "where": where,
    "value": value,
    "resize": resize,
    "screenshot": screenshot,
    "pdf": pdf,
    "expire": expire,
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
        page.goto(BASE)
        # Chromium picked a free port and wrote it down.
        port = (profile / "DevToolsActivePort").read_text().split()[0]
        # From here on `stop` knows whom to ask, and its signal waits until it is read.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTERM})
        state = {"pid": os.getpid(), "group": os.getpgid(0), "endpoint": f"http://127.0.0.1:{port}"}
        (STATE / "page.tmp").write_text(json.dumps(state))
        (STATE / "page.tmp").replace(STATE / "page.json")
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
    (STATE / "fit").write_text(str(time.time()))


def stop() -> bool:
    """Ends the holder, its browser and its xvfb. Says whether one ran."""
    state = running()
    if not state:
        return False
    (STATE / "page.json").unlink(missing_ok=True)
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
    (STATE / "size.json").unlink(missing_ok=True)
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
        joining = time.time()
        browser = p.chromium.connect_over_cdp(state["endpoint"])
        # The holder puts the size back within a second of the last verb's connection ending.
        holder_since(joining)
        yield browser.contexts[0].pages[0]


def verb(name: str, args: tuple[str, ...], yes: bool) -> str:
    """Runs a verb of the window. Each box it meets is answered, and the output names it."""
    if name not in VERBS:
        known = ", ".join(["start", "stop", *VERBS, "box", "tidy"])
        raise Refused(f'no verb "{name}": there are {known}')
    try:
        inspect.signature(VERBS[name]).bind(None, *args)
    except TypeError:
        takes = " ".join(list(inspect.signature(VERBS[name]).parameters)[1:]).upper()
        raise Refused(f"{name} takes: {takes}") from None
    NOTES.clear()
    with joined() as page:
        asked = answered(page, yes)
        # A tab left open would be the next verb's page: it goes also when the verb fails.
        try:
            try:
                said = VERBS[name](page, *args)
            except Error as error:
                # A box answered no stops the navigation it came with: the page stays where it is.
                if not asked or yes or "ERR_ABORTED" not in error.message:
                    raise
                said = f"the page stayed on {page.url}"
        finally:
            closed = close_tabs(page)
        place = here(page)
    lines = []
    for kind, text in asked:
        word = "yes" if yes else "no"
        line = f'A box asked: "{text}" ({kind}). Answered {word}.'
        if not yes:
            line += f" To say yes: box yes {shlex.join([name, *args])}"
        lines.append(line)
    return "\n".join([said, *closed, *lines, place])


def main(name: str = "", *args: str) -> str:
    if name == "hold":
        hold()
        return ""
    if name == "start":
        return start()
    if name == "stop":
        return "stopped" if stop() else "no page was running"
    if name == "tidy":
        return tidy()
    if name == "box":
        if len(args) < 2 or args[0] not in ("yes", "no"):
            raise Refused('box takes yes or no, then a verb: box yes click "Löschen"')
        return verb(args[1], args[2:], args[0] == "yes")
    return verb(name, args, False)


if __name__ == "__main__":
    try:
        print(main(*sys.argv[1:]))
    except Refused as error:
        sys.exit(str(error))
    except Error as error:
        # Playwright's own words, without its log of calls.
        sys.exit(error.message.splitlines()[0])
