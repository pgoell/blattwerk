"""Loose blocks turned together keep one level frame round them all; a turned group's handles stand
on its frame (issue 664)."""

import math

import pytest
from playwright.sync_api import expect
from test_group_turn import G, group, hull
from test_rotate import turn
from ui import LINE, RECT, at, box, centre, drag, expect_picked, pick, saved, user

# The frame's distance from the blocks, in px (FRAME in Editor.tsx).
GAP = 8
# How far a handle may stand off its spot, in px.
NEAR = 3
CORNERS = ["nw", "ne", "se", "sw"]
ARROW = {**LINE, "kind": "arrow"}


def loose():
    """Two rectangles side by side, loose, the left one high and the right one low."""
    return [
        box("a", "shape", RECT, x=40, y=60, w=40, h=30),
        box("b", "shape", RECT, z=2, x=120, y=100, w=50, h=20),
    ]


def corners(page):
    """The centres of the frame's four corner handles, as x, y in px on the screen."""
    return {c: centre(page.locator(f".moveable-control.moveable-{c}")) for c in CORNERS}


def screen_hull(page, names):
    """The level box round the blocks as drawn, turned or not: left, top, right, bottom."""
    boxes = [at(page, name).bounding_box() for name in names]
    return (
        min(b["x"] for b in boxes),
        min(b["y"] for b in boxes),
        max(b["x"] + b["width"] for b in boxes),
        max(b["y"] + b["height"] for b in boxes),
    )


def expect_level(page):
    """The frame's corner handles stand at the corners of one level box."""
    c = corners(page)
    assert c["nw"][0] == pytest.approx(c["sw"][0], abs=NEAR)
    assert c["ne"][0] == pytest.approx(c["se"][0], abs=NEAR)
    assert c["nw"][1] == pytest.approx(c["ne"][1], abs=NEAR)
    assert c["sw"][1] == pytest.approx(c["se"][1], abs=NEAR)


def expect_round(page, names):
    """The level frame lies GAP px outside the blocks as they are drawn, all round."""
    left, top, right, bottom = screen_hull(page, names)
    c = corners(page)
    for corner, (x, y) in {
        "nw": (left - GAP, top - GAP),
        "ne": (right + GAP, top - GAP),
        "se": (right + GAP, bottom + GAP),
        "sw": (left - GAP, bottom + GAP),
    }.items():
        assert c[corner] == pytest.approx((x, y), abs=NEAR), corner


def distance(p, a, b):
    """How far the point p lies from the segment a to b."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def on_frame(page, point):
    """Whether the point lies on an edge of the frame's quadrilateral, the corners in turn."""
    c = corners(page)
    ring = [c[name] for name in ("nw", "ne", "se", "sw")]
    return any(distance(point, ring[i], ring[(i + 1) % 4]) <= NEAR for i in range(4))


def handles(page):
    """The centres of every visible handle the editor draws for the selection."""
    found = page.evaluate(
        """() => [...document.querySelectorAll('.sheet .moveable-control, .sheet .end')]
            .filter((el) => el.getClientRects().length)
            .filter((el) => !el.classList.contains('moveable-rotation-control'))
            .map((el) => {
                const r = el.getBoundingClientRect();
                return [r.left + r.width / 2, r.top + r.height / 2];
            })"""
    )
    return [tuple(p) for p in found]


