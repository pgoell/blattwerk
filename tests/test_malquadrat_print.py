"""The Malquadrat on screen and on paper: the given cells, the empty cells, the key in red, the note on a square
with free numbers.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, pick, user

MQ = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "op": "*",
    "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
    "max": 20,
    "task": "factors",
    "seed": 7,
}
NOTE = "Auch andere Lösungen sind richtig."
TYPED_WRONG = [[0, 0, 1, 2], [0, 1, 0, 3], [0, 1, 1, 7]]
TYPED_FREE = [[0, 0, 1, 3], [0, 1, 1, 12]]
TYPED_ONE = [
    [0, 1, 0, 5],
    [0, 1, 3, 16],
    [0, 3, 1, 19],
    [0, 3, 2, 11],
]  # one solution: columns 5 and 1, rows 5 and 4
H = 93.98  # the default height for the block at 180 mm wide; the drawing does not depend on it
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


def full(found, size):
    """The numbers of each square as a grid of (size + 2) by (size + 2); None where a position has no number.
    Row 0 holds the column numbers, column 0 the row numbers, the last row and column the sums and the total."""
    out = {}
    for item in found:
        grid = out.setdefault(item["square"], [[None] * (size + 2) for _ in range(size + 2)])
        grid[item["row"]][item["col"]] = item["number"]
    return out


@pytest.mark.parametrize("task", ["factors", "mixed", "knobel"])
def test_the_pupils_sheet_shows_only_the_given_cells(editor, browser, server, task):
    """Sheet (#826): the pupils' page shows the given cells only, no text.answer; the key shows the empty cells in
    red."""
    client = user()
    page = editor(box("k", "malquadrat", {**MQ, "task": task}, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat text.given")).not_to_have_count(0)
    expect(paper.locator(".malquadrat text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat text.answer")).not_to_have_count(0)
    paper.context.close()


@pytest.mark.parametrize("op", ["*", "+"])
@pytest.mark.parametrize("task", ["factors", "knobel"])
def test_the_key_fills_every_empty_cell_and_every_sum_and_the_total_add_up(
    editor, browser, server, op, task
):
    """Key (#826): the key shows a number in every cell; each inner cell is row number op column number, each row
    and column sum adds up, and the total is the sum of the row sums and of the column sums."""
    client = user()
    page = editor(box("k", "malquadrat", {**MQ, "op": op, "task": task}, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    found = cells(paper.locator(".malquadrat"))
    paper.context.close()
    assert not [i for i in found if i["number"] is None], "a cell has no number"
    assert any(i["answer"] for i in found), "the key has no answer"
    apply = (lambda a, b: a * b) if op == "*" else (lambda a, b: a + b)
    n = 3
    for square, grid in full(found, n).items():
        for i in range(1, n + 1):
            for j in range(1, n + 1):
                assert grid[i][j] == apply(grid[i][0], grid[0][j]), (square, i, j, grid)
            assert grid[i][n + 1] == sum(grid[i][1 : n + 1]), (square, i, grid)
        for j in range(1, n + 1):
            assert grid[n + 1][j] == sum(grid[i][j] for i in range(1, n + 1)), (square, j, grid)
        total = grid[n + 1][n + 1]
        assert total == sum(grid[i][n + 1] for i in range(1, n + 1)), (square, grid)
        assert total == sum(grid[n + 1][j] for j in range(1, n + 1)), (square, grid)


def test_the_key_has_the_other_answers_note_only_on_a_typed_square_with_free_numbers(
    editor, browser, server
):
    """Other answers (#826): square 0 has typed numbers that leave some free, so the key carries "Auch andere
    Lösungen sind richtig." on it; square 1 is drawn and has no note."""
    client = user()
    typed = {**MQ, "size": 2, "typed": TYPED_FREE}
    page = editor(box("k", "malquadrat", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat g.square[data-square='0'] text.note")).to_have_text(NOTE)
    expect(paper.locator(".malquadrat g.square[data-square='1'] text.note")).to_have_count(0)
    paper.context.close()


def test_the_key_note_lies_within_the_width_of_its_own_square(editor, browser, server):
    """Other answers (#826): with the narrowest square (size 2) and typed numbers that leave some free, the key's
    note of each square lies inside the width of that square's cells, so that the two notes do not overlap."""
    client = user()
    typed = {**MQ, "size": 2, "typed": TYPED_FREE}
    page = editor(box("k", "malquadrat", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    notes = paper.locator(".malquadrat g.square").evaluate_all(
        """els => els.filter(g => g.querySelector('text.note')).map(g => {
            const note = g.querySelector('text.note').getBoundingClientRect();
            const rects = [...g.querySelectorAll('g.cell rect')].map(r => r.getBoundingClientRect());
            const left = Math.min(...rects.map(r => r.left));
            const right = Math.max(...rects.map(r => r.right));
            return note.left >= left - 0.5 && note.right <= right + 0.5;
        })"""
    )
    assert notes, "the key has no note"
    assert all(notes)
    paper.context.close()


def test_a_wrong_typed_square_shows_no_answer_in_the_key(editor, browser, server):
    """Typed (#826): a square whose typed numbers fit no Malquadrat shows no answer in the key; the other square
    keeps its answers."""
    client = user()
    typed = {**MQ, "typed": TYPED_WRONG}
    page = editor(box("k", "malquadrat", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat g.square[data-square='0'].wrong")).to_have_count(1)
    expect(paper.locator(".malquadrat g.square[data-square='0'] text.answer")).to_have_count(0)
    expect(paper.locator(".malquadrat g.square[data-square='1'] text.answer")).not_to_have_count(0)
    paper.context.close()


def test_typed_numbers_win_also_outside_the_reihen_and_the_key_works_out_from_them(
    editor, browser, server
):
    """Typed (#826): typed numbers win over the seed, also a column number 37 outside the Reihen and above max 20;
    the square is not wrong, the sheet shows the 37, and the key's inner cells, sums and total add up from it."""
    client = user()
    typed = [[0, 0, 1, 37], [0, 1, 1, 74]]
    page = editor(box("k", "malquadrat", {**MQ, "typed": typed}, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(
        paper.locator(".malquadrat g.square[data-square='0'] text.given", has_text="37")
    ).to_have_count(1)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat g.square[data-square='0'].wrong")).to_have_count(0)
    found = cells(paper.locator(".malquadrat g.square[data-square='0']"))
    paper.context.close()
    n = 3
    grid = full(found, n)[0]
    assert grid[0][1] == 37, grid
    assert grid[1][1] == 74, grid
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            assert grid[i][j] == grid[i][0] * grid[0][j], (i, j, grid)
        assert grid[i][n + 1] == sum(grid[i][1 : n + 1]), (i, grid)
    total = grid[n + 1][n + 1]
    assert total == sum(grid[i][n + 1] for i in range(1, n + 1)), grid


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """Print (#826): the print and the key show the editor's numbers in the same cells."""
    client = user()
    page = editor(box("k", "malquadrat", MQ, w=180, h=H), client=client)
    shown = {
        (i["square"], i["row"], i["col"]): i["number"]
        for i in cells(at(page, "k").locator(".malquadrat"))
    }
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_items = cells(paper.locator(".malquadrat"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = cells(paper.locator(".malquadrat"))
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


def test_a_typed_square_with_one_solution_has_no_note_and_no_hint(editor, browser, server):
    """One solution (#954): a typed square that fixes one solution has no "Auch andere Lösungen" note in the key and
    no hint in the panel, and is neither marked many nor wrong; the key shows that one solution."""
    client = user()
    typed = {**MQ, "op": "+", "size": 2, "count": 1, "typed": TYPED_ONE}
    page = editor(box("k", "malquadrat", typed, w=180, h=H), client=client, theme="")
    pick(page, "k")
    expect(page.locator(".panel")).to_be_visible()
    expect(page.locator(".panel p.hint[role=status]")).to_have_count(0)
    expect(at(page, "k").locator("g.square.many")).to_have_count(0)
    expect(at(page, "k").locator("g.square.wrong")).to_have_count(0)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".malquadrat text.note")).to_have_count(0)
    grid = full(cells(paper.locator(".malquadrat")), 2)[0]
    paper.context.close()
    assert grid[0][1:3] == [5, 1], grid
    assert [grid[1][0], grid[2][0]] == [5, 4], grid
    assert [grid[1][1], grid[1][2], grid[2][1], grid[2][2]] == [10, 6, 9, 5], grid
