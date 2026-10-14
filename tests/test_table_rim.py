"""Issue #584: a row added below a table's last row keeps a box round some of its cells where it is.

The lines are read as in test_table_edges.py: `thick_between` gives the rows or columns in which a
line of the given width stands on a line of the table.
"""

from playwright.sync_api import expect
from test_table_edges import FRAME, INK, THREE, thick_between
from ui import at, box, pick, saved, user


def add_row_below(page, cell):
    """Open the cell, give it a 1,25 mm solid box and add a row below it."""
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(cell).dblclick()
    slider = page.get_by_label("Linienstärke")
    slider.focus()
    for _ in range(4):
        page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="1,25 mm")).to_be_visible()
    page.get_by_role("group", name="Rahmen").get_by_role("button", name="Außen", exact=True).click()


def test_issue_584_a_box_round_a_cell_of_the_last_row_stays_round_it(editor):
    """Issue #584: a box of 1.25 mm round the first cell of row 3 of a 3 by 3 table stays round that
    cell when a row is added below. The line under row 3 stays thick under col 1, and the new row
    has plain lines: its left side and its bottom are not thick."""
    client = user()
    page = editor(box("t", "table", {**THREE, "line": INK}), client=client)
    add_row_below(page, 6)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 3, ("h", 3), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("h", 4), 1.25) == set()
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {2}
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {2}


def test_issue_584_a_frame_round_the_table_stays_closed(editor):
    """Issue #562 with #584: a frame of 1.25 mm round the whole table stays closed when a row is
    added below its last row. The new bottom is the frame's, and the line between the rows is not
    thick."""
    client = user()
    frame = [FRAME] * 3
    edges = {"h": [frame, [None] * 3, [None] * 3, frame], "v": [[FRAME, None, None, FRAME]] * 3}
    page = editor(box("t", "table", {**THREE, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(6).dblclick()
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 3, ("h", 4), 1.25) == {0, 1, 2}
    assert thick_between(at(page, "t"), 3, ("h", 3), 1.25) == set()
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {0, 1, 2, 3}
    assert thick_between(at(page, "t"), 3, ("v", 3), 1.25) == {0, 1, 2, 3}


DOTTED = {"style": "dotted", "width": 1.25}
SOLID = {"style": "solid", "width": 1.25}
# A 3 by 4 table, as the issue's steps.
FOUR = {
    "cells": [["a", "b", "c", "d"], ["e", "f", "g", "h"], ["i", "j", "k", "l"]],
    "cols": [1, 1, 1, 1],
    "size": 14,
    "align": "center",
}


def test_issue_591_column_boxes_stay_closed_beside_a_solid_box_round_a_cell(editor):
    """Issue #591: a dotted box round column A and one round column C stay closed when a row is
    added below the last row, with a solid box round B3. The solid box keeps its bottom under row 3,
    the columns' bottoms move to the new rim, and the new row takes their pen."""
    client = user()
    edges = {
        "h": [
            [DOTTED, None, DOTTED, None],
            [None] * 4,
            [None, SOLID, None, None],
            [DOTTED, SOLID, DOTTED, None],
        ],
        "v": [[DOTTED, DOTTED, DOTTED, DOTTED, None]] * 2 + [[DOTTED, SOLID, SOLID, DOTTED, None]],
    }
    page = editor(box("t", "table", {**FOUR, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(9).dblclick()
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(16)
    saved_edges = next(b for b in saved(page, client) if b["id"] == "t")["props"]["edges"]
    assert saved_edges["h"][3] == [None, SOLID, None, None]
    assert saved_edges["h"][4] == [DOTTED, None, DOTTED, None]
    assert saved_edges["v"][3] == [DOTTED, DOTTED, DOTTED, DOTTED, None]


def test_issue_591_column_box_beside_a_box_round_a_cell_in_the_same_pen(editor):
    """Issue #591: a dotted box round column A and a dotted box round B3 of the last row: the column
    box stays closed, its bottom moves to the new rim, and the box round B3 stays under row 3."""
    client = user()
    edges = {
        "h": [
            [DOTTED, None, None, None],
            [None] * 4,
            [None, DOTTED, None, None],
            [DOTTED, DOTTED, None, None],
        ],
        "v": [[DOTTED, DOTTED, None, None, None]] * 2 + [[DOTTED, DOTTED, DOTTED, None, None]],
    }
    page = editor(box("t", "table", {**FOUR, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(9).dblclick()
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(16)
    saved_edges = next(b for b in saved(page, client) if b["id"] == "t")["props"]["edges"]
    assert saved_edges["h"][3] == [None, DOTTED, None, None]
    assert saved_edges["h"][4] == [DOTTED, None, None, None]
    assert saved_edges["v"][3] == [DOTTED, DOTTED, None, None, None]


def test_issue_584_undo_brings_the_box_back(editor):
    """Issue #584: after Zeile darunter, Ctrl+Z takes the new row away and the box stays round the
    cell of row 3, as it was before."""
    client = user()
    page = editor(box("t", "table", {**THREE, "line": INK}), client=client)
    add_row_below(page, 6)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    assert thick_between(at(page, "t"), 3, ("h", 3), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("h", 2), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {2}
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {2}
