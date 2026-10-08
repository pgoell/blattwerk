"""Lining blocks up with each other or with the page, and giving them one size: the Format panel."""

from playwright.sync_api import expect
from ui import LINE, RECT, at, box, expect_picked, pick, picture, unpick, upload, user

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
