"""The Zehnerfeld block on paper: the pupils' sheet and the answer key (#829, the print and key lines).

The numbers are read from the printed page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import box, pick

ZEH = {
    "count": 4,
    "columns": 2,
    "field": "zwanzig",
    "op": "+",
    "task": "dots",
    "max": 20,
    "cross": "any",
    "lines": True,
    "colors": "color",
    "manual": False,
    "seed": 7,
}
MINUS = "\N{MINUS SIGN}"
NOTE = "Auch andere Lösungen sind richtig."


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zehnerfeld settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zeh(props=None):
    return box("k", "zehnerfeld", {**ZEH, **(props or {})}, w=127, h=53)


def marks(paper, task):
    """The data-mark of each dot of a task on the printed page, in dot order."""
    return paper.locator(f".zehnerfeld g.task[data-task='{task}'] circle.dot").evaluate_all(
        "els => els.map(e => +e.dataset.mark)"
    )


def numbers(paper, task):
    """The number at each position of a task's line 0 on the printed page."""
    found = paper.locator(f".zehnerfeld g.task[data-task='{task}'] g.slot text").evaluate_all(
        "els => els.map(t => [t.closest('g.slot').dataset.pos, t.textContent])"
    )
    return {int(pos): int(text.replace(MINUS, "-")) for pos, text in found}


def test_the_key_fills_a_b_and_r_of_every_dots_task_and_the_sheet_leaves_them_empty(
    editor, browser, server
):
    """Key (#829): the key fills a, b and r of every "dots" task; the pupils' sheet leaves the numbers empty."""
    page = editor(zeh())
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    for task in range(4):
        assert numbers(sheet, task) == {}
    sheet.context.close()
    paper = key_print(browser, server, sheet_id(page))
    for task in range(4):
        top = numbers(paper, task)
        assert set(top) == {0, 1, 2}, top
        assert top[0] + top[1] == top[2], top
    paper.context.close()


def test_the_print_draws_the_same_dots_as_the_screen(editor, browser, server):
    """Print (#829): the pupils' sheet draws the same dots, with the same marks, as the editor's drawing."""
    page = editor(zeh({"count": 2}))
    pick(page, "k")
    on_screen = (
        page.locator(".zehnerfeld")
        .first.locator("circle.dot")
        .evaluate_all("els => els.map(e => +e.dataset.mark)")
    )
    sheet = printed(browser, server, sheet_id(page))
    assert marks(sheet, 0) + marks(sheet, 1) == on_screen
    sheet.context.close()


def test_a_wrong_typed_task_has_no_answer_in_the_key(editor, browser, server):
    """Key (#829): a typed task that does not fit shows no dots and no answer in the key."""
    page = editor(zeh({"count": 1, "typed": [[0, 0, 15], [0, 1, 9]]}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    assert numbers(paper, 0) == {}
    assert all(m == 0 for m in marks(paper, 0))
    paper.context.close()


@pytest.mark.parametrize("op", ["+", "-"])
def test_no_task_ever_has_the_note_about_other_solutions(editor, browser, server, op):
    """Key (#829): every task shows a and b, so the key never says "Auch andere Lösungen sind richtig."."""
    page = editor(zeh({"op": op, "count": 6}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.get_by_text(NOTE)).to_have_count(0)
    paper.context.close()


def test_a_minus_task_prints_the_minus_sign(editor, browser, server):
    """Print (#829): Minus prints U+2212 in the task line of the key."""
    page = editor(zeh({"op": "-", "count": 1}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zehnerfeld text.op").first).to_have_text(MINUS)
    paper.context.close()
