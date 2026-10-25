"""A real window with a real mouse, for the session that only uses the app (docs/teacher-run.md).

    mise -C /home/pascal/Code/blattwerk run teacher:page -- <verb> [args]

    start                  opens the window, 1280 x 1024, on the stage; a second start replaces it
    stop                   shuts the window
    open PATH              goes to a path of the app: / or /blatt/12, never /admin
    click TARGET           also: double-click TARGET, shift-click TARGET, hover TARGET
    drag FROM TO           presses the mouse at FROM, moves it to TO and lets go
    key-drag KEY FROM TO   holds KEY, drags from FROM to TO and lets the key go. Space pans
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

import inspect
import json
import os
import posixpath
import re
import shlex
import sys
import time
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote, urlsplit

from playwright.sync_api import ElementHandle, Error, Locator, Page, sync_playwright
from playwright.sync_api import TimeoutError as Late


def _load(name):
    """Loads a sibling module by path and registers it, so the verbs share this process."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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
# A disabled button in the panel has pointer-events: none, so elementFromPoint falls through it.
GREYED = """([x, y]) => {
    const near = "button, input, select, textarea, [aria-disabled]";
    const grey = (el) =>
        !!el && (el.disabled === true || el.getAttribute("aria-disabled") === "true");
    if (grey(document.elementFromPoint(x, y)?.closest(near))) return true;
    for (const el of document.querySelectorAll(near)) {
        if (!grey(el)) continue;
        const r = el.getBoundingClientRect();
        if (Math.hypot(r.left + r.width / 2 - x, r.top + r.height / 2 - y) <= 1) return true;
    }
    return false;
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


_ns = _load("teacher_page_ns")
_acts = _load("teacher_page_acts")
_keys = _load("teacher_page_keys")
_clock = _load("teacher_page_clock")
click = _acts.click
double_click = _acts.double_click
shift_click = _acts.shift_click
hover = _acts.hover
ends = _acts.ends
drag = _acts.drag
middle_drag = _acts.middle_drag


def key_drag(page: Page, key: str, start: str, end: str) -> str:
    """Holds KEY, drags, and lets the key go. Space held is the hand that pans the desk."""
    (x, y), to = ends(page, start, end)
    # The key is down before the press, as a hand holds Space, and up again however the drag ends.
    page.mouse.move(x, y)
    page.keyboard.down(key)
    try:
        page.mouse.down()
        page.mouse.move(*to, steps=10)
        page.mouse.up()
    finally:
        page.keyboard.up(key)
    return shown(page, f"dragged with {key} held from {x:g},{y:g} to {to[0]:g},{to[1]:g}")


swipe = _acts.swipe
wheel = _acts.wheel
key = _keys.key
type_ = _keys.type_
began = _clock.began
clock = _clock.clock
where = _acts.where
value = _acts.value
wanted = _acts.wanted
holder_since = _acts.holder_since
resize = _acts.resize
screenshot = _acts.screenshot
WAITS = _acts.WAITS
CHOICES = _acts.CHOICES
WAIT_REFUSAL = _acts.WAIT_REFUSAL
pdf = _acts.pdf
DROP = _acts.DROP
drop = _acts.drop
upload = _acts.upload
RECORD = _acts.RECORD
close_tabs = _acts.close_tabs
paste_elsewhere = _acts.paste_elsewhere
expire = _acts.expire
answered = _acts.answered
remember = _acts.remember
overdue = _acts.overdue
hold = _acts.hold
fit = _acts.fit
stop = _acts.stop
start = _acts.start
_ns.bind(globals())


VERBS: dict[str, Callable[..., str]] = {
    "open": go,
    "click": click,
    "double-click": double_click,
    "shift-click": shift_click,
    "hover": hover,
    "drag": drag,
    "key-drag": key_drag,
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
    return "\n".join([said, *closed, *lines, clock(), place])


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
