"""Exact row and column sizes of a table: the panel's fields and buttons, the drawing, undo, and the
copies. The docstrings name the lines of the checklist (Asked n, Implied n).

A table's line at its left and top is 1 px wide (EDGE mm). It is no column or row, so a block
`w` mm wide holds columns of `w - EDGE`. The fixtures add EDGE, so that round numbers hold.
"""

from playwright.sync_api import expect
from test_cells import GRID, MERGED, cell, open_cell, print_page
from ui import at, box, doc, drag, pick, thumb, user

EDGE = 25.4 / 96
# Block sizes that give columns of exactly 60 mm (cols 1:1:1) and rows of exactly 10 mm.
W = 180 + EDGE
H = 30 + EDGE


def num(page, label):
    return page.get_by_label(label, exact=True)


def typed(page, label, text):
    field = num(page, label)
    field.click()
    field.fill(text)
    field.press("Enter")


def block(page, client, name="t"):
    return next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == name)


def mm(page, locator):
    """A locator's width and height in mm: the sheet is 210 mm wide."""
    sheet = page.locator('.sheet[data-page="0"]').bounding_box()["width"] / 210
    box_ = locator.bounding_box()
    return box_["width"] / sheet, box_["height"] / sheet


def mm_width(page, locator):
    return mm(page, locator)[0]


def mm_height(page, locator):
    return mm(page, locator)[1]


def number(text):
    return float(text.replace(",", "."))


def widths_mm(found):
    """The columns' widths in mm of a saved block."""
    cols = found["props"]["cols"]
    return [c / sum(cols) * (found["w"] - EDGE) for c in cols]


def test_the_panel_shows_width_and_height_of_the_cell(editor):
    """Asked 1"""
    page = editor(box("t", "table", GRID, w=W))
    pick(page, "t")
    expect(num(page, "Spaltenbreite")).to_have_count(0)
    expect(num(page, "Zeilenhöhe")).to_have_count(0)
    open_cell(page, "t", 0)
    expect(num(page, "Spaltenbreite")).to_have_value("60")
    height = number(num(page, "Zeilenhöhe").input_value())
    assert abs(height - mm_height(page, cell(page, "t", 0))) <= 0.1


def test_a_typed_width_sets_the_column_and_moves_the_block_edge(editor):
    """Asked 2, Implied 3"""
    client = user()
    page = editor(box("t", "table", GRID, w=W), client=client)
    before = block(page, client)
    open_cell(page, "t", 0)
    typed(page, "Spaltenbreite", "40")
    after = block(page, client)
    assert abs(after["w"] - (160 + EDGE)) <= 0.01
    assert after["x"] == before["x"]
    for got, want in zip(widths_mm(after), [40, 60, 60], strict=True):
        assert abs(got - want) <= 0.01
    assert abs(mm_width(page, cell(page, "t", 0)) - 40) <= 0.1

    typed(page, "Spaltenbreite", "2")
    assert abs(mm_width(page, cell(page, "t", 0)) - 5) <= 0.1
    assert abs(widths_mm(block(page, client))[0] - 5) <= 0.01

    snapshot = block(page, client)
    typed(page, "Spaltenbreite", "abc")
    assert block(page, client) == snapshot

    num(page, "Spaltenbreite").click()
    num(page, "Spaltenbreite").fill("30")
    num(page, "Spaltenbreite").press("Escape")
    assert block(page, client) == snapshot


