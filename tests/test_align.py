"""Lining blocks up with each other or with the page, and giving them one size: the Format panel."""

import math

import pytest
from playwright.sync_api import expect
from ui import (
    LINE,
    RECT,
    RULING,
    TEXT,
    at,
    box,
    drawer,
    expect_picked,
    maths,
    pick,
    picture,
    unpick,
    upload,
    user,
)

STAR = {"code": "2B50"}
SIDES = {"x": "left", "y": "top", "w": "width", "h": "height"}
# On A4, upright, 210 by 297 mm: "a" is 30 by 20 mm and "b" 50 by 30 mm.
A = {"x": 20, "y": 30, "w": 30, "h": 20}
B = {"x": 70, "y": 90, "w": 50, "h": 30}


def rects(**more):
    return box("a", "shape", RECT, **A), box("b", "shape", RECT, z=2, **B, **more)


def button(page, name):
    """A button of the panel that acts at once. A shape's own "Links" for its text is none."""
    return page.locator(".panel .acts").get_by_role("button", name=name, exact=True)


def switch(page, name):
    return page.locator(".panel .seg").get_by_role("button", name=name, exact=True)


def expect_box(page, name, **mm):
    """Waits until the block lies at these mm of the page, or is this large."""
    # A block's own style holds its box in px at 96 to the inch. What the browser lays out is
    # rounded to its own steps, so the style is read.
    page.wait_for_function(
        """([name, box]) => {
            const style = document.querySelector(`.block[data-id="${name}"]`).style;
            const off = ([side, mm]) => Math.abs(parseFloat(style[side]) * 25.4 / 96 - mm);
            return Object.entries(box).every((want) => off(want) < 0.01);
        }""",
        arg=[name, {SIDES[side]: value for side, value in mm.items()}],
        timeout=2000,
    )


def expect_switch(page, name, enabled=True):
    """Waits until the switch under Ausrichten shows this one of its two sides."""
    for side in ("Auswahl", "Seite"):
        expect(switch(page, side)).to_have_attribute("aria-pressed", str(side == name).lower())
        expect(switch(page, side)).to_be_enabled(enabled=enabled)


def test_the_switch_starts_on_the_selection_and_stays(editor):
    page = editor(*(box(name, "shape", RECT, z=i + 1) for i, name in enumerate("abcd")))
    pick(page, "a", "b")
    expect_switch(page, "Auswahl")
    switch(page, "Seite").click()
    expect_switch(page, "Seite")
    pick(page, "c", "d")
    expect_switch(page, "Seite")
    switch(page, "Auswahl").click()
    expect_switch(page, "Auswahl")
    pick(page, "a", "b")
    expect_switch(page, "Auswahl")


def test_several_blocks_line_up_with_the_page(editor):
    page = editor(*rects())
    pick(page, "a", "b")
    switch(page, "Seite").click()
    for name, side, a, b in (
        ("Links", "x", 0, 0),
        ("Mitte waagerecht", "x", 90, 80),
        ("Rechts", "x", 180, 160),
        ("Oben", "y", 0, 0),
        ("Mitte senkrecht", "y", 138.5, 133.5),
        ("Unten", "y", 277, 267),
    ):
        button(page, name).click()
        expect_box(page, "a", **{side: a})
        expect_box(page, "b", **{side: b})


def test_several_blocks_line_up_with_each_other(editor):
    page = editor(*rects())
    pick(page, "a", "b")
    # Each step starts from where the one before left the two.
    for name, side, a, b in (
        ("Links", "x", 20, 20),
        ("Mitte waagerecht", "x", 30, 20),
        ("Rechts", "x", 40, 20),
        ("Oben", "y", 30, 30),
        ("Mitte senkrecht", "y", 35, 30),
        ("Unten", "y", 40, 30),
    ):
        button(page, name).click()
        expect_box(page, "a", **{side: a})
        expect_box(page, "b", **{side: b})


def test_same_width(editor):
    page = editor(*rects(), box("c", "shape", RECT, z=3, x=100, y=150, w=40, h=10))
    pick(page, "a", "b", "c")
    button(page, "Gleiche Breite").click()
    expect_box(page, "a", **{**A, "w": 50})
    expect_box(page, "b", **B)
    expect_box(page, "c", x=100, y=150, w=50, h=10)


