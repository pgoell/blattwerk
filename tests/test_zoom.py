"""Ctrl and the wheel zoom about the pointer, Space and a drag move the desk, "Ganze Seite" fits."""

import math
import re

import pytest
from playwright.sync_api import expect
from test_drop import spot
from ui import (
    BROWSER,
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    centre,
    drag,
    maths,
    picture,
    upload,
)

PAN = re.compile(r"\bpan\b")
PANNING = re.compile(r"\bpanning\b")
# The overlay that takes the drag while Space is down.
HAND = ".stage > .hand"
# A block with room around it, well inside the page.
PLACE = {"x": 60, "y": 60, "w": 60, "h": 40}
KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group"]
# After the app's own listener: whether the last wheel was kept from the browser.
WATCH = (
    "addEventListener('wheel', (e) => setTimeout(() => (window.kept = e.defaultPrevented)), true)"
)
INSIDE = """(n) => {
    const s = document.querySelector(`.sheet[data-page="${n}"]`).getBoundingClientRect();
    const d = document.querySelector(".desk").getBoundingClientRect();
    const down = s.top >= d.top - 1 && s.bottom <= d.bottom + 1;
    return down && s.left >= d.left - 1 && s.right <= d.right + 1;
}"""
WIDE = "(w) => Math.abs(document.querySelector('.sheet.on').getBoundingClientRect().width - w) < 2"


def width(page):
    """The width on the screen of the page in use, in px."""
    return page.locator(".sheet.on").evaluate("el => el.getBoundingClientRect().width")


def expect_width(page, wide):
    """Waits until the page in use is this wide."""
    page.wait_for_function(WIDE, arg=wide)


def percent(page):
    return int(page.locator("button.zoom").first.inner_text().split()[0])


def page_width(page):
    """Picks "Seitenbreite" in the zoom list: the page is as wide as on paper."""
    page.locator("button.zoom").first.click()
    page.locator("dialog:modal").get_by_role("menuitem", name="Seitenbreite", exact=True).click()


def expect_percent(page):
    """The percent button shows the page's size on the screen against its size on paper."""
    assert percent(page) == pytest.approx(width(page) / 210 * 2540 / 96, abs=1)


def wheel(page, delta, point=None, ctrl=True):
    """Turns the wheel over the point, the desk's middle if none: -100 is one step in, 100 out."""
    page.mouse.move(*(point or centre(page.locator(".desk"))))
    if ctrl:
        page.keyboard.down("Control")
    page.mouse.wheel(0, delta)
    if ctrl:
        page.keyboard.up("Control")


def pinch(page, delta, point):
    """A trackpad pinch: Ctrl and a wheel whose delta is not a whole number.

    Chromium delivers that delta as it is. WebKit rounds a wheel it is sent to a
    whole number, and a whole delta is a notch, so there the page sends the event.
    """
    if BROWSER != "webkit":
        wheel(page, delta, point)
        return
    page.mouse.move(*point)
    page.evaluate(
        """([x, y, delta]) => {
            const el = document.elementFromPoint(x, y);
            el.dispatchEvent(new WheelEvent("wheel", {
                deltaX: 0, deltaY: delta, ctrlKey: true, bubbles: true, cancelable: true,
                clientX: x, clientY: y,
            }));
        }""",
        [*point, delta],
    )


def kept(page):
    """Whether the page kept the last wheel from the browser, once that wheel has arrived."""
    page.wait_for_function("window.kept !== undefined")
    return page.evaluate("() => { const was = window.kept; delete window.kept; return was; }")


def scroll(page):
    return page.locator(".desk").evaluate("el => [el.scrollLeft, el.scrollTop]")


def expect_scroll(page, left, top):
    page.wait_for_function(
        """([left, top]) => {
            const desk = document.querySelector(".desk");
            return Math.abs(desk.scrollLeft - left) < 1 && Math.abs(desk.scrollTop - top) < 1;
        }""",
        arg=[left, top],
    )


