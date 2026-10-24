"""How a merged cell spans on the sheet, in the thumb and on the PDF.

The table helpers live in test_cells.py."""

import re

import pytest
from pixels import (
    LIMITS,
    measures,
    over,
    screen_and_print,
)
from playwright.sync_api import expect
from test_cells import (
    CELLS,
    FULL,
    GRID,
    MERGED,
    SPANS_BROKEN,
    cell,
    merged_box_ok,
    open_cell,
    print_page,
    props,
)
from test_unknown_values import watch
from ui import (
    at,
    box,
    centre,
    drag,
    pick,
    reload,
    sheet,
    thumb,
    user,
)


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
