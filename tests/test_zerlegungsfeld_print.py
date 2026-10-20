"""The Zerlegungsfeld on screen and on paper: the given boxes, the empty boxes, the key in red, the note on a task
with more than one solution.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import box, user

ZF = {
    "count": 6,
    "columns": 3,
    "op": "+",
    "max": 20,
    "step": "zehner",
    "big": False,
    "task": "task",
    "seed": 7,
}
NOTE = "Auch andere Lösungen sind richtig."
MINUS = "\N{MINUS SIGN}"
H = 128.9  # the default height at 180 mm wide: 111 * 180 / 155
TYPED_FIRST = [[0, 0, 7], [0, 1, 6]]  # task 1: Erste Zahl 7, Zweite Zahl 6
TYPED_WRONG = [[0, 0, 10]]  # Erste Zahl 10: a multiple of ten makes no Zehnerübergang
TYPED_MANY = [[0, 2, 13], [0, 5, 10]]  # Ergebnis 13 and Zwischenergebnis 10: more than one task
GIVEN = {"task": {0, 1}, "split": {0, 1, 3, 4}, "result": {0, 2}}
# Each box of a task: its position and line, and the text it shows (None where empty).
BOXES = """els => els.map(g => {
    const t = g.querySelector('text');
    return {
        task: +g.closest('g.task').dataset.task,
        pos: +g.dataset.pos,
        line: +g.dataset.line,
        text: t ? t.textContent : null,
        answer: !!g.querySelector('text.answer'),
        given: !!g.querySelector('text.given'),
    };
})"""


def boxes(locator):
    """Each box of the locator's tasks, as BOXES reads it."""
    return locator.locator("g.box").evaluate_all(BOXES)


def values(locator, task):
    """The number at each position of one task (None where the box is empty), as the key shows it."""
    found = {}
    for item in boxes(locator):
        if item["task"] == task and item["text"] is not None:
            found[item["pos"]] = int(item["text"].replace(MINUS, "-"))
    return found


def given(locator):
    """Per task, the positions whose box shows a given number on the sheet."""
    out = {}
    for item in boxes(locator):
        if item["given"]:
            out.setdefault(item["task"], set()).add(item["pos"])
    return out


@pytest.mark.parametrize("op", ["+", "-"])
@pytest.mark.parametrize("task", ["task", "split", "result"])
def test_the_key_fills_every_box_and_every_task_keeps_the_rule(editor, browser, server, op, task):
    """Key (#827): the key fills every box of every task, and each task keeps the rule: Plus a + b = r, a + b1 = t,
    t + b2 = r; Minus a - b = r, a - b1 = t, t - b2 = r; b2 is at least 1."""
    page = editor(
        box("k", "zerlegungsfeld", {**ZF, "op": op, "task": task}, w=180, h=H), client=user()
    )
    paper = key_print(browser, server, sheet_id(page))
    grid = paper.locator(".zerlegungsfeld")
    # Every task has 11 boxes: 3 on line 0, 2 on line 1, 3 on line 2 and 3 on line 3.
    expect(grid.locator("g.box text")).to_have_count(6 * 11)
    for n in range(6):
        v = values(grid, n)
        assert set(v) == {0, 1, 2, 3, 4, 5}, (n, v)
        a, b, r, b1, b2, t = (v[p] for p in range(6))
        if op == "+":
            assert a + b == r, v
            assert a + b1 == t, v
            assert t + b2 == r, v
        else:
            assert a - b == r, v
            assert a - b1 == t, v
            assert t - b2 == r, v
        assert b2 >= 1, v
    paper.context.close()


@pytest.mark.parametrize("task", ["task", "split", "result"])
def test_the_pupils_sheet_shows_only_the_given_positions(editor, browser, server, task):
    """Sheet (#827): the pupils' page shows exactly the given positions of each Aufgabentyp and no answer; the key
    shows the empty boxes in red."""
    page = editor(box("k", "zerlegungsfeld", {**ZF, "task": task}, w=180, h=H), client=user())
    paper = printed(browser, server, sheet_id(page))
    shown = given(paper.locator(".zerlegungsfeld"))
    assert set(shown) == set(range(6))
    assert all(positions == GIVEN[task] for positions in shown.values()), shown
    expect(paper.locator(".zerlegungsfeld text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zerlegungsfeld text.answer")).not_to_have_count(0)
    paper.context.close()


def test_the_print_has_the_numbers_the_teacher_typed(editor, browser, server):
    """Eigene Zahlen (#827): the printed pupils' sheet shows the typed numbers in their boxes: Erste Zahl 7 and
    Zweite Zahl 6 in task 1."""
    page = editor(
        box("k", "zerlegungsfeld", {**ZF, "typed": TYPED_FIRST}, w=180, h=H), client=user()
    )
    paper = printed(browser, server, sheet_id(page))
    shown = given(paper.locator(".zerlegungsfeld"))
    assert {0, 1} <= shown[0]
    texts = {
        item["pos"]: item["text"]
        for item in boxes(paper.locator(".zerlegungsfeld"))
        if item["task"] == 0 and item["given"]
    }
    assert texts[0] == "7" and texts[1] == "6", texts
    paper.context.close()


def test_a_wrong_typed_task_shows_no_answer_in_the_key(editor, browser, server):
    """Eigene Zahlen (#827): a task whose typed numbers do not fit shows no answer in the key, and its boxes stay
    empty: never a false number."""
    page = editor(
        box("k", "zerlegungsfeld", {**ZF, "typed": TYPED_WRONG}, w=180, h=H), client=user()
    )
    paper = key_print(browser, server, sheet_id(page))
    grid = paper.locator(".zerlegungsfeld")
    # Only the typed a = 10 shows, in its two boxes (line 0 and the first step on line 2); no other number.
    expect(grid.locator("g.task[data-task='0'] g.box text")).to_have_text(["10", "10"])
    expect(grid.locator("g.task[data-task='0'] text.answer")).to_have_count(0)
    paper.context.close()


def test_the_note_shows_only_on_a_typed_task_with_many_solutions(editor, browser, server):
    """Key (#827): the note "Auch andere Lösungen sind richtig." shows under the one task with typed numbers that
    allow more than one solution, and under no other task and on no drawn sheet."""
    page = editor(
        box("k", "zerlegungsfeld", {**ZF, "typed": TYPED_MANY}, w=180, h=H), client=user()
    )
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zerlegungsfeld text.note")).to_have_count(1)
    expect(paper.locator(".zerlegungsfeld text.note").first).to_have_text(NOTE)
    paper.context.close()
    plain = editor(box("p", "zerlegungsfeld", ZF, w=180, h=H), client=user())
    paper = key_print(browser, server, sheet_id(plain))
    expect(paper.locator(".zerlegungsfeld text.note")).to_have_count(0)
    paper.context.close()
