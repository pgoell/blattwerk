"""Turning and flipping blocks, in Chromium on the built frontend."""

import math

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
    TABLE,
    TEXT,
    angle,
    arc,
    at,
    box,
    centre,
    drag,
    expect_picked,
    mirror,
    pick,
    picture,
    saved,
    swipe,
    upload,
    user,
)

# Moveable's handle above the selection, the one that turns it.
HANDLE = ".moveable-rotation-control"
TURNS = ("Rechtsdrehung 90°", "Linksdrehung 90°")
FLIPS = ("Horizontal spiegeln", "Vertikal spiegeln")
STAR = {"code": "2B50"}


def turn(page, about, degrees, keys=()):
    """Drags the handle so many degrees clockwise around the point."""
    drag(page, *arc(centre(page.locator(HANDLE)), about, degrees), keys=keys)


def expect_no_handle(page):
    """Moveable draws no handle at all for what cannot turn."""
    expect(page.locator(HANDLE)).to_have_count(0)


def button(page, label):
    return page.get_by_label(label, exact=True)


def size(page, name):
    """The block's own width and height in px of the layout, whichever way it is turned."""
    return at(page, name).evaluate("el => [el.offsetWidth, el.offsetHeight]")


def grow(page, by):
    """Drags the selection's handle at its lower right corner away from the upper left one."""
    start, end = (centre(page.locator(f".moveable-control.moveable-{c}")) for c in ("nw", "se"))
    far = math.dist(start, end)
    drag(page, end, tuple(e + (e - s) * by / far for s, e in zip(start, end, strict=True)))


def a_picture(client, **more):
    """A picture 60 by 40 mm with room around it to turn in."""
    place = {"id": "bild", "x": 75, "y": 60, "w": 60, "h": 40}
    return {**picture(upload(client)), **place, **more}


def test_the_handle_turns_a_block_about_its_centre(editor):
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20))
    pick(page, "a")
    middle = centre(at(page, "a"))
    # The handle stands above the block, so a quarter of the way round takes it to the right side.
    turn(page, middle, 90)
    assert abs(angle(page, "a") - 90) <= 3
    assert centre(at(page, "a")) == pytest.approx(middle, abs=1)


def test_shift_turns_in_steps_of_15_degrees(editor):
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20))
    pick(page, "a")
    turn(page, centre(at(page, "a")), 50, keys=["Shift"])
    assert angle(page, "a") != 0
    assert angle(page, "a") % 15 == 0


def test_flip_mirrors_a_picture(editor):
    client = user()
    page = editor(
        a_picture(client), box("stern", "symbol", STAR, x=30, y=60, w=20, h=20), client=client
    )
    for name in ("bild", "stern"):
        pick(page, name)
        assert mirror(page, name) == (1, 1)
        # Each flip is of one axis, and a second one of the same axis takes the first back.
        for label, drawn in zip((*FLIPS, FLIPS[0]), [(-1, 1), (-1, -1), (1, -1)], strict=True):
            button(page, label).click()
            assert mirror(page, name) == drawn


def test_flip_turns_an_arrow_round(editor):
    client = user()
    page = editor(box("pfeil", "shape", {**LINE, "kind": "arrow"}), client=client)
    pick(page, "pfeil")
    # An arrow starts at the upper left corner of its box. A flip moves the start to another
    # corner and mirrors nothing.
    for label, corner in zip(FLIPS, ("ne", "se"), strict=True):
        button(page, label).click()
        (arrow,) = saved(page, client)
        assert arrow["props"]["from"] == corner
        assert not arrow.get("flipX") and not arrow.get("flipY")


def test_a_turned_block_moves_and_snaps(editor):
    # On its side the block is 20 mm wide about its centre at 70 mm: its outline starts at 60 mm.
    page = editor(box("a", "shape", RECT, x=40, y=80, w=60, h=20, angle=90))
    sheet = page.locator(".sheet").bounding_box()
    k = sheet["width"] / 210
    pick(page, "a")
    x, y = centre(at(page, "a"))
    # The drag leaves the outline 0.8 mm short of the page's margin at 15 mm, and the margin takes
    # it. The block's own box, 20 mm further left, is near no guide.
    drag(page, (x, y), (x - 44.2 * k, y))
    assert at(page, "a").bounding_box()["x"] == pytest.approx(sheet["x"] + 15 * k, abs=0.5)
    assert angle(page, "a") == 90


