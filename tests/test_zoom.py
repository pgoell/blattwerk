"""Ctrl and the wheel zoom about the pointer, Space and a drag move the desk, "Ganze Seite" fits."""

import re

import pytest
from playwright.sync_api import expect
from test_drop import spot
from test_fields import by_id, field
from test_pages import expect_in_use
from ui import (
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
    doc,
    drag,
    expect_picked,
    maths,
    pick,
    picture,
    saved,
    thumb,
    upload,
    user,
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
        # The page has its new width and the same mm of it under the pointer, to half a mm.
        page.wait_for_function(
            """([x, y, wide]) => {
                const r = document.querySelector(".sheet.on").getBoundingClientRect();
                const mm = [(x - r.x) / (r.width / 210), (y - r.y) / (r.width / 210)];
                const there = Math.abs(mm[0] - 60) < 0.5 && Math.abs(mm[1] - 80) < 0.5;
                return Math.abs(r.width - wide) < 2 && there;
            }""",
            arg=[*point, wide * to],
        )


def test_space_and_drag_moves_the_desk(editor):
    """A3"""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    wide = width(page)
    middle = centre(page.locator(".desk"))
    pan(page, middle, 100, 60)
    pan(page, middle, -40, -90)
    pan(page, middle, 0, 30)
    pan(page, middle, -30, 0)
    # Space on a zoom button that has the focus pans too, and does not press the button.
    page.get_by_label("Größer", exact=True).first.focus()
    pan(page, middle, 20, 20)
    settled(page)
    assert width(page) == pytest.approx(wide, abs=1)
    expect(page.locator(HAND)).to_have_count(0)


def test_fit_shows_the_whole_page(editor):
    """A4"""
    page = editor(box("a", "text", TEXT))
    # Right after the percent button.
    assert fit(page).evaluate("el => !!el.previousElementSibling?.classList.contains('zoom')")
    assert not page.evaluate(INSIDE, 0)
    wide = width(page)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    expect_percent(page)
    # The percent button still sets the width. The fit works from a zoom that overflows both ways.
    page.locator("button.zoom").first.click()
    expect_width(page, wide)
    assert not page.evaluate(INSIDE, 0)
    roomy(page)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)


@pytest.mark.parametrize("kind", KINDS)
def test_a_space_drag_leaves_the_block_alone(editor, kind):
    """I1"""
    client = user()
    blocks = of_kind(kind, client)
    names = [b["id"] for b in blocks]
    page = editor(*blocks, client=client)
    roomy(page)
    before = places(page, *names)
    # Not selected: the drag starts on the block and neither picks nor moves it.
    pan(page, centre(at(page, "a")), 100, 60)
    expect_picked(page)
    expect_in_place(page, names, before)
    # Selected, a group by one click: it stays so, and where it was.
    at(page, "a").click()
    expect_picked(page, *names)
    pan(page, centre(at(page, "a")), -60, -40)
    expect_picked(page, *names)
    expect_in_place(page, names, before)
    # Nothing opened either: no text, no cell, no crop.
    expect(page.locator(".ProseMirror, .block textarea:not([readonly]), .crop")).to_have_count(0)
    expect(page.locator(HAND)).to_have_count(0)


def test_a_space_drag_keeps_a_selection_of_several(editor):
    """I1"""
    low, lower = {**PLACE, "y": 110}, {**PLACE, "y": 160}
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("b", "shape", RECT, z=2, **low),
        box("c", "shape", LINE, z=3, **lower),
        box("d", "shape", RECT, z=4, x=15, y=110, w=35, h=40),
    )
    names = ["a", "b", "c"]
    pick(page, *names)
    roomy(page)
    before = places(page, *names, "d")
    # On the empty page, on a block that is not picked, and on one that is.
    for start in (
        lambda: spot(page, 40, 90),
        lambda: centre(at(page, "d")),
        lambda: centre(at(page, "b")),
    ):
        pan(page, start(), 60, 40)
        expect_picked(page, *names)
        expect_in_place(page, [*names, "d"], before)