def test_same_height(editor):
    page = editor(*rects(), box("c", "shape", RECT, z=3, x=100, y=150, w=40, h=10))
    pick(page, "a", "b", "c")
    button(page, "Gleiche Höhe").click()
    expect_box(page, "a", **{**A, "h": 30})
    expect_box(page, "b", **B)
    expect_box(page, "c", x=100, y=150, w=40, h=30)


def test_a_finger_lines_up_with_the_page(editor):
    page = editor(*rects(), touch=True)
    # With "Mehrere" on, each tap adds a block.
    page.get_by_label("Mehrere", exact=True).tap()
    at(page, "a").tap()
    at(page, "b").tap()
    expect_picked(page, "a", "b")
    drawer(page, "right")
    switch(page, "Seite").tap()
    expect_switch(page, "Seite")
    button(page, "Links").tap()
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=0)
    button(page, "Gleiche Breite").tap()
    expect_box(page, "a", w=50)
    button(page, "Gleiche Höhe").tap()
    expect_box(page, "a", x=0, y=30, w=50, h=30)
    expect_box(page, "b", x=0, y=90, w=50, h=30)


def test_one_block_lines_up_with_the_page(editor):
    page = editor(*rects())
    pick(page, "a", "b")
    expect_switch(page, "Auswahl")
    # The frame around the two lies over them, so the selection starts over.
    unpick(page)
    pick(page, "a")
    expect_switch(page, "Seite", enabled=False)
    button(page, "Rechts").click()
    expect_box(page, "a", x=180)
    button(page, "Unten").click()
    expect_box(page, "a", x=180, y=277)
    expect_box(page, "b", **B)
    # The switch is where it was set once two are picked again.
    unpick(page)
    pick(page, "a", "b")
    expect_switch(page, "Auswahl")


def test_undo_of_page_align_and_same_size(editor):
    page = editor(*rects())
    pick(page, "a", "b")
    switch(page, "Seite").click()
    button(page, "Links").click()
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=0)
    page.keyboard.press("Control+z")
    expect_box(page, "a", **A)
    expect_box(page, "b", **B)
    # The switch is no change to the sheet.
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    for name, side in (("Gleiche Breite", "w"), ("Gleiche Höhe", "h")):
        button(page, name).click()
        expect_box(page, "a", **{**A, side: B[side]})
        page.keyboard.press("Control+z")
        expect_box(page, "a", **A)
        expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_a_locked_block_stays(editor):
    # The locked one is the largest and lies furthest left and down.
    held = {"x": 10, "y": 200, "w": 120, "h": 60}
    page = editor(*rects(), box("fest", "shape", RECT, z=3, **held, locked=True))
    pick(page, "a", "b", "fest")
    button(page, "Links").click()
    expect_box(page, "a", x=20)
    expect_box(page, "b", x=20)
    button(page, "Unten").click()
    expect_box(page, "a", y=100)
    switch(page, "Seite").click()
    button(page, "Rechts").click()
    expect_box(page, "a", x=180)
    expect_box(page, "b", x=160)
    button(page, "Gleiche Breite").click()
    expect_box(page, "a", w=50)
    button(page, "Gleiche Höhe").click()
    expect_box(page, "a", h=30)
    expect_box(page, "fest", **held)
    # One block that can take a size is too few.
    unpick(page)
    pick(page, "b", "fest")
    expect(button(page, "Gleiche Breite")).to_be_disabled()
    expect(button(page, "Gleiche Höhe")).to_be_disabled()


def test_same_size_keeps_a_pictures_shape(editor):
    client = user()
    line = {"x": 20, "y": 230, "w": 100, "h": 50}
    page = editor(
        box("stern", "symbol", STAR, x=20, y=30, w=20, h=20),
        box("a", "shape", RECT, z=2, x=70, y=30, w=40, h=10),
        {**picture(upload(client)), "id": "bild", "z": 3, "x": 20, "y": 120, "w": 30, "h": 15},
        box("strich", "shape", LINE, z=4, **line),
        client=client,
    )
    pick(page, "stern", "a", "bild", "strich")
    # The line is the widest and the highest, and does not count.
    button(page, "Gleiche Breite").click()
    expect_box(page, "stern", x=20, y=30, w=40, h=40)
    expect_box(page, "bild", x=20, y=120, w=40, h=20)
    expect_box(page, "a", w=40, h=10)
    button(page, "Gleiche Höhe").click()
    expect_box(page, "a", w=40, h=40)
    expect_box(page, "bild", x=20, y=120, w=80, h=40)
    expect_box(page, "stern", x=20, y=30, w=40, h=40)
    expect_box(page, "strich", **line)
    for names in (["stern"], ["stern", "strich"]):
        unpick(page)
        pick(page, *names)
        expect(button(page, "Gleiche Breite")).to_be_disabled()
        expect(button(page, "Gleiche Höhe")).to_be_disabled()


