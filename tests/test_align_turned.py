"""Align and same-size use the outline of a block that is turned.

The helpers live in test_align.py."""

import math

import pytest
from playwright.sync_api import expect
from test_align import (
    STAR,
    A,
    B,
    button,
    expect_box,
    expect_outline,
    group,
    pair,
    row,
    spread,
    switch,
)
from ui import (
    RECT,
    RULING,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    upload,
    user,
)


@pytest.mark.parametrize("kind", ["text", "shape", "image", "symbol", "ruling", "maths"])
def test_a_turned_block_lines_up_by_its_outline(editor, kind):
    client = user()
    props = {"text": TEXT, "shape": RECT, "symbol": STAR, "ruling": RULING}.get(kind)
    if kind == "image":
        props = picture(upload(client))["props"]
    if kind == "maths":
        props = maths(client)
    page = editor(
        box("a", kind, props, x=60, y=60, w=40, h=20, angle=45),
        box("b", "shape", RECT, z=2, x=20, y=120, w=50, h=30),
        client=client,
    )
    pick(page, "a", "b")
    # 40 by 20 mm turned by 45 degrees is as wide as it is high, around its centre at 80 and 70 mm.
    size = 60 * math.cos(math.pi / 4)
    top = 70 - size / 2
    for name, side, a, b in (
        ("Links", "x", 20, 20),
        ("Rechts", "x", 70 - size, 20),
        ("Mitte waagerecht", "x", 45 - size / 2, 20),
        ("Oben", "y", top, top),
        ("Unten", "y", top, top + size - 30),
        ("Mitte senkrecht", "y", top, 55),
    ):
        button(page, name).click()
        expect_outline(page, "a", **{side: a})
        expect_box(page, "b", **{side: b})
    switch(page, "Seite").click()
    button(page, "Rechts").click()
    expect_outline(page, "a", x=210 - size)
    button(page, "Unten").click()
    expect_outline(page, "a", y=297 - size, w=size, h=size)


def test_turned_blocks_spread_by_their_outlines(editor):
    # The last, 60 by 20 mm on its side, is 20 mm wide and starts at 120 mm.
    page = editor(*row(10, 40), box("c", "shape", RECT, z=3, x=100, y=100, w=60, h=20, angle=90))
    pick(page, "a", "b", "c")
    spread(page).click()
    expect_box(page, "b", x=65)
    expect_box(page, "a", x=10)
    expect_box(page, "c", x=100)


def test_same_width_of_a_block_on_its_side(editor):
    page = editor(box("a", "shape", RECT, **A, angle=90), box("b", "shape", RECT, z=2, **B))
    pick(page, "a", "b")
    # The outline is 20 by 30 mm and starts at 25 and 25 mm. It keeps that corner.
    button(page, "Gleiche Breite").click()
    expect_box(page, "a", x=35, y=15, w=30, h=50)
    expect_outline(page, "a", x=25, y=25, w=50, h=30)
    expect_box(page, "b", **B)


def test_same_height_of_a_block_on_its_side(editor):
    high = {**B, "h": 40}
    page = editor(box("a", "shape", RECT, **A, angle=90), box("b", "shape", RECT, z=2, **high))
    pick(page, "a", "b")
    button(page, "Gleiche Höhe").click()
    expect_box(page, "a", x=15, y=35, w=40, h=20)
    expect_outline(page, "a", x=25, y=25, w=20, h=40)
    expect_box(page, "b", **high)


@pytest.mark.parametrize(
    "degrees, name, grows",
    [
        (30, "Gleiche Breite", "w"),
        (60, "Gleiche Breite", "h"),
        (120, "Gleiche Breite", "h"),
        (30, "Gleiche Höhe", "h"),
        (60, "Gleiche Höhe", "w"),
    ],
)
def test_same_size_grows_the_side_that_lies_along_it(editor, degrees, name, grows):
    large = {"x": 70, "y": 90, "w": 60, "h": 60}
    page = editor(
        box("a", "shape", RECT, **A, angle=degrees), box("b", "shape", RECT, z=2, **large)
    )
    c, s = abs(math.cos(math.radians(degrees))), abs(math.sin(math.radians(degrees)))
    was = {"x": 20 + (30 - 30 * c - 20 * s) / 2, "y": 30 + (20 - 30 * s - 20 * c) / 2}
    pick(page, "a", "b")
    button(page, name).click()
    # The outline keeps its corner and is as large as the square on that side.
    expect_outline(page, "a", **was, **{"w" if "Breite" in name else "h": 60})
    kept = "h" if grows == "w" else "w"
    expect_box(page, "a", **{kept: A[kept]})
    expect_box(page, "b", **large)


def test_same_size_keeps_a_turned_pictures_shape(editor):
    client = user()
    page = editor(
        {**picture(upload(client)), "id": "bild", "x": 20, "y": 30, "w": 30, "h": 15, "angle": 90},
        box("a", "shape", RECT, z=2, x=70, y=90, w=40, h=10),
        client=client,
    )
    pick(page, "bild", "a")
    # The picture's outline is 15 mm wide and starts at 27.5 and 22.5 mm.
    button(page, "Gleiche Breite").click()
    expect_box(page, "bild", w=80, h=40)
    expect_outline(page, "bild", x=27.5, y=22.5, w=40, h=80)
    expect_box(page, "a", x=70, y=90, w=40, h=10)


def test_one_undo_takes_back_a_step_of_groups_and_turned_blocks(editor):
    turned = {"x": 150, "y": 200, "w": 30, "h": 20}
    page = editor(*pair(), box("c", "shape", RECT, z=3, **turned, angle=90))

    def back():
        page.keyboard.press("Control+z")
        expect_box(page, "a", **A)
        expect_box(page, "b", **B)
        expect_box(page, "c", **turned)
        expect(page.get_by_label("Rückgängig")).to_be_disabled()

    group(page, "a", "b")
    button(page, "Rechts").click()
    expect_box(page, "b", x=160)
    back()
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    button(page, "Links").click()
    expect_outline(page, "c", x=20)
    back()
    button(page, "Unten").click()
    expect_box(page, "a", y=135)
    expect_box(page, "b", y=195)
    back()
    button(page, "Gleiche Breite").click()
    expect_box(page, "a", w=50)
    expect_outline(page, "c", w=50)
    back()
