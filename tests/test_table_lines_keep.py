"""Lines a table keeps: a merged cell, new rows and columns, a second table, and a copy.

The helpers live in test_table_lines.py.
"""

from playwright.sync_api import expect
from test_table_lines import (
    GRID,
    border,
    cell,
    drawn,
    open_cell,
    props,
    schneidelinien,
    style,
)
from ui import at, box, doc, pick, user

# A 3 by 3 table with cells (0,0) and (0,1) merged into one, cell (0,1) holding no text.
MERGED = {
    **GRID,
    "cells": [["a", "", "c"], ["d", "e", "f"], ["g", "h", "i"]],
    "spans": [[0, 0, 1, 2]],
}
# A 2 by 2 table with a dashed line below cell (0,0) and one right of cell (0,0).
DASHED = {
    **GRID,
    "cells": [["a", "b"], ["c", "d"]],
    "cols": [1, 1],
    "edges": {
        "h": [[None, None], [{"style": "dashed"}, None], [None, None]],
        "v": [[None, {"style": "dashed"}, None], [None, None, None]],
    },
}


def lines_of(p):
    """The stored sizes, as (len h, len h[0], len v, len v[0]), and the lines with an entry."""
    e = p["edges"]
    sizes = (len(e["h"]), len(e["h"][0]), len(e["v"]), len(e["v"][0]))
    held = set()
    for axis in ("h", "v"):
        held |= {(axis, r, c) for r, row in enumerate(e[axis]) for c, x in enumerate(row) if x}
    return sizes, held


def test_i4_a_merged_cell_counts_as_one_for_the_border_buttons(editor):
    """I4: a merged cell is one cell for the border buttons; its inner line is not written."""
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    open_cell(page, 0)
    for label in ("Innen", "Innen waagerecht", "Innen senkrecht"):
        expect(border(page, label)).to_be_disabled()
    style(page).select_option("dashed")
    border(page, "Außen").click()
    p = props(page, client)
    assert drawn(p) == {"h0,0", "h0,1", "h1,0", "h1,1", "v0,0", "v0,2"}
    # From the merged cell to cell (1,2): the rect is rows 0 to 1 and columns 0 to 2.
    cell(page, 5).click(modifiers=["Shift"])
    border(page, "Innen senkrecht").click()
    p = props(page, client)
    assert {"v0,1", "v1,1", "v0,2", "v1,2"} <= drawn(p)
    assert "v0,1" in drawn(p) and p["edges"]["v"][0][1] == {"style": "dashed", "width": 0.25}


def test_i5_rows_and_columns_keep_their_lines(editor):
    """I5: a row or column that comes or goes keeps each line with its cells. A new row or column
    takes the lines that cross its neighbour, as Word does (#567); the line beside it is null."""
    client = user()
    page = editor(box("t", "table", DASHED), client=client)
    pick(page, "t")
    page.get_by_role("button", name="Eine Zeile mehr").click()
    expect(at(page, "t").locator("[data-cell]")).to_have_count(6)
    assert lines_of(props(page, client)) == ((4, 2, 3, 3), {("h", 1, 0), ("v", 0, 1)})
    page.get_by_role("button", name="Eine Spalte mehr").click()
    expect(at(page, "t").locator("[data-cell]")).to_have_count(9)
    assert lines_of(props(page, client)) == ((4, 3, 3, 4), {("h", 1, 0), ("v", 0, 1)})
    open_cell(page, 0)
    border_row = page.get_by_role("button", name="Zeile darüber", exact=True)
    border_row.click()
    expect(at(page, "t").locator("[data-cell]")).to_have_count(12)
    # The rim stays the rim, so the lines below the new row move down by one; the new row takes
    # the dashed line that crosses the first row.
    held = {("h", 2, 0), ("v", 0, 1), ("v", 1, 1)}
    assert lines_of(props(page, client)) == ((5, 3, 4, 4), held)
    page.get_by_role("button", name="Spalte links", exact=True).click()
    expect(at(page, "t").locator("[data-cell]")).to_have_count(16)
    held = {("h", 2, 0), ("h", 2, 1), ("v", 0, 2), ("v", 1, 2)}
    assert lines_of(props(page, client)) == ((5, 4, 4, 5), held)
    # Delete the first row: its own line and the line on its left go; the others move up.
    cell(page, 0).dblclick()
    page.get_by_role("button", name="Zeile löschen", exact=True).click()
    expect(at(page, "t").locator("[data-cell]")).to_have_count(12)
    assert lines_of(props(page, client)) == ((4, 4, 3, 5), {("h", 1, 0), ("h", 1, 1), ("v", 0, 2)})
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator("[data-cell]")).to_have_count(16)
    assert lines_of(props(page, client)) == ((5, 4, 4, 5), held)