def test_a_typed_height_is_a_lowest_height(editor):
    """Asked 3, Implied 1"""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    before = block(page, client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 0)
    typed(page, "Zeilenhöhe", "20")
    assert abs(mm_height(page, cell(page, "t", 0)) - 20) <= 0.1
    for n, was in zip((3, 6), rows_before[1:], strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.1
    after = block(page, client)
    assert abs(after["h"] - (before["h"] + 10)) <= 0.01
    assert after["y"] == before["y"]
    rows = after["props"]["rows"]
    assert len(rows) == 3
    assert abs(rows[0] - 20) <= 0.01

    typed(page, "Zeilenhöhe", "2")
    real = mm_height(page, cell(page, "t", 0))
    assert real > 2
    shown = num(page, "Zeilenhöhe")
    expect(shown).not_to_have_value("2")
    assert abs(number(shown.input_value()) - real) <= 0.1


def test_fields_set_every_picked_column_and_row(editor):
    """Asked 4, Implied 2"""
    client = user()
    page = editor(box("t", "table", {**GRID, "cols": [1, 2, 3]}, w=W), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(num(page, "Spaltenbreite")).to_have_value("")
    typed(page, "Spaltenbreite", "25")
    assert abs(mm_width(page, cell(page, "t", 0)) - 25) <= 0.1
    assert abs(mm_width(page, cell(page, "t", 1)) - 25) <= 0.1
    assert abs(mm_width(page, cell(page, "t", 2)) - 90) <= 0.1
    assert abs(block(page, client)["w"] - (140 + EDGE)) <= 0.01

    typed(page, "Zeilenhöhe", "12")
    assert abs(mm_height(page, cell(page, "t", 0)) - 12) <= 0.1
    assert abs(mm_height(page, cell(page, "t", 3)) - 12) <= 0.1
    expect(num(page, "Zeilenhöhe")).to_have_value("12")


def test_spalten_verteilen(editor):
    """Asked 5"""
    client = user()
    page = editor(box("t", "table", {**GRID, "cols": [1, 2, 3]}, w=W), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 1).click(modifiers=["Shift"])
    page.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    found = block(page, client)
    assert abs(found["w"] - W) <= 0.01
    for got, want in zip(widths_mm(found), [45, 45, 90], strict=True):
        assert abs(got - want) <= 0.01

    again = editor(box("t", "table", {**GRID, "cols": [1, 2, 3]}, w=W), client=client)
    open_cell(again, "t", 0)
    again.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    for got in widths_mm(block(again, client)):
        assert abs(got - 60) <= 0.01


def test_zeilen_verteilen(editor):
    """Asked 6, Implied 6"""
    client = user()
    text = {**GRID, "cells": [["eins\nzwei\ndrei", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]]}
    page = editor(box("t", "table", text, h=60 + EDGE), client=client)
    open_cell(page, "t", 3)
    page.get_by_role("button", name="Zeilen gleichmäßig verteilen", exact=True).click()
    heights = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    assert max(heights) - min(heights) <= 0.1
    rows = block(page, client)["props"]["rows"]
    assert len(rows) == 3
    assert max(rows) - min(rows) <= 0.01

    short = editor(box("t", "table", text, h=20 + EDGE), client=client)
    open_cell(short, "t", 3)
    short.get_by_role("button", name="Zeilen gleichmäßig verteilen", exact=True).click()
    heights = [mm_height(short, cell(short, "t", n)) for n in (0, 3, 6)]
    assert max(heights) - min(heights) <= 0.1
    assert heights[0] > 20 / 3
    assert block(short, client)["h"] > 20


def test_a_drag_of_a_column_line_moves_the_field(editor):
    """Asked 7"""
    client = user()
    page = editor(box("t", "table", GRID, w=W), client=client)
    pick(page, "t")
    handle = page.locator("i.bar").first
    sheet = page.locator('.sheet[data-page="0"]').bounding_box()["width"] / 210
    x = handle.bounding_box()["x"] + handle.bounding_box()["width"] / 2
    y = handle.bounding_box()["y"] + handle.bounding_box()["height"] / 2
    drag(page, (x, y), (x + 20 * sheet, y))
    open_cell(page, "t", 0)
    shown = number(num(page, "Spaltenbreite").input_value())
    assert shown != 60
    assert abs(shown - mm_width(page, cell(page, "t", 0))) <= 0.1


def test_a_resize_scales_columns_and_rows(editor):
    """Asked 8, Implied 4"""
    client = user()
    page = editor(
        box("t", "table", {**GRID, "cols": [40, 60, 60], "rows": [10, 10, 10]}, w=160 + EDGE, h=H),
        client=client,
    )
    pick(page, "t")
    typed(page, "Breite", "80,26")
    typed(page, "Höhe", "60,26")
    open_cell(page, "t", 0)
    expect(num(page, "Spaltenbreite")).to_have_value("20")
    expect(num(page, "Zeilenhöhe")).to_have_value("20")
    for got in block(page, client)["props"]["rows"]:
        assert abs(got - 20) <= 0.01


def test_an_old_table_opens_and_saves_unchanged(editor):
    """Asked 9"""
    client = user()
    for table in (MERGED, GRID):
        page = editor(box("t", "table", table), client=client)
        grid = at(page, "t").locator(".table")
        assert grid.evaluate("el => el.style.gridTemplateRows") == ""
        open_cell(page, "t", 0)
        page.keyboard.type("x")
        found = block(page, client)["props"]
        assert "rows" not in found
        assert found["cols"] == [1, 1, 1]


def test_each_change_is_one_step_of_undo_and_redo(editor):
    """Asked 10"""
    client = user()
    page = editor(box("t", "table", {**GRID, "cols": [1, 2, 3]}, w=W, h=H), client=client)
    start = block(page, client)
    open_cell(page, "t", 0)

    # Column 0 is 30 mm of 180 (cols 1:2:3); typing 40 widens the block by 10.
    typed(page, "Spaltenbreite", "40")
    assert abs(block(page, client)["w"] - (start["w"] + 10)) <= 0.01
    num(page, "Spaltenbreite").press("Control+z")
    undone = block(page, client)
    assert undone["w"] == start["w"]
    assert undone["props"]["cols"] == start["props"]["cols"]
    num(page, "Spaltenbreite").press("Control+y")
    assert abs(block(page, client)["w"] - (start["w"] + 10)) <= 0.01

    typed(page, "Zeilenhöhe", "20")
    assert "rows" in block(page, client)["props"]
    num(page, "Zeilenhöhe").press("Control+z")
    back = block(page, client)
    assert "rows" not in back["props"]
    assert back["h"] == start["h"]
    num(page, "Zeilenhöhe").press("Control+y")
    assert "rows" in block(page, client)["props"]

    typed_cols = block(page, client)["props"]["cols"]
    page.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    evened = block(page, client)["props"]["cols"]
    assert evened != typed_cols
    page.keyboard.press("Control+z")
    assert block(page, client)["props"]["cols"] == typed_cols
    page.keyboard.press("Control+y")
    assert block(page, client)["props"]["cols"] == evened

    typed_h = block(page, client)["h"]
    page.get_by_role("button", name="Zeilen gleichmäßig verteilen", exact=True).click()
    shared = block(page, client)
    assert shared["h"] != typed_h or shared["props"] != back["props"]
    page.keyboard.press("Control+z")
    assert block(page, client)["h"] == typed_h
    page.keyboard.press("Control+y")
    assert block(page, client)["h"] == shared["h"]


def test_sizes_agree_on_screen_thumb_and_pdf(editor, browser, server):
    """Asked 11"""
    client = user()
    table = {**GRID, "cols": [40, 60, 60], "rows": [20, 10, 10]}
    page = editor(box("t", "table", table, w=160 + EDGE, h=40 + EDGE), client=client, theme="")
    on_screen = cell(page, "t", 0)
    assert abs(mm_width(page, on_screen) - 40) <= 0.1
    assert abs(mm_height(page, on_screen) - 20) <= 0.1

    shown = thumb(page, 0).locator(".table")
    small = thumb(page, 0).locator('.table > div[data-cell="0"]')
    tw = shown.bounding_box()["width"]
    th = shown.bounding_box()["height"]
    assert abs(small.bounding_box()["width"] / tw - 0.25) <= 0.005
    assert abs(small.bounding_box()["height"] / th - 0.5) <= 0.01

    context, printed = print_page(browser, server, client, page.url.rsplit("/", 1)[1])
    drawn = printed.locator('.table > div[data-cell="0"]')
    assert abs(drawn.bounding_box()["width"] - 151.18) <= 0.3
    assert abs(drawn.bounding_box()["height"] - 75.59) <= 0.3
    context.close()


def test_sizes_with_merged_cells(editor):
    """Asked 12"""
    client = user()
    page = editor(box("t", "table", MERGED, w=W, h=H), client=client)
    open_cell(page, "t", 0)
    expect(num(page, "Spaltenbreite")).to_have_value("120")
    typed(page, "Spaltenbreite", "60")
    found = block(page, client)
    for got, want in zip(widths_mm(found), [30, 30, 60], strict=True):
        assert abs(got - want) <= 0.01
    assert abs(found["w"] - (120 + EDGE)) <= 0.01
    assert found["props"]["spans"] == [[0, 0, 2, 2]]

    typed(page, "Zeilenhöhe", "30")
    assert abs(mm_height(page, cell(page, "t", 2)) - 15) <= 0.1
    assert abs(mm_height(page, cell(page, "t", 5)) - 15) <= 0.1

    tall = {**MERGED, "cells": [["a\nb\nc\nd", "", "c"], ["", "", "f"], ["g", "h", "i"]]}
    page = editor(box("t", "table", tall, w=W, h=H), client=client)
    open_cell(page, "t", 0)
    typed(page, "Zeilenhöhe", "5")
    expect(num(page, "Zeilenhöhe")).not_to_have_value("5")
    real = number(num(page, "Zeilenhöhe").input_value())
    assert real > 5
    assert abs(real - mm_height(page, cell(page, "t", 0))) <= 0.1
    assert page.locator('.block[data-id="t"] .table > div[data-cell="0"]').evaluate(
        "el => el.scrollHeight <= el.clientHeight + 1"
    )

    spread = {**GRID, "cols": [1, 2, 3], "spans": [[0, 0, 1, 2]]}
    spread["cells"] = [["a", "", "c"], ["d", "e", "f"], ["g", "h", "i"]]
    page = editor(box("t", "table", spread, w=W), client=client)
    open_cell(page, "t", 3)
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    for got, want in zip(widths_mm(block(page, client)), [45, 45, 90], strict=True):
        assert abs(got - want) <= 0.01
    assert abs(mm_width(page, cell(page, "t", 0)) - 90) <= 0.1


def test_a_locked_table_takes_no_sizes(editor):
    """Implied 7. The app does not open a locked table's cell: no cell is open, so the fields are
    not there."""
    page = editor(box("t", "table", GRID, locked=True))
    pick(page, "t")
    cell(page, "t", 0).dblclick()
    expect(page.locator(".block.sel textarea")).to_have_count(0)
    expect(num(page, "Spaltenbreite")).to_have_count(0)
    expect(num(page, "Zeilenhöhe")).to_have_count(0)


def test_rows_and_copies_keep_the_set_heights(editor):
    """Implied 5"""
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [20, 10, 10]}, h=40 + EDGE), client=client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    rows = block(page, client)["props"]["rows"]
    assert len(rows) == 4
    assert abs(rows[0] - 20) <= 0.01
    assert abs(rows[2] - 10) <= 0.01

    page.keyboard.press("Escape")
    pick(page, "t")
    page.keyboard.press("Control+d")
    expect(page.locator(".block")).to_have_count(2)
    tables = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "table"]
    assert len(tables) == 2
    assert tables[0]["props"]["rows"] == tables[1]["props"]["rows"]


