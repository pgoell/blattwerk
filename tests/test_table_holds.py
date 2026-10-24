"""A table keeps what was set when its columns or rows change, and goes back to its height when its
text goes. Issue 517 is the columns, issue 520 the height.
"""

from playwright.sync_api import expect
from test_cells import GRID, MERGED, open_cell, props
from test_sizes import EDGE, H, W, block, typed, widths_mm
from ui import box, user

LONG = " ".join(f"wort{n}" for n in range(25))


def test_a_set_column_width_holds_when_a_column_is_added_right(editor):
    """Issue 517: a column set to 40 mm stays 40 mm when a column comes to its right, and the block
    grows by the average width, while it has room before the right margin (#602)."""
    client = user()
    page = editor(box("t", "table", GRID, x=15, w=120 + EDGE), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    before = block(page, client)
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    after = block(page, client)
    # The new column takes the average of the old widths, the others keep theirs.
    old = widths_mm(before)
    avg = sum(old) / len(old)
    for got, want in zip(widths_mm(after), [old[0], avg, *old[1:]], strict=True):
        assert abs(got - want) <= 0.05
    assert abs(after["w"] - (before["w"] + avg)) <= 0.05


def test_a_set_column_width_holds_when_a_column_is_added_left(editor):
    """Issue 517: a column set to 40 mm stays 40 mm when a column comes to its left, and the block
    grows by the average width, while it has room before the right margin (#602)."""
    client = user()
    page = editor(box("t", "table", GRID, x=15, w=120 + EDGE), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    before = block(page, client)
    page.get_by_role("button", name="Spalte links", exact=True).click()
    after = block(page, client)
    old = widths_mm(before)
    avg = sum(old) / len(old)
    for got, want in zip(widths_mm(after), [avg, *old], strict=True):
        assert abs(got - want) <= 0.05
    assert abs(after["w"] - (before["w"] + avg)) <= 0.05


def test_a_set_column_width_holds_when_another_column_is_deleted(editor):
    """Issue 517: a column set to 40 mm stays 40 mm when another column goes, and the block shrinks
    by that one."""
    client = user()
    page = editor(box("t", "table", GRID, w=W), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    before = block(page, client)
    open_cell(page, "t", 2)
    page.get_by_role("button", name="Spalte löschen", exact=True).click()
    after = block(page, client)
    old = widths_mm(before)
    for got, want in zip(widths_mm(after), old[:2], strict=True):
        assert abs(got - want) <= 0.05
    assert abs(after["w"] - (before["w"] - old[2])) <= 0.05


def test_a_set_column_width_holds_when_another_column_is_deleted_in_six_columns(editor):
    """Issue 517: in six columns, a column set to 40 mm stays 40 mm when another goes, and the block
    shrinks by that one."""
    client = user()
    six = {**GRID, "cells": [["", "", "", "", "", ""] for _ in range(3)], "cols": [1] * 6}
    page = editor(box("t", "table", six, w=W), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    before = block(page, client)
    open_cell(page, "t", 4)
    page.get_by_role("button", name="Spalte löschen", exact=True).click()
    after = block(page, client)
    old = widths_mm(before)
    assert len(widths_mm(after)) == 5
    for got, want in zip(widths_mm(after), [*old[:4], old[5]], strict=True):
        assert abs(got - want) <= 0.05
    assert abs(after["w"] - (before["w"] - old[4])) <= 0.05


def test_every_column_keeps_its_width_when_a_column_comes_or_goes(editor):
    """Issue 517: columns of 20, 40 and 60 mm keep their widths when one comes and when one goes,
    in a table with room before the right margin (#602)."""
    client = user()
    page = editor(box("t", "table", {**GRID, "cols": [1, 2, 3]}, x=15, w=120 + EDGE), client=client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    # The new column takes the average of 20, 40 and 60.
    for got, want in zip(widths_mm(block(page, client)), [20, 40, 40, 60], strict=True):
        assert abs(got - want) <= 0.05
    open_cell(page, "t", 2)
    page.get_by_role("button", name="Spalte löschen", exact=True).click()
    for got, want in zip(widths_mm(block(page, client)), [20, 40, 60], strict=True):
        assert abs(got - want) <= 0.05


def test_a_column_added_or_deleted_is_one_step_of_undo(editor):
    """Issue 517: one Ctrl+Z takes back the widths and the block's width, Ctrl+Y sets them again."""
    client = user()
    page = editor(box("t", "table", GRID, w=W), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    start = block(page, client)
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    added = block(page, client)
    page.keyboard.press("Control+z")
    assert block(page, client)["w"] == start["w"]
    assert block(page, client)["props"]["cols"] == start["props"]["cols"]
    page.keyboard.press("Control+y")
    assert abs(block(page, client)["w"] - added["w"]) <= 0.01
    assert block(page, client)["props"]["cols"] == added["props"]["cols"]
    open_cell(page, "t", 1)
    page.get_by_role("button", name="Spalte löschen", exact=True).click()
    removed = block(page, client)
    page.keyboard.press("Control+z")
    assert abs(block(page, client)["w"] - added["w"]) <= 0.01
    page.keyboard.press("Control+y")
    assert abs(block(page, client)["w"] - removed["w"]) <= 0.01


def test_a_column_deleted_through_a_merged_cell_leaves_the_other_widths(editor):
    """Issue 517: deleting the first column through the merged cell that starts it leaves the other
    columns at their widths, and the block shrinks by that column."""
    client = user()
    page = editor(box("t", "table", {**MERGED, "cols": [1, 2, 3]}, w=W), client=client)
    before = block(page, client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Spalte löschen", exact=True).click()
    after = block(page, client)
    old = widths_mm(before)
    for got, want in zip(widths_mm(after), old[1:], strict=True):
        assert abs(got - want) <= 0.05
    assert abs(after["w"] - (before["w"] - old[0])) <= 0.05


def test_typing_and_deleting_adds_no_step_of_undo(editor):
    """Issue 520, I3: the heights belong to the typing's own step. A text typed and deleted in one
    go is one step, as before: one Ctrl+Z gives the table as it was, with no row heights, and there
    is no step more."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    was = props(page, client)["cells"][1][1]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > H + 20
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - H) <= 0.05
    page.keyboard.press("Control+z")
    assert props(page, client)["cells"][1][1] == was
    assert block(page, client)["h"] == H
    assert "rows" not in props(page, client)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    page.keyboard.press("Control+y")
    assert props(page, client)["cells"][1][1] == ""
    assert abs(block(page, client)["h"] - H) <= 0.05


def test_a_table_past_the_right_edge_is_warned_of(editor):
    """Issue 537: a table that reaches past the page's edge, and the panel says that what lies past
    the edge is not printed. A table from margin to margin says nothing, nor after a column more,
    which keeps it inside the margin (#602)."""
    client = user()
    page = editor(box("t", "table", GRID, x=15, w=180), client=client)
    open_cell(page, "t", 0)
    expect(page.locator('[data-edge="over"]')).to_be_hidden()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    assert block(page, client)["w"] <= 180.05
    expect(page.locator('[data-edge="over"]')).to_be_hidden()
    page = editor(box("t", "table", GRID, x=40, w=180), client=client)
    open_cell(page, "t", 0)
    expect(page.locator('[data-edge="over"]')).to_be_visible()


def test_a_typed_column_width_past_the_right_edge_is_warned_of(editor):
    """Issue 523: two columns set wide on a six-column table show the warning past the edge."""
    client = user()
    six = {**GRID, "cells": [["", "", "", "", "", ""] for _ in range(3)], "cols": [1] * 6}
    page = editor(box("t", "table", six, x=15, w=180), client=client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    open_cell(page, "t", 1)
    typed(page, "Spaltenbreite", "45")
    expect(page.locator('[data-edge="over"]')).to_be_visible()
