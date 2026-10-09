"""Escape while the mouse holds a block, in Chromium on the built frontend."""

import pytest
from playwright.sync_api import expect
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    arc,
    at,
    box,
    centre,
    expect_picked,
    maths,
    picture,
    upload,
    user,
)

KINDS = ("text", "shape", "line", "picture", "table", "ruling", "maths", "group")
# A table does not turn, and a line turns by its ends, also the blocks picked with it.
LEVEL = {("table", False), ("table", True), ("line", False), ("line", True)}
# A line alone has a handle at each end, and a selection with a line one at each corner.
ENDS = {("line", False), ("line", True)}


def made(kind, client):
    """The blocks of the kind, the first named "a", with room around them to move and turn in."""
    place = {"x": 60, "w": 60}
    if kind == "group":
        return [box(n, "text", TEXT, z=z, group=["g"], **place) for n, z in (("a", 1), ("b", 2))]
    if kind == "picture":
        return [{**picture(upload(client)), "id": "a", "x": 60, "y": 50, "w": 60, "h": 40}]
    types = {"text": "text", "shape": "shape", "line": "shape", "table": "table"}
    props = {"text": TEXT, "shape": RECT, "line": LINE, "table": TABLE, "ruling": RULING}
    return [box("a", types.get(kind, kind), props.get(kind) or maths(client), **place)]


def opened(editor, kind, more=False):
    """The editor with the kind's blocks selected, with one more text beside them if asked."""
    client = user()
    blocks = made(kind, client)
    if more:
        blocks.append(box("z", "text", TEXT, z=4, x=60, w=60))
    page = editor(*blocks, client=client)
    # A click on one block of a group picks the whole group.
    at(page, "a").click()
    if more:
        at(page, "z").click(modifiers=["Shift"])
    expect_picked(page, *(b["id"] for b in blocks))
    return page


LOOK = "[...document.querySelectorAll('.sheet .block[data-id]')].map((el) => el.outerHTML).join()"


def look(page):
    """All the first page's blocks as they are drawn: where, how large, how turned, and what in."""
    return page.evaluate(LOOK)


def expect_look(page, was, same=True):
    """Waits until the blocks are drawn as they `was`, or with `same` off, some other way."""
    page.wait_for_function(f"([was, same]) => ({LOOK} === was) === same", arg=[was, same])


def hold(page, way, kind, more, keys=()):
    """Presses the mouse for a move, a resize or a turn and takes it some way. Gives the way on."""
    if way == "move":
        x, y = centre(at(page, "a"))
        points = [(x, y), (x + 60, y + 40), (x + 90, y + 70)]
    elif way == "resize":
        corner = ".sheet .end" if (kind, more) in ENDS else ".moveable-control.moveable-se"
        x, y = centre(page.locator(corner).last)
        points = [(x, y), (x + 40, y + 30), (x + 70, y + 50)]
    else:
        x, y = centre(page.locator(".moveable-rotation-control"))
        points = arc((x, y), (x, y + 80), 60, steps=2)
    page.mouse.move(*points[0])
    for key in keys:
        page.keyboard.down(key)
    page.mouse.down()
    page.mouse.move(*points[1], steps=5)
    return points[2]


WAYS = [
    (kind, more, way)
    for kind in KINDS
    for more in (False, True)
    for way in ("move", "resize", "turn")
    if way != "turn" or (kind, more) not in LEVEL
]


@pytest.mark.parametrize(("kind", "more", "way"), WAYS)
def test_escape_calls_a_drag_off(editor, kind, more, way):
    page = opened(editor, kind, more)
    was, names = look(page), page.locator(".block.sel").count()
    on = hold(page, way, kind, more)
    expect_look(page, was, same=False)
    page.keyboard.press("Escape")
    expect_look(page, was)
    # The mouse still held moves nothing more, and its release neither moves nor deselects.
    page.mouse.move(*on, steps=3)
    assert look(page) == was
    page.mouse.up()
    assert look(page) == was
    expect(page.locator(".block.sel")).to_have_count(names)
    expect(page.locator(".sheet .block[data-id]")).to_have_count(names)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    # Moveable's handles are back with the blocks, and the next Escape is a lone one again.
    if (kind, more) not in ENDS:
        nw = page.locator(".moveable-control.moveable-nw").bounding_box()
        boxes = [b.bounding_box() for b in page.locator(".sheet .block.sel").all()]
        assert abs(nw["x"] + nw["width"] / 2 - min(b["x"] for b in boxes)) < 2
        assert abs(nw["y"] + nw["height"] / 2 - min(b["y"] for b in boxes)) < 2
    page.keyboard.press("Escape")
    expect_picked(page)


