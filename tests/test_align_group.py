"""Align and same-size when the selection holds a group.

The helpers live in test_align.py."""

from playwright.sync_api import expect
from test_align import (
    A,
    B,
    button,
    expect_box,
    expect_switch,
    group,
    pair,
    rects,
    row,
    spread,
    switch,
)
from ui import (
    RECT,
    at,
    box,
    expect_picked,
)


def test_a_group_lines_up_with_the_page_as_it_is(editor):
    page = editor(*pair())
    group(page, "a", "b")
    for name, side, a, b in (
        ("Links", "x", 0, 50),
        ("Mitte waagerecht", "x", 55, 105),
        ("Rechts", "x", 110, 160),
        ("Oben", "y", 0, 60),
        ("Mitte senkrecht", "y", 103.5, 163.5),
        ("Unten", "y", 207, 267),
    ):
        button(page, name).click()
        expect_box(page, "a", **{side: a})
        expect_box(page, "b", **{side: b})


def test_a_group_with_a_locked_block_stays_as_it_is(editor):
    # "b" is locked: the group would lose its shape if "a" moved alone.
    page = editor(
        *[{**b, "group": ["g"]} for b in rects(locked=True)],
        box("c", "shape", RECT, z=3, x=100, y=200, w=20, h=20),
    )
    group(page, "a", "b")
    expect(button(page, "Rechts")).to_be_disabled()
    # Beside a loose block the group neither moves nor counts: the block has only the page.
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    expect(switch(page, "Auswahl")).to_be_disabled()
    button(page, "Rechts").click()
    expect_box(page, "c", x=190)
    expect_box(page, "a", x=A["x"])
    expect_box(page, "b", x=B["x"])


def test_a_group_spreads_as_one_thing(editor):
    grouped = {"b": {"group": ["g"]}, "c": {"group": ["g"]}}
    page = editor(*row(10, 40, 70, 150, **grouped))
    group(page, "b", "c")
    at(page, "a").click(modifiers=["Shift"])
    at(page, "d").click(modifiers=["Shift"])
    expect_picked(page, *"abcd")
    spread(page).click()
    # The group is 50 mm wide: 35 mm lie free on each side of it.
    expect_box(page, "b", x=65)
    expect_box(page, "c", x=95)
    expect_box(page, "a", x=10)
    expect_box(page, "d", x=150)
    page.keyboard.press("Control+z")
    expect_box(page, "b", x=40)
    expect_box(page, "c", x=70)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_a_group_and_a_block_line_up_as_two_things(editor):
    page = editor(*pair(), box("c", "shape", RECT, z=3, x=150, y=200, w=20, h=20))
    group(page, "a", "b")
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    expect_switch(page, "Auswahl")
    button(page, "Rechts").click()
    expect_box(page, "a", x=70)
    expect_box(page, "b", x=120)
    expect_box(page, "c", x=150)
    button(page, "Oben").click()
    expect_box(page, "c", y=30)
    expect_box(page, "a", y=30)
    expect_box(page, "b", y=90)


def test_a_group_in_a_group_lines_up_as_one_thing(editor):
    inner = [{**b, "group": ["g", "inner"]} for b in rects()]
    page = editor(*inner, box("c", "shape", RECT, z=3, x=150, y=200, w=20, h=20, group=["g"]))
    group(page, "a", "b", "c")
    expect_switch(page, "Seite", enabled=False)
    button(page, "Links").click()
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=50)
    expect_box(page, "c", x=130)


def test_a_part_of_a_group_lines_up_by_itself(editor):
    page = editor(*pair())
    group(page, "b", "a")
    # The frame around the picked group lies over the block.
    at(page, "b").click(force=True)
    expect_picked(page, "b")
    expect_switch(page, "Seite", enabled=False)
    button(page, "Links").click()
    expect_box(page, "b", x=0)
    expect_box(page, "a", **A)


def test_a_group_alone_has_only_the_page(editor):
    page = editor(*pair())
    group(page, "a", "b")
    expect_switch(page, "Seite", enabled=False)
