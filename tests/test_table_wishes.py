"""Table wishes: Tab picks the next cell's text (#104)."""

from playwright.sync_api import expect
from ui import at, box, doc, user

TABLE = {"cells": [["H", "Z"], ["3", "7"]], "cols": [1, 1], "size": 14, "align": "center"}


def cell(page, name, n):
    return at(page, name).locator(f'.table > div[data-cell="{n}"]')


def cells(page, client, name="t"):
    blocks = doc(page, client)["pages"][0]["blocks"]
    return next(b for b in blocks if b["id"] == name)["props"]["cells"]


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
