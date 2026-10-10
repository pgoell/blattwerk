"""A group turns and flips as one by the panel's buttons, as by the handle and as in PowerPoint.
Asked #317."""

import math

import pytest
from playwright.sync_api import expect
from test_rotate import FLIPS, TURNS, button, turn
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    picture,
    saved,
    upload,
    user,
)

G = {"group": ["g"]}
TRIANGLE = {**RECT, "kind": "triangle"}
RIGHT, LEFT = TURNS
ACROSS, DOWN = FLIPS
# From which corner a line runs on after a quarter turn clockwise.
NEXT = {"nw": "ne", "ne": "se", "se": "sw", "sw": "nw"}


def pair(**triangle):
    """A rectangle on the left and a triangle on the right, in one group."""
    return [
        box("a", "shape", RECT, x=60, y=80, w=30, h=20, **G),
        box("b", "shape", TRIANGLE, z=2, **{"x": 100, "y": 80, "w": 30, "h": 20, **G, **triangle}),
    ]


def hull(blocks):
    """The level box around the blocks as they lie, turned or not: left, top, right, bottom."""
    sides = []
    for b in blocks:
        c, s = (abs(f(math.radians(b.get("angle", 0)))) for f in (math.cos, math.sin))
        w, h = b["w"] * c + b["h"] * s, b["w"] * s + b["h"] * c
        x, y = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        sides.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2))
    left, top, right, bottom = zip(*sides, strict=True)
    return min(left), min(top), max(right), max(bottom)


def round_about(blocks, quarters=1):
    """Level blocks after so many quarter turns clockwise as one, about the middle of their box.

    Only for places that stay on the sheet's hundredths: Python rounds a half another way.
    """
    for _ in range(quarters % 4):
        left, top, right, bottom = hull(blocks)
        cx, cy = (left + right) / 2, (top + bottom) / 2
        turned = []
        for b in blocks:
            x, y = b["x"] + b["w"] / 2 - cx, b["y"] + b["h"] / 2 - cy
            line = b["props"].get("kind") == "line"
            w, h = (b["h"], b["w"]) if line else (b["w"], b["h"])
            now = {**b, "x": cx - y - w / 2, "y": cy + x - h / 2, "w": w, "h": h}
            if line:
                now["props"] = {**b["props"], "from": NEXT[b["props"].get("from", "nw")]}
            else:
                now["angle"] = (b.get("angle", 0) + 90) % 360
            turned.append(now)
        blocks = turned
    return blocks


def lie(blocks):
    """Where and how each block lies: its box, its angle, its flips and a line's start."""
    return {
        b["id"]: (
            *(pytest.approx(b[side], abs=0.001) for side in "xywh"),
            b.get("angle", 0),
            bool(b.get("flipX")),
            bool(b.get("flipY")),
            b["props"].get("from", "nw") if b["props"].get("kind") == "line" else None,
        )
        for b in blocks
    }


def frame(page, *names):
    """The box around the blocks on the screen, as the frame around a group shows it."""
    boxes = [at(page, name).bounding_box() for name in names]
    return (
        min(b["x"] for b in boxes),
        min(b["y"] for b in boxes),
        max(b["x"] + b["width"] for b in boxes),
        max(b["y"] + b["height"] for b in boxes),
    )


def group(page, name, *names):
    """Picks the whole group by a click on one of its blocks."""
    at(page, name).click()
    expect_picked(page, name, *names)


