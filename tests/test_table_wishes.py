"""Table wishes: Tab picks the next cell's text (#104)."""

from playwright.sync_api import expect
from ui import at, box, centre, doc, drawer, finger, user

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
    drawer(page, "right")
    page.get_by_role("button", name="Zellen verbinden", exact=True).tap()
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
    expect(page.locator(".cell-handle")).to_have_count(2)


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