@pytest.mark.parametrize("way", ["move", "resize", "turn"])
def test_escape_in_a_drag_keeps_undo_and_redo(editor, way):
    page = opened(editor, "text")
    first = look(page)
    page.keyboard.press("ArrowRight")
    expect_look(page, first, same=False)
    second = look(page)
    # A run of arrows is one undo step, and a press of the mouse ends the run.
    at(page, "a").click()
    page.keyboard.press("ArrowDown")
    expect_look(page, second, same=False)
    third = look(page)
    page.keyboard.press("Control+z")
    expect_look(page, second)
    hold(page, way, "text", False)
    expect_look(page, second, same=False)
    page.keyboard.press("Escape")
    page.mouse.up()
    expect_look(page, second)
    page.keyboard.press("Control+y")
    expect_look(page, third)
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect_look(page, first)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_escape_before_the_mouse_moves_takes_no_undo_step(editor):
    page = opened(editor, "text")
    first = look(page)
    page.keyboard.press("ArrowRight")
    expect_look(page, first, same=False)
    second = look(page)
    page.mouse.move(*centre(at(page, "a")))
    page.mouse.down()
    page.keyboard.press("Escape")
    page.mouse.up()
    assert look(page) == second
    expect_picked(page, "a")
    page.keyboard.press("Control+z")
    expect_look(page, first)


def test_a_drag_after_one_called_off_is_an_undo_step_of_its_own(editor):
    page = opened(editor, "text")
    first = look(page)
    page.keyboard.press("ArrowRight")
    expect_look(page, first, same=False)
    second = look(page)
    hold(page, "move", "text", False)
    page.keyboard.press("Escape")
    page.mouse.up()
    expect_look(page, second)
    hold(page, "move", "text", False)
    page.mouse.up()
    expect_look(page, second, same=False)
    page.keyboard.press("Control+z")
    expect_look(page, second)
    page.keyboard.press("Control+z")
    expect_look(page, first)


@pytest.mark.parametrize("more", [False, True])
def test_escape_in_a_drag_with_ctrl_leaves_no_copy(editor, more):
    page = opened(editor, "group" if more else "text")
    was = look(page)
    on = hold(page, "move", "text", False, keys=["Control"])
    expect_look(page, was, same=False)
    page.keyboard.press("Escape")
    page.mouse.move(*on, steps=3)
    page.mouse.up()
    page.keyboard.up("Control")
    expect_look(page, was)
    expect(page.locator(".sheet .block[data-id]")).to_have_count(2 if more else 1)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


# What Escape calls off besides Moveable's drags: the line between a table's columns, a guide line
# of the sheet or of one page, and in a crop a handle of the frame or the frame itself.
GRIPS = {
    "column": ".sheet > .bar",
    "guide": ".sheet .rule b",
    "own guide": ".sheet .rule.own b",
    "crop handle": ".crop .end",
    "crop frame": ".crop > div",
}
LINES = "[...document.querySelectorAll('.sheet .rule, .sheet > .bar, .crop > div')]"
DRAWN = f"{LOOK} + {LINES}.map((el) => el.style.cssText).join()"


def drawn(page):
    """The blocks, and where the guide lines, a table's column lines and a crop's frame lie."""
    return page.evaluate(DRAWN)


def expect_drawn(page, was, same=True):
    page.wait_for_function(f"([was, same]) => ({DRAWN} === was) === same", arg=[was, same])


def click(page):
    """Clicks the block "a" clear of its handles and of the line in a table's middle."""
    box = at(page, "a").bounding_box()
    page.mouse.click(box["x"] + box["width"] / 4, box["y"] + box["height"] / 2)


def laid(editor, thing):
    """The editor with the block "a" selected and what the thing needs.

    That is a table, a guide line, which took one undo step, or a picture cut on every side, so
    that its frame has room to move.
    """
    if "guide" not in thing:
        client = user()
        cut = {"upload": upload(client), "ratio": 1.5, "cut": [0.2, 0.2, 0.2, 0.2]}
        a = box("a", "image", cut, x=60, w=60, h=40)
        page = editor(a if "crop" in thing else box("a", "table", TABLE, x=60, w=60), client=client)
        click(page)
        expect_picked(page, "a")
        return page
    page = editor(box("a", "text", TEXT, x=60, w=60))
    at(page, "a").click()
    page.get_by_role("tab", name="Ansicht").click()
    if thing == "own guide":
        page.get_by_role("button", name="Nur diese Seite").click()
    page.get_by_role("button", name="Senkrecht").click()
    expect(page.locator(GRIPS[thing])).to_have_count(1)
    return page