def test_a_table_with_solution_words_takes_a_row_height(editor):
    """Review 1: the box of solution words is no row of the grid."""
    client = user()
    table = {**GRID, "gaps": [[True, False, False], [False] * 3, [False] * 3], "bank": 3}
    page = editor(box("t", "table", table, w=W, h=50 + EDGE), client=client)
    open_cell(page, "t", 3)
    typed(page, "Zeilenhöhe", "20")
    rows = block(page, client)["props"]["rows"]
    assert len(rows) == 3
    assert abs(rows[1] - 20) <= 0.01
    assert abs(mm_height(page, cell(page, "t", 3)) - 20) <= 0.1
    expect(num(page, "Zeilenhöhe")).to_have_value("20")

    page.get_by_role("button", name="Zeilen gleichmäßig verteilen", exact=True).click()
    rows = block(page, client)["props"]["rows"]
    assert len(rows) == 3
    assert max(rows) - min(rows) <= 0.01


def test_a_tiny_height_in_a_merged_cell_keeps_the_other_rows(editor):
    """Review 2: a height far below the text's need leaves the other rows as they are."""
    client = user()
    table = {
        **GRID,
        "cells": [["a", "b"], ["", "c"], ["", "d"], ["e", "f"]],
        "cols": [1, 1],
        "spans": [[0, 0, 3, 1]],
        "rows": [10, 10, 10, 30],
    }
    page = editor(box("t", "table", table, h=60 + EDGE), client=client)
    open_cell(page, "t", 0)
    typed(page, "Zeilenhöhe", "0,01")
    rows = block(page, client)["props"]["rows"]
    assert len(rows) == 4
    assert all(r > 0 for r in rows)
    assert abs(rows[3] - 30) <= 0.01
    assert abs(mm_height(page, cell(page, "t", 6)) - 30) <= 0.1


