"""A table keeps what was set when its columns or rows change, and goes back to its height when its
text goes. Issue 517 is the columns, issue 520 the height.
"""

from playwright.sync_api import expect
from test_cells import GRID, MERGED, cell, open_cell, print_page, props
from test_sizes import EDGE, H, W, block, mm_height, num, typed, widths_mm
from ui import box, centre, drag, pick, thumb, unpick, user

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


def test_a_set_row_height_holds_when_a_row_comes_or_goes(editor):
    """Issue 520: a row set to 20 mm stays 20 mm when a row comes below it or goes, and the block's
    height changes by the row that came or went."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 0)
    typed(page, "Zeilenhöhe", "20")
    before = block(page, client)["h"]
    open_cell(page, "t", 3)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    came = block(page, client)["h"]
    assert came > before
    open_cell(page, "t", 0)
    expect_height(page, 20)
    open_cell(page, "t", 6)
    page.get_by_role("button", name="Zeile löschen", exact=True).click()
    assert block(page, client)["h"] < came
    open_cell(page, "t", 0)
    expect_height(page, 20)
    assert abs(mm_height(page, cell(page, "t", 0)) - 20) <= 0.1


def expect_height(page, mm):
    assert abs(float(num(page, "Zeilenhöhe").input_value().replace(",", ".")) - mm) <= 0.05


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


def test_a_set_row_height_comes_back_when_the_long_text_is_deleted(editor):
    """Issue 520: a row set to 20 mm, grown by a long text, is 20 mm again when the text goes. The
    other rows and the block keep their heights."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    typed(page, "Zeilenhöhe", "20")
    before = block(page, client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 6)]
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > before["h"] + 10
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    back = block(page, client)
    assert abs(back["h"] - before["h"]) <= 0.05
    assert abs(back["props"]["rows"][1] - 20) <= 0.05
    assert abs(mm_height(page, cell(page, "t", 3)) - 20) <= 0.1
    for n, was in zip((0, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


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


def test_a_table_goes_back_when_its_long_text_is_deleted(editor):
    """Issue 520: a table of 30 mm, grown by a long text, goes back to 30 mm, rows as they were."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > H + 20
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - H) <= 0.05
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - H) <= 0.05
    for n, was in zip((0, 3, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_table_made_taller_by_hand_goes_back_to_that_height(editor):
    """Issue 520: a table of 60 mm with no rows set, grown by a long text, goes back to 60 mm."""
    client = user()
    page = editor(box("t", "table", GRID, h=60), client=client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG + " " + LONG)
    assert block(page, client)["h"] > 60
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 60) <= 0.05
    # The rows too: the row typed into did not keep the room it took from the others.
    for n, was in zip((0, 3, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_typed_height_holds_on_a_table_with_rows_and_solution_words(editor):
    """From the review: the rows of a table with a box of solution words do not sum to its height,
    so such a table does not shrink by itself and a typed `Höhe` holds."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    open_cell(page, "t", 3)
    typed(page, "Zeilenhöhe", "12")
    page.keyboard.press("Escape")
    pick(page, "t")
    typed(page, "Höhe", "90")
    assert block(page, client)["h"] == 90


def test_a_height_set_on_a_table_grown_by_its_text_holds(editor):
    """A table that a text made tall and the teacher then made taller keeps that height: on its
    own, and when one more letter is typed. Only a table with no spare room comes down."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert 60 < block(page, client)["h"] < 85
    page.keyboard.press("Escape")
    pick(page, "t")
    typed(page, "Höhe", "90")
    assert block(page, client)["h"] == 90
    open_cell(page, "t", 4)
    page.keyboard.press("End")
    page.keyboard.type("x")
    assert props(page, client)["cells"][1][1].endswith("x")
    assert block(page, client)["h"] == 90


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


def test_a_shrunk_table_agrees_on_screen_thumb_and_pdf(editor, browser, server):
    """Issue 520: a table that shrank back to its height draws alike on screen, thumb and PDF."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client, theme="")
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    on_screen = cell(page, "t", 0)
    height = mm_height(page, on_screen)
    assert abs(block(page, client)["h"] - H) <= 0.05

    shown = thumb(page, 0).locator(".table")
    small = thumb(page, 0).locator('.table > div[data-cell="0"]')
    th = shown.bounding_box()["height"]
    assert abs(small.bounding_box()["height"] / th - height / (H - EDGE)) <= 0.02

    context, printed = print_page(browser, server, client, page.url.rsplit("/", 1)[1])
    drawn = printed.locator('.table > div[data-cell="0"]')
    # A millimetre is 96 / 25.4 px in the PDF.
    assert abs(drawn.bounding_box()["height"] - height * 96 / 25.4) <= 0.3
    context.close()


def typed_height(page, mm):
    pick(page, "t")
    typed(page, "Höhe", str(mm))


def test_a_typed_height_holds_when_more_text_is_typed_and_deleted(editor):
    """Issue 540: a height typed in the panel holds when more text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    typed_height(page, 90)
    assert block(page, client)["h"] == 90
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - 90) <= 0.1


def test_a_dragged_height_holds_when_text_is_typed_and_deleted(editor):
    """Issue 540: a height dragged on the bottom handle holds when text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    pick(page, "t")
    start = centre(page.locator(".moveable-control.moveable-s"))
    drag(page, start, (start[0], start[1] + 60))
    dragged = block(page, client)["h"]
    assert dragged > H + 5
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - dragged) <= 0.1


def test_a_typed_height_holds_when_the_text_goes_into_another_row(editor):
    """Issue 540: a height typed in the panel holds when the long text goes into another row."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    typed_height(page, 90)
    open_cell(page, "t", 6)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1


def test_a_table_with_solution_words_goes_back_when_its_long_text_is_deleted(editor):
    """Issue 539: a table with a box of solution words goes back to its height after long text."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    before = block(page, client)["h"]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > before + 10
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - before) <= 0.05


