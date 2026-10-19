"""The Rechentabelle on screen and on paper: the given cells, the empty cells, the key in red.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

RT = {
    "count": 2,
    "columns": 2,
    "rows": 4,
    "cols": 4,
    "op": "+",
    "max": 20,
    "seed": 7,
}
DIV = ":"
RED = "rgb(192, 57, 43)"
NOTE = "Auch andere Lösungen sind richtig."
H = 84.22  # the default height: 51 * 180 / 109, rounded as insert.ts does
# Each cell or head: its table, its row and column, its number (None when it has no text), whether it is
# an answer and whether it is struck through.
CELLS = """els => els.map(g => {
    const t = g.querySelector('text.given, text.answer');
    return {
        head: g.tagName === 'g' && g.classList.contains('head'),
        table: +g.closest('g.table').dataset.table,
        row: +g.dataset.row,
        col: +g.dataset.col,
        number: t ? Number(t.textContent) : null,
        answer: !!g.querySelector('text.answer'),
        strike: !!g.querySelector('line.strike'),
    };
})"""


def apply(op, x, y):
    """The number that x op y gives, with Geteilt as whole division."""
    return {"+": x + y, "-": x - y, "*": x * y, DIV: x // y}[op]


def back_row(op, cell, col):
    """The row value that a cell gives with its column value, worked back from the cell."""
    return {"+": cell - col, "-": cell + col, "*": cell // col, DIV: cell * col}[op]


def back_col(op, cell, row):
    """The column value that a cell gives with its row value, worked back from the cell."""
    return {"+": cell - row, "-": row - cell, "*": cell // row, DIV: row // cell}[op]


def items(locator):
    """Each cell and head of the locator's Rechentabellen, as CELLS reads it."""
    return locator.locator("g.head, g.cell").evaluate_all(CELLS)


def tables(found):
    """The items grouped by table: the row values, the column values and the result cells."""
    out = {}
    for item in found:
        group = out.setdefault(item["table"], {"rows": {}, "cols": {}, "cells": {}})
        if item["head"] and item["col"] == 0:
            group["rows"][item["row"]] = item
        elif item["head"] and item["row"] == 0:
            group["cols"][item["col"]] = item
        else:
            group["cells"][(item["row"], item["col"])] = item
    return out


def places(found):
    """The items by their place: table, head or cell, row and column."""
    return {(i["table"], i["head"], i["row"], i["col"]): i for i in found}


