"""Merged table cells: how they are picked, merged, split, drawn, stepped over and stored."""

import re

import pytest
from pixels import LIMITS, measures, over, screen_and_print
from playwright.sync_api import expect
from test_unknown_values import watch
from ui import at, box, centre, doc, drag, pick, reload, sheet, thumb, user

from blattwerk import pdf

CELLS = [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]]
GRID = {
    "cells": CELLS,
    "cols": [1, 1, 1],
    "size": 14,
    "align": "center",
    "line": "#222222",
}
MERGED = {
    **GRID,
    "cells": [["a", "", "c"], ["", "", "f"], ["g", "h", "i"]],
    "spans": [[0, 0, 2, 2]],
}
# A span over cells that hold text: it is not applied.
FULL = {**GRID, "spans": [[0, 0, 2, 2]]}


def cell(page, name, n):
    return at(page, name).locator(f'.table > div[data-cell="{n}"]')


def field(page, name):
    return at(page, name).locator("textarea")


def open_cell(page, name, n):
    """Picks the table, then opens its cell n."""
    pick(page, name)
    cell(page, name, n).dblclick()
    expect(cell(page, name, n).locator("textarea")).to_be_focused()


def picked_cells(page, name):
    return (
        at(page, name)
        .locator(".table > div.picked")
        .evaluate_all("els => els.map((e) => Number(e.dataset.cell))")
    )


def props(page, client, name="t"):
    blocks = doc(page, client)["pages"][0]["blocks"]
    return next(b for b in blocks if b["id"] == name)["props"]


def merged_box_ok(page, name):
    """The merged cell is as wide as columns 1 and 2 and as high as rows 1 and 2."""
    big = cell(page, name, 0).bounding_box()
    width = (
        cell(page, name, 6).bounding_box()["width"] + cell(page, name, 7).bounding_box()["width"]
    )
    height = (
        cell(page, name, 2).bounding_box()["height"] + cell(page, name, 5).bounding_box()["height"]
    )
    assert abs(big["width"] - width) <= 1, (big["width"], width)
    assert abs(big["height"] - height) <= 1, (big["height"], height)


def print_page(browser, server, client, sheet_id):
    """The PDF's page of the sheet in a new window, once it has drawn."""
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.add_init_script("localStorage.setItem('tour', '1')")
    printed = context.new_page()
    printed.set_extra_http_headers({"X-Render-Token": pdf.new_token(sheet_id)})
    printed.goto(f"{server}/druck/{sheet_id}")
    printed.wait_for_selector("body.ready", state="attached")
    return context, printed


def test_drag_and_shift_click_pick_a_rectangle_of_cells(editor):
    page = editor(box("t", "table", GRID))
    start = at(page, "t").bounding_box()
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    assert picked_cells(page, "t") == [0, 1, 3, 4]
    expect(field(page, "t")).to_have_count(1)

    drag(page, centre(cell(page, "t", 4)), *[centre(cell(page, "t", 8))])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    assert picked_cells(page, "t") == [4, 5, 7, 8]
    assert at(page, "t").bounding_box() == start
    expect(field(page, "t")).to_have_count(1)


