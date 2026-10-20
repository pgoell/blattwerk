"""The Halbschriftlich block on paper: the pupils' sheet and the answer key (#828, the print and key lines).

The numbers are read from the printed page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_halbschriftlich import MINUS, NOTE, hal, step_count, values
from test_suchsel_print import key_print
from ui import pick


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Halbschriftlich settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def line_of(paper, task, line):
    """The digits of one line of one task on the printed page."""
    return values(paper.locator(".halbschriftlich"), task, line)


def test_the_key_keeps_the_path_from_a_to_r_through_every_step(editor, browser, server):
    """Key (#828): the key shows the full path: step j ends where step j + 1 starts, the first step starts at a and
    the last step ends at r, in every drawn task."""
    page = editor(hal())
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    for task in range(6):
        last = step_count(loc, task)
        assert last >= 1
        top = line_of(paper, task, 0)
        assert line_of(paper, task, 1)[0] == top[0]
        for line in range(1, last):
            assert line_of(paper, task, line)[2] == line_of(paper, task, line + 1)[0]
        assert line_of(paper, task, last)[2] == top[2]
    paper.context.close()


def test_the_pupils_sheet_shows_only_a_and_b_of_a_typed_task(editor, browser, server):
    """Print (#828): a typed a and b print on the pupils' sheet; the result and the steps stay empty, the key fills them."""
    page = editor(hal(props={"count": 1, "typed": [[0, 0, 345], [0, 1, 103]]}))
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    assert line_of(sheet, 0, 0) == {0: 345, 1: 103}
    assert line_of(sheet, 0, 1) == {}
    sheet.context.close()
    paper = key_print(browser, server, sheet_id(page))
    assert line_of(paper, 0, 0) == {0: 345, 1: 103, 2: 448}
    paper.context.close()


def test_the_key_fills_every_box_of_every_drawn_task_and_the_sheet_leaves_the_result_empty(
    editor, browser, server
):
    """Key (#828): the key fills every number box of every drawn task; the pupils' sheet leaves the results empty."""
    page = editor(hal())
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    for task in range(6):
        assert 2 not in line_of(sheet, task, 0)
    sheet.context.close()
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        top = line_of(paper, task, 0)
        assert set(top) == {0, 1, 2}, top
        assert top[0] + top[1] == top[2], top
    paper.context.close()


@pytest.mark.parametrize("op", ["+", "-"])
def test_the_key_of_each_drawn_task_keeps_the_rule_and_the_steps_add_or_take_away(
    editor, browser, server, op
):
    """Key (#828): each drawn task keeps the rule: Plus r = a + b ≤ 9999, Minus r = a minus b ≥ 0, and every step adds
    or takes away its part."""
    page = editor(hal(props={"op": op}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    for task in range(6):
        a, b, r = (line_of(paper, task, 0)[p] for p in (0, 1, 2))
        if op == "+":
            assert a >= 1 and b >= 1 and r == a + b and r <= 9999, (a, b, r)
        else:
            assert a >= 1 and b >= 1 and r == a - b and r >= 0, (a, b, r)
        for line in range(1, step_count(loc, task) + 1):
            s = line_of(paper, task, line)
            if op == "+":
                assert s[0] + s[1] == s[2], s
            else:
                assert s[0] - s[1] == s[2], s
    paper.context.close()


def test_the_step_signs_leave_the_pupils_sheet_when_the_print_option_is_off(
    editor, browser, server
):
    """Print (#828): with "Rechenzeichen der Schritte drucken" off, the pupils' sheet keeps the sign of each task line
    only; the key still shows the signs of every step."""
    page = editor(hal(props={"ops": False, "count": 2}))
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    assert sheet.locator(".halbschriftlich text.op").count() == 2
    sheet.context.close()
    paper = key_print(browser, server, sheet_id(page))
    assert paper.locator(".halbschriftlich text.op").count() > 2
    paper.context.close()


def test_a_minus_task_prints_the_minus_sign(editor, browser, server):
    """Print (#828): Minus prints U+2212 in the task line and in the key's step lines."""
    page = editor(hal(props={"op": "-", "count": 1}))
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    expect(sheet.locator(".halbschriftlich text.op").first).to_have_text(MINUS)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".halbschriftlich text.op").last).to_have_text(MINUS)
    paper.context.close()
    sheet.context.close()


def test_a_wrong_typed_task_shows_no_answer_in_the_key(editor, browser, server):
    """Key (#828): a typed task that does not fit shows its typed numbers only; the key has no answer for it."""
    page = editor(hal(props={"op": "-", "count": 1, "typed": [[0, 0, 5], [0, 1, 9]]}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    assert line_of(paper, 0, 0) == {0: 5, 1: 9}
    paper.context.close()


def test_the_key_of_a_no_task_setting_is_empty(editor, browser, server):
    """Key (#828): with no task (Plus, bis 1000, einstellig, Einer "ohne", Zehner "mit Übergang"), the printed key
    has no answer text."""
    page = editor(hal(props={"digits": 1, "einer": "no", "zehner": "yes"}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".halbschriftlich text")).to_have_count(0)
    paper.context.close()


def test_the_note_shows_only_on_a_typed_task_with_many_solutions(editor, browser, server):
    """Key (#828): "Auch andere Lösungen sind richtig." shows in the key's note row of a task with many solutions and
    of no other task."""
    page = editor(hal(props={"count": 2, "typed": [[0, 0, 5]]}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    notes = paper.locator(".halbschriftlich text.note")
    expect(notes).to_have_count(1)
    expect(notes).to_have_text(NOTE)
    paper.context.close()
