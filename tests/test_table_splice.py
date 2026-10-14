"""Issues #589, #594 and #595: a row or column added beside a table's rim keeps its lines.

Each test seeds a table's edges and reads back the lines drawn on the page. A line is a pen
`(style, mm)`; `drawn` gives the pen of every line position `("h", r, c)` (the line above cell
(r, c), r = rows for the bottom) and `("v", r, c)` (the line left of cell (r, c)), and `paint`
builds the same grid from what should be drawn.
"""

import pytest
from playwright.sync_api import expect
from test_table_edges import INK, THREE
from ui import at, box, pick, user

PLAIN = ("solid", 0.25)
DASHED = ("dashed", 0.25)
SOLID = ("solid", 1.25)
DOTTED = ("dotted", 1.25)
WIDTHS = (0.25, 1.25)
PER_MM = "t => parseFloat(getComputedStyle(t).getPropertyValue('--edge')) * 4"
# The lines of each cell's svg, as test_table_edges reads them.
LINES = """(svgs) => svgs.flatMap((s) => [...s.querySelectorAll('line')].map((l) => ({
    edge: +s.dataset.edge, side: l.dataset.side, style: l.dataset.style,
    w: +l.getAttribute('stroke-width') })))"""
FOUR = {
    "cells": [["a", "b", "c", "d"], ["e", "f", "g", "h"], ["i", "j", "k", "l"]],
    "cols": [1, 1, 1, 1],
    "size": 14,
    "align": "center",
}
ONE_ROW = {"cells": [["a", "b", "c"]], "cols": [1, 1, 1], "size": 14, "align": "center"}


def dashed_look():
    """A 3 by 4 grid, every line dashed 0.25 mm, each an explicit edge as Rahmen gives it."""
    return {
        **FOUR,
        "line": INK,
        "lineStyle": "dashed",
        "lineWidth": 0.25,
        "edges": edges(3, 4, paint(3, 4, DASHED)),
    }


def pen_of(pen):
    return None if pen is None else {"style": pen[0], "width": pen[1]}


def edges(rows, cols, pens):
    """The props' edges from {(axis, r, c): pen}; a position not in pens is null."""
    return {
        "h": [[pen_of(pens.get(("h", r, c))) for c in range(cols)] for r in range(rows + 1)],
        "v": [[pen_of(pens.get(("v", r, c))) for c in range(cols + 1)] for r in range(rows)],
    }


def paint(rows, cols, base, *edits):
    """The pen of every line position of a rows by cols table: base, then the edits in order."""
    grid = {("h", r, c): base for r in range(rows + 1) for c in range(cols)}
    grid |= {("v", r, c): base for r in range(rows) for c in range(cols + 1)}
    for edit in edits:
        grid |= edit
    return grid


def rim(rows, cols, pen):
    """The lines on the outside of a rows by cols table."""
    top = {("h", 0, c): pen for c in range(cols)}
    bottom = {("h", rows, c): pen for c in range(cols)}
    left = {("v", r, 0): pen for r in range(rows)}
    right = {("v", r, cols): pen for r in range(rows)}
    return top | bottom | left | right


def round_cell(r, c, pen):
    """The four lines round cell (r, c)."""
    return {("h", r, c): pen, ("h", r + 1, c): pen, ("v", r, c): pen, ("v", r, c + 1): pen}


def drawn(page, cols):
    """The pen of every line position drawn on the table, as a set of pens per position."""
    block = at(page, "t")
    per_mm = block.locator(".table").first.evaluate(PER_MM)
    svgs = block.locator('.table svg.edge[data-edge]:not([data-edge="bank"])')
    grid = {}
    for one in svgs.evaluate_all(LINES):
        r, c = divmod(one["edge"], cols)
        where = {
            "top": ("h", r, c),
            "bottom": ("h", r + 1, c),
            "left": ("v", r, c),
            "right": ("v", r, c + 1),
        }[one["side"]]
        mm = min(WIDTHS, key=lambda w: abs(w - one["w"] / per_mm))
        grid.setdefault(where, set()).add((one["style"], mm))
    return grid


def expect_grid(page, rows, cols, want):
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(rows * cols)
    assert drawn(page, cols) == {key: {pen} for key, pen in want.items()}


def splice(page, cell, button):
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(cell).dblclick()
    page.get_by_role("button", name=button, exact=True).click()


