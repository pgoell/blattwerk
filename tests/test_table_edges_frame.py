"""A table's frame when a row or a column is added: the ends, a thick line, and a closed box.

The helpers live in test_table_edges.py.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_table_edges import (
    FRAME,
    INK,
    LINES,
    THREE,
    scale,
    thick_between,
)
from ui import TABLE, at, box, pick, saved, user


def frame_lines(page, rows, cols):
    """The lines on the rim of a rows by cols table, and every solid line drawn."""
    lines = page.locator('.table svg.edge[data-edge]:not([data-edge="bank"])').evaluate_all(LINES)
    rim = []
    for line in lines:
        r, c = divmod(line["edge"], cols)
        sides = {"top": r == 0, "bottom": r == rows - 1, "left": c == 0, "right": c == cols - 1}
        on_rim = sides[line["side"]]
        if on_rim:
            rim.append(line)
    return rim, [line for line in lines if line["style"] == "solid"]


def test_issue_562_a_new_row_takes_the_frame_at_its_ends(editor):
    """Issue #562 (PR #546): a frame of 1.25 mm solid lines round a dotted grid stays closed when a
    row is added below one of its rows. The new row's ends take the frame's pen, and no solid line
    is drawn inside the frame."""
    frame = [FRAME] * 3
    edges = {
        "h": [frame, [None] * 3, [None] * 3, frame],
        "v": [[FRAME, None, None, FRAME]] * 3,
    }
    page = editor(box("t", "table", {**THREE, "line": INK, "lineStyle": "dotted", "edges": edges}))
    expect(page.locator(".table svg.edge line")).not_to_have_count(0)
    rim, solid = frame_lines(page, 3, 3)
    assert len(rim) == 12 and len(solid) == 12
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(3).dblclick()
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    rim, solid = frame_lines(page, 4, 3)
    assert [line for line in rim if line["style"] != "solid"] == []
    assert len(rim) == 14 and len(solid) == 14
    assert all(abs(line["w"] - 1.25 * scale(page)) < 0.5 for line in rim)
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    rim, solid = frame_lines(page, 3, 3)
    assert len(rim) == 12 and len(solid) == 12


def test_issue_562_a_new_column_takes_the_frame_at_its_ends(editor):
    """Issue #562 (PR #546): the same frame stays closed when a column is added to the right of its
    last column. The new column's top and bottom are the frame's pen, and no solid line is drawn
    inside the frame."""
    frame = [FRAME] * 3
    edges = {
        "h": [frame, [None] * 3, [None] * 3, frame],
        "v": [[FRAME, None, None, FRAME]] * 3,
    }
    page = editor(box("t", "table", {**THREE, "line": INK, "lineStyle": "dotted", "edges": edges}))
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(2).dblclick()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    rim, solid = frame_lines(page, 3, 4)
    assert [line for line in rim if line["style"] != "solid"] == []
    assert len(rim) == 14 and len(solid) == 14
    assert len({line["w"] for line in rim}) == 1


def test_beyond_broken_edges_are_ignored_and_the_width_holds(editor):
    """Beyond the brief: edges of the wrong shape are left out whole; every line then takes the
    table's style and width."""
    broken = {"h": [[None, None]], "v": [[None] * 3, [None] * 3]}
    page = editor(box("t", "table", {**TABLE, "line": INK, "lineWidth": 1, "edges": broken}))
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator(".table svg.edge line")).to_have_count(12)
    expect(page.locator(".table svg.edge line[data-style='solid']")).to_have_count(12)
    widths = page.locator(".table svg.edge line").evaluate_all(
        "els => els.map((e) => +e.getAttribute('stroke-width'))"
    )
    assert all(abs(w - scale(page)) < 0.5 for w in widths)


