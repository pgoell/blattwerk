"""Touches the tests send by hand: a swipe, a finger, and a hold that becomes a drag."""

import os
import re
from contextlib import contextmanager

from playwright.sync_api import expect

# The suite's browser, as ui.py reads it. WebKit has no debugging line for a touch.
BROWSER = os.environ.get("BLATTWERK_BROWSER", "chromium")


def swipe(page, *points):
    """Puts a finger down at the first point, moves it through the others and lifts it."""
    with finger(page, points[0]) as touch:
        for point in points[1:]:
            touch("touchMove", point)


# What Safari on an iPad sends for a touch: the pointer event, then the touch event, and the mouse's
# events only after a tap. A finger keeps the element it came down on, wherever it moves, so the
# page remembers it.
TOUCH = """([kind, points]) => {
    const held = (window.fingers ??= { on: [], at: [], tap: true });
    const known = held.on.length;
    points.forEach(([x, y], i) => (held.on[i] ??= document.elementFromPoint(x, y)));
    if (points.length) held.at = points;
    // WebKit on Linux has no `new Touch` and takes no array for a list, unlike Safari; the old
    // calls of the document make both.
    const list = (touches) => document.createTouchList(...touches);
    const all = held.at.map(([x, y], id) =>
        document.createTouch(window, held.on[id], id, x + scrollX, y + scrollY, x, y),
    );
    const over = kind === "touchEnd" || kind === "touchCancel";
    const changed = kind === "touchStart" ? all.slice(known) : all;
    if (!changed.length) return;
    if (over) window.fingers = undefined;
    // A lift is a tap when one finger stayed within 10 px of where it came down, and the page
    // kept neither the touch's start nor its end from the browser.
    const [fx, fy] = (held.from ??= held.at[0]);
    const far = Math.hypot(held.at[0][0] - fx, held.at[0][1] - fy) > 10;
    held.tap &&= all.length === 1 && !far;
    const pointer = {
        touchStart: "pointerdown",
        touchMove: "pointermove",
        touchEnd: "pointerup",
        touchCancel: "pointercancel",
    }[kind];
    for (const { target, identifier, clientX, clientY } of changed) {
        const init = { pointerId: identifier, pointerType: "touch", isPrimary: !identifier };
        const place = { clientX, clientY, buttons: over ? 0 : 1, bubbles: true, cancelable: true };
        target.dispatchEvent(new PointerEvent(pointer, { ...init, ...place }));
    }
    const on = changed[0].target;
    const touches = over ? [] : all;
    const init = {
        touches: list(touches),
        targetTouches: list(touches.filter((touch) => touch.target === on)),
        changedTouches: list(changed),
        bubbles: true,
        cancelable: true,
    };
    const kept = on.dispatchEvent(new TouchEvent(kind.toLowerCase(), init));
    // WebKit has no real touch, so the events above scroll nothing (#205). A finger moving up
    // or down the page list scrolls that panel, unless the page cancelled the touch: a drag
    // calls preventDefault, and that is what keeps the panel still.
    if (kind === "touchMove" && kept && held.pan !== false && held.at.length === 1) {
        const [x, y] = held.at[0];
        const [sx, sy] = held.from;
        if (!held.pan && Math.hypot(x - sx, y - sy) > 10) {
            const down = Math.abs(y - sy) > Math.abs(x - sx);
            const panel = down ? on.closest("aside.left") : null;
            let scroll = !!(panel && panel.scrollHeight > panel.clientHeight);
            for (let node = on; scroll && node; node = node.parentElement) {
                const action = getComputedStyle(node).touchAction;
                if (action === "none" || action === "pan-x") scroll = false;
                if (node === panel) break;
            }
            held.pan = scroll ? { panel, y: sy } : false;
        }
        if (held.pan) {
            held.pan.panel.scrollTop += held.pan.y - y;
            held.pan.y = y;
        }
    } else if (kind === "touchMove") held.pan = false;
    if (kind !== "touchMove") held.tap &&= kept;
    if (kind !== "touchEnd" || !held.tap) return;
    // A tap: Safari then sends the mouse's events too, where the finger came down.
    const [clientX, clientY] = held.from;
    for (const type of ["mousemove", "mousedown", "mouseup", "click"]) {
        const press = { buttons: +(type === "mousedown"), detail: +(type !== "mousemove") };
        const mouse = { clientX, clientY, view: window, bubbles: true, cancelable: true, ...press };
        held.on[0].dispatchEvent(new MouseEvent(type, mouse));
    }
}"""


@contextmanager
def finger(page, start):
    """A finger down at the start for as long as the block runs. Gives the way to send touches."""
    # Playwright's own touchscreen only taps, so the browser is told of each touch by hand: Chromium
    # over its debugging line, WebKit, which has none, by the events themselves. The page list's
    # scroll goes with those events: a touch the page dispatched scrolls nothing on its own.
    session = None if BROWSER == "webkit" else page.context.new_cdp_session(page)
    cancelled = []
    began = 0

    def touch(kind, *at):
        nonlocal began
        if kind == "touchCancel":
            cancelled.append(kind)
        # A finger that comes down again after a cancel is a new touch, and it lifts.
        if kind == "touchStart":
            began += 1
        if session:
            touched = [{"x": x, "y": y} for x, y in at]
            session.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": touched})
        else:
            page.evaluate(TOUCH, [kind, at])

    touch("touchStart", start)
    yield touch
    # A cancelled touch has no lift to send. One that came down again after the cancel does.
    if began > 1 or not cancelled:
        touch("touchEnd")
    if session:
        session.detach()


def jitter(held, start, *by):
    """Tells `held` that the finger on it lies off the start by each of `by`, in px."""
    # Chrome keeps a finger's moves from the page until it is more than 15 px from where it came
    # down. Safari on an iPad does not, so the page is told by hand, as it is there.
    for dx, dy in by:
        if BROWSER == "webkit":
            # WebKit keeps no move back, so the finger that is down just moves.
            held.page.evaluate(TOUCH, ["touchMove", [(start[0] + dx, start[1] + dy)]])
            continue
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
