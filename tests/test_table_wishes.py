"""Table wishes: Tab picks the next cell's text (#104), a finger picks cells by handles (#511)."""

import math

import pytest
from playwright.sync_api import expect
from test_zoom import wheel
from ui import BROWSER, at, bar, box, centre, doc, finger, user

TABLE = {"cells": [["H", "Z"], ["3", "7"]], "cols": [1, 1], "size": 14, "align": "center"}
GRID = {
    "cells": [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]],
    "cols": [1, 1, 1],
    "size": 14,
    "align": "center",
}


def cell(page, name, n):
    return at(page, name).locator(f'.table > div[data-cell="{n}"]')


def cells(page, client, name="t"):
    blocks = doc(page, client)["pages"][0]["blocks"]
    return next(b for b in blocks if b["id"] == name)["props"]["cells"]


def test_a_finger_drags_the_bottom_right_handle_over_cells_and_they_are_picked(editor):
    """#511: a finger on the open cell's bottom right handle picks the cells it is dragged over."""
    client = user()
    page = editor(box("t", "table", GRID), client=client, touch=True)
    tap_open(page, 0)
    handle = page.locator(".cell-handle-se")
    expect(handle).to_be_visible()
    start = centre(handle)
    target = centre(cell(page, "t", 4))
    still = at(page, "t").bounding_box()
    where = "() => [scrollX, scrollY, document.querySelector('main')?.scrollTop]"
    scrolled = page.evaluate(where)
    with finger(page, start) as touch:
        touch("touchMove", ((start[0] + target[0]) / 2, (start[1] + target[1]) / 2))
        touch("touchMove", target)
        # The table neither moves nor does the page scroll while the handle is dragged.
        assert at(page, "t").bounding_box() == still
    assert page.evaluate(where) == scrolled
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    # On the iPad held upright the format panel is a drawer: its button keeps the cells picked.
    # Chromium's touch emulation loses a tap after such a drag now and then, WebKit's does not
    # (#723): Chromium clicks.
    press = (
        (lambda button: button.tap()) if BROWSER == "webkit" else (lambda button: button.click())
    )
    press(bar(page, "right"))
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")
    press(page.get_by_role("button", name="Zellen verbinden", exact=True))
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")


def tap_open(page, n):
    """A finger's two taps on a cell: the first picks the table, the second opens the cell."""
    for _ in range(2):
        with finger(page, centre(cell(page, "t", n))):
            pass


def test_a_finger_drags_the_top_left_handle_and_the_range_grows_the_other_way(editor):
    """#511: the top left handle grows the range too, from the bottom right corner."""
    page = editor(box("t", "table", GRID), touch=True)
    tap_open(page, 4)
    handle = page.locator(".cell-handle-nw")
    expect(handle).to_be_visible()
    with finger(page, centre(handle)) as touch:
        touch("touchMove", centre(cell(page, "t", 0)))
    picked = at(page, "t").locator(".table > div.picked")
    expect(picked).to_have_count(4)
    for n in (0, 1, 3, 4):
        expect(cell(page, "t", n)).to_have_class("picked")


def test_a_handle_drag_back_shrinks_the_range(editor):
    """#511: a handle dragged back over the range picks fewer cells."""
    page = editor(box("t", "table", GRID), touch=True)
    tap_open(page, 0)
    with finger(page, centre(page.locator(".cell-handle-se"))) as touch:
        touch("touchMove", centre(cell(page, "t", 8)))
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(9)
    with finger(page, centre(page.locator(".cell-handle-se"))) as touch:
        touch("touchMove", centre(cell(page, "t", 1)))
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(2)


def test_a_mouse_shows_no_handles(editor):
    """#511: with a mouse the open cell has no handles; drag and Shift+click pick cells."""
    page = editor(box("t", "table", GRID))
    cell(page, "t", 0).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    expect(page.locator(".cell-handle")).to_have_count(0)