@pytest.mark.parametrize("label", TURNS)
def test_a_button_turns_a_group_as_the_handle_does(editor, label):
    client = user()
    page = editor(*pair(), client=client)
    group(page, "a", "b")
    # A group has no angle of its own to type.
    expect(page.get_by_label("Drehung", exact=True)).to_be_disabled()
    button(page, label).click()
    by_button = {b["id"]: b for b in saved(page, client)}
    # The blocks went round the middle of the group, at 95 by 90 mm: clockwise the left one is
    # now on top and the right one below.
    over, under = ("a", "b") if label == RIGHT else ("b", "a")
    assert lie(by_button.values()) == {
        over: (80, 60, 30, 20, 90 if label == RIGHT else 270, False, False, None),
        under: (80, 100, 30, 20, 90 if label == RIGHT else 270, False, False, None),
    }
    expect(page.get_by_label("Drehung", exact=True)).to_be_disabled()
    page.keyboard.press("Control+z")
    assert lie(saved(page, client)) == lie(pair())
    # The handle, dragged a quarter of the way round, gives the same sheet within a drag's reach.
    sheet = page.locator(".sheet").bounding_box()
    k = sheet["width"] / 210
    turn(page, (sheet["x"] + 95 * k, sheet["y"] + 90 * k), 90 if label == RIGHT else -90)
    for b in saved(page, client):
        want = by_button[b["id"]]
        assert abs(b["angle"] - want["angle"]) <= 3
        assert (b["x"], b["y"]) == pytest.approx((want["x"], want["y"]), abs=2)


@pytest.mark.parametrize("label", FLIPS)
def test_a_flip_mirrors_a_group_as_one(editor, label):
    client = user()
    # The triangle lies to the right of the rectangle and below it.
    page = editor(*pair(y=110), client=client)
    group(page, "a", "b")
    was = frame(page, "a", "b")
    button(page, label).click()
    # The blocks swap sides, and the triangle itself is mirrored: a rectangle looks the same.
    wanted = {
        ACROSS: {
            "a": (100, 80, 30, 20, 0, False, False, None),
            "b": (60, 110, 30, 20, 0, True, False, None),
        },
        DOWN: {
            "a": (60, 110, 30, 20, 0, False, False, None),
            "b": (100, 80, 30, 20, 0, False, True, None),
        },
    }
    assert lie(saved(page, client)) == wanted[label]
    # The box around the group stays where it was.
    assert frame(page, "a", "b") == pytest.approx(was, abs=0.5)


@pytest.mark.parametrize("label", FLIPS)
def test_a_flip_leaves_the_frame_of_a_group_with_a_turned_block(editor, label):
    client = user()
    page = editor(*pair(y=110, angle=30), client=client)
    group(page, "a", "b")
    was = frame(page, "a", "b")
    button(page, label).click()
    a, b = saved(page, client)
    assert hull([a, b]) == pytest.approx(hull(pair(y=110, angle=30)), abs=0.011)
    assert frame(page, "a", "b") == pytest.approx(was, abs=0.5)
    # The turned triangle leans the other way, on the other side.
    assert b["angle"] == 330
    assert (b["x"] < a["x"]) if label == ACROSS else (b["y"] < a["y"])


def kinds(client):
    return {
        "text": ("text", TEXT),
        "shape": ("shape", TRIANGLE),
        "picture": ("image", picture(upload(client))["props"]),
        "symbol": ("symbol", {"code": "2B50"}),
        "ruling": ("ruling", RULING),
        "maths": ("maths", maths(client)),
        "line": ("shape", LINE),
        "table": ("table", TABLE),
    }


def with_mate(client, name):
    """A block of the kind on the left and a rectangle on the right, in one group."""
    kind, props = kinds(client)[name]
    return [
        box("k", kind, props, x=30, y=60, w=60, h=40, **G),
        box("m", "shape", RECT, z=2, x=110, y=60, w=40, h=40, **G),
    ]


@pytest.mark.parametrize("name", ["text", "shape", "picture", "symbol", "ruling", "maths", "line"])
def test_every_type_goes_with_its_group(editor, name):
    client = user()
    first = with_mate(client, name)
    page = editor(*first, client=client)
    group(page, "k", "m")
    for label in (*TURNS, *FLIPS):
        expect(button(page, label)).to_be_enabled()
    button(page, RIGHT).click()
    # A line has no angle: its box goes round, and it starts at the next corner.
    assert lie(saved(page, client)) == lie(round_about(first))
    button(page, LEFT).click()
    assert lie(saved(page, client)) == lie(first)
    button(page, ACROSS).click()
    k, m = saved(page, client)
    # The group's box runs from 30 to 150 mm: each block lies as far from the right as it did
    # from the left.
    assert (k["x"], k["y"], m["x"], m["y"]) == (90, 60, 30, 60)
    # What can be mirrored is; a line starts at the other end; the rest stays readable.
    flips = name in ("shape", "picture", "symbol")
    assert lie([k])["k"][4:] == (0, flips, False, "ne" if name == "line" else None)