def test_a_typed_height_holds_on_a_table_with_solution_words_after_typing_and_deleting(editor):
    """Issue 539: a height typed on a table with a box of solution words holds after long text."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    # The long text alone needs some 96 mm: 120 is a height above that.
    typed_height(page, 120)
    assert block(page, client)["h"] == 120
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > 130
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 120) <= 0.1
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - 120) <= 0.1


def test_undo_brings_back_the_height_and_rows_before_a_typed_height(editor):
    """Issue 540: one Ctrl+Z after a typed height takes back the height and the rows before it."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    start = block(page, client)
    typed_height(page, 90)
    assert block(page, client)["h"] == 90
    unpick(page)
    page.keyboard.press("Control+z")
    after = block(page, client)
    assert abs(after["h"] - start["h"]) <= 0.05
    assert after["props"].get("rows") == start["props"].get("rows")


def saved_rows(page, client, name="t"):
    return block(page, client, name)["props"]["rows"]


def test_a_row_held_up_by_its_text_keeps_the_screens_proportion_when_the_table_grows(editor):
    """Issue 540, PowerPoint: a row its text holds up keeps the screen's proportion as it grows.

    Guards #514: a fix that scales the saved rows must not undo this.
    """
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [10, 10, 10]}, h=30 + EDGE), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(" ".join(f"wort{n}" for n in range(8)))
    page.keyboard.press("Escape")
    ratio = mm_height(page, cell(page, "t", 3)) / mm_height(page, cell(page, "t", 6))
    typed_height(page, 90)
    rows = saved_rows(page, client)
    assert abs(rows[1] / rows[2] - ratio) <= 0.05 * ratio
    assert abs(rows[0] - rows[2]) <= 0.05


def test_a_turned_table_holds_its_typed_height(editor):
    """Issue 540: a turned table keeps a typed height when long text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H, angle=90), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    typed_height(page, 90)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1


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
