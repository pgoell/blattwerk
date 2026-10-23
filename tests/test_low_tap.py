"""A tap on the block under a selected one picks it, where the lower handle reaches in (#206)."""

from playwright.sync_api import expect
from ui import RECT, at, box, drag, expect_picked, pick, saved, user

# 5 mm apart, as a new block lands under the one above it.
ABOVE = {"x": 40, "y": 40, "w": 80, "h": 40}
BELOW = {"x": 40, "y": 85, "w": 80, "h": 40}


def covered(page):
    """A point on the lower block, 8 px under its top, in the selected block's lower handle."""
    place = at(page, "b").bounding_box()
    return place["x"] + place["width"] / 2, place["y"] + 8


def on_handle(page, point):
    return page.evaluate(
        "([x, y]) => document.elementFromPoint(x, y).classList.contains('moveable-s')",
        list(point),
    )


def test_a_finger_tap_on_the_block_under_the_selection_picks_it(editor):
    """#206: the lower handle covers the top of the block under the selection.
    A tap there picks that block and sizes nothing."""
    page = editor(box("a", "shape", RECT, **ABOVE), box("b", "shape", RECT, **BELOW), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    point = covered(page)
    assert on_handle(page, point)
    page.touchscreen.tap(*point)
    expect_picked(page, "b")
    expect(page.locator(".ProseMirror, textarea")).to_have_count(0)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_click_on_the_block_under_the_selection_picks_it(editor):
    """The mouse lands on the same handle and still picks the block under it."""
    page = editor(box("a", "shape", RECT, **ABOVE), box("b", "shape", RECT, **BELOW))
    pick(page, "a")
    point = covered(page)
    assert on_handle(page, point)
    page.mouse.click(*point)
    expect_picked(page, "b")
    expect(page.locator(".ProseMirror, textarea")).to_have_count(0)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_drag_of_that_handle_still_sizes_the_block(editor):
    """A drag that starts where the handle covers the block under it still sizes, and keeps the pick."""
    client = user()
    page = editor(box("a", "shape", RECT, **ABOVE), box("b", "shape", RECT, **BELOW), client=client)
    pick(page, "a")
    x, y = covered(page)
    assert on_handle(page, (x, y))
    drag(page, (x, y), (x, y + 30))
    expect_picked(page, "a")
    a, b = saved(page, client)
    assert a["h"] > 40
    assert (b["y"], b["h"]) == (85, 40)