def test_a_turned_block_resizes_from_its_corner(editor):
    page = editor(box("a", "shape", RECT, x=75, y=60, w=60, h=20, angle=90))
    pick(page, "a")
    was = at(page, "a").bounding_box()
    before = size(page, "a")
    grow(page, 40)
    assert angle(page, "a") == 90
    assert all(now > was for now, was in zip(size(page, "a"), before, strict=True))
    # Turned a quarter clockwise, the block's upper left corner is the upper right one of its
    # outline. It lies across from the dragged corner and is where it was on the screen.
    now = at(page, "a").bounding_box()
    assert now["x"] + now["width"] == pytest.approx(was["x"] + was["width"], abs=1.5)
    assert now["y"] == pytest.approx(was["y"], abs=1.5)


def test_an_edge_handle_on_a_turned_block_leaves_the_other_axis(editor):
    client = user()
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=30, angle=30), client=client)
    pick(page, "a")
    # The right edge's handle, pulled 40 px out along the block's own width.
    x, y = centre(page.locator(".moveable-control.moveable-e"))
    drag(page, (x, y), (x + 40 * math.cos(math.radians(30)), y + 40 * math.sin(math.radians(30))))
    (a,) = saved(page, client)
    assert a["h"] == 30
    assert a["w"] > 65
    assert a["angle"] == 30


@pytest.mark.parametrize("degrees", [0, 90])
def test_the_top_handle_resizes_under_the_rotate_stem(editor, degrees):
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20, angle=degrees))
    pick(page, "a")
    width, height = size(page, "a")
    # The stem of the handle that turns runs from the exact centre of the top edge's handle.
    x, y = centre(page.locator(".moveable-control.moveable-n"))
    out = (30, 0) if degrees else (0, -30)
    drag(page, (x, y), (x + out[0], y + out[1]))
    assert size(page, "a")[0] == width
    assert size(page, "a")[1] > height + 20
    assert angle(page, "a") == degrees


def test_a_group_with_a_turned_block_resizes(editor):
    page = editor(
        box("a", "shape", RECT, x=40, y=60, w=40, h=20, angle=30),
        box("b", "shape", RECT, z=2, x=110, y=60, w=40, h=20),
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    pick(page, "a", "b")
    before = [size(page, name) for name in ("a", "b")]
    grow(page, 60)
    for name, was in zip(("a", "b"), before, strict=True):
        assert size(page, name) != was
    assert [angle(page, name) for name in ("a", "b")] == [30, 0]
    assert errors == []


def test_a_turned_picture_crops_in_place(editor):
    client = user()
    page = editor(a_picture(client, angle=90, flipX=True), client=client)
    pick(page, "bild")
    expect(page.locator(HANDLE)).to_have_count(1)
    page.get_by_role("button", name="Zuschneiden").click()
    expect(page.locator(".crop")).to_have_count(1)
    expect_no_handle(page)
    was = at(page, "bild").bounding_box()
    # Turned a quarter clockwise, the picture's left edge is the top of its outline on the screen.
    # The flip decides which of the frame's handles stands there, so the handle is found by its
    # place: the one in the middle of the outline's top edge.
    top = (was["x"] + was["width"] / 2, was["y"])
    handle = min(
        (centre(end) for end in page.locator(".crop .end").all()),
        key=lambda end: math.dist(end, top),
    )
    drag(page, handle, (handle[0], handle[1] + 15))
    page.get_by_role("button", name="Fertig").click()
    expect(page.locator(".crop")).to_have_count(0)
    now = at(page, "bild").bounding_box()
    # The top of the outline came down with the handle. What stays of the picture keeps its place:
    # the bottom, across from the handle, and the two sides have not moved.
    assert now["y"] - was["y"] == pytest.approx(15, abs=2)
    for side in ("x", "width"):
        assert now[side] == pytest.approx(was[side], abs=1.5)
    assert now["y"] + now["height"] == pytest.approx(was["y"] + was["height"], abs=1.5)
    assert angle(page, "bild") == 90
    assert mirror(page, "bild") == (-1, 1)


def test_a_finger_turns_a_block(editor):
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    middle = centre(at(page, "a"))
    swipe(page, *arc(centre(page.locator(HANDLE)), middle, 90))
    # A finger is less exact than a mouse: the browser may keep its first few pixels to itself.
    assert abs(angle(page, "a") - 90) <= 5
    assert centre(at(page, "a")) == pytest.approx(middle, abs=1)


def test_undo_takes_back_a_turn_and_a_flip(editor):
    page = editor(box("stern", "symbol", STAR, x=95, y=80, w=20, h=20))
    pick(page, "stern")
    turn(page, centre(at(page, "stern")), 90)
    turned = angle(page, "stern")
    assert abs(turned - 90) <= 3
    # The whole drag was one step: one undo takes it all back and leaves nothing to undo.
    page.keyboard.press("Control+z")
    assert angle(page, "stern") == 0
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    page.keyboard.press("Control+y")
    assert angle(page, "stern") == turned
    # A flip mirrors the picture and the angle in one step.
    button(page, FLIPS[0]).click()
    assert mirror(page, "stern") == (-1, 1)
    assert angle(page, "stern") == pytest.approx(360 - turned, abs=0.02)
    page.keyboard.press("Control+z")
    assert mirror(page, "stern") == (1, 1)
    assert angle(page, "stern") == turned


def test_the_buttons_turn_by_90_degrees(editor):
    page = editor(box("a", "text", TEXT, x=75, y=100, w=60, h=20))
    pick(page, "a")
    right, left = (button(page, label) for label in TURNS)
    for _ in range(2):
        right.click()
    assert angle(page, "a") == 180
    # Past 0 the angle goes on from 360.
    for _ in range(3):
        left.click()
    assert angle(page, "a") == 270
    # Each press is a step of its own to undo.
    page.keyboard.press("Control+z")
    assert angle(page, "a") == 0


def test_flip_mirrors_the_angle(editor):
    page = editor(box("a", "shape", {**RECT, "text": "Hallo"}, x=75, y=80, w=60, h=20, angle=30))
    pick(page, "a")
    for label, degrees in zip(FLIPS, (330, 30), strict=True):
        button(page, label).click()
        assert angle(page, "a") == degrees
        # The words of a shape stay readable: nothing in it is mirrored.
        expect(at(page, "a").locator(".frame")).to_have_css("transform", "none")
        expect(at(page, "a").locator(".frame p")).to_have_css("transform", "none")


def test_a_locked_block_does_not_turn(editor):
    # A shape that is not locked can both turn and flip.
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20, locked=True))
    pick(page, "a")
    expect_no_handle(page)
    for label in (*TURNS, *FLIPS):
        expect(button(page, label)).to_be_disabled()