def fill_colours(paper):
    return paper.locator(".rechentabelle text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )


def test_the_pupils_sheet_shows_only_the_given_cells(editor, browser, server):
    """The pupils' page shows the given cells and values only, no text.answer; the key shows the
    empty cells and the hidden values in red."""
    client = user()
    page = editor(box("k", "rechentabelle", RT, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".rechentabelle text.given")).not_to_have_count(0)
    expect(paper.locator(".rechentabelle text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechentabelle text.answer")).not_to_have_count(0)
    paper.context.close()


def test_the_key_fills_every_empty_cell_and_every_hidden_head_in_red(editor, browser, server):
    """The key fills each empty cell and each hidden head in red; no cell is left blank without a strike."""
    client = user()
    page = editor(box("k", "rechentabelle", RT, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    found = items(paper.locator(".rechentabelle"))
    colours = fill_colours(paper)
    paper.context.close()
    blank = [i for i in found if i["number"] is None and not i["strike"]]
    assert not blank, blank
    assert colours, "the key has no answer"
    assert colours == [RED] * len(colours)


@pytest.mark.parametrize("op", ["+", "-", "*", ":"], ids=["plus", "minus", "mal", "geteilt"])
def test_on_the_key_every_cell_equals_row_op_column(editor, browser, server, op):
    """On the key, each cell is its row value worked with its column value. A struck Geteilt cell has
    no text on the key and no whole answer; a cell that is not struck is the row value divided by the
    column value."""
    client = user()
    page = editor(box("k", "rechentabelle", {**RT, "op": op}, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    found = tables(items(paper.locator(".rechentabelle")))
    paper.context.close()
    assert len(found) == RT["count"]
    for table in found.values():
        assert len(table["rows"]) == RT["rows"]
        assert len(table["cols"]) == RT["cols"]
        for (i, j), cell in table["cells"].items():
            row = table["rows"][i]["number"]
            col = table["cols"][j]["number"]
            assert row is not None and col is not None, (i, j)
            if cell["strike"]:
                assert op == DIV, (i, j)
                assert cell["number"] is None, (i, j)
                assert row % col != 0, (i, j, row, col)
            else:
                assert cell["number"] == apply(op, row, col), (i, j, row, col)


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print and the key show the editor's numbers in the same cells and heads."""
    client = user()
    page = editor(box("k", "rechentabelle", RT, w=180, h=H), client=client)
    shown = items(at(page, "k").locator(".rechentabelle"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_items = items(paper.locator(".rechentabelle"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = items(paper.locator(".rechentabelle"))
    paper.context.close()
    assert len(printed_items) <= len(shown) and len(key) == len(shown)
    editor_at = places(shown)
    compared = 0
    for paper_items in (printed_items, key):
        for place, item in places(paper_items).items():
            # The editor may leave some numbers out, so compare where both show one.
            if item["number"] is not None and editor_at[place]["number"] is not None:
                assert item["number"] == editor_at[place]["number"], place
                compared += 1
    assert compared, "no number to compare"


def test_a_wrong_typed_table_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: table 0 has 9999 in cell row 1, column 1, which no row and column value gives. On the key that
    table is marked wrong and shows no answer; table 1 keeps its answers."""
    client = user()
    typed = {**RT, "typed": [[0, 1, 1, 9999]]}
    page = editor(box("k", "rechentabelle", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechentabelle g.table[data-table='0'].wrong")).to_have_count(1)
    expect(paper.locator(".rechentabelle g.table[data-table='0'] text.answer")).to_have_count(0)
    expect(paper.locator(".rechentabelle g.table[data-table='1'] text.answer")).not_to_have_count(0)
    paper.context.close()


def test_the_key_never_has_the_other_answers_note(editor, browser, server):
    """Other answers: a Rechentabelle has one right answer per empty cell, so the key never carries the
    note "Auch andere Lösungen sind richtig.", with Mal and with each Rechenart."""
    client = user()
    page = editor(
        box("m", "rechentabelle", {**RT, "op": "*"}, w=180, h=H),
        box("x", "rechentabelle", {**RT, "op": ":"}, w=180, h=H, y=150),
        client=client,
    )
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechentabelle")).to_have_count(2)
    expect(paper.get_by_text(NOTE)).to_have_count(0)
    paper.context.close()


@pytest.mark.parametrize("op", ["+", "-", "*"], ids=["plus", "minus", "mal"])
def test_with_hidden_values_the_key_works_them_back(editor, browser, server, op):
    """Hidden: with 2 row values and 2 column values hidden, each hidden value is a red head on the key,
    and the given cell in its row gives it back: row value = given cell (op back) column value."""
    client = user()
    hidden = {**RT, "op": op, "hideRows": 2, "hideCols": 2}
    page = editor(box("k", "rechentabelle", hidden, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    found = tables(items(paper.locator(".rechentabelle")))
    paper.context.close()
    assert len(found) == RT["count"]
    for table in found.values():
        hidden_rows = [i for i, h in table["rows"].items() if h["answer"]]
        hidden_cols = [j for j, h in table["cols"].items() if h["answer"]]
        assert len(hidden_rows) == 2, table["rows"]
        assert len(hidden_cols) == 2, table["cols"]
        for i in hidden_rows:
            given = [(j, c) for (r, j), c in table["cells"].items() if r == i and not c["answer"]]
            assert given, i
            for j, cell in given:
                col = table["cols"][j]["number"]
                assert back_row(op, cell["number"], col) == table["rows"][i]["number"], (i, j)
        for j in hidden_cols:
            given = [(i, c) for (i, r), c in table["cells"].items() if r == j and not c["answer"]]
            assert given, j
            for i, cell in given:
                row = table["rows"][i]["number"]
                assert back_col(op, cell["number"], row) == table["cols"][j]["number"], (i, j)


def test_a_struck_geteilt_cell_has_no_text_on_the_sheet_or_the_key(editor, browser, server):
    """Geteilt: a cell with no whole answer is struck through and has no number, on the pupils' sheet and
    on the key alike; the struck cells are the same on both."""
    client = user()
    page = editor(box("k", "rechentabelle", {**RT, "op": DIV}, w=180, h=H), client=client)
    struck = {}
    for label, make in (("sheet", printed), ("key", key_print)):
        paper = make(browser, server, sheet_id(page))
        found = items(paper.locator(".rechentabelle"))
        paper.context.close()
        cells = [i for i in found if not i["head"] and i["strike"]]
        assert all(i["number"] is None for i in cells), label
        struck[label] = {(i["table"], i["row"], i["col"]) for i in cells}
    assert struck["sheet"], "no struck cell"
    assert struck["sheet"] == struck["key"]
