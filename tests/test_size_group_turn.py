"""Turning a group, or a turned block, from the size fields.

The helpers live in test_size_group.py.
"""

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, number
from ui import LINE, RECT, TABLE, at, box, pick, saved, user


def centre(block):
    return (block["x"] + block["w"] / 2, block["y"] + block["h"] / 2)


def test_a_turned_block_alone_halves_its_own_width_on_a_percent(editor):
    client = user()
    page = editor(box("a", "shape", RECT, x=40, y=60, w=30, h=20, angle=90), client=client)
    pick(page, "a")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite")).to_have_value("15")
    (a,) = saved(page, client)
    assert (a["x"], a["y"], a["w"], a["h"], a["angle"]) == (40, 60, 15, 20, 90)


def test_a_group_turns_about_its_centre(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"]),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    enter(page, "Drehung", "90")
    expect(field(page, "Drehung")).to_have_value("90")
    blocks = by_id(saved(page, client))
    # The centre of the group is (52.5, 60). Each block's centre turns about it.
    assert blocks["a"]["angle"] == blocks["b"]["angle"] == 90
    assert centre(blocks["a"]) == pytest.approx((52.5, 37.5), abs=0.05)
    assert centre(blocks["b"]) == pytest.approx((52.5, 82.5), abs=0.05)


def test_a_group_with_a_table_does_not_turn(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"]),
        box("t", "table", TABLE, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect(field(page, "Drehung")).to_be_disabled()
    expect(field(page, "Breite")).to_be_enabled()


def test_a_group_of_shapes_and_a_line_turns_about_its_centre(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"]),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        box("l", "shape", LINE, z=3, x=60, y=80, w=30, h=0, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    enter(page, "Drehung", "90")
    expect(field(page, "Drehung")).to_have_value("90")
    blocks = by_id(saved(page, client))
    # The group's centre is (52.5, 65). The shape's centre turns about it.
    assert blocks["a"]["angle"] == blocks["b"]["angle"] == 90
    assert centre(blocks["a"]) == pytest.approx((57.5, 42.5), abs=0.05)
    # The line has no angle: its box goes on its side.
    assert (blocks["l"]["w"], blocks["l"]["h"]) == pytest.approx((0, 30), abs=0.05)


def test_a_group_turns_by_the_difference_of_its_first_angle(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"], angle=30),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    expect(field(page, "Drehung")).to_have_value("30")
    enter(page, "Drehung", "40")
    expect(field(page, "Drehung")).to_have_value("40")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["angle"], blocks["b"]["angle"]) == (40, 10)


def test_a_turned_shape_in_a_group_takes_the_factor_of_its_own_axis(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"], angle=90),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    wide = number(page, "Breite")
    enter(page, "Breite", f"{2 * wide:g}")
    expect(field(page, "Breite")).not_to_have_value(f"{wide:g}".replace(".", ","))
    blocks = by_id(saved(page, client))
    # A shape on its side: its height takes the factor 2, its width stays.
    assert (blocks["a"]["w"], blocks["a"]["h"]) == (30, 40)
