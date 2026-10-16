"""A turned group scales in its own frame: the arrow in it stays level under the box (#658)."""

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, number
from ui import LINE, RECT, at, box, expect_picked, saved, user

ARROW = {**LINE, "kind": "arrow"}
# A rectangle 60 by 30 with an arrow lying under its lower edge, in one group.
SHAPES = [
    box("a", "shape", RECT, x=60, y=80, w=60, h=30, group=["g"]),
    box("b", "shape", ARROW, z=2, x=60, y=110, w=60, h=0, group=["g"]),
]
# Two rectangles 30 by 20 side by side in one group, level: their centres are 50 apart.
PAIR = [
    box("a", "shape", RECT, x=20, y=50, w=30, h=20, group=["g"]),
    box("b", "shape", RECT, z=2, x=70, y=50, w=30, h=20, group=["g"]),
]


def pick_group(page, name, *names):
    at(page, name).click()
    expect_picked(page, name, *names)


def assert_level_under(blocks):
    """The rectangle is 30 by 30. The arrow lies level under its lower edge, within its width."""
    rect, arrow = blocks["a"], blocks["b"]
    assert rect["angle"] == 0
    assert rect["w"] == pytest.approx(30, abs=0.5)
    assert rect["h"] == pytest.approx(30, abs=0.5)
    assert arrow["h"] == pytest.approx(0, abs=0.5)
    assert arrow["y"] >= rect["y"] + rect["h"] - 0.5
    assert arrow["x"] >= rect["x"] - 0.5
    assert arrow["x"] + arrow["w"] <= rect["x"] + rect["w"] + 0.5


def turned_group(editor, client, *blocks):
    """The blocks in one group, picked and turned to 45 degrees in the panel."""
    page = editor(*blocks, client=client)
    pick_group(page, "a", *(["b"] if len(blocks) > 1 else []))
    enter(page, "Drehung", "45")
    expect(field(page, "Drehung")).to_have_value("45")
    return page


def test_breite_percent_on_a_turned_group_keeps_the_arrow_level(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    enter(page, "Breite %", "50")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    assert_level_under(by_id(saved(page, client)))


def test_breite_in_mm_on_a_turned_group_keeps_the_arrow_level(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    enter(page, "Breite", f"{number(page, 'Breite') / 2:g}")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    assert_level_under(by_id(saved(page, client)))


def test_hoehe_percent_on_a_turned_group_keeps_the_arrow_on_its_edge(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    enter(page, "Höhe %", "50")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    blocks = by_id(saved(page, client))
    rect, arrow = blocks["a"], blocks["b"]
    assert rect["w"] == pytest.approx(60, abs=0.5)
    assert rect["h"] == pytest.approx(15, abs=0.5)
    assert arrow["h"] == pytest.approx(0, abs=0.5)
    assert arrow["y"] == pytest.approx(rect["y"] + rect["h"], abs=0.5)


def test_one_undo_takes_back_a_turned_group_percent(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    before = saved(page, client)
    shown = field(page, "Breite").input_value()
    enter(page, "Breite %", "50")
    expect(field(page, "Breite")).not_to_have_value(shown)
    scaled_to = field(page, "Breite").input_value()
    after = saved(page, client)
    assert after != before
    page.keyboard.press("Control+z")
    expect(field(page, "Breite")).to_have_value(shown)
    assert saved(page, client) == before
    page.keyboard.press("Control+y")
    expect(field(page, "Breite")).to_have_value(scaled_to)
    assert saved(page, client) == after


def test_a_group_of_two_rectangles_at_30_degrees_keeps_them_level_after_a_percent(editor):
    client = user()
    page = editor(*PAIR, client=client)
    pick_group(page, "a", "b")
    enter(page, "Drehung", "30")
    expect(field(page, "Drehung")).to_have_value("30")
    enter(page, "Breite %", "50")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    blocks = by_id(saved(page, client))
    a, b = blocks["a"], blocks["b"]
    centre = {k: (v["x"] + v["w"] / 2, v["y"] + v["h"] / 2) for k, v in (("a", a), ("b", b))}
    assert a["w"] == pytest.approx(15, abs=0.5) and b["w"] == pytest.approx(15, abs=0.5)
    assert a["h"] == pytest.approx(20, abs=0.5) and b["h"] == pytest.approx(20, abs=0.5)
    assert centre["b"][0] - centre["a"][0] == pytest.approx(25, abs=0.5)
    assert centre["a"][1] == pytest.approx(centre["b"][1], abs=0.5)