def test_two_loose_blocks_turned_together_keep_a_level_frame(editor):
    client = user()
    page = editor(*loose(), client=client)
    pick(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowRight")
    expect(page.locator(".moveable-control.moveable-nw")).to_have_count(1)
    expect_level(page)
    expect_round(page, ["a", "b"])


def test_each_loose_block_still_shows_its_own_turned_outline(editor):
    client = user()
    page = editor(*loose(), client=client)
    pick(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowRight")
    # Each block's outline is drawn turned with it: its own lines are not level.
    lines = page.evaluate(
        """() => [...document.querySelectorAll('.sheet .moveable-line')]
            .filter((el) => el.getClientRects().length)
            .map((el) => {
                const r = el.getBoundingClientRect();
                return [r.width, r.height];
            })"""
    )
    # A line of a turned outline is diagonal: both its sides are longer than a hair.
    assert any(w > 2 and h > 2 for w, h in lines)


def test_turning_loose_blocks_by_the_handle_keeps_the_frame_level(editor):
    client = user()
    first = loose()
    page = editor(*first, client=client)
    pick(page, "a", "b")
    sheet = page.locator(".sheet").bounding_box()
    k = sheet["width"] / 210
    middle = hull(first)
    about = ((middle[0] + middle[2]) / 2, (middle[1] + middle[3]) / 2)
    turn(page, (sheet["x"] + about[0] * k, sheet["y"] + about[1] * k), 30)
    expect_level(page)
    expect_round(page, ["a", "b"])


def test_a_turned_group_of_a_rectangle_and_an_arrow_has_handles_on_its_frame(editor):
    client = user()
    rect = box("r", "shape", RECT, x=60, y=60, w=40, h=30, **G)
    arrow = box("p", "shape", ARROW, z=2, x=120, y=110, w=50, h=30, **G)
    page = editor(rect, arrow, client=client)
    group(page, "r", "p")
    for _ in range(3):
        page.keyboard.press("Alt+ArrowRight")
    # The four size handles stand on the turned frame, as a rectangle (#667).
    expect(page.locator(".sheet i.end")).to_have_count(4)
    nw, ne, sw, se = (centre(page.locator(".sheet i.end").nth(i)) for i in range(4))
    assert (nw[0] + se[0], nw[1] + se[1]) == pytest.approx((ne[0] + sw[0], ne[1] + sw[1]), abs=1)
    assert math.dist(nw, se) == pytest.approx(math.dist(ne, sw), abs=1)
    # The one frame drawn is the turned one: each corner of it touches the level box round it.
    frame = page.locator(".sheet .turned-frame").bounding_box()
    sides = (frame["x"], frame["x"] + frame["width"]), (frame["y"], frame["y"] + frame["height"])
    for point in (nw, ne, sw, se):
        near = [abs(point[axis] - side) for axis in (0, 1) for side in sides[axis]]
        assert min(near) <= NEAR, point
    lines = page.evaluate(
        """() => [...document.querySelectorAll('.sheet .moveable-line')]
            .filter((el) => el.getClientRects().length && getComputedStyle(el).display !== 'none')
            .map((el) => el.className.baseVal ?? el.className)"""
    )
    # Only the stalk of the turn handle: Moveable's own frame, wider than the group's, is not drawn.
    assert all("rotation" in line for line in lines), lines
    expect(page.locator(".sheet .moveable-direction")).to_have_count(0)
    expect(page.locator(".sheet .moveable-rotation-control")).to_be_visible()


def test_a_level_group_of_a_rectangle_and_an_arrow_keeps_its_corner_handles(editor):
    rect = box("r", "shape", RECT, x=60, y=60, w=40, h=30, **G)
    arrow = box("p", "shape", ARROW, z=2, x=120, y=110, w=50, h=30, **G)
    page = editor(rect, arrow)
    group(page, "r", "p")
    expect(page.locator(".sheet i.end")).to_have_count(4)


def test_escape_and_pick_again_keep_the_level_frame(editor):
    client = user()
    page = editor(*loose(), client=client)
    pick(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Escape")
    pick(page, "a", "b")
    expect_level(page)
    expect_round(page, ["a", "b"])


def test_a_drag_of_the_corner_resizes_both_turned_loose_blocks(editor):
    client = user()
    first = loose()
    page = editor(*first, client=client)
    pick(page, "a", "b")
    page.keyboard.press("Alt+ArrowRight")
    page.keyboard.press("Alt+ArrowRight")
    before = {b["id"]: (b["w"], b["h"]) for b in saved(page, client)}
    x, y = centre(page.locator(".moveable-control.moveable-se"))
    drag(page, (x, y), (x + 40, y + 40))
    after = {b["id"]: (b["w"], b["h"]) for b in saved(page, client)}
    assert after["a"] != before["a"]
    assert after["b"] != before["b"]
    expect_picked(page, "a", "b")
    # The frame stays level through the resize.
    expect_level(page)


def test_a_turned_loose_block_picked_with_a_line_keeps_its_corner_handles(editor):
    """Not one group: the frame is level, so the editor's own corner handles stand on it."""
    rect = box("r", "shape", RECT, x=60, y=60, w=40, h=30, angle=45)
    line = box("l", "shape", LINE, z=2, x=60, y=120, w=50, h=10)
    page = editor(rect, line)
    pick(page, "r", "l")
    expect(page.locator(".sheet i.end")).to_have_count(4)
