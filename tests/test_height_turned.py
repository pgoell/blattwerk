"""A turned maths block or Lineatur that gets a new height, in Chromium on the built frontend."""

import math

import pytest
from playwright.sync_api import expect
from test_grow_turned import corner, stays
from test_painter import paint
from ui import RULING, at, box, maths, pick, saved, user

ANGLES = [90, 30, 200]
# A block with room around it on a page of 210 by 297 mm.
ROOM = {"x": 75, "y": 140, "w": 60}
MARGIN = 15


def changed(page, client, act):
    """The block "a" as the server holds it once `act` has given it a new height."""
    high = at(page, "a").evaluate("e => getComputedStyle(e).height")
    act()
    expect(at(page, "a")).not_to_have_css("height", high)
    return {b["id"]: b for b in saved(page, client)}["a"]


def ruling(degrees):
    """A Lineatur 4 of two rows. One turned by nothing has no angle, as a new one."""
    return box("a", "ruling", RULING, **ROOM, h=20, **({"angle": degrees} if degrees else {}))


def sums(client, degrees):
    """A maths block of three sums in one row."""
    return box("a", "maths", maths(client), **ROOM, h=12, **({"angle": degrees} if degrees else {}))


def kept(now, was):
    """The edge the block starts at is where it was, as wide and as turned as before."""
    return stays(now, was) and (now["w"], now.get("angle", 0)) == (was["w"], was.get("angle", 0))


def corners(b, more):
    """The four corners on the page, in mm, of the turned block grown `more` mm from its edge."""
    turn = math.radians(b.get("angle", 0))
    c, s = math.cos(turn), math.sin(turn)
    x, y = corner(b)
    ends = [(0, 0), (b["w"], 0), (0, b["h"] + more), (b["w"], b["h"] + more)]
    return [(x + w * c - h * s, y + w * s + h * c) for w, h in ends]


def fits(b, more=0):
    """Whether the turned block lies within the margins of an upright page, grown so or as it is."""
    return all(
        MARGIN - 0.01 <= x <= 210 - MARGIN + 0.01 and MARGIN - 0.01 <= y <= 297 - MARGIN + 0.01
        for x, y in corners(b, more)
    )


@pytest.mark.parametrize("degrees", ANGLES)
@pytest.mark.parametrize("change", ["Eine Aufgabe mehr", "Schriftlich"])
def test_a_turned_maths_block_keeps_its_edge_when_the_panel_changes_it(editor, change, degrees):
    client = user()
    was = sums(client, degrees)
    page = editor(was, client=client)
    pick(page, "a")
    button = page.locator(".panel").get_by_role("button", name=change, exact=True)
    a = changed(page, client, button.click)
    assert a["h"] > 12
    assert kept(a, was)


@pytest.mark.parametrize("degrees", ANGLES)
@pytest.mark.parametrize(("label", "h"), [("Eine Zeile mehr", 30), ("Eine Zeile weniger", 10)])
def test_a_turned_lineatur_keeps_its_edge_with_a_row_more_or_less(editor, label, h, degrees):
    client = user()
    was = ruling(degrees)
    page = editor(was, client=client)
    pick(page, "a")
    a = changed(page, client, page.get_by_label(label).click)
    assert a["h"] == h
    assert kept(a, was)


@pytest.mark.parametrize("degrees", ANGLES)
def test_a_turned_lineatur_keeps_its_edge_when_its_type_changes(editor, degrees):
    client = user()
    was = ruling(degrees)
    page = editor(was, client=client)
    pick(page, "a")
    kind = page.get_by_label("Art der Lineatur")
    a = changed(page, client, lambda: kind.select_option("l2"))
    # Two rows as before, each 16 mm high now.
    assert (a["props"]["kind"], a["h"]) == ("l2", 32)
    assert kept(a, was)


@pytest.mark.parametrize("degrees", ANGLES)
def test_a_turned_lineatur_grows_to_the_margin_it_grows_towards(editor, degrees):
    client = user()
    was = ruling(degrees)
    page = editor(was, client=client)
    pick(page, "a")
    a = changed(page, client, page.get_by_role("button", name="Bis Seitenende").click)
    assert kept(a, was)
    # Whole rows, as many as fit: one more would cross the margin.
    assert a["h"] % 10 == 0
    assert a["h"] > 20
    assert fits(a)
    assert not fits(a, 10)


def test_the_brush_gives_a_turned_maths_block_its_size_from_its_edge(editor):
    client = user()
    was = box("b", "maths", maths(client, seed=8), z=2, x=75, y=150, w=100, h=12, angle=30)
    page = editor(box("a", "maths", maths(client, size=28), h=24), was, client=client)
    paint(page, "a", "b")
    b = saved(page, client)[1]
    assert b["h"] == 24
    assert kept(b, was)


@pytest.mark.parametrize("kind", ["maths", "ruling"])
def test_level_blocks_keep_their_place_with_a_new_height(editor, kind):
    client = user()
    was = sums(client, 0) if kind == "maths" else ruling(0)
    page = editor(was, client=client)
    pick(page, "a")
    panel = page.locator(".panel")
    acts = {
        "maths": [panel.get_by_label("Eine Aufgabe mehr").click],
        "ruling": [
            panel.get_by_label("Eine Zeile mehr").click,
            lambda: panel.get_by_label("Art der Lineatur").select_option("l2"),
            panel.get_by_role("button", name="Bis Seitenende").click,
        ],
    }
    for act in acts[kind]:
        a = changed(page, client, act)
        assert (a["x"], a["y"], a["w"]) == (was["x"], was["y"], was["w"])
        assert "angle" not in a
    # To the end of the page: 142 mm of room below 140 mm hold eight rows of 16 mm.
    assert kind == "maths" or a["h"] == 128


def test_the_brush_leaves_a_level_maths_block_in_its_place(editor):
    client = user()
    was = box("b", "maths", maths(client, seed=8), z=2, h=12)
    page = editor(box("a", "maths", maths(client, size=28), h=24), was, client=client)
    paint(page, "a", "b")
    b = saved(page, client)[1]
    assert (b["x"], b["y"], b["h"]) == (was["x"], was["y"], 24)


@pytest.mark.parametrize("kind", ["maths", "ruling"])
def test_one_undo_takes_back_the_height_and_the_place_of_a_turned_block(editor, kind):
    client = user()
    was = sums(client, 30) if kind == "maths" else ruling(30)
    page = editor(was, client=client)
    pick(page, "a")
    label = "Eine Aufgabe mehr" if kind == "maths" else "Eine Zeile mehr"
    a = changed(page, client, page.locator(".panel").get_by_label(label).click)
    assert (a["x"], a["y"]) != (was["x"], was["y"])
    back = page.get_by_label("Rückgängig")
    a = changed(page, client, back.click)
    assert [a[side] for side in "xyh"] == [was[side] for side in "xyh"]
    expect(back).to_be_disabled()
