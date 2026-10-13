"""A table keeps what was set when its columns or rows change, and goes back to its height when its
text goes. Issue 517 is the columns, issue 520 the height.
"""

from test_cells import GRID, cell, open_cell
from test_sizes import H, W, block, mm_height, num, typed, widths_mm
from ui import box, pick, user


def test_a_set_column_width_holds_when_a_column_is_added_right(editor):
    """Issue 517: a column set to 40 mm stays 40 mm when a column comes to its right, and the block
    grows by the average width."""
    client = user()
    page = editor(box("t", "table", GRID, w=W), client=client)
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


def test_a_table_goes_back_when_its_long_text_is_deleted(editor):
    """Issue 520: a table of 30 mm, grown by a long text, goes back to 30 mm, rows as they were."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 4)
    page.keyboard.type(" ".join(f"wort{n}" for n in range(25)))
    assert block(page, client)["h"] > H + 20
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    back = block(page, client)
    assert abs(back["h"] - H) <= 0.05
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - H) <= 0.05
    for n, was in zip((0, 3, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_table_made_taller_by_hand_goes_back_to_that_height(editor):
    """Issue 520: a table of 60 mm with no rows set, grown by a long text, goes back to 60 mm."""
    client = user()
    page = editor(box("t", "table", GRID, h=60), client=client)
    open_cell(page, "t", 4)
    page.keyboard.type(" ".join(f"wort{n}" for n in range(25)))
    assert block(page, client)["h"] > 60
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 60) <= 0.05
