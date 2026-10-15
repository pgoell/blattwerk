"""The size fields for a group and the percent fields, in Chromium on the built app."""

import pytest
from playwright.sync_api import expect
from test_fields import ROOM, by_id, enter, expect_fields, field, number
from test_hunderterfeld_block import FELD
from test_panel_undo import UHR, ZAHLENSTRAHL
from test_rechendreieck import DREIECK
from test_selbstkontrolle_block import SK
from test_variants import SUCHSEL
from test_zahlenmauer_block import WALL
from ui import LINE, RECT, RULING, TABLE, TEXT, at, box, maths, pick, picture, saved, upload, user

STAR = {"code": "2B50"}

# Two blocks side by side in one group: the box around them is 75 wide, 20 high, from (15, 50).
PAIR = [
    box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"]),
    box("b", "text", TEXT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
]


def pair_group(editor, client):
    return editor(*PAIR, client=client)


def centre(block):
    return (block["x"] + block["w"] / 2, block["y"] + block["h"] / 2)


def test_a_group_width_scales_about_its_left_edge(editor):
    client = user()
    page = pair_group(editor, client)
    at(page, "a").click()
    # The fields show the box round the group. A new width scales every block about its left edge.
    enter(page, "Breite", "150")
    expect(field(page, "Breite")).to_have_value("150")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["x"], blocks["a"]["w"]) == (15, 60)
    assert (blocks["b"]["x"], blocks["b"]["w"]) == (105, 60)
    # The heights stay, and the text keeps its size.
    assert (blocks["a"]["h"], blocks["b"]["h"]) == (20, 20)
    assert blocks["b"]["props"]["size"] == 14


def test_a_group_height_scales_about_its_top_edge(editor):
    client = user()
    page = pair_group(editor, client)
    at(page, "a").click()
    enter(page, "Höhe", "40")
    expect(field(page, "Höhe")).to_have_value("40")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["y"], blocks["a"]["h"]) == (50, 40)
    assert (blocks["b"]["y"], blocks["b"]["h"]) == (50, 40)


def test_one_undo_takes_back_a_group_width(editor):
    client = user()
    page = pair_group(editor, client)
    at(page, "a").click()
    before = by_id(saved(page, client))
    enter(page, "Breite", "150")
    expect(field(page, "Breite")).to_have_value("150")
    saved(page, client)
    page.get_by_label("Rückgängig").click()
    expect(field(page, "Breite")).to_have_value("75")
    assert by_id(saved(page, client)) == before


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


