"""Turning several picked blocks by the handle: loose blocks each about their own centre."""

import pytest
from test_rotate import turn
from ui import RECT, angle, at, box, centre, pick


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
