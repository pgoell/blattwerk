"""Issue #584: a row added below a table's last row keeps a box round some of its cells where it is.

The lines are read as in test_table_edges.py: `thick_between` gives the rows or columns in which a
line of the given width stands on a line of the table.
"""

from playwright.sync_api import expect
from test_table_edges import FRAME, INK, THREE, thick_between
from ui import at, box, pick, user


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
