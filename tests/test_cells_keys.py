"""Keys, the caret and the selection in a table that has a merged cell.

The table helpers live in test_cells.py."""

import re

from playwright.sync_api import expect
from test_cells import (
    CELLS,
    GRID,
    MERGED,
    cell,
    field,
    open_cell,
    picked_cells,
    props,
)
from test_unknown_values import watch
from ui import at, box, user


def test_tab_and_arrows_step_over_a_merged_cell(editor):
    page = editor(box("t", "table", MERGED))
    open_cell(page, "t", 0)
    page.keyboard.press("Tab")
    expect(cell(page, "t", 2).locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    expect(cell(page, "t", 5).locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    expect(cell(page, "t", 6).locator("textarea")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(cell(page, "t", 5).locator("textarea")).to_be_focused()

    cell(page, "t", 0).click()
    page.keyboard.press("ArrowDown")
    expect(cell(page, "t", 6).locator("textarea")).to_be_focused()
    page.keyboard.press("ArrowUp")
    expect(cell(page, "t", 0).locator("textarea")).to_be_focused()

    cell(page, "t", 2).click()
    page.keyboard.press("Home")
    page.keyboard.press("ArrowLeft")
    expect(cell(page, "t", 0).locator("textarea")).to_be_focused()

    cell(page, "t", 0).click()
    page.keyboard.press("End")
    page.keyboard.press("ArrowRight")
    expect(cell(page, "t", 2).locator("textarea")).to_be_focused()

    # A text that wraps into two shown lines keeps the arrow down inside its cell.
    long = {
        **GRID,
        "cols": [0.3, 1, 1],
        "cells": [
            ["Ein langer Text der in der schmalen Zelle umbricht", "b", "c"],
            ["d", "e", "f"],
            ["g", "h", "i"],
        ],
    }
    wrap = editor(box("w", "table", long))
    open_cell(wrap, "w", 0)
    wrap.keyboard.press("Control+Home")
    wrap.keyboard.press("ArrowDown")
    expect(cell(wrap, "w", 0).locator("textarea")).to_be_focused()
    # On its last shown line the arrow goes on to the cell below.
    wrap.keyboard.press("Control+End")
    wrap.keyboard.press("ArrowDown")
    expect(cell(wrap, "w", 3).locator("textarea")).to_be_focused()


def test_a_selection_grows_over_a_merged_cell(editor):
    page = editor(box("t", "table", MERGED))
    open_cell(page, "t", 2)
    cell(page, "t", 0).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(3)
    assert picked_cells(page, "t") == [0, 2, 5]

    cell(page, "t", 6).click()
    cell(page, "t", 5).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(6)
    assert picked_cells(page, "t") == [0, 2, 5, 6, 7, 8]


def test_caret_after_merge_and_picked_after_split(editor):
    page = editor(box("t", "table", GRID))
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(field(page, "t")).to_be_focused()
    expect(field(page, "t")).to_have_value("a\nb\nd\ne")
    page.keyboard.type("z")
    expect(field(page, "t")).to_have_value(re.compile("z"))

    page.get_by_role("button", name="Zellen teilen", exact=True).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    assert picked_cells(page, "t") == [0, 1, 3, 4]


def test_the_selection_drops_and_the_buttons_know_when(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    verbinden = page.get_by_role("button", name="Zellen verbinden", exact=True)
    teilen = page.get_by_role("button", name="Zellen teilen", exact=True)
    open_cell(page, "t", 0)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    expect(teilen).to_have_attribute("aria-disabled", "true")
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(verbinden).not_to_have_attribute("aria-disabled", "true")

    # A plain click drops the selection.
    cell(page, "t", 6).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Tab")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.type("x")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Escape")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    # An arrow drops it too, whether it steps to the next cell or moves the caret in the text.
    for key in ("ArrowDown", "ArrowLeft"):
        open_cell(page, "t", 0)
        cell(page, "t", 4).click(modifiers=["Shift"])
        expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
        page.keyboard.press(key)
        expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)
        page.keyboard.press("Escape")

    # A disabled button changes nothing.
    open_cell(page, "t", 0)
    before = props(page, client)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    # Playwright waits for a button that is off to come on, so the press is forced.
    verbinden.click(force=True)
    expect(field(page, "t")).to_be_focused()
    assert props(page, client) == before
    assert "spans" not in before


def test_teilen_is_off_in_a_plain_cell_and_on_in_a_merged_one(editor):
    page = editor(box("t", "table", GRID))
    open_cell(page, "t", 0)
    expect(page.get_by_role("button", name="Zellen teilen", exact=True)).to_have_attribute(
        "aria-disabled", "true"
    )
    page2 = editor(box("m", "table", MERGED))
    open_cell(page2, "m", 0)
    expect(page2.get_by_role("button", name="Zellen teilen", exact=True)).not_to_have_attribute(
        "aria-disabled", "true"
    )


def test_add_after_a_merged_cell_and_caret_after_delete(editor):
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]").first).to_be_visible()
    stored = props(page, client)
    assert stored["spans"] == [[0, 0, 2, 2]]
    assert stored["cells"][3][0] == "g"

    cell(page, "t", 0).click()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    stored = props(page, client)
    assert len(stored["cols"]) == 4
    assert stored["cells"][0][3] == "c"
    assert stored["spans"] == [[0, 0, 2, 2]]

    other = editor(box("t", "table", MERGED), client=client)
    open_cell(other, "t", 0)
    other.get_by_role("button", name="Zeile löschen", exact=True).click()
    assert props(other, client)["spans"] == [[0, 0, 1, 2]]
    expect(at(other, "t").locator("textarea")).to_have_count(1)
    expect(at(other, "t").locator("textarea")).to_be_focused()
    assert props(other, client)["cells"][0][0] == "a"


def test_undo_drops_the_cells_picked(editor):
    """Undo may take the picked cells away with their row: none stays picked, and nothing throws."""
    client = user()
    page = editor(box("t", "table", GRID, h=40), client=client)
    errors = watch(page)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    cell(page, "t", 11).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(12)
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)
    verbinden = page.get_by_role("button", name="Zellen verbinden", exact=True)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    verbinden.click(force=True)
    assert props(page, client)["cells"] == CELLS
    assert not errors, errors


def test_shift_click_in_the_open_cell_picks_text(editor):
    """As before merged cells: Shift+click in the field picks its text up to the click."""
    grid = {**GRID, "cells": [["hello world here", "b", "c"], *CELLS[1:]]}
    page = editor(box("t", "table", grid, w=150))
    open_cell(page, "t", 0)
    area = field(page, "t")
    area.evaluate("e => e.setSelectionRange(0, 0)")
    size = area.bounding_box()
    page.keyboard.down("Shift")
    page.mouse.click(size["x"] + size["width"] / 2 + 20, size["y"] + size["height"] / 2)
    page.keyboard.up("Shift")
    start, end = area.evaluate("e => [e.selectionStart, e.selectionEnd]")
    assert start == 0 and end > 0
    expect(area).to_be_focused()