def crop(page, thing):
    """Opens the crop for the things that are part of it."""
    if "crop" in thing:
        at(page, "a").dblclick()
        expect(page.locator(".crop")).to_have_count(1)


def grab(page, thing, by=(40, 30)):
    """Presses the mouse on the thing and takes it some way. Gives the way on."""
    x, y = centre(page.locator(GRIPS[thing]).first)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + by[0], y + by[1], steps=5)
    return x + 2 * by[0], y + 2 * by[1]


@pytest.mark.parametrize("thing", GRIPS)
def test_escape_calls_the_drag_of_a_line_or_a_frame_off(editor, thing):
    """#199"""
    page = laid(editor, thing)
    shut = look(page)
    crop(page, thing)
    was = drawn(page)
    on = grab(page, thing)
    expect_drawn(page, was, same=False)
    page.keyboard.press("Escape")
    expect_drawn(page, was)
    # The mouse still held moves nothing more, and neither does its release.
    page.mouse.move(*on, steps=3)
    assert drawn(page) == was
    page.mouse.up()
    # The handle hears that it was let go with the pointer's next move.
    page.mouse.move(on[0] + 5, on[1], steps=2)
    assert drawn(page) == was
    expect_picked(page, "a")
    if "crop" in thing:
        # The crop is still open, and the next Escape ends it with nothing cut.
        expect(page.locator(".crop")).to_have_count(1)
        page.keyboard.press("Escape")
        expect(page.locator(".crop")).to_have_count(0)
        expect_look(page, shut)
    if "guide" in thing:
        # The one undo step is the guide line's own.
        page.keyboard.press("Control+z")
        expect(page.locator(".sheet .rule")).to_have_count(0)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


@pytest.mark.parametrize("thing", GRIPS)
def test_escape_in_the_drag_of_a_line_or_a_frame_keeps_undo_and_redo(editor, thing):
    """#199: what redo held stays, and the next drag is an undo step of its own."""
    page = laid(editor, thing)
    first = look(page)
    page.keyboard.press("ArrowRight")
    expect_look(page, first, same=False)
    second = look(page)
    # A run of arrows is one undo step, and a press of the mouse ends the run.
    click(page)
    page.keyboard.press("ArrowDown")
    expect_look(page, second, same=False)
    third = look(page)
    page.keyboard.press("Control+z")
    expect_look(page, second)
    crop(page, thing)
    was = drawn(page)
    grab(page, thing)
    expect_drawn(page, was, same=False)
    page.keyboard.press("Escape")
    page.mouse.up()
    expect_drawn(page, was)
    if "crop" in thing:
        page.keyboard.press("Escape")
        expect(page.locator(".crop")).to_have_count(0)
    page.keyboard.press("Control+y")
    expect_look(page, third)
    if "crop" in thing:
        # A crop's drag is no undo step: the cut is, when the crop ends.
        return
    page.keyboard.press("Control+z")
    expect_drawn(page, was)
    grab(page, thing)
    page.mouse.up()
    expect_drawn(page, was, same=False)
    page.keyboard.press("Control+z")
    expect_drawn(page, was)
    page.keyboard.press("Control+z")
    expect_look(page, first)
    expect(page.locator(GRIPS[thing])).to_have_count(1)


@pytest.mark.parametrize("thing", ["guide", "own guide"])
def test_a_guide_line_dragged_off_the_page_and_called_off_stays(editor, thing):
    """#199"""
    page = laid(editor, thing)
    was = drawn(page)
    # Left of the page a guide line is let go for good.
    away = page.locator(".sheet").bounding_box()["x"] - 30 - centre(page.locator(GRIPS[thing]))[0]
    on = grab(page, thing, by=(away, 0))
    expect_drawn(page, was, same=False)
    page.keyboard.press("Escape")
    expect_drawn(page, was)
    page.mouse.up()
    page.mouse.move(on[0] + 5, on[1] + 5, steps=2)
    assert drawn(page) == was
    expect(page.locator(GRIPS[thing])).to_have_count(1)
    page.keyboard.press("Control+z")
    expect(page.locator(".sheet .rule")).to_have_count(0)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