def test_a_tap_in_one_cell_ends_the_range(editor):
    """#511: after a handle drag, a tap in one cell leaves that cell open alone."""
    page = editor(box("t", "table", GRID), touch=True)
    tap_open(page, 0)
    with finger(page, centre(page.locator(".cell-handle-se"))) as touch:
        touch("touchMove", centre(cell(page, "t", 4)))
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    with finger(page, centre(cell(page, "t", 8))):
        pass
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)
    expect(cell(page, "t", 8).locator("textarea")).to_have_count(1)
    expect_corners(page, 8, 8)


def expect_corners(page, first, last, turned=False):
    """The handles stand at the top left of cell `first` and the bottom right of cell `last`.
    A table turned by 90 degrees has those corners at the top right and the bottom left."""
    page.wait_for_function("() => document.querySelectorAll('.cell-handle').length === 2")
    a, b = cell(page, "t", first).bounding_box(), cell(page, "t", last).bounding_box()
    nw = (a["x"] + a["width"], a["y"]) if turned else (a["x"], a["y"])
    se = (b["x"], b["y"] + b["height"]) if turned else (b["x"] + b["width"], b["y"] + b["height"])
    for corner, want in (("nw", nw), ("se", se)):
        got = centre(page.locator(f".cell-handle-{corner}"))
        assert math.dist(got, want) <= 3, (corner, got, want)


def test_the_handles_stand_at_the_cells_corners(editor):
    """Review: the bottom right handle stood beside the cell's corner."""
    page = editor(box("t", "table", GRID), touch=True)
    tap_open(page, 4)
    expect_corners(page, 4, 4)


def test_the_handles_of_a_turned_table_stand_at_its_cells_corners(editor):
    """Review: on a turned table the handles stood far from the cells."""
    page = editor(box("t", "table", GRID, angle=90), touch=True)
    tap_open(page, 4)
    expect_corners(page, 4, 4, turned=True)


@pytest.mark.skipif(
    BROWSER == "webkit",
    reason="the iPad's WebKit has no wheel, and a key in the field stays the field's",
)
def test_the_handles_follow_a_zoom(editor):
    """Review: after a zoom the handles kept their old place."""
    page = editor(box("t", "table", GRID), touch=True)
    tap_open(page, 4)
    expect_corners(page, 4, 4)
    wide = "() => document.querySelector('.sheet.on').getBoundingClientRect().width"
    before = page.evaluate(wide)
    wheel(page, -100)
    page.wait_for_function(f"(w) => ({wide})() > w + 1", arg=before)
    expect(cell(page, "t", 4).locator("textarea")).to_have_count(1)
    expect_corners(page, 4, 4)


def test_tab_from_an_open_cell_picks_the_next_cells_text(editor):
    """#104: Tab from an open cell picks all the next cell's text; typing replaces it."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    cell(page, "t", 0).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    page.keyboard.type("X")
    assert cells(page, client) == [["H", "X"], ["3", "7"]]


def test_shift_tab_picks_the_cell_before_its_text(editor):
    """#104: Shift+Tab into the cell before picks its text too."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    cell(page, "t", 1).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    page.keyboard.type("Y")
    assert cells(page, client) == [["Y", "Z"], ["3", "7"]]


def test_ctrl_z_after_typing_over_a_picked_text_brings_the_old_text_back(editor):
    """#104: Ctrl+Z after typing over the picked text brings the old text back in one step."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    cell(page, "t", 0).dblclick()
    page.keyboard.press("Tab")
    page.keyboard.type("X")
    assert cells(page, client) == [["H", "X"], ["3", "7"]]
    page.keyboard.press("Control+z")
    assert cells(page, client) == [["H", "Z"], ["3", "7"]]


def test_tab_into_an_empty_cell_puts_the_caret_there(editor):
    """#104: Tab into an empty cell: caret there, typing fills it."""
    client = user()
    page = editor(box("t", "table", {**TABLE, "cells": [["H", ""], ["3", "7"]]}), client=client)
    cell(page, "t", 0).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    page.keyboard.type("Q")
    assert cells(page, client) == [["H", "Q"], ["3", "7"]]


def test_tab_past_the_last_cell_adds_a_row_with_the_caret_in_it(editor):
    """#104: Tab past the last cell still adds a row with the caret in it."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    cell(page, "t", 3).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    page.keyboard.type("N")
    assert cells(page, client) == [["H", "Z"], ["3", "7"], ["N", ""]]
