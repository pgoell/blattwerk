"""Shift+click selects an arrow or a line together with a box, so that the two can be aligned (#807)."""

import pytest
from ui import RECT, at, box, expect_picked, pick

ARROW = {"kind": "arrow", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
LINE = {"kind": "line", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
ELLIPSE = {**RECT, "kind": "ellipse"}
# On A4, upright: the box of the Format panel's align tests.
A = {"x": 20, "y": 30, "w": 30, "h": 20}


def button(page, name):
    """A button of the panel that acts at once."""
    return page.locator(".panel .acts").get_by_role("button", name=name, exact=True)


def expect_box(page, name, tol=0.01, **mm):
    """Waits until the block lies at these mm of the page, to within `tol` mm."""
    sides = {"x": "left", "y": "top", "w": "width", "h": "height"}
    page.wait_for_function(
        """([name, box, tol]) => {
            const style = document.querySelector(`.block[data-id="${name}"]`).style;
            const off = ([side, mm]) => Math.abs(parseFloat(style[side]) * 25.4 / 96 - mm);
            return Object.entries(box).every((want) => off(want) < tol);
        }""",
        arg=[name, {sides[side]: value for side, value in mm.items()}, tol],
        timeout=2000,
    )


def pair(editor, line):
    """A box and a line of one kind, each with a place of its own on the page."""
    return editor(
        box("kasten", "shape", RECT, **A),
        box("strich", "shape", line, z=2, x=70, y=120, w=50, h=30),
    )


@pytest.mark.parametrize("line", [ARROW, LINE], ids=["arrow", "line"])
@pytest.mark.parametrize("first", ["kasten", "strich"])
def test_shift_click_adds_a_line_to_a_box_in_either_order(editor, line, first):
    page = pair(editor, line)
    second = "strich" if first == "kasten" else "kasten"
    pick(page, first, second)


@pytest.mark.parametrize("line", [ARROW, LINE], ids=["arrow", "line"])
def test_shift_click_on_a_box_under_a_line_adds_the_box(editor, line):
    # The line lies across the middle of the box, so the box is clicked near its corner.
    page = editor(
        box("kasten", "shape", RECT, **A),
        box("strich", "shape", line, z=2, x=20, y=39.5, w=30, h=1),
    )
    at(page, "strich").click()
    at(page, "kasten").click(modifiers=["Shift"], position={"x": 5, "y": 5})
    expect_picked(page, "strich", "kasten")


@pytest.mark.parametrize("line", [ARROW, LINE], ids=["arrow", "line"])
def test_shift_click_on_a_box_under_the_frame_of_a_line(editor, line):
    # With the line picked, its frame lies over the box, and the click goes through it.
    page = editor(
        box("kasten", "shape", RECT, **A),
        box("strich", "shape", line, z=2, x=70, y=120, w=50, h=30),
    )
    at(page, "strich").click()
    at(page, "kasten").click(modifiers=["Shift"], force=True)
    expect_picked(page, "strich", "kasten")


@pytest.mark.parametrize("line", [ARROW, LINE], ids=["arrow", "line"])
def test_shift_click_on_a_box_beside_a_line_across_its_corner(editor, line):
    # The line runs from inside the box to outside it, and the box is clicked away from the line.
    page = editor(
        box("kasten", "shape", RECT, **A),
        box("strich", "shape", line, z=2, x=40, y=35, w=60, h=40),
    )
    at(page, "strich").click()
    at(page, "kasten").click(modifiers=["Shift"], position={"x": 3, "y": 3})
    expect_picked(page, "strich", "kasten")


@pytest.mark.parametrize("line", [ARROW, LINE], ids=["arrow", "line"])
def test_shift_click_takes_the_line_out_and_keeps_the_box(editor, line):
    page = pair(editor, line)
    pick(page, "kasten", "strich")
    at(page, "strich").click(modifiers=["Shift"], force=True)
    expect_picked(page, "kasten")


def test_shift_click_adds_an_arrow_to_an_ellipse(editor):
    page = editor(
        box("oval", "shape", ELLIPSE, **A),
        box("pfeil", "shape", ARROW, z=2, x=70, y=120, w=50, h=30),
    )
    pick(page, "oval", "pfeil")


def test_align_an_arrow_with_a_box(editor):
    page = pair(editor, ARROW)
    pick(page, "kasten", "strich")
    button(page, "Links").click()
    expect_box(page, "kasten", x=20)
    # The arrow's ink (its head and stroke) lines up at 20 mm, so its box lies within half a stroke of it.
    expect_box(page, "strich", tol=0.5, x=20)


def test_undo_aligns_an_arrow_with_a_box(editor):
    page = pair(editor, ARROW)
    pick(page, "kasten", "strich")
    button(page, "Links").click()
    expect_box(page, "strich", tol=0.5, x=20)
    page.keyboard.press("Control+z")
    expect_box(page, "kasten", **A)
    expect_box(page, "strich", x=70)