@pytest.mark.parametrize("group", [None, ["g"]])
def test_a_group_turns_as_one(editor, group):
    # Side by side, 40 mm from centre to centre: two loose blocks, or a group.
    page = editor(
        box("a", "shape", RECT, x=60, y=80, w=30, h=20, group=group),
        box("b", "shape", RECT, z=2, x=100, y=80, w=30, h=20, group=group),
    )
    k = page.locator(".sheet").bounding_box()["width"] / 210
    if group:
        # One click picks a whole group.
        at(page, "a").click()
        expect_picked(page, "a", "b")
    else:
        pick(page, "a", "b")

    def middle():
        """The centre of the box around both blocks."""
        (ax, ay), (bx, by) = centre(at(page, "a")), centre(at(page, "b"))
        return (ax + bx) / 2, (ay + by) / 2

    about = middle()
    turn(page, about, 90)
    for name in ("a", "b"):
        assert abs(angle(page, name) - 90) <= 3
    assert middle() == pytest.approx(about, abs=2)
    # Each block went a quarter of the way round the common centre: the left one is now above it,
    # and the right one below.
    x, y = centre(at(page, "a"))
    assert abs(x - about[0]) < 8
    assert about[1] - y == pytest.approx(20 * k, abs=5)


def test_a_turned_text_takes_typing(editor):
    page = editor(box("a", "text", TEXT, x=75, y=100, w=60, h=20, angle=90))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")
    assert angle(page, "a") == 90


def test_a_copy_keeps_angle_and_flip(editor):
    client = user()
    page = editor(a_picture(client, angle=45, flipX=True), client=client)
    pick(page, "bild")
    page.keyboard.press("Control+d")
    expect(page.locator(".block")).to_have_count(2)
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block")).to_have_count(3)
    for name in page.eval_on_selector_all(".block", "els => els.map((el) => el.dataset.id)"):
        assert angle(page, name) == 45
        assert mirror(page, name) == (-1, 1)


def test_a_table_and_a_line_have_no_handle(editor):
    page = editor(
        box("table", "table", TABLE), box("line", "shape", LINE, z=2), box("a", "shape", RECT, z=3)
    )
    right, left = (button(page, label) for label in TURNS)
    # A shape has the handle, so the checks below would see one.
    pick(page, "a")
    expect(page.locator(HANDLE)).to_have_count(1)
    expect(right).to_be_enabled()
    # A table stays level.
    pick(page, "table")
    expect_no_handle(page)
    expect(right).to_be_disabled()
    expect(left).to_be_disabled()
    # A line turns by its ends, and a flip moves its start to another corner.
    pick(page, "line")
    expect_no_handle(page)
    expect(right).to_be_disabled()
    expect(left).to_be_disabled()
    for label in FLIPS:
        expect(button(page, label)).to_be_enabled()
    pick(page, "a", "line")
    expect_no_handle(page)