def expect_outline(page, name, **mm):
    """Waits until the level box around the block, turned as it is, lies at these mm."""
    page.wait_for_function(
        """([name, want]) => {
            const style = document.querySelector(`.block[data-id="${name}"]`).style;
            const mm = (side) => parseFloat(style[side]) * 25.4 / 96;
            const [x, y, w, h] = ["left", "top", "width", "height"].map(mm);
            const degrees = /rotate\\((-?[\\d.]+)deg\\)/.exec(style.transform)?.[1] ?? 0;
            const turn = degrees * Math.PI / 180;
            const [c, s] = [Math.abs(Math.cos(turn)), Math.abs(Math.sin(turn))];
            const box = { w: w * c + h * s, h: w * s + h * c };
            box.x = x + (w - box.w) / 2;
            box.y = y + (h - box.h) / 2;
            // A block lies on a hundredth of a mm, so its outline can be that far off.
            return Object.entries(want).every(([side, at]) => Math.abs(box[side] - at) < 0.02);
        }""",
        arg=[name, mm],
        timeout=2000,
    )


def group(page, name, *names):
    """Picks the whole group by a click on one of its blocks."""
    at(page, name).click()
    expect_picked(page, name, *names)


def spread(page, name="Waagerecht"):
    return button(page, name)


def row(*starts, **more):
    """Blocks 20 mm wide, each starting at its mm from the left, named from "a" on."""
    return [
        box(name, "shape", RECT, z=i + 1, x=x, y=30, w=20, h=20, **more.get(name, {}))
        for i, (name, x) in enumerate(zip("abcd", starts, strict=False))
    ]


def pair():
    """ "a" and "b" as one group: together 100 mm wide and 90 mm high."""
    return [{**b, "group": ["g"]} for b in rects()]


def test_an_align_that_moves_nothing_leaves_undo_as_it_was(editor):
    # Both lie on the left edge, "a" in the middle of the page's height too.
    page = editor(
        box("a", "shape", RECT, x=0, y=138.5, w=30, h=20),
        box("b", "shape", RECT, z=2, x=0, y=30, w=50, h=30),
    )
    undo = page.get_by_label("Rückgängig")
    pick(page, "a")
    button(page, "Links").click()
    button(page, "Mitte senkrecht").click()
    expect(undo).to_be_disabled()
    pick(page, "a", "b")
    button(page, "Links").click()
    expect(undo).to_be_disabled()
    switch(page, "Seite").click()
    button(page, "Links").click()
    expect(undo).to_be_disabled()
    expect_box(page, "a", x=0, y=138.5)


def test_a_same_size_that_changes_nothing_leaves_undo_as_it_was(editor):
    page = editor(
        box("a", "shape", RECT, x=20, y=30, w=50, h=30),
        box("b", "shape", RECT, z=2, x=20, y=90, w=50, h=30),
    )
    pick(page, "a", "b")
    button(page, "Gleiche Breite").click()
    button(page, "Gleiche Höhe").click()
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_a_press_that_moves_nothing_adds_no_step_and_keeps_redo(editor):
    # The three lie 50 mm apart already.
    page = editor(*row(10, 80, 150))
    undo, redo = page.get_by_label("Rückgängig"), page.get_by_label("Wiederholen")
    pick(page, "a", "b", "c")
    spread(page).click()
    expect(undo).to_be_disabled()
    switch(page, "Seite").click()
    button(page, "Unten").click()
    expect_box(page, "a", y=277)
    page.keyboard.press("Control+z")
    expect_box(page, "a", y=30)
    expect(redo).to_be_enabled()
    switch(page, "Auswahl").click()
    button(page, "Oben").click()
    button(page, "Gleiche Breite").click()
    spread(page).click()
    expect(redo).to_be_enabled()
    expect(undo).to_be_disabled()


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


def test_spreading_needs_three_things(editor):
    page = editor(*pair(), box("c", "shape", RECT, z=3, x=150, y=200, w=20, h=20))
    group(page, "a", "b")
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    expect(spread(page)).to_be_disabled()
    expect(spread(page, "Senkrecht")).to_be_disabled()


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