@pytest.mark.parametrize("button", ["Zeile darunter", "Zeile darüber"])
def test_issue_567_a_thick_line_inside_runs_on_through_a_new_row(editor, browser, server, button):
    """Issue #567 (PR #546): the first column framed in 1.25 mm, so the line between column 1 and 2
    is thick inside the table. A row added below or above the middle row carries that line, on the
    screen and on the print page; Ctrl+Z takes the row away."""
    client = user()
    edges = {
        "h": [[FRAME, None, None], [None] * 3, [None] * 3, [FRAME, None, None]],
        "v": [[FRAME, FRAME, None, None]] * 3,
    }
    page = editor(box("t", "table", {**THREE, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(4).dblclick()
    page.get_by_role("button", name=button, exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {0, 1, 2, 3}
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {0, 1, 2, 3}
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert thick_between(paper, 3, ("v", 1), 1.25) == {0, 1, 2, 3}
    paper.context.close()
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {0, 1, 2}


def test_issue_567_a_thick_line_across_runs_on_through_a_new_column(editor, browser, server):
    """Issue #567: the first row framed in 1.25 mm, so the line under it is thick inside the table.
    A column added to the right of the middle one carries that line, on the screen and in print."""
    client = user()
    edges = {
        "h": [[FRAME] * 3, [FRAME] * 3, [None] * 3, [None] * 3],
        "v": [[FRAME, None, None, FRAME], [None] * 4, [None] * 4],
    }
    page = editor(box("t", "table", {**THREE, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(4).dblclick()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 4, ("h", 1), 1.25) == {0, 1, 2, 3}
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert thick_between(paper, 4, ("h", 1), 1.25) == {0, 1, 2, 3}
    paper.context.close()


def test_issue_574_a_new_row_below_keeps_the_box_closed(editor, browser, server):
    """Issue #574: a box of 1.25 mm round the cell in row 2, column 0 of a four-row table stays
    closed when a row is added below that cell. The new row has the table's plain lines, on the
    screen and in print."""
    client = user()
    four = {**THREE, "cells": [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"], ["j", "k", "l"]]}
    edges = {
        "h": [[None] * 3, [None] * 3, [FRAME, None, None], [FRAME, None, None], [None] * 3],
        "v": [[None] * 4, [None] * 4, [FRAME, FRAME, None, None], [None] * 4],
    }
    page = editor(box("t", "table", {**four, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(6).dblclick()
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(15)
    assert thick_between(at(page, "t"), 3, ("h", 3), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("h", 2), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("h", 4), 1.25) == set()
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {2}
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {2}
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert thick_between(paper, 3, ("h", 3), 1.25) == {0}
    assert thick_between(paper, 3, ("h", 4), 1.25) == set()
    assert thick_between(paper, 3, ("v", 1), 1.25) == {2}
    paper.context.close()


def test_issue_574_a_new_column_right_keeps_the_box_closed(editor):
    """Issue #574: a box of 1.25 mm round the middle cell of a 3x3 table stays closed when a column
    is added to its right."""
    edges = {
        "h": [[None] * 3, [None, FRAME, None], [None, FRAME, None], [None] * 3],
        "v": [[None] * 4, [None, FRAME, FRAME, None], [None] * 4],
    }
    page = editor(box("t", "table", {**THREE, "line": INK, "edges": edges}))
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(4).dblclick()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 4, ("v", 1), 1.25) == {1}
    assert thick_between(at(page, "t"), 4, ("v", 2), 1.25) == {1}
    assert thick_between(at(page, "t"), 4, ("v", 3), 1.25) == set()
    assert thick_between(at(page, "t"), 4, ("h", 1), 1.25) == {1}
    assert thick_between(at(page, "t"), 4, ("h", 2), 1.25) == {1}


def test_issue_574_a_row_above_then_undo_restores_the_box(editor):
    """Issue #574: a row added above a boxed cell, undone with Ctrl+Z, keeps the box."""
    four = {**THREE, "cells": [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"], ["j", "k", "l"]]}
    edges = {
        "h": [[None] * 3, [None] * 3, [FRAME, None, None], [FRAME, None, None], [None] * 3],
        "v": [[None] * 4, [None] * 4, [FRAME, FRAME, None, None], [None] * 4],
    }
    page = editor(box("t", "table", {**four, "line": INK, "edges": edges}))
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(6).dblclick()
    page.get_by_role("button", name="Zeile darüber", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(15)
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    assert thick_between(at(page, "t"), 3, ("h", 2), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("h", 3), 1.25) == {0}
    assert thick_between(at(page, "t"), 3, ("v", 0), 1.25) == {2}
    assert thick_between(at(page, "t"), 3, ("v", 1), 1.25) == {2}


@pytest.mark.parametrize(
    ("cell", "button", "boxed"), [(3, "Zeile darunter", 3), (9, "Zeile darüber", 2)]
)
def test_review_574_a_box_beside_the_new_row_stays_closed(
    editor, browser, server, cell, button, boxed
):
    """Review of #574: the box round row 2, column 0 stays closed when the new row comes in on its
    other side: below the row above it, or above the row under it. On screen and in print."""
    client = user()
    four = {**THREE, "cells": [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"], ["j", "k", "l"]]}
    edges = {
        "h": [[None] * 3, [None] * 3, [FRAME, None, None], [FRAME, None, None], [None] * 3],
        "v": [[None] * 4, [None] * 4, [FRAME, FRAME, None, None], [None] * 4],
    }
    page = editor(box("t", "table", {**four, "line": INK, "edges": edges}), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(cell).dblclick()
    page.get_by_role("button", name=button, exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(15)
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    for where in (at(page, "t"), paper):
        assert thick_between(where, 3, ("h", boxed), 1.25) == {0}
        assert thick_between(where, 3, ("h", boxed + 1), 1.25) == {0}
        assert thick_between(where, 3, ("v", 1), 1.25) == {boxed}
    paper.context.close()