def settled(page):
    """Waits for the browser to draw twice: what a key or a wheel scrolls has scrolled by then."""
    page.evaluate(
        "() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
    )


def roomy(page):
    """Zooms in two steps, so the desk scrolls both ways, and scrolls it away from its corner."""
    wide = width(page)
    for step in (1.25, 1.25**2):
        page.get_by_label("Größer", exact=True).first.click()
        expect_width(page, wide * step)
    # Space on a button is a click on it: the focus goes, as a click on the desk takes it.
    page.evaluate("document.activeElement.blur()")
    page.locator(".desk").evaluate("el => el.scrollTo(200, 200)")
    left, top = scroll(page)
    assert left >= 150 and top >= 150
    return left, top


def pan(page, start, across, down):
    """Holds Space and drags from the point. Waits until the desk has gone along."""
    left, top = scroll(page)
    drag(page, start, (start[0] + across, start[1] + down), keys=["Space"])
    expect_scroll(page, left - across, top - down)


def places(page, *names):
    """Where the blocks lie on their page and how large, in px."""
    held = page.locator(".sheet.on").bounding_box()
    found = [at(page, name).bounding_box() for name in names]
    return [(b["x"] - held["x"], b["y"] - held["y"], b["width"], b["height"]) for b in found]


def expect_in_place(page, names, before):
    assert places(page, *names) == [pytest.approx(place, abs=1) for place in before]


def fit(page):
    return page.get_by_label("Ganze Seite", exact=True).first


def expect_fitted(page, n, w, h):
    """Waits until page n, of w by h mm, lies whole in the desk, as large as its padding lets it."""
    page.wait_for_function(INSIDE, arg=n)
    room = page.locator(".desk").evaluate("el => [el.clientWidth - 64, el.clientHeight - 120]")
    k = min(room[0] / w, room[1] / h)
    held = page.locator(f'.sheet[data-page="{n}"]').bounding_box()
    assert (held["width"], held["height"]) == pytest.approx((w * k, h * k), abs=3)


def of_kind(kind, client):
    """The blocks of one kind: one named "a", and for a group "a" and "b"."""
    if kind == "group":
        low = {**PLACE, "y": 110}
        return [
            box("a", "shape", RECT, **PLACE, group=["g"]),
            box("b", "shape", RECT, z=2, **low, group=["g"]),
        ]
    if kind == "picture":
        return [{**picture(upload(client)), "id": "a", **PLACE}]
    if kind == "maths":
        return [box("a", "maths", maths(client), **{**PLACE, "h": 12})]
    props = {"text": TEXT, "shape": RECT, "line": LINE, "table": TABLE, "ruling": RULING}[kind]
    return [box("a", "shape" if kind == "line" else kind, props, **PLACE)]


def test_ctrl_wheel_zooms_in_and_out(editor):
    """A1"""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    wheel(page, -100)
    expect_width(page, wide * 1.25)
    wheel(page, 100)
    expect_width(page, wide)
    wheel(page, 100)
    expect_width(page, wide / 1.25)
    expect_percent(page)


def expect_under(page, point, mm, wide, n=0):
    """Waits until page n, an A4 page, is this wide with these mm of it at the point, to 0.5 mm."""
    page.wait_for_function(
        """([x, y, across, down, wide, n]) => {
            const r = document.querySelector(`.sheet[data-page="${n}"]`).getBoundingClientRect();
            const off = [(x - r.x) / (r.width / 210) - across, (y - r.y) / (r.width / 210) - down];
            return Math.abs(r.width - wide) < 2 && Math.abs(off[0]) < 0.5 && Math.abs(off[1]) < 0.5;
        }""",
        arg=[*point, *mm, wide, n],
    )


# Asked #164


