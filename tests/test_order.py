"""One step forward and one step backward in the stack: the buttons under "Ebene"."""

import pytest
from playwright.sync_api import expect
from ui import (
    BROWSER,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    unpick,
    upload,
    user,
)

GROUP = {"group": ["g"]}


def boxes(*names, grouped=""):
    """Loose blocks from back to front, one letter each; those in `grouped` are one group."""
    return [
        box(name, "shape", RECT, z=i + 1, **(GROUP if name in grouped else {}))
        for i, name in enumerate(names)
    ]


def step(page, name, tap=False):
    button = page.get_by_role("button", name=name, exact=True)
    button.tap() if tap else button.click()


def expect_stack(page, names):
    """Waits until the blocks lie in this order, from back to front."""
    for i, name in enumerate(names):
        expect(at(page, name)).to_have_css("z-index", str(i + 1))


def test_forward_steps_over_one_block(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "a")
    step(page, "Eine nach vorn")
    expect_stack(page, "bac")


def test_backward_steps_under_one_block(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "c")
    step(page, "Eine nach hinten")
    expect_stack(page, "acb")


def test_a_part_of_a_group_steps_within_the_group(editor):
    page = editor(*boxes(*"abcde", grouped="bcd"))
    # One click picks the whole group, a second one the block alone.
    at(page, "b").click()
    expect_picked(page, "b", "c", "d")
    # The frame around the picked group lies over the block.
    at(page, "b").click(force=True)
    expect_picked(page, "b")
    step(page, "Eine nach vorn")
    expect_stack(page, "acbde")
    step(page, "Eine nach vorn")
    expect_stack(page, "acdbe")
    # In front of its group it stays: one step back from there shows it never passed "e".
    step(page, "Eine nach vorn")
    step(page, "Eine nach hinten")
    expect_stack(page, "acbde")
    step(page, "Eine nach hinten")
    expect_stack(page, "abcde")
    step(page, "Eine nach hinten")
    step(page, "Eine nach vorn")
    expect_stack(page, "acbde")


def test_a_whole_group_steps_as_one(editor):
    page = editor(*boxes(*"abcde", grouped="bc"))
    at(page, "b").click()
    expect_picked(page, "b", "c")
    step(page, "Eine nach vorn")
    expect_stack(page, "adbce")
    step(page, "Eine nach hinten")
    expect_stack(page, "abcde")
    step(page, "Eine nach hinten")
    expect_stack(page, "bcade")


def test_a_finger_steps_the_order(editor):
    page = editor(*boxes(*"abc"), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    step(page, "Eine nach vorn", tap=True)
    expect_stack(page, "bac")
    step(page, "Eine nach vorn", tap=True)
    expect_stack(page, "bca")
    step(page, "Eine nach hinten", tap=True)
    expect_stack(page, "bac")


def test_undo_and_redo_of_a_step(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "a")
    step(page, "Eine nach vorn")
    expect_stack(page, "bac")
    step(page, "Eine nach vorn")
    expect_stack(page, "bca")
    page.keyboard.press("Control+z")
    expect_stack(page, "bac")
    page.keyboard.press("Control+y")
    expect_stack(page, "bca")
    page.keyboard.press("Control+z")
    expect_stack(page, "bac")
    page.keyboard.press("Control+z")
    expect_stack(page, "abc")


def test_a_step_at_the_end_leaves_nothing_to_undo(editor):
    page = editor(*boxes(*"abcd"))
    # Another change first: it is what undo takes back if the steps after it change nothing.
    pick(page, "a")
    step(page, "Eine nach vorn")
    expect_stack(page, "bacd")
    pick(page, "d")
    step(page, "Eine nach vorn")
    pick(page, "b")
    step(page, "Eine nach hinten")
    # Several with nothing unselected beyond them.
    pick(page, "c", "d")
    step(page, "Eine nach vorn")
    pick(page, "b", "a")
    step(page, "Eine nach hinten")
    page.keyboard.press("Control+z")
    expect_stack(page, "abcd")


def test_a_step_jumps_a_whole_group(editor):
    page = editor(*boxes(*"abcd", grouped="bc"))
    pick(page, "a")
    step(page, "Eine nach vorn")
    expect_stack(page, "bcad")
    step(page, "Eine nach hinten")
    expect_stack(page, "abcd")
    pick(page, "d")
    step(page, "Eine nach hinten")
    expect_stack(page, "adbc")


def test_several_blocks_step_together(editor):
    page = editor(*boxes(*"abcd"))
    pick(page, "b", "c")
    step(page, "Eine nach vorn")
    expect_stack(page, "adbc")
    step(page, "Eine nach hinten")
    expect_stack(page, "abcd")
    step(page, "Eine nach hinten")
    expect_stack(page, "bcad")


# Asked #143

KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group"]
LEFT = {"x": 15, "y": 20, "w": 80}


def member(kind, client):
    """The block "a" of one kind, in the group "g"; as a group, in a group of its own inside it."""
    if kind == "picture":
        return {**picture(upload(client)), "id": "a", **LEFT, "h": 20, **GROUP}
    if kind == "maths":
        return box("a", "maths", maths(client), **LEFT, h=12, **GROUP)
    if kind == "group":
        return box("a", "shape", RECT, **LEFT, group=["g", "inner"])
    if kind == "line":
        return box("a", "shape", LINE, **LEFT, h=0, **GROUP)
    props = {"text": TEXT, "shape": RECT, "table": TABLE, "ruling": RULING}[kind]
    return box("a", kind, props, **LEFT, **GROUP)


def seam(page, locator):
    """A point on the left edge that the mouse is over, while the point it reports lies beside it.

    A mouse reports whole pixels, and a block's edge lies between two: Moveable looks up what
    lies under the reported point when the button comes up, and finds another element.
    """
    held = locator.bounding_box()
    y = held["y"] + held["height"] / 2
    page.evaluate("addEventListener('mousemove', (e) => (window.moved = e), true)")
    for quarter in range(-8, 5):
        page.mouse.move(held["x"] + quarter / 4, y)
        over, found = locator.evaluate(
            """(el) => [el.contains(moved.target),
                el.contains(document.elementFromPoint(moved.clientX, moved.clientY))]"""
        )
        # WebKit puts the mouse on the whole pixel it reports, so there the two never part: the
        # first point on the edge is as close as a click comes.
        if over and (BROWSER == "webkit" or not found):
            return held["x"] + quarter / 4, y
    raise AssertionError("no such point")


@pytest.mark.parametrize("kind", KINDS)
def test_a_click_on_a_block_of_a_group_picks_the_whole_group(editor, kind):
    client = user()
    page = editor(
        member(kind, client),
        box("b", "shape", RECT, z=2, x=110, y=20, w=80, **GROUP),
        box("c", "table", TABLE, z=3, x=15, y=110, w=80, group=["h"]),
        box("d", "shape", RECT, z=4, x=110, y=110, w=80, group=["h"]),
        client=client,
    )
    unpick(page)
    # In a table the press is on a cell and the reported point in the cell before, as in the issue.
    cell = '[data-cell="1"]'
    page.mouse.click(*seam(page, at(page, "a").locator(cell) if kind == "table" else at(page, "a")))
    expect_picked(page, "a", "b")
    # Shift adds the whole of a second group.
    page.keyboard.down("Shift")
    page.mouse.click(*seam(page, at(page, "c").locator(cell)))
    page.keyboard.up("Shift")
    expect_picked(page, "a", "b", "c", "d")
