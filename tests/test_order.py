"""One step forward and one step backward in the stack: the buttons under "Ebene"."""

from playwright.sync_api import expect
from ui import RECT, at, box, expect_picked, pick

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