def test_a_trackpad_pinch_follows_the_fingers(editor):
    """A pinch whose delta is not a whole number grows the page with the fingers.

    Chrome sends about -100 * ln(scale). A whole notch stays one step of the buttons.
    """
    page = editor(box("a", "text", TEXT))
    roomy(page)
    wide = width(page)
    point = spot(page, 60, 80)
    assert page.evaluate(
        "([x, y]) => !!document.elementFromPoint(x, y).closest('.sheet.on')", point
    )
    # Four small events, as a trackpad sends them: together the fingers have doubled.
    step = -100 * math.log(2) / 4
    for n in range(1, 5):
        pinch(page, step, point)
        expect_under(page, point, (60, 80), wide * 2 ** (n / 4))
    for n in range(3, -1, -1):
        pinch(page, -step, point)
        expect_under(page, point, (60, 80), wide * 2 ** (n / 4))
    # The same doubling in one event, then back.
    pinch(page, -100 * math.log(2), point)
    expect_under(page, point, (60, 80), wide * 2)
    pinch(page, 100 * math.log(2), point)
    expect_under(page, point, (60, 80), wide)
    # A mouse wheel's notch is a whole number.
    wheel(page, -100, point)
    expect_under(page, point, (60, 80), wide * 1.25)
    wheel(page, 100, point)
    expect_under(page, point, (60, 80), wide)


def test_ctrl_wheel_keeps_the_point_under_the_pointer(editor):
    """A2"""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    wide = width(page)
    # Off the page's middle and off the desk's.
    point = spot(page, 60, 80)
    assert page.evaluate(
        "([x, y]) => !!document.elementFromPoint(x, y).closest('.sheet.on')", point
    )
    for delta, to in ((-100, 1.25), (-100, 1.25**2), (100, 1.25), (100, 1), (100, 0.8)):
        wheel(page, delta, point)
        expect_under(page, point, (60, 80), wide * to)


def test_ctrl_wheel_keeps_the_point_on_a_page_not_in_use(editor):
    """A2"""
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    page = editor(box("a", "text", TEXT), pages=rest)
    wide = width(page)
    page.locator('.sheet[data-page="2"]').evaluate("el => el.scrollIntoView()")
    # The first page is still the one in use, two gaps above the pointer.
    expect(page.locator('.sheet[data-page="0"]')).to_have_class(re.compile(r"\bon\b"))
    point = spot(page, 60, 40, 2)
    expect_under(page, point, (60, 40), wide, 2)
    for step in (1, 2, 3):
        wheel(page, -100, point)
        expect_under(page, point, (60, 40), wide * 1.25**step, 2)
    for step in (2, 1, 0):
        wheel(page, 100, point)
        expect_under(page, point, (60, 40), wide * 1.25**step, 2)


def test_ctrl_wheel_keeps_the_point_when_the_desk_is_measured_in_the_same_turn(editor):
    """A wheel while the desk is measured keeps the point. The listener still holds the old scale (#325)."""
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    page = editor(box("a", "text", TEXT), pages=rest)
    page.locator('.sheet[data-page="2"]').evaluate("el => el.scrollIntoView()")
    # The resize delivers the wheel: the page is already the new width, and the listener is still the old one.
    page.evaluate(
        """() => {
            const desk = document.querySelector(".desk");
            const start = desk.clientWidth;
            new ResizeObserver(() => {
                if (desk.clientWidth === start || window.__wheeled) return;
                window.__wheeled = true;
                const sheet = document.querySelector('.sheet[data-page="2"]');
                const before = sheet.getBoundingClientRect();
                const k = before.width / 210;
                window.__point = [before.x + 60 * k, before.y + 40 * k];
                sheet.dispatchEvent(new WheelEvent("wheel", {
                    deltaY: -100, ctrlKey: true, clientX: window.__point[0], clientY: window.__point[1],
                    bubbles: true, cancelable: true,
                }));
            }).observe(desk);
        }"""
    )
    page.set_viewport_size({"width": 1700, "height": 1000})
    page.wait_for_function("window.__point")
    point = page.evaluate("window.__point")
    room = page.locator(".desk").evaluate(
        """el => {
            const look = getComputedStyle(el);
            return el.clientWidth - parseFloat(look.paddingLeft) - parseFloat(look.paddingRight);
        }"""
    )
    expect_under(page, point, (60, 40), room * 1.25, 2)


