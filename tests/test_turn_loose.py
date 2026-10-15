"""Turning several picked blocks by the handle: loose blocks each about their own centre."""

import math

import pytest
from playwright.sync_api import expect
from test_rotate import HANDLE, turn
from ui import LINE, RECT, angle, at, box, centre, expect_picked, pick, saved, user


def test_the_handle_turns_loose_blocks_each_on_its_spot(editor):
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
    )
    pick(page, "a", "b")
    before = {n: centre(at(page, n)) for n in ("a", "b")}
    (ax, ay), (bx, by) = before["a"], before["b"]
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 90)
    for name in ("a", "b"):
        assert abs(angle(page, name) - 90) <= 3
        x, y = centre(at(page, name))
        assert x == pytest.approx(before[name][0], abs=2)
        assert y == pytest.approx(before[name][1], abs=2)


def test_shift_turns_loose_blocks_in_15_degree_steps(editor):
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20),
    )
    pick(page, "a", "b")
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 50, keys=("Shift",))
    for name in ("a", "b"):
        assert angle(page, name) % 15 == 0
        assert angle(page, name) != 0


def ends(arrow):
    """The two ends of a line in mm, from its box and the corner it starts at."""
    f = arrow.get("props", {}).get("from", "nw")
    x, y, w, h = arrow["x"], arrow["y"], arrow["w"], arrow["h"]
    start = (x + (w if f[1] == "e" else 0), y + (h if f[0] == "s" else 0))
    end = (x + (0 if f[1] == "e" else w), y + (0 if f[0] == "s" else h))
    return start, end


def test_a_group_with_a_line_turns_by_the_handle(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20, group=["g"]),
        box("b", "shape", {**LINE, "kind": "arrow"}, z=2, x=100, y=80, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect_picked(page, "a", "b")
    expect(page.locator(HANDLE)).to_have_count(1)
    start = {b["id"]: b for b in saved(page, client)}
    (p, q) = ends(start["b"])
    cx, cy = (60 + 130) / 2, (80 + 100) / 2
    (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
    turn(page, ((ax + bx) / 2, (ay + by) / 2), 30)
    after = {b["id"]: b for b in saved(page, client)}
    (p2, q2) = ends(after["b"])
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))

    def rot(pt):
        dx, dy = pt[0] - cx, pt[1] - cy
        return cx + dx * c - dy * s, cy + dx * s + dy * c

    # Each end went round the centre: it is now where one of the new ends lies, within 1 mm.
    for end in (rot(p), rot(q)):
        assert any(math.dist(end, new) <= 1 for new in (p2, q2))
    assert math.dist(p2, q2) == pytest.approx(math.dist(p, q), abs=0.05)
    assert angle(page, "a") == pytest.approx(30, abs=1)
