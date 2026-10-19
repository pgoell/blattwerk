"""The Magisches Quadrat on screen and on paper: the given cells, the empty cells, the key in red.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

MQ = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "max": 20,
    "given": 4,
    "showSum": False,
    "seed": 7,
}
RED = "rgb(192, 57, 43)"
NOTE = "Auch andere Lösungen sind richtig."
TYPED_WRONG = [[0, 1, 1, 1], [0, 1, 2, 2], [0, 1, 3, 3], [0, 2, 1, 5], [0, 3, 1, 9]]
H = 96.52  # the default height for the block at 180 mm wide; the drawing does not depend on it
# Each cell of a square: its square, its row and column, its number (None when it has no text), whether it is
# an answer.
CELLS = """els => els.map(g => {
    const t = g.querySelector('text.given, text.answer');
    return {
        square: +g.closest('g.square').dataset.square,
        row: +g.dataset.row,
        col: +g.dataset.col,
        number: t ? Number(t.textContent) : null,
        answer: !!g.querySelector('text.answer'),
    };
})"""


def cells(locator):
    """Each cell of the locator's squares, as CELLS reads it."""
    return locator.locator("g.cell").evaluate_all(CELLS)


def grids(found, size):
    """The numbers of each square as a list of rows, size by size; None where a cell has no number."""
    out = {}
    for item in found:
        grid = out.setdefault(item["square"], [[None] * size for _ in range(size)])
        grid[item["row"] - 1][item["col"] - 1] = item["number"]
    return out


def fill_colours(paper):
    return paper.locator(".magischesquadrat text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )


@pytest.mark.parametrize("size", [3, 5], ids=["3x3", "5x5"])
def test_the_pupils_sheet_shows_only_the_given_cells(editor, browser, server, size):
    """Sheet (#825): the pupils' page shows the given cells only, no text.answer; the key shows the empty cells in
    red."""
    client = user()
    page = editor(box("k", "magischesquadrat", {**MQ, "size": size}, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".magischesquadrat text.given")).not_to_have_count(0)
    expect(paper.locator(".magischesquadrat text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".magischesquadrat text.answer")).not_to_have_count(0)
    paper.context.close()


@pytest.mark.parametrize("size", [3, 5], ids=["3x3", "5x5"])
def test_the_key_fills_every_empty_cell_in_red_and_every_line_sums_to_the_same(
    editor, browser, server, size
):
    """Key (#825): the key fills every empty cell in red, and every row, column and both diagonals of each square sum
    to the same number."""
    client = user()
    page = editor(box("k", "magischesquadrat", {**MQ, "size": size}, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    found = cells(paper.locator(".magischesquadrat"))
    colours = fill_colours(paper)
    paper.context.close()
    blank = [i for i in found if i["number"] is None]
    assert not blank, blank
    empty = [i for i in found if not i["answer"] and i["number"] is not None]
    assert colours, "the key has no answer"
    assert colours == [RED] * len(colours)
    assert len(colours) == sum(1 for i in found if i["answer"])
    assert empty, "the given cells are all missing"
    for square, grid in grids(found, size).items():
        lines = [sum(row) for row in grid]
        lines += [sum(grid[r][c] for r in range(size)) for c in range(size)]
        lines += [
            sum(grid[i][i] for i in range(size)),
            sum(grid[i][size - 1 - i] for i in range(size)),
        ]
        assert len(set(lines)) == 1, (square, grid)


def test_with_show_sum_the_sheet_and_the_key_show_the_sum_and_it_is_the_row_sum(
    editor, browser, server
):
    """Zielzahl (#825): with showSum the key and the sheet show text.sum "Zielzahl: S", and S is the sum of each row
    of the key."""
    client = user()
    page = editor(box("k", "magischesquadrat", {**MQ, "showSum": True}, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".magischesquadrat text.sum")).to_have_count(2)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    sums = paper.locator(".magischesquadrat g.square[data-square='0'] text.sum")
    expect(sums).to_have_count(1)
    total = int(sums.text_content().removeprefix("Zielzahl: "))
    found = cells(paper.locator(".magischesquadrat g.square[data-square='0']"))
    paper.context.close()
    grid = grids(found, 3)[0]
    assert all(sum(row) == total for row in grid), (total, grid)


@pytest.mark.parametrize(
    "given, note",
    [(2, True), (4, False)],
    ids=["zwei-gegeben", "vier-gegeben"],
)
def test_the_key_has_the_other_answers_note_only_with_too_few_given(
    editor, browser, server, given, note
):
    """Other answers (#825): with 2 given cells (3 x 3) the key carries "Auch andere Lösungen sind richtig."; with 4 it
    has no note."""
    client = user()
    page = editor(box("k", "magischesquadrat", {**MQ, "given": given}, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    if note:
        expect(paper.locator(".magischesquadrat text.note", has_text=NOTE)).not_to_have_count(0)
    else:
        expect(paper.locator(".magischesquadrat text.note")).to_have_count(0)
    paper.context.close()


def test_a_wrong_typed_square_shows_no_answer_and_no_sum_in_the_key(editor, browser, server):
    """Typed (#825): a square whose typed numbers fit no magic square shows no answer in the key and no text.sum; the
    other square keeps its answers."""
    client = user()
    typed = {**MQ, "showSum": True, "typed": TYPED_WRONG}
    page = editor(box("k", "magischesquadrat", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".magischesquadrat g.square[data-square='0'].wrong")).to_have_count(1)
    expect(paper.locator(".magischesquadrat g.square[data-square='0'] text.answer")).to_have_count(
        0
    )
    expect(paper.locator(".magischesquadrat g.square[data-square='0'] text.sum")).to_have_count(0)
    expect(
        paper.locator(".magischesquadrat g.square[data-square='1'] text.answer")
    ).not_to_have_count(0)
    paper.context.close()


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """Print (#825): the print and the key show the editor's numbers in the same cells."""
    client = user()
    page = editor(box("k", "magischesquadrat", MQ, w=180, h=H), client=client)
    shown = {
        (i["square"], i["row"], i["col"]): i["number"]
        for i in cells(at(page, "k").locator(".magischesquadrat"))
    }
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_items = cells(paper.locator(".magischesquadrat"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = cells(paper.locator(".magischesquadrat"))
    paper.context.close()
    assert len(key) == len(shown)
    compared = 0
    for paper_items in (printed_items, key):
        for item in paper_items:
            place = (item["square"], item["row"], item["col"])
            if item["number"] is not None and shown.get(place) is not None:
                assert item["number"] == shown[place], place
                compared += 1
    assert compared, "no number to compare"