def test_i6_two_tables_take_the_style_width_and_cut(editor):
    """I6: with two tables picked the style, width and Schneidelinien go to both; no Rahmen."""
    client = user()
    page = editor(box("a", "table", GRID), box("b", "table", GRID, z=2), client=client)
    pick(page, "a", "b")
    expect(page.get_by_role("group", name="Rahmen")).to_have_count(0)
    style(page).select_option("dashed")
    slider = page.get_by_label("Linienstärke")
    slider.focus()
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="1,00 mm")).to_be_visible()
    schneidelinien(page).click()
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "true")
    blocks = doc(page, client)["pages"][0]["blocks"]
    for name in ("a", "b"):
        p = next(b for b in blocks if b["id"] == name)["props"]
        assert p["cut"] is True and p["lineStyle"] == "dashed" and p["lineWidth"] == 0.25


def test_i8_copy_paste_and_duplicate_keep_the_lines(editor):
    """I8: copy and paste, and Duplizieren, keep a table's four keys, deep-equal."""
    keys = ("lineStyle", "lineWidth", "cut", "edges")
    seed = {
        **GRID,
        "lineStyle": "dotted",
        "lineWidth": 0.5,
        "cut": True,
        "edges": {
            "h": [[{"style": "dashed"}, None, None]] + [[None] * 3] * 3,
            "v": [[None] * 4] * 3,
        },
    }
    for shortcut in ("Control+c", "Control+d"):
        client = user()
        page = editor(box("t", "table", seed), client=client)
        pick(page, "t")
        page.keyboard.press(shortcut)
        if shortcut == "Control+c":
            page.keyboard.press("Control+v")
        expect(page.locator(".block")).to_have_count(2)
        blocks = doc(page, client)["pages"][0]["blocks"]
        tables = [b["props"] for b in blocks if b["type"] == "table"]
        assert len(tables) == 2
        for p in tables:
            assert {k: p[k] for k in keys} == {k: seed[k] for k in keys}


def test_i7_the_panel_shows_the_table_and_a_pen_changes_no_doc(editor):
    """I7: the panel shows the table's style, width and Schneidelinien; the pen changes no doc."""
    client = user()
    seed = {**GRID, "lineStyle": "dotted", "lineWidth": 1.5, "cut": True}
    page = editor(box("t", "table", seed), client=client)
    pick(page, "t")
    expect(style(page)).to_have_value("dotted")
    expect(page.get_by_label("Linienstärke")).to_have_value("1.5")
    expect(page.locator("output", has_text="1,50 mm")).to_be_visible()
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "true")
    before = doc(page, client)
    cell(page, 0).dblclick()
    expect(cell(page, 0).locator("textarea")).to_be_focused()
    expect(style(page)).to_have_value("dotted")
    expect(page.get_by_label("Linienstärke")).to_have_value("1.5")
    style(page).select_option("solid")
    expect(style(page)).to_have_value("solid")
    slider = page.get_by_label("Linienstärke")
    slider.focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="1,75 mm")).to_be_visible()
    assert doc(page, client) == before
