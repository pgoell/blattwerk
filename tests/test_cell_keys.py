"""Keys on picked table cells: Entf, Backspace, Ctrl+C, Ctrl+X and Ctrl+V act on the rectangle."""

from playwright.sync_api import expect
from ui import BROWSER, at, box, copy_text, doc, pick, user

ROWS = {"cols": [1, 1, 1], "size": 14, "align": "center"}
# A 2 by 3 table with nothing in it.
TABLE = {**ROWS, "cells": [["", "", ""], ["", "", ""]]}
# A 4 by 4 table: a, b over c, d in the top left corner, the rest empty.
SQUARE = {
    **ROWS,
    "cols": [1, 1, 1, 1],
    "cells": [["a", "b", "", ""], ["c", "d", "", ""], ["", "", "", ""], ["", "", "", ""]],
}
# The same with a merged cell in the top left: 2 by 2, holding m.
MERGED = {
    **SQUARE,
    "cells": [["m", "", "", ""], ["", "", "", ""], ["", "", "", ""], ["", "", "", ""]],
    "spans": [[0, 0, 2, 2]],
}


def cell(page, name, n):
    return at(page, name).locator(f'.table > div[data-cell="{n}"]')


def picked(page, name):
    return at(page, name).locator(".table > div.picked")


def cells(page, client, name="t"):
    blocks = doc(page, client)["pages"][0]["blocks"]
    return next(b for b in blocks if b["id"] == name)["props"]["cells"]


def open_at(page, name, n):
    """Opens the cell n of the table, which is picked first."""
    pick(page, name)
    cell(page, name, n).dblclick()
    expect(at(page, name).locator("textarea")).to_be_focused()


def pick_square(page, name):
    """The four cells of the top left 2 by 2 square: the first cell opened, then a Shift+click."""
    open_at(page, name, 0)
    cell(page, name, 5).click(modifiers=["Shift"])
    expect(picked(page, name)).to_have_count(4)


def fill(page):
    """Types 8:00, Deutsch, Rest, 8:45, Mathe into the first 2 by 3 table, a Tab between them."""
    page.keyboard.type("8:00")
    for word in ["Deutsch", "Rest", "8:45", "Mathe"]:
        page.keyboard.press("Tab")
        page.keyboard.type(word)


def test_entf_with_cells_picked_empties_those_cells(editor):
    """C1, #522"""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    open_at(page, "t", 0)
    fill(page)
    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(picked(page, "t")).to_have_count(4)
    page.keyboard.press("Delete")
    assert cells(page, client) == [["", "", "Rest"], ["", "", ""]]


def test_after_entf_the_cells_stay_picked(editor):
    """I3"""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    open_at(page, "t", 0)
    fill(page)
    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Delete")
    expect(picked(page, "t")).to_have_count(4)
    expect(at(page, "t").locator("textarea")).to_have_count(1)


def test_backspace_on_picked_cells_empties_them(editor):
    """I3"""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    open_at(page, "t", 0)
    fill(page)
    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Backspace")
    assert cells(page, client) == [["", "", "Rest"], ["", "", ""]]


def test_ctrl_c_and_ctrl_v_put_picked_cells_into_other_cells(editor):
    """D1, #521"""
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    pick_square(page, "t")
    page.keyboard.press("Control+c")
    cell(page, "t", 10).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    assert cells(page, client) == [
        ["a", "b", "", ""],
        ["c", "d", "", ""],
        ["", "", "a", "b"],
        ["", "", "c", "d"],
    ]


def test_copied_cells_reach_the_clipboard_as_text_with_tabs(editor):
    """D2"""
    if BROWSER == "webkit":
        return  # WebKit on Linux grants the page no clipboard read.
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    pick_square(page, "t")
    page.keyboard.press("Control+c")
    assert page.evaluate("navigator.clipboard.readText()") == "a\tb\nc\td"


def test_entf_and_paste_on_cells_are_one_step_of_undo_each(editor):
    """I1"""
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    pick_square(page, "t")
    page.keyboard.press("Delete")
    assert cells(page, client)[0][:2] == ["", ""]
    page.keyboard.press("Control+z")
    assert cells(page, client) == SQUARE["cells"]
    page.keyboard.press("Control+y")
    assert cells(page, client)[1][:2] == ["", ""]
    # The paste: all four cells come in one step and go in one.
    page.keyboard.press("Control+z")
    cell(page, "t", 0).click()
    cell(page, "t", 5).click(modifiers=["Shift"])
    expect(picked(page, "t")).to_have_count(4)
    page.keyboard.press("Control+c")
    cell(page, "t", 10).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    assert cells(page, client)[2:] == [["", "", "a", "b"], ["", "", "c", "d"]]
    page.keyboard.press("Control+z")
    assert cells(page, client) == SQUARE["cells"]
    page.keyboard.press("Control+y")
    assert cells(page, client)[2:] == [["", "", "a", "b"], ["", "", "c", "d"]]


def test_ctrl_x_with_cells_picked_copies_and_empties_them(editor):
    """I2"""
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    pick_square(page, "t")
    page.keyboard.press("Control+x")
    assert cells(page, client) == [["", "", "", ""]] * 2 + [["", "", "", ""]] * 2
    cell(page, "t", 10).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    assert cells(page, client)[2:] == [["", "", "a", "b"], ["", "", "c", "d"]]


def test_pasted_cells_past_the_edge_are_left_out(editor):
    """I4"""
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    pick_square(page, "t")
    page.keyboard.press("Control+c")
    cell(page, "t", 15).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    grid = cells(page, client)
    assert len(grid) == 4 and all(len(row) == 4 for row in grid)
    assert grid[3][3] == "a"
    # The four texts of the square stay, and the one pasted into the last cell.
    assert sum(text != "" for row in grid for text in row) == 5


def test_a_merged_cell_in_the_pick_copies_as_its_text(editor):
    """I4"""
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    # The pick grows over the merged cell it cuts: the merged cell's text comes along.
    open_at(page, "t", 0)
    cell(page, "t", 2).click(modifiers=["Shift"])
    page.keyboard.press("Control+c")
    cell(page, "t", 10).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    assert cells(page, client)[2][2] == "m"


def test_text_with_tabs_from_another_program_spreads_over_the_cells(editor):
    """I5"""
    client = user()
    page = editor(box("t", "table", SQUARE), client=client)
    copy_text(page, "x\ty\nz\tw")
    cell(page, "t", 10).dblclick()
    expect(at(page, "t").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+v")
    assert cells(page, client)[2:] == [["", "", "x", "y"], ["", "", "z", "w"]]


def test_backspace_on_one_cell_still_deletes_one_letter(editor):
    """Extra: one open cell, no pick, Backspace removes a letter as before."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    open_at(page, "t", 0)
    page.keyboard.type("abc")
    page.keyboard.press("Backspace")
    assert cells(page, client)[0][0] == "ab"


def test_a_table_comes_down_when_entf_empties_the_cell_that_made_it_tall(editor):
    """From the review: Entf on picked cells lets the table go back, as Entf in one cell does."""
    client = user()
    page = editor(box("t", "table", SQUARE, h=40), client=client)

    def height():
        return doc(page, client)["pages"][0]["blocks"][0]["h"]

    before = height()
    open_at(page, "t", 10)
    page.keyboard.type(" ".join(f"wort{n}" for n in range(25)))
    assert height() > before + 10
    cell(page, "t", 11).click(modifiers=["Shift"])
    expect(picked(page, "t")).to_have_count(2)
    page.keyboard.press("Delete")
    assert cells(page, client)[2] == ["", "", "", ""]
    assert abs(height() - before) <= 0.05