def test_verbinden_joins_the_texts_in_reading_order(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")
    assert props(page, client)["cells"] == [["a\nb\nd\ne", "", "c"], ["", "", "f"], ["g", "h", "i"]]
    assert props(page, client)["spans"] == [[0, 0, 2, 2]]
    for n in (1, 3, 4):
        expect(at(page, "t").locator(f'.table > div[data-cell="{n}"]')).to_have_count(0)

    # An empty cell among them adds no empty line.
    empty = {**GRID, "cells": [["a", "b", "c"], ["", "e", "f"], ["g", "h", "i"]]}
    again = editor(box("t", "table", empty), client=client)
    open_cell(again, "t", 0)
    cell(again, "t", 4).click(modifiers=["Shift"])
    again.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(cell(again, "t", 0)).to_have_attribute("data-span", "2x2")
    assert props(again, client)["cells"][0][0] == "a\nb\ne"


def test_menu_merges_and_splits(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    cell(page, "t", 4).click(button="right")
    expect(page.get_by_role("menu")).to_be_visible()
    page.get_by_role("menuitem", name="Zellen verbinden", exact=True).click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")
    assert props(page, client)["spans"] == [[0, 0, 2, 2]]

    cell(page, "t", 0).click(button="right")
    page.get_by_role("menuitem", name="Zellen teilen", exact=True).click()
    expect(at(page, "t").locator("[data-span]")).to_have_count(0)
    assert "spans" not in props(page, client)


def test_teilen_brings_the_cells_back(editor):
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zellen teilen", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    stored = props(page, client)
    assert "spans" not in stored
    assert stored["cells"][0][0] == "a"
    assert stored["cells"][0][1] == "" and stored["cells"][1][0] == ""
    assert stored["cells"][1][1] == ""


def test_a_merged_cell_spans_on_screen_thumb_and_pdf(editor, browser, server):
    client = user()
    # With the panel Seiten open, which holds the thumbnails.
    page = editor(box("t", "table", MERGED), client=client, theme="")
    merged_box_ok(page, "t")
    for n in (1, 3, 4):
        expect(at(page, "t").locator(f'.table > div[data-cell="{n}"]')).to_have_count(0)
    expect(thumb(page, 0).locator('[data-span="2x2"]')).to_have_count(1)

    context, printed = print_page(browser, server, client, page.url.rsplit("/", 1)[1])
    expect(printed.locator('[data-span="2x2"]')).to_have_count(1)
    context.close()


def test_a_cell_over_rows_shares_its_height(editor):
    tall = {
        **GRID,
        "cells": [["1\n2\n3\n4\n5\n6", "b", "c"], ["", "e", "f"], ["g", "h", "i"]],
        "spans": [[0, 0, 2, 1]],
    }
    client = user()
    page = editor(box("t", "table", tall, h=20), client=client)
    # A change of the table makes the block as high as its rows need.
    open_cell(page, "t", 8)
    page.keyboard.type("x")
    assert props(page, client)["cells"][2][2] == "ix"
    text = cell(page, "t", 0).locator("p")
    assert text.bounding_box()["height"] <= cell(page, "t", 0).bounding_box()["height"] + 1
    row = {n: cell(page, "t", n).bounding_box()["height"] for n in (2, 5, 6)}
    assert row[2] > row[6] and row[5] > row[6]
    assert abs(row[2] - row[5]) < 2


@pytest.mark.parametrize(
    "open_at, label, stored_spans, size",
    [
        # Through a row: the new row 1 lies inside the span.
        (5, "Zeile darüber", [[0, 0, 3, 2]], (4, 3)),
        (7, "Spalte links", [[0, 0, 2, 3]], (3, 4)),
        (2, "Zeile darüber", [[1, 0, 2, 2]], (4, 3)),
        (5, "Zeile löschen", [[0, 0, 1, 2]], (2, 3)),
        (7, "Spalte löschen", [[0, 0, 2, 1]], (3, 2)),
        # The span's first row and its first column: its text goes to the cell that starts it now.
        (2, "Zeile löschen", [[0, 0, 1, 2]], (2, 3)),
        (6, "Spalte löschen", [[0, 0, 2, 1]], (3, 2)),
    ],
)
def test_rows_and_columns_through_a_merged_cell(editor, open_at, label, stored_spans, size):
    client = user()
    # High enough that the handle in the middle of its lower edge lies below the last row's cells.
    page = editor(box("t", "table", MERGED, h=40), client=client)
    errors = watch(page)
    open_cell(page, "t", open_at)
    page.get_by_role("button", name=label, exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]").first).to_be_visible()
    stored = props(page, client)
    assert stored["spans"] == stored_spans
    for row in stored["cells"]:
        assert len(row) == len(stored["cols"])
    assert (len(stored["cells"]), len(stored["cols"])) == size
    # The merged cell keeps its text, whatever was cut.
    row, col = stored_spans[0][:2]
    assert stored["cells"][row][col] == "a"
    assert not errors, errors


def test_a_column_border_drags_through_a_merged_cell(editor):
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    pick(page, "t")
    handle = page.locator("i.bar").first
    mm = page.locator('.sheet[data-page="0"]').bounding_box()["width"] / 210
    x, y = centre(handle)
    drag(page, (x, y), (x + 20 * mm, y))
    stored = props(page, client)
    assert stored["cols"] != [1, 1, 1]
    assert sum(stored["cols"]) == 3
    assert stored["spans"] == [[0, 0, 2, 2]]
    merged_box_ok(page, "t")


def test_tab_and_arrows_step_over_a_merged_cell(editor):
    page = editor(box("t", "table", MERGED))
    open_cell(page, "t", 0)
    page.keyboard.press("Tab")
    expect(cell(page, "t", 2).locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    expect(cell(page, "t", 5).locator("textarea")).to_be_focused()
    page.keyboard.press("Tab")
    expect(cell(page, "t", 6).locator("textarea")).to_be_focused()
    page.keyboard.press("Shift+Tab")
    expect(cell(page, "t", 5).locator("textarea")).to_be_focused()

    cell(page, "t", 0).click()
    page.keyboard.press("ArrowDown")
    expect(cell(page, "t", 6).locator("textarea")).to_be_focused()
    page.keyboard.press("ArrowUp")
    expect(cell(page, "t", 0).locator("textarea")).to_be_focused()

    cell(page, "t", 2).click()
    page.keyboard.press("Home")
    page.keyboard.press("ArrowLeft")
    expect(cell(page, "t", 0).locator("textarea")).to_be_focused()

    cell(page, "t", 0).click()
    page.keyboard.press("End")
    page.keyboard.press("ArrowRight")
    expect(cell(page, "t", 2).locator("textarea")).to_be_focused()

    # A text that wraps into two shown lines keeps the arrow down inside its cell.
    long = {
        **GRID,
        "cols": [0.3, 1, 1],
        "cells": [
            ["Ein langer Text der in der schmalen Zelle umbricht", "b", "c"],
            ["d", "e", "f"],
            ["g", "h", "i"],
        ],
    }
    wrap = editor(box("w", "table", long))
    open_cell(wrap, "w", 0)
    wrap.keyboard.press("Control+Home")
    wrap.keyboard.press("ArrowDown")
    expect(cell(wrap, "w", 0).locator("textarea")).to_be_focused()
    # On its last shown line the arrow goes on to the cell below.
    wrap.keyboard.press("Control+End")
    wrap.keyboard.press("ArrowDown")
    expect(cell(wrap, "w", 3).locator("textarea")).to_be_focused()


def test_head_row_and_alignment_on_a_merged_cell(editor):
    client = user()
    page = editor(box("t", "table", {**MERGED, "head": True}), client=client)
    pick(page, "t")
    expect(cell(page, "t", 0)).to_have_css("font-weight", "700")
    expect(cell(page, "t", 6)).not_to_have_css("font-weight", "700")
    page.locator('button[aria-label="Links"][aria-pressed]').click()
    expect(cell(page, "t", 0)).to_have_css("text-align", re.compile("left|start"))
    assert props(page, client)["align"] == "left"


def test_an_old_table_is_stored_and_drawn_as_before(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    styles = (
        at(page, "t")
        .locator(".table > div[data-cell]")
        .evaluate_all("els => els.map((e) => e.getAttribute('style') || '')")
    )
    assert not any("grid-row" in s or "grid-column" in s for s in styles)
    expect(at(page, "t").locator("[data-span]")).to_have_count(0)
    open_cell(page, "t", 4)
    page.keyboard.type("x")
    stored = props(page, client)
    assert "spans" not in stored
    assert set(stored) == set(GRID)

    open_cell(page, "t", 8)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    cell(page, "t", 9).click()
    page.get_by_role("button", name="Zeile löschen", exact=True).click()
    assert "spans" not in props(page, client)


def test_merge_and_split_undo_and_redo_in_one_step(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 0)
    page.keyboard.type("x")
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")
    undo = page.get_by_label("Rückgängig", exact=True)
    redo = page.get_by_label("Wiederholen", exact=True)

    undo.click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    # The letter typed before the merge is a step of its own: it is still there.
    assert props(page, client)["cells"] == [["ax", "b", "c"], *CELLS[1:]]
    assert "spans" not in props(page, client)
    redo.click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")
    assert props(page, client)["cells"][0][0] == "ax\nb\nd\ne"

    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zellen teilen", exact=True).click()
    expect(at(page, "t").locator("[data-span]")).to_have_count(0)
    undo.click()
    expect(cell(page, "t", 0)).to_have_attribute("data-span", "2x2")
    assert props(page, client)["spans"] == [[0, 0, 2, 2]]
    redo.click()
    expect(at(page, "t").locator("[data-span]")).to_have_count(0)
    assert "spans" not in props(page, client)


def test_a_merged_table_prints_as_the_screen_shows_it(browser, server):
    client = user()
    both = {
        **GRID,
        "cells": [["a", "b", ""], ["", "e", "f"], ["g", "h", "i"]],
        "spans": [[0, 0, 2, 1], [0, 1, 1, 2]],
    }
    sheet_id = sheet(client, [box("t", "table", both, h=60)])["id"]
    screen, printed = screen_and_print(browser, server, client, sheet_id)
    found, _ = measures(screen, printed)
    assert not over(screen, printed), {name: found[name] for name in LIMITS}


def test_a_selection_grows_over_a_merged_cell(editor):
    page = editor(box("t", "table", MERGED))
    open_cell(page, "t", 2)
    cell(page, "t", 0).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(3)
    assert picked_cells(page, "t") == [0, 2, 5]

    cell(page, "t", 6).click()
    cell(page, "t", 5).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(6)
    assert picked_cells(page, "t") == [0, 2, 5, 6, 7, 8]


SPANS_BROKEN = [
    [[0, 0, 5, 5]],
    [[0, 0, 2, 2], [1, 1, 2, 2]],
    "x",
    [[0, 0, 2]],
    [[0, 0, 0, 2]],
    [[0.5, 0, 2, 2]],
    [None],
]


@pytest.mark.parametrize("spans", [*SPANS_BROKEN, FULL["spans"]])
def test_a_broken_span_is_not_applied(editor, server, spans):
    texts = {**GRID, "spans": spans}
    client = user()
    page = editor(box("t", "table", texts), client=client)
    errors = watch(page)
    for row in CELLS:
        for text in row:
            if text:
                expect(at(page, "t")).to_contain_text(text)
    assert not errors, errors
    address = f"{server}/api/sheets/{page.url.rsplit('/', 1)[1]}"
    reload(page, address)
    assert props(page, client)["spans"] == spans


def test_caret_after_merge_and_picked_after_split(editor):
    page = editor(box("t", "table", GRID))
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.get_by_role("button", name="Zellen verbinden", exact=True).click()
    expect(field(page, "t")).to_be_focused()
    expect(field(page, "t")).to_have_value("a\nb\nd\ne")
    page.keyboard.type("z")
    expect(field(page, "t")).to_have_value(re.compile("z"))

    page.get_by_role("button", name="Zellen teilen", exact=True).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
    assert picked_cells(page, "t") == [0, 1, 3, 4]


def test_the_selection_drops_and_the_buttons_know_when(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    verbinden = page.get_by_role("button", name="Zellen verbinden", exact=True)
    teilen = page.get_by_role("button", name="Zellen teilen", exact=True)
    open_cell(page, "t", 0)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    expect(teilen).to_have_attribute("aria-disabled", "true")
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(verbinden).not_to_have_attribute("aria-disabled", "true")

    # A plain click drops the selection.
    cell(page, "t", 6).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Tab")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.type("x")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    cell(page, "t", 0).click()
    cell(page, "t", 4).click(modifiers=["Shift"])
    page.keyboard.press("Escape")
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)

    # An arrow drops it too, whether it steps to the next cell or moves the caret in the text.
    for key in ("ArrowDown", "ArrowLeft"):
        open_cell(page, "t", 0)
        cell(page, "t", 4).click(modifiers=["Shift"])
        expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)
        page.keyboard.press(key)
        expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)
        page.keyboard.press("Escape")

    # A disabled button changes nothing.
    open_cell(page, "t", 0)
    before = props(page, client)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    # Playwright waits for a button that is off to come on, so the press is forced.
    verbinden.click(force=True)
    expect(field(page, "t")).to_be_focused()
    assert props(page, client) == before
    assert "spans" not in before


def test_teilen_is_off_in_a_plain_cell_and_on_in_a_merged_one(editor):
    page = editor(box("t", "table", GRID))
    open_cell(page, "t", 0)
    expect(page.get_by_role("button", name="Zellen teilen", exact=True)).to_have_attribute(
        "aria-disabled", "true"
    )
    page2 = editor(box("m", "table", MERGED))
    open_cell(page2, "m", 0)
    expect(page2.get_by_role("button", name="Zellen teilen", exact=True)).not_to_have_attribute(
        "aria-disabled", "true"
    )


def test_add_after_a_merged_cell_and_caret_after_delete(editor):
    client = user()
    page = editor(box("t", "table", MERGED), client=client)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]").first).to_be_visible()
    stored = props(page, client)
    assert stored["spans"] == [[0, 0, 2, 2]]
    assert stored["cells"][3][0] == "g"

    cell(page, "t", 0).click()
    page.get_by_role("button", name="Spalte rechts", exact=True).click()
    stored = props(page, client)
    assert len(stored["cols"]) == 4
    assert stored["cells"][0][3] == "c"
    assert stored["spans"] == [[0, 0, 2, 2]]

    other = editor(box("t", "table", MERGED), client=client)
    open_cell(other, "t", 0)
    other.get_by_role("button", name="Zeile löschen", exact=True).click()
    assert props(other, client)["spans"] == [[0, 0, 1, 2]]
    expect(at(other, "t").locator("textarea")).to_have_count(1)
    expect(at(other, "t").locator("textarea")).to_be_focused()
    assert props(other, client)["cells"][0][0] == "a"


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


def test_undo_drops_the_cells_picked(editor):
    """Undo may take the picked cells away with their row: none stays picked, and nothing throws."""
    client = user()
    page = editor(box("t", "table", GRID, h=40), client=client)
    errors = watch(page)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    cell(page, "t", 11).click(modifiers=["Shift"])
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(12)
    page.keyboard.press("Control+z")
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(9)
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(0)
    verbinden = page.get_by_role("button", name="Zellen verbinden", exact=True)
    expect(verbinden).to_have_attribute("aria-disabled", "true")
    verbinden.click(force=True)
    assert props(page, client)["cells"] == CELLS
    assert not errors, errors


def test_shift_click_in_the_open_cell_picks_text(editor):
    """As before merged cells: Shift+click in the field picks its text up to the click."""
    grid = {**GRID, "cells": [["hello world here", "b", "c"], *CELLS[1:]]}
    page = editor(box("t", "table", grid, w=150))
    open_cell(page, "t", 0)
    area = field(page, "t")
    area.evaluate("e => e.setSelectionRange(0, 0)")
    size = area.bounding_box()
    page.keyboard.down("Shift")
    page.mouse.click(size["x"] + size["width"] / 2 + 20, size["y"] + size["height"] / 2)
    page.keyboard.up("Shift")
    start, end = area.evaluate("e => [e.selectionStart, e.selectionEnd]")
    assert start == 0 and end > 0
    expect(area).to_be_focused()
