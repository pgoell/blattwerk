"""Copy, paste and a gap in a merged cell.

The table helpers live in test_cells.py."""

from playwright.sync_api import expect
from test_cells import (
    GRID,
    MERGED,
    cell,
    open_cell,
    props,
)
from ui import (
    at,
    box,
    doc,
    pick,
    user,
)


def test_a_merged_gap_cell(editor):
    client = user()
    gapped = {**GRID, "gaps": [[True, True, False], [False] * 3, [False] * 3], "bank": 1}
    page = editor(box("t", "table", gapped), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 1).click(modifiers=["Shift"])
    page.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "1x2")
    assert props(page, client)["gaps"][0] == [True, False, False]
    expect(cell(page, "t", 0).locator(".gap")).to_have_count(1)
    expect(at(page, "t").locator(".bank span")).to_have_count(1)


def test_copy_keeps_the_merged_cells(editor):
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    pick(page, "t")
    page.keyboard.press("Control+d")
    expect(page.locator('[data-span="2x2"]')).to_have_count(2)
    tables = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "table"]
    assert len(tables) == 2
    assert tables[0]["props"]["spans"] == tables[1]["props"]["spans"]


def test_copy_and_paste_keeps_the_merged_cells(editor):
    """Ctrl+C, Ctrl+V of a table with merged cells keeps the merged cells (Asked 13)."""
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    pick(page, "t")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block")).to_have_count(2)
    tables = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "table"]
    assert len(tables) == 2
    assert tables[0]["props"]["spans"] == tables[1]["props"]["spans"]
    assert tables[0]["props"]["cells"] == tables[1]["props"]["cells"]
    expect(page.locator('[data-span="2x2"]')).to_have_count(2)
