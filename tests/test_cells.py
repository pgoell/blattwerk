"""Merged table cells: how they are picked, merged, split, drawn, stepped over and stored."""

from playwright.sync_api import expect
from ui import at, box, centre, doc, drag, unpick, user

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
    unpick(page)
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


SPANS_BROKEN = [
    [[0, 0, 5, 5]],
    [[0, 0, 2, 2], [1, 1, 2, 2]],
    "x",
    [[0, 0, 2]],
    [[0, 0, 0, 2]],
    [[0.5, 0, 2, 2]],
    [None],
]
