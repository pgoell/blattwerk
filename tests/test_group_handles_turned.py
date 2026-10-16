"""A turned group with a line has four size handles on its frame; a drag sizes it there (#667)."""

import math

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, number
from test_group_scale_turned import SHAPES, pick_group, turned_group
from ui import LINE, RECT, box, centre, drag, pick, saved, user

# Handles in order: nw, ne, sw, se (Editor.tsx draws the four `i.end` as [0, 1, 2, 3]).
SE = 3


def handle(page, i):
    return centre(page.locator(".sheet i.end").nth(i))


def drag_se_inward(page, dx, dy):
    """Drags the se handle by (dx, dy) px on the screen. At 45 degrees, straight up runs inward."""
    x, y = handle(page, SE)
    drag(page, (x, y), (x + dx / 2, y + dy / 2), (x + dx, y + dy))


def test_a_turned_group_with_a_line_has_four_size_handles_on_its_frame(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    expect(page.locator(".sheet i.end")).to_have_count(4)
    nw, ne, sw, se = (handle(page, i) for i in (0, 1, 2, 3))
    # The frame is a rectangle turned on the page: its diagonals bisect each other and are equal,
    # and its sides meet at a right angle.
    assert (nw[0] + se[0], nw[1] + se[1]) == pytest.approx((ne[0] + sw[0], ne[1] + sw[1]), abs=1)
    assert math.dist(nw, se) == pytest.approx(math.dist(ne, sw), abs=1)
    # The dot product of two sides is near 0 px squared: a right angle, up to pixel rounding.
    dot = (ne[0] - nw[0]) * (se[0] - ne[0]) + (ne[1] - nw[1]) * (se[1] - ne[1])
    assert dot == pytest.approx(0, abs=3)
    # The rectangle is 60 by 30 mm. Each side is its mm length times k px, plus 8 px of padding
    # at each end: the long side less 16 px is twice the short side less 16 px.
    long_side, short_side = math.dist(nw, ne), math.dist(ne, se)
    assert (long_side - 16) == pytest.approx(2 * (short_side - 16), abs=1)


def test_a_drag_of_a_size_handle_scales_the_turned_group_uniformly(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    drag_se_inward(page, 0, -60)
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    blocks = by_id(saved(page, client))
    rect, arrow = blocks["a"], blocks["b"]
    # The rectangle is 60 by 30, so it keeps its 2 to 1 shape at any factor.
    assert rect["w"] == pytest.approx(2 * rect["h"], abs=0.5)
    assert rect["h"] < 30
    # The arrow keeps its length in the group's frame and lies level under the lower edge.
    assert arrow["w"] == pytest.approx(rect["w"], abs=0.5)
    assert arrow["h"] == pytest.approx(0, abs=0.5)
    assert arrow["y"] == pytest.approx(rect["y"] + rect["h"], abs=0.5)


def test_one_undo_takes_back_a_size_handle_drag_on_a_turned_group(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    before = saved(page, client)
    drag_se_inward(page, 0, -60)
    after = saved(page, client)
    assert after != before
    page.keyboard.press("Control+z")
    expect(page.locator(".sheet i.end")).to_have_count(4)
    assert saved(page, client) == before
    page.keyboard.press("Control+y")
    assert saved(page, client) == after


def test_ctrl_during_a_size_handle_drag_keeps_the_group_centre(editor):
    """The rectangle 60 by 30 at (60, 80) has its centre at (90, 95), where the group turns."""
    client = user()
    page = turned_group(editor, client, *SHAPES)
    x, y = handle(page, SE)
    drag(page, (x, y), (x, y - 30), (x, y - 60), keys=["Control"])
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    rect = by_id(saved(page, client))["a"]
    assert rect["x"] + rect["w"] / 2 == pytest.approx(90, abs=0.5)
    assert rect["y"] + rect["h"] / 2 == pytest.approx(95, abs=0.5)


def test_a_size_handle_drag_past_the_opposite_corner_stops_at_a_tenth(editor):
    """The group does not flip: its rectangle stays 6 by 3, a tenth of 60 by 30."""
    client = user()
    page = turned_group(editor, client, *SHAPES)
    x, y = handle(page, SE)
    drag(page, (x, y), (x, y - 200), (x, y - 400))
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    rect = by_id(saved(page, client))["a"]
    assert rect["w"] == pytest.approx(6, abs=0.5)
    assert rect["h"] == pytest.approx(3, abs=0.5)


def test_the_panel_shows_the_new_own_size_after_a_handle_drag(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    drag_se_inward(page, 0, -60)
    expect(field(page, "Breite")).not_to_have_value("60")
    # Read while the group is still turned: its own size, not the box round it on the page.
    shown = number(page, "Breite"), number(page, "Höhe")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    rect = by_id(saved(page, client))["a"]
    assert shown == (pytest.approx(rect["w"], abs=0.1), pytest.approx(rect["h"], abs=0.1))


def test_the_opposite_corner_stays_where_it_was_on_the_screen(editor):
    page = turned_group(editor, user(), *SHAPES)
    nw = handle(page, 0)
    drag_se_inward(page, 0, -60)
    expect(field(page, "Breite")).not_to_have_value("60")
    assert handle(page, 0) == pytest.approx(nw, abs=1.5)
    assert handle(page, SE) != pytest.approx(nw, abs=1.5)


def test_loose_blocks_turned_alike_with_a_line_keep_level_handles_that_size_along_the_page(editor):
    """Not one group: no own frame, so the handles stand on the level box and a drag scales it."""
    client = user()
    rect = box("r", "shape", RECT, x=60, y=60, w=40, h=30, angle=30)
    line = box("l", "shape", LINE, z=2, x=60, y=120, w=50, h=10)
    page = editor(rect, line, client=client)
    pick(page, "r", "l")
    expect(page.locator(".sheet i.end")).to_have_count(4)
    nw, ne, sw, se = (handle(page, i) for i in (0, 1, 2, 3))
    assert (nw[1], sw[0]) == (pytest.approx(ne[1], abs=1), pytest.approx(nw[0], abs=1))
    assert (se[0], se[1]) == (pytest.approx(ne[0], abs=1), pytest.approx(sw[1], abs=1))
    expect(page.locator(".sheet .turned-frame")).to_have_count(0)
    drag(page, se, (se[0] + 20, se[1] + 20), (se[0] + 40, se[1] + 40))
    blocks = by_id(saved(page, client))
    # The rectangle stays turned as it was and grows; the line grows along the page.
    assert blocks["r"]["angle"] == 30 and blocks["r"]["w"] > 40
    assert blocks["l"]["w"] > 50


def test_a_level_group_with_a_line_keeps_its_handles_after_another_turn(editor):
    page = editor(*SHAPES, client=user())
    pick_group(page, "a", "b")
    for _ in range(3):
        page.keyboard.press("Alt+ArrowRight")
    expect(page.locator(".sheet i.end")).to_have_count(4)
    before = handle(page, 0)
    page.keyboard.press("Alt+ArrowRight")
    expect(page.locator(".sheet i.end")).to_have_count(4)
    # The frame turned a quarter, so its nw handle moved with it.
    assert math.dist(before, handle(page, 0)) > 10