def test_a_locked_block_in_a_group_takes_no_size_percent_or_angle(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"], locked=True),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    for label in ("Breite", "Höhe", "Drehung", "Breite %", "Höhe %"):
        expect(field(page, label)).to_be_disabled()


def test_a_percent_halves_one_shape_and_then_its_height(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite %")).to_have_value("100")
    expect_fields(page, "40", "60", "40", "40", "0")
    enter(page, "Höhe %", "50")
    expect(field(page, "Höhe %")).to_have_value("100")
    (a,) = saved(page, client)
    assert (a["x"], a["w"], a["h"]) == (40, 40, 20)


def test_a_picture_keeps_its_ratio_when_a_shape_does_not(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "z": 4, "x": 20, "y": 150, "w": 60, "h": 40}
    page = editor(box("r", "shape", RECT, **ROOM), bild, client=client)
    pick(page, "r", "bild")
    enter(page, "Breite", "30")
    expect(field(page, "Breite")).to_have_value("30")
    blocks = by_id(saved(page, client))
    # The rect takes the new width and keeps its height. The picture keeps its ratio.
    assert (blocks["r"]["w"], blocks["r"]["h"]) == (30, 40)
    assert (blocks["bild"]["w"], blocks["bild"]["h"]) == (30, 20)


def test_originalgrosse_gives_a_picture_its_first_size(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "x": 20, "y": 150, "w": 60, "h": 40}
    page = editor(bild, client=client)
    pick(page, "bild")
    enter(page, "Breite", "30")
    expect(field(page, "Breite")).to_have_value("30")
    page.get_by_label("Originalgröße", exact=True).click()
    expect(field(page, "Breite")).to_have_value("100")
    (b,) = saved(page, client)
    # The picture is 1.5 to 1 as sent: 100 wide, 66.67 high, and its place stays.
    assert (b["x"], b["y"], b["w"]) == (20, 150, 100)
    assert b["h"] == pytest.approx(66.67, abs=0.01)


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


def test_a_line_alone_halves_its_width_on_a_percent(editor):
    client = user()
    page = editor(box("l", "shape", LINE, x=15, y=50, w=60, h=10), client=client)
    pick(page, "l")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite %")).to_have_value("100")
    (line,) = saved(page, client)
    assert (line["x"], line["w"]) == (15, 30)


def test_the_lock_on_a_group_scales_both_sides_alike(editor):
    client = user()
    page = pair_group(editor, client)
    at(page, "a").click()
    page.get_by_label("Seitenverhältnis sperren", exact=True).click()
    blocks = by_id(saved(page, client))
    assert blocks["a"]["keep"] is True and blocks["b"]["keep"] is True
    enter(page, "Breite", "150")
    expect(field(page, "Breite")).to_have_value("150")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["w"], blocks["a"]["h"]) == (60, 40)
    assert (blocks["b"]["w"], blocks["b"]["h"]) == (60, 40)


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


def school_block(client, kind):
    """A block of each kind the rule covers, named k."""
    if kind == "picture":
        return {**picture(upload(client)), "id": "k", "x": 20, "y": 150, "w": 60, "h": 40}
    if kind == "maths":
        return box("k", "maths", maths(client))
    if kind == "uhr":
        return box("k", "uhr", UHR, w=180, h=58.5, y=15)
    if kind == "suchsel":
        return box("k", "suchsel", SUCHSEL, y=290, h=20)
    if kind == "zahlenstrahl":
        return box("k", "zahlenstrahl", ZAHLENSTRAHL)
    if kind == "hunderterfeld":
        return box("k", "hunderterfeld", FELD)
    if kind == "rechendreieck":
        return box("k", "rechendreieck", DREIECK)
    if kind == "zahlenmauer":
        return box("k", "zahlenmauer", WALL, w=180, h=60)
    if kind == "selbstkontrolle":
        return box("k", "selbstkontrolle", SK, w=180, h=30)
    if kind == "name":
        return box("k", "name", {}, y=15, h=10, w=180)
    if kind == "points":
        return box("k", "points", {"max": 10})
    props = {"text": TEXT, "shape": RECT, "table": TABLE, "ruling": RULING, "symbol": STAR}[kind]
    return box("k", kind, props)


@pytest.mark.parametrize(
    "kind",
    [
        "text",
        "shape",
        "picture",
        "table",
        "ruling",
        "maths",
        "symbol",
        "uhr",
        "suchsel",
        "zahlenstrahl",
        "hunderterfeld",
        "rechendreieck",
        "zahlenmauer",
        "selbstkontrolle",
        "name",
        "points",
    ],
)
def test_every_kind_halves_its_width_on_a_percent(editor, kind):
    client = user()
    before = by_id([{**school_block(client, kind)}])["k"]
    page = editor(school_block(client, kind), client=client)
    pick(page, "k")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite %")).to_have_value("100")
    (b,) = saved(page, client)
    assert b["w"] == pytest.approx(before["w"] / 2, abs=0.05)


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


def test_a_group_of_a_ruling_and_maths_scales_by_height_percent(editor):
    client = user()
    page = editor(
        box("r", "ruling", RULING, x=15, y=50, w=60, h=20, group=["g"]),
        box("m", "maths", maths(client), z=2, x=15, y=90, group=["g"]),
        client=client,
    )
    at(page, "r").click()
    enter(page, "Höhe %", "50")
    expect(field(page, "Höhe %")).to_have_value("100")
    blocks = by_id(saved(page, client))
    assert blocks["r"]["h"] == pytest.approx(10, abs=0.05)


def test_a_percent_on_loose_blocks_scales_each_about_its_own_left_edge(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20),
        client=client,
    )
    pick(page, "a", "b")
    enter(page, "Breite %", "50")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["x"], blocks["a"]["w"]) == (15, 15)
    assert (blocks["b"]["x"], blocks["b"]["w"]) == (60, 15)


def test_a_picture_halves_both_sides_on_a_percent(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "x": 20, "y": 150, "w": 60, "h": 40}
    page = editor(bild, client=client)
    pick(page, "bild")
    enter(page, "Breite %", "50")
    (b,) = saved(page, client)
    assert (b["x"], b["w"], b["h"]) == (20, 30, 20)


def test_a_percent_on_a_group_scales_about_its_left_edge(editor):
    client = user()
    page = pair_group(editor, client)
    at(page, "a").click()
    enter(page, "Breite %", "50")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["x"], blocks["a"]["w"]) == (15, 15)
    assert (blocks["b"]["x"], blocks["b"]["w"]) == (37.5, 15)