@pytest.mark.parametrize("where", ["text", "cell", "field"])
def test_space_in_a_text_types_a_space(editor, where):
    """I2"""
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("t", "table", TABLE, z=2, x=60, y=120, w=60, h=40),
    )
    if where == "text":
        caret(page, "Hallo", 2)
        held = page.locator(FIELD)
    elif where == "cell":
        pick(page, "t")
        page.keyboard.press("Enter")
        held = at(page, "t").locator("textarea")
        expect(held).to_be_focused()
        page.keyboard.press("End")
    else:
        pick(page, "t")
        held = field(page, "X")
        held.click()
        expect(held).to_be_focused()
        # The click picked all of the number.
        page.keyboard.press("End")
    page.keyboard.down("Space")
    if where == "text":
        expect(held).to_have_text("Ha llo")
    else:
        expect(held).to_have_value("H " if where == "cell" else "60 ")
    expect(page.locator(HAND)).to_have_count(0)
    expect(page.locator("main.editor")).not_to_have_class(PAN)
    # The page is higher than the desk: a pan by a drag upwards would scroll it down.
    assert scroll(page) == [0, 0]
    if where == "text":
        # Along the first line and a little up, from behind the last letter to before the first.
        edge = held.bounding_box()
        drag(page, (edge["x"] + 80, edge["y"] + 16), (edge["x"] + 2, edge["y"] + 4))
    else:
        x, y = centre(held)
        drag(page, (x, y), (x - 30, y - 40))
    settled(page)
    page.keyboard.up("Space")
    assert scroll(page) == [0, 0]
    expect(page.locator("main.editor")).not_to_have_class(PANNING)
    expect(held).to_be_focused()
    if where == "text":
        # The drag picked letters, as it does with no key held.
        assert page.evaluate("getSelection().toString()") != ""


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
    page.locator("button.zoom").first.click()
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
    page.locator("button.zoom").first.click()
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


def test_zoom_and_pan_are_no_undo_steps(editor):
    """I5"""
    client = user()
    page = editor(box("a", "shape", RECT, **PLACE), box("b", "text", TEXT, z=3), client=client)
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("Rückgängig")).to_be_enabled()
    edited = doc(page, client)
    assert by_id(edited["pages"][0]["blocks"])["a"]["x"] != PLACE["x"]
    wide = width(page)
    wheel(page, -100)
    expect_width(page, wide * 1.25)
    wheel(page, -100)
    expect_width(page, wide * 1.25**2)
    page.locator(".desk").evaluate("el => el.scrollTo(200, 200)")
    pan(page, centre(page.locator(".desk")), 80, 50)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    expect_picked(page, "a")
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")
    assert doc(page, client) == edited
    # One step back is the edit's, and there is no other.
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert by_id(saved(page, client))["a"]["x"] == PLACE["x"]
    expect_picked(page, "a")


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


def test_space_shows_a_hand_and_lets_go(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    main, hand, desk = page.locator("main.editor"), page.locator(HAND), page.locator(".desk")
    # On the empty desk, so nothing else has the focus. Space alone scrolls nothing.
    corner = desk.bounding_box()
    page.mouse.click(corner["x"] + 10, corner["y"] + 10)
    page.keyboard.down("Space")
    expect(main).to_have_class(PAN)
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(1)
    expect(hand).to_have_css("cursor", "grab")
    settled(page)
    page.keyboard.up("Space")
    expect(main).not_to_have_class(PAN)
    expect(hand).to_have_count(0)
    settled(page)
    assert scroll(page) == [0, 0]

    # The drag goes on after Space is let go, until the mouse lifts.
    x, y = centre(desk)
    page.keyboard.down("Space")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 50, steps=5)
    expect(main).to_have_class(PANNING)
    expect(hand).to_have_css("cursor", "grabbing")
    expect_scroll(page, 0, 50)
    page.keyboard.up("Space")
    expect(main).not_to_have_class(PAN)
    expect(main).to_have_class(PANNING)
    expect(hand).to_have_count(1)
    page.mouse.move(x, y - 80, steps=5)
    expect_scroll(page, 0, 80)
    page.mouse.up()
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(0)
    # The mouse alone moves no desk now.
    drag(page, (x, y), (x, y - 40))
    settled(page)
    assert scroll(page) == [0, 80]

    # The window losing the focus ends both.
    page.keyboard.down("Space")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 20, steps=5)
    expect(main).to_have_class(PANNING)
    expect(main).to_have_class(PAN)
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    expect(main).not_to_have_class(PAN)
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(0)
    page.mouse.up()
    page.keyboard.up("Space")
    expect(hand).to_have_count(0)


def test_fit_takes_the_page_in_use(editor):
    """I8"""
    rest = [
        {"blocks": [box("b", "text", TEXT)], "landscape": True},
        {"blocks": [box("c", "text", TEXT)]},
    ]
    page = editor(box("a", "text", TEXT), pages=rest, theme="")
    for n, (w, h) in ((1, (297, 210)), (2, (210, 297)), (0, (210, 297))):
        thumb(page, n).click()
        expect_in_use(page, n)
        fit(page).click()
        expect_fitted(page, n, w, h)
        # No other page has room beside it.
        assert [m for m in range(3) if page.evaluate(INSIDE, m)] == [n]
