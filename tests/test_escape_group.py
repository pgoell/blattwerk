"""Escape on a part of a group goes back to the group before it selects nothing. Asked #190."""

import pytest
from playwright.sync_api import expect
from ui import LINE, RECT, RULING, TABLE, TEXT, at, box, expect_picked, maths, picture, upload, user

OPEN = ".ProseMirror, .block textarea:not([readonly])"
GROUP = ["text", "shape", "line", "picture", "table", "ruling", "maths", "deep", "mate"]


def everything(client):
    """One block of every type in one group, two of them a group inside it, and a text outside."""
    left, right = {"x": 15, "w": 80, "group": ["g"]}, {"x": 110, "w": 80, "group": ["g"]}
    inner = {"group": ["g", "inner"]}
    return [
        box("text", "text", TEXT, y=20, **left),
        box("shape", "shape", RECT, z=2, y=50, **left),
        box("line", "shape", LINE, z=3, y=80, **left),
        {**picture(upload(client)), "id": "picture", "y": 110, "h": 20, "z": 4, **left},
        box("table", "table", TABLE, z=5, y=20, **right),
        box("ruling", "ruling", RULING, z=6, y=50, **right),
        box("maths", "maths", maths(client), z=7, y=80, **right),
        box("deep", "text", TEXT, z=8, y=140, **{**left, **inner}),
        box("mate", "text", TEXT, z=9, y=140, **{**right, **inner}),
        box("out", "text", TEXT, z=10, y=200),
    ]


def three(editor):
    """Three texts in one group and a fourth outside it."""
    group = {"group": ["g"]}
    return editor(
        *(box(name, "text", TEXT, z=z, **group) for z, name in enumerate("abc", 1)),
        box("d", "text", TEXT, z=4),
    )


def alone(page, name, group):
    """Picks the block out of its group: one click picks the group, a second one the block."""
    at(page, name).click()
    expect_picked(page, *group)
    # The frame around the picked group lies over the block.
    at(page, name).click(force=True)
    expect_picked(page, name)


@pytest.mark.parametrize("name", GROUP[:-1])
def test_escape_on_a_block_picked_out_of_its_group_selects_the_group(editor, name):
    client = user()
    page = editor(*everything(client), client=client)
    alone(page, name, GROUP)
    page.keyboard.press("Escape")
    # The outermost group, as a click picks it.
    expect_picked(page, *GROUP)
    # Escape is no step to undo.
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    page.keyboard.press("Escape")
    expect_picked(page)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    expect(page.locator(".block")).to_have_count(10)


@pytest.mark.parametrize("name", ["text", "table", "ruling"])
def test_escape_while_writing_in_a_block_of_a_group_ends_the_writing_first(editor, name):
    client = user()
    page = editor(*everything(client), client=client)
    alone(page, name, GROUP)
    page.keyboard.press("Enter")
    expect(page.locator(OPEN)).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator(OPEN)).to_have_count(0)
    expect_picked(page, name)
    page.keyboard.press("Escape")
    expect_picked(page, *GROUP)
    page.keyboard.press("Escape")
    expect_picked(page)


def test_escape_on_two_of_three_blocks_of_a_group_selects_the_group(editor):
    page = three(editor)
    alone(page, "a", "abc")
    at(page, "b").click(modifiers=["Shift"])
    expect_picked(page, "a", "b")
    page.keyboard.press("Escape")
    expect_picked(page, *"abc")
    page.keyboard.press("Escape")
    expect_picked(page)


def test_escape_on_a_part_of_a_group_and_a_block_outside_it_selects_nothing(editor):
    page = three(editor)
    alone(page, "a", "abc")
    at(page, "d").click(modifiers=["Shift"])
    expect_picked(page, "a", "d")
    page.keyboard.press("Escape")
    expect_picked(page)