def test_ctrl_wheel_stacks_on_a_zoom_in_the_same_turn(editor):
    """A button's notch and a wheel's notch in one turn stack. The listener still holds the old zoom (#325)."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    point = spot(page, 60, 80)
    page.evaluate(
        """([x, y]) => {
            window.addEventListener("click", () => {
                document.querySelector(".sheet.on").dispatchEvent(new WheelEvent("wheel", {
                    deltaY: -100, ctrlKey: true, clientX: x, clientY: y, bubbles: true, cancelable: true,
                }));
            });
            document.querySelector('button[aria-label="Größer"]').click();
        }""",
        list(point),
    )
    expect_under(page, point, (60, 80), wide * 1.25**2)


def test_ctrl_wheel_is_the_editors_alone(editor):
    """I3"""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    window = page.evaluate("[innerWidth, devicePixelRatio]")
    page.evaluate(WATCH)
    wheel(page, -100)
    assert kept(page) is True
    expect_width(page, wide * 1.25)
    # At a limit nothing changes at all, and the wheel is still not the browser's.
    for step in range(2, 8):
        wheel(page, -100)
        expect_width(page, wide * min(4, 1.25**step))
        assert kept(page) is True
    at_limit = scroll(page)
    wheel(page, -100)
    assert kept(page) is True
    settled(page)
    assert scroll(page) == at_limit
    assert width(page) == pytest.approx(wide * 4, abs=2)
    assert page.evaluate("[innerWidth, devicePixelRatio]") == window


def test_a_plain_wheel_scrolls(editor):
    """I3"""
    page = editor(box("a", "text", TEXT))
    wide, shown = width(page), percent(page)
    page.evaluate(WATCH)
    wheel(page, 100, ctrl=False)
    assert kept(page) is False
    page.wait_for_function("document.querySelector('.desk').scrollTop > 0")
    assert width(page) == pytest.approx(wide, abs=1)
    assert percent(page) == shown
    wheel(page, -100, ctrl=False)
    assert kept(page) is False
    expect_scroll(page, 0, 0)
    assert width(page) == pytest.approx(wide, abs=1)


def test_ctrl_wheel_stops_at_the_limits(editor):
    """I4"""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    for step in range(1, 8):
        wheel(page, -100)
        expect_width(page, wide * min(4, 1.25**step))
        expect_percent(page)
    # One more does nothing: the step back starts from 4, not from above it.
    wheel(page, -100)
    wheel(page, 100)
    expect_width(page, wide * 4 / 1.25)
    expect_percent(page)
    page_width(page)
    expect_width(page, wide)
    for step in range(1, 8):
        wheel(page, 100)
        expect_width(page, wide * max(0.25, 0.8**step))
        expect_percent(page)
    wheel(page, 100)
    wheel(page, -100)
    expect_width(page, wide * 0.25 * 1.25)
    expect_percent(page)
    # The buttons go on from where the wheel left the zoom.
    page_width(page)
    expect_width(page, wide)
    wheel(page, -100)
    expect_width(page, wide * 1.25)
    page.get_by_label("Größer", exact=True).first.click()
    expect_width(page, wide * 1.25**2)
    expect_percent(page)
    wheel(page, 100)
    expect_width(page, wide * 1.25)
    for step in (1, 0.8):
        page.get_by_label("Kleiner", exact=True).first.click()
        expect_width(page, wide * step)
    expect_percent(page)


def test_ctrl_wheel_keeps_a_text_open(editor):
    """I6"""
    page = editor(box("a", "text", TEXT, **PLACE))
    wide = width(page)
    caret(page, "Hallo", 2)
    wheel(page, -100, centre(at(page, "a")))
    expect_width(page, wide * 1.25)
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Haxllo")
    wheel(page, 100)
    expect_width(page, wide)
    page.keyboard.type("y")
    expect(page.locator(FIELD)).to_have_text("Haxyllo")
    expect(page.locator(FIELD)).to_be_focused()