def test_distribution_takes_what_a_picked_merged_cell_covers(editor):
    """Review 4, Asked 12: a merged cell's columns and rows are the ones shared out."""
    client = user()
    table = {
        **GRID,
        "cols": [1, 2, 3],
        "spans": [[0, 0, 2, 2]],
        "cells": [["a", "", "c"], ["", "", "f"], ["g", "h", "i"]],
        "rows": [12, 20, 10],
    }
    page = editor(box("t", "table", table, w=W, h=42 + EDGE), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 6).click(modifiers=["Shift"])
    page.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    for got, want in zip(widths_mm(block(page, client)), [45, 45, 90], strict=True):
        assert abs(got - want) <= 0.01
    assert abs(mm_width(page, cell(page, "t", 0)) - 90) <= 0.1

    rows_page = editor(box("t", "table", table, w=W, h=42 + EDGE), client=client)
    open_cell(rows_page, "t", 0)
    cell(rows_page, "t", 2).click(modifiers=["Shift"])
    rows_page.get_by_role("button", name="Zeilen gleichmäßig verteilen", exact=True).click()
    rows = block(rows_page, client)["props"]["rows"]
    for got, want in zip(rows, [16, 16, 10], strict=True):
        assert abs(got - want) <= 0.01
    assert abs(mm_height(rows_page, cell(rows_page, "t", 2)) - 16) <= 0.1
    assert abs(mm_height(rows_page, cell(rows_page, "t", 5)) - 16) <= 0.1
    assert abs(mm_height(rows_page, cell(rows_page, "t", 8)) - 10) <= 0.1
    assert abs(mm_height(rows_page, cell(rows_page, "t", 0)) - 32) <= 0.1

    caret = editor(box("t", "table", table, w=W, h=42 + EDGE), client=client)
    open_cell(caret, "t", 0)
    caret.get_by_role("button", name="Spalten gleichmäßig verteilen", exact=True).click()
    for got in widths_mm(block(caret, client)):
        assert abs(got - 60) <= 0.01


def test_a_row_added_drops_heights_that_do_not_hold(editor):
    """Review 5: a sheet with one row height too many has no set heights; a row added keeps none."""
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [30, 10, 10, 10]}, h=H), client=client)
    assert at(page, "t").locator(".table").evaluate("el => el.style.gridTemplateRows") == ""
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    found = block(page, client)
    assert len(found["props"]["cells"]) == 4
    assert "rows" not in found["props"]
    assert found["h"] < 45