def test_a_group_with_a_table_flips_and_does_not_turn(editor):
    client = user()
    page = editor(*with_mate(client, "table"), client=client)
    group(page, "k", "m")
    # The app has no turned table.
    for label in TURNS:
        expect(button(page, label)).to_be_disabled()
    button(page, ACROSS).click()
    k, m = saved(page, client)
    assert (k["x"], k["y"], m["x"], m["y"]) == (90, 60, 30, 60)
    assert lie([k])["k"][4:] == (0, False, False, None)


def odd():
    """A group of odd sizes: its middle lies on a half and a quarter of a mm."""
    return [
        box("a", "shape", RECT, x=60, y=80, w=31, h=20, **G),
        box("b", "shape", TRIANGLE, z=2, x=100.5, y=83, w=30, h=25, **G),
        box("c", "shape", LINE, z=3, x=70.25, y=110, w=33.3, h=7, **G),
    ]


@pytest.mark.parametrize("label", [*TURNS, *FLIPS])
def test_one_undo_takes_a_turn_or_a_flip_of_a_group_back(editor, label):
    client = user()
    page = editor(*odd(), client=client)
    group(page, "a", "b", "c")
    button(page, label).click()
    assert lie(saved(page, client)) != lie(odd())
    page.keyboard.press("Control+z")
    assert lie(saved(page, client)) == lie(odd())
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


@pytest.mark.parametrize("label", [*TURNS, *FLIPS])
def test_four_turns_or_two_flips_of_a_group_give_the_first_sheet(editor, label):
    client = user()
    page = editor(*odd(), client=client)
    group(page, "a", "b", "c")
    for _ in range(4 if label in TURNS else 2):
        button(page, label).click()
    assert lie(saved(page, client)) == lie(odd())
    # Not for want of a change: one step back is another sheet.
    page.keyboard.press("Control+z")
    assert lie(saved(page, client)) != lie(odd())


def test_a_group_goes_as_one_and_a_loose_block_about_its_own_middle(editor):
    client = user()
    loose = box("c", "shape", RECT, z=3, x=40, y=150, w=40, h=10)
    page = editor(*pair(), loose, client=client)
    group(page, "a", "b")
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    button(page, RIGHT).click()
    assert lie(saved(page, client)) == lie([*round_about(pair()), {**loose, "angle": 90}])
    # A flip too: the group's blocks swap sides, and the loose block stays in its place.
    button(page, LEFT).click()
    button(page, ACROSS).click()
    a, b, c = saved(page, client)
    assert (a["x"], b["x"], c["x"]) == (100, 60, 40)


def test_a_block_picked_out_of_its_group_turns_on_its_spot(editor):
    client = user()
    page = editor(*pair(), client=client)
    group(page, "a", "b")
    # A second click picks the block alone. The frame around the picked group lies over it.
    at(page, "b").click(force=True)
    expect_picked(page, "b")
    button(page, RIGHT).click()
    a, b = pair()
    assert lie(saved(page, client)) == lie([a, {**b, "angle": 90}])
    button(page, ACROSS).click()
    assert lie(saved(page, client)) == lie([a, {**b, "angle": 270, "flipX": True}])


def test_nested_groups_go_as_the_outermost_group(editor):
    client = user()
    a, b = pair(group=["g", "inner"])
    blocks = [
        {**a, "group": ["g", "inner"]},
        b,
        box("c", "shape", RECT, z=3, x=60, y=120, w=70, **G),
    ]
    page = editor(*blocks, client=client)
    group(page, "a", "b", "c")
    button(page, RIGHT).click()
    assert lie(saved(page, client)) == lie(round_about(blocks))
    button(page, RIGHT).click()
    assert lie(saved(page, client)) == lie(round_about(blocks, 2))