def test_issue_595_a_frame_stays_closed_beside_a_dotted_box_round_a_cell_of_the_last_row(editor):
    """Issue #595: a 1.25 mm frame round a 3 by 4 table stays closed when a row is added below.
    The box of 1.25 mm dotted round B3 stays round B3, under row 3, and the new row is plain."""
    client = user()
    pens = {**rim(3, 4, SOLID), **round_cell(2, 1, DOTTED)}
    look = {**FOUR, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(box("t", "table", {**look, "edges": edges(3, 4, pens)}), client=client)
    splice(page, 9, "Zeile darunter")
    want = paint(4, 4, PLAIN, rim(4, 4, SOLID), round_cell(2, 1, DOTTED))
    expect_grid(page, 4, 4, want)


def test_issue_594_a_dashed_grid_stays_dashed_under_a_new_row(editor):
    """Issue #594: every line of a 3 by 4 grid dashed 0.25 mm stays dashed when a row is added
    below its last row, the line between the old last row and the new row included."""
    client = user()
    look = dashed_look()
    page = editor(box("t", "table", look), client=client)
    splice(page, 8, "Zeile darunter")
    expect_grid(page, 4, 4, paint(4, 4, DASHED))


def test_issue_594_a_solid_box_under_a_dashed_grid_leaves_the_new_rim_dashed(editor):
    """Issue #594: with a solid 1.25 mm box round B3 in a dashed grid, the new rim under B is
    dashed, and the box stays round B3."""
    client = user()
    look = dashed_look()
    pens = {**paint(3, 4, DASHED), **round_cell(2, 1, SOLID)}
    page = editor(box("t", "table", {**look, "edges": edges(3, 4, pens)}), client=client)
    splice(page, 9, "Zeile darunter")
    want = paint(4, 4, DASHED, round_cell(2, 1, SOLID))
    expect_grid(page, 4, 4, want)


def test_issue_589_a_box_round_a_cell_stays_round_it_when_a_row_is_added_above(editor):
    """Issue #589: a solid 1.25 mm box round the first cell of a 3 by 3 table stays round that cell,
    now in row 2, when a row is added above. The new top row is plain."""
    client = user()
    look = {**THREE, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(
        box("t", "table", {**look, "edges": edges(3, 3, round_cell(0, 0, SOLID))}), client=client
    )
    splice(page, 0, "Zeile darüber")
    expect_grid(page, 4, 3, paint(4, 3, PLAIN, round_cell(1, 0, SOLID)))


def test_issue_589_a_box_round_a_cell_of_the_last_column_stays_when_a_column_is_added_right(editor):
    """Issue #589: a solid 1.25 mm box round the last column's top cell stays round it when a column
    is added to the right. The new column is plain."""
    client = user()
    look = {**THREE, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(
        box("t", "table", {**look, "edges": edges(3, 3, round_cell(0, 2, SOLID))}), client=client
    )
    splice(page, 2, "Spalte rechts")
    expect_grid(page, 3, 4, paint(3, 4, PLAIN, round_cell(0, 2, SOLID)))


def test_issue_589_a_box_round_a_cell_of_the_first_column_stays_when_a_column_is_added_left(editor):
    """Issue #589: a solid 1.25 mm box round the first column's top cell stays round that cell,
    now in column 2, when a column is added to the left. The new column is plain."""
    client = user()
    look = {**THREE, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(
        box("t", "table", {**look, "edges": edges(3, 3, round_cell(0, 0, SOLID))}), client=client
    )
    splice(page, 0, "Spalte links")
    expect_grid(page, 3, 4, paint(3, 4, PLAIN, round_cell(0, 1, SOLID)))


# Per side: the button, the cell to press, the box's cell before and after the splice, and the
# table's size after it. The cells are the middle of each rim, not a corner.
SPLICE = {
    "below": ("Zeile darunter", 9, (2, 1), (2, 1), (4, 4)),
    "above": ("Zeile darüber", 1, (0, 1), (1, 1), (4, 4)),
    "right": ("Spalte rechts", 7, (1, 3), (1, 3), (3, 5)),
    "left": ("Spalte links", 4, (1, 0), (1, 1), (3, 5)),
}
MATRIX = [
    *[
        (side, case)
        for side in SPLICE
        for case in ("frame_two_pens", "frame_one_pen", "dashed_grid")
    ],
    ("inside", "dashed_grid"),
]


@pytest.mark.parametrize("side,case", MATRIX, ids=[f"{s}-{c}" for s, c in MATRIX])
def test_splice_matrix(editor, side, case):
    """A row or column added at a rim keeps the frame closed on the new rim, and the box round its
    cell; a dashed grid stays dashed. The inside case adds a row below row 0 and a column right of
    column 0, in a dashed grid."""
    client = user()
    if side == "inside":
        look = dashed_look()
        page = editor(box("t", "table", look), client=client)
        splice(page, 0, "Zeile darunter")
        expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(16)
        splice(page, 0, "Spalte rechts")
        expect_grid(page, 4, 5, paint(4, 5, DASHED))
        return

    button, cell, before, after, (rows, cols) = SPLICE[side]
    if case == "dashed_grid":
        look = dashed_look()
        page = editor(box("t", "table", look), client=client)
        splice(page, cell, button)
        expect_grid(page, rows, cols, paint(rows, cols, DASHED))
        return

    box_pen = DOTTED if case == "frame_two_pens" else SOLID
    pens = {**rim(3, 4, SOLID), **round_cell(*before, box_pen)}
    look = {**FOUR, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(box("t", "table", {**look, "edges": edges(3, 4, pens)}), client=client)
    splice(page, cell, button)
    want = paint(rows, cols, PLAIN, rim(rows, cols, SOLID), round_cell(*after, box_pen))
    expect_grid(page, rows, cols, want)


def test_beyond_issue_595_undo_brings_the_old_lines_back(editor):
    """Beyond the brief: after Zeile darunter with a frame and a dotted box, Ctrl+Z takes the new
    row away and the 3 by 4 table is drawn as before."""
    client = user()
    pens = {**rim(3, 4, SOLID), **round_cell(2, 1, DOTTED)}
    look = {**FOUR, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(box("t", "table", {**look, "edges": edges(3, 4, pens)}), client=client)
    splice(page, 9, "Zeile darunter")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(16)
    page.keyboard.press("Control+z")
    expect_grid(page, 3, 4, paint(3, 4, PLAIN, rim(3, 4, SOLID), round_cell(2, 1, DOTTED)))


def test_beyond_issue_595_a_one_row_frame_stays_closed_under_a_new_row(editor):
    """Beyond the brief: a one-row table framed in 1.25 mm solid stays closed when a row is added
    below it: the frame's bottom is the new rim, and the line between the two rows is plain."""
    client = user()
    look = {**ONE_ROW, "line": INK, "lineStyle": "solid", "lineWidth": 0.25}
    page = editor(
        box("t", "table", {**look, "edges": edges(1, 3, rim(1, 3, SOLID))}), client=client
    )
    splice(page, 1, "Zeile darunter")
    expect_grid(page, 2, 3, paint(2, 3, PLAIN, rim(2, 3, SOLID)))
