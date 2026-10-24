"""Spreading blocks across the page.

The helpers live in test_align.py."""

from playwright.sync_api import expect
from test_align import (
    A,
    B,
    expect_box,
    expect_outline,
    expect_switch,
    group,
    pair,
    rects,
    spread,
    switch,
)
from ui import (
    RECT,
    at,
    box,
    expect_picked,
    pick,
    unpick,
)


def test_spreading_needs_three_things(editor):
    page = editor(*pair(), box("c", "shape", RECT, z=3, x=150, y=200, w=20, h=20))
    group(page, "a", "b")
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    expect(spread(page)).to_be_disabled()
    expect(spread(page, "Senkrecht")).to_be_disabled()


def test_spreading_on_the_page_reaches_its_edges(editor):
    page = editor(*rects(), box("c", "shape", RECT, z=3, x=100, y=150, w=40, h=10))
    pick(page, "a", "b")
    switch(page, "Seite").click()
    spread(page).click()
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=160)
    spread(page, "Senkrecht").click()
    expect_box(page, "a", y=0)
    expect_box(page, "b", y=267)
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect_box(page, "a", **A)
    expect_box(page, "b", **B)
    # With three the gaps between them are equal: 45 mm each.
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    spread(page).click()
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=75)
    expect_box(page, "c", x=170)


def test_one_thing_spreads_to_the_middle_of_the_page(editor):
    page = editor(*rects())
    pick(page, "a")
    expect_switch(page, "Seite", enabled=False)
    expect(spread(page)).to_be_enabled()
    spread(page).click()
    expect_box(page, "a", x=90)
    spread(page, "Senkrecht").click()
    expect_box(page, "a", y=138.5)
    # On the selection two things are too few to spread.
    unpick(page)
    pick(page, "a", "b")
    expect_switch(page, "Auswahl")
    expect(spread(page)).to_be_disabled()


def test_spreading_on_the_page_is_one_undo_step(editor):
    page = editor(*pair(), box("c", "shape", RECT, z=3, x=150, y=200, w=20, h=20))
    group(page, "a", "b")
    at(page, "c").click(modifiers=["Shift"])
    expect_picked(page, "a", "b", "c")
    switch(page, "Seite").click()
    spread(page).click()
    # The group is 100 mm wide and spreads as one thing: "b" keeps its 50 mm to "a".
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=50)
    expect_box(page, "c", x=190)
    page.keyboard.press("Control+z")
    expect_box(page, "a", **A)
    expect_box(page, "b", **B)
    expect_box(page, "c", x=150, y=200, w=20, h=20)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_a_turned_block_spreads_on_the_page_by_its_outline(editor):
    # Turned, "a" is 20 mm wide by its outline and starts at 70 mm.
    page = editor(
        box("a", "shape", RECT, z=1, x=60, y=60, w=40, h=20, angle=90),
        box("b", "shape", RECT, z=2, **B),
    )
    pick(page, "a", "b")
    switch(page, "Seite").click()
    spread(page).click()
    expect_outline(page, "a", x=0)
    expect_box(page, "b", x=160)


def test_a_locked_block_stays_when_spreading_on_the_page(editor):
    page = editor(*rects(), box("fest", "shape", RECT, z=3, x=100, y=200, w=20, h=20, locked=True))
    pick(page, "a", "b", "fest")
    switch(page, "Seite").click()
    spread(page).click()
    # The locked block does not count and stays where it is.
    expect_box(page, "a", x=0)
    expect_box(page, "b", x=160)
    expect_box(page, "fest", x=100, y=200, w=20, h=20)
