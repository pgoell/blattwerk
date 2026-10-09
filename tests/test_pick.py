"""Selecting blocks by click: Shift adds a block to the selection or takes it out, in Chromium."""

from ui import RECT, RULING, TEXT, at, box, expect_picked, pick


def four(editor):
    """A shape, a text, a shape and a Lineatur, each with a place of its own."""
    return editor(
        box("a", "shape", RECT, x=20, y=40, w=40, h=30),
        box("b", "text", TEXT, z=2),
        box("c", "shape", RECT, z=3, x=20, y=200, w=40, h=40),
        box("d", "ruling", RULING, z=4, y=250),
    )


def test_shift_click_adds_each_of_four_blocks(editor):
    page = four(editor)
    # As in PowerPoint: a Shift+click adds the block, whatever its type.
    pick(page, "a", "b", "c", "d")


def test_shift_click_on_a_selected_block_takes_it_out(editor):
    page = four(editor)
    pick(page, "a", "b", "c", "d")
    for i, name in enumerate("dba"):
        # The frame of the selection lies over the block, and the click goes through it.
        at(page, name).click(modifiers=["Shift"], force=True)
        expect_picked(page, *[other for other in "abcd" if other not in "dba"[: i + 1]])
