"""Typed numbers in a Malquadrat: what they replace, when the square is wrong, and the hint.

The helpers live in test_malquadrat.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import re

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_malquadrat import (
    MQ,
    editor,  # noqa: F401
    field,
    mq,
    props_of,
)
from test_words import undo
from ui import at, doc, pick, user

TYPED_WRONG = [
    [0, 0, 1, 2],
    [0, 1, 0, 3],
    [0, 1, 1, 7],
]  # column 1 = 2, row 1 = 3, cell (1, 1) = 7 is no 3 x 2


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def test_typing_a_number_is_one_undo_step_and_the_box_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#826): typing "12" into "Zeile 1, Spalte 3" keeps the focus and both digits while the block
    redraws, stores a typed entry, and one Ctrl+Z in the box takes the whole number back."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 3")
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    assert [0, 1, 3, 12] in props_of(doc(page, client))["typed"]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_the_first_typed_number_keeps_the_drawn_given_numbers_as_typed_entries(editor):
    """Eigene Zahlen (#826): the first number typed into an empty box stores the square's drawn given cells as typed
    entries too, so the typed entries are the drawn given numbers + 1."""
    client = user()
    page = editor(mq("d", MQ), client=client)
    pick(page, "d")
    drawn = at(page, "d").locator("g.square[data-square='0'] text.given").count()
    boxes = page.locator(".panel").get_by_label(re.compile(r"^Zeile \d+, Spalte \d+$"))
    empty = next(b for b in boxes.all() if b.input_value() == "")
    empty.click()
    step(page, lambda: page.keyboard.type("1"))
    assert len(props_of(doc(page, client))["typed"]) == drawn + 1


def test_a_stored_entry_at_no_position_does_not_stop_the_drawn_numbers_being_kept(editor):
    """Eigene Zahlen (#826): an entry at row 5, column 5 of a 3 by 3 (no position, from the MCP say) plays no part, so
    the first number typed still keeps the drawn given numbers."""
    client = user()
    page = editor(mq("d", {**MQ, "typed": [[0, 5, 5, 9]]}), client=client)
    pick(page, "d")
    drawn = at(page, "d").locator("g.square[data-square='0'] text.given").count()
    assert drawn > 0
    boxes = page.locator(".panel").get_by_label(re.compile(r"^Zeile \d+, Spalte \d+$"))
    empty = next(b for b in boxes.all() if b.input_value() == "")
    empty.click()
    step(page, lambda: page.keyboard.type("1"))
    assert len(props_of(doc(page, client))["typed"]) == drawn + 2


def test_typed_numbers_win_and_the_square_works_out_from_them(editor):
    """Eigene Zahlen (#826): column number 1 = 3 and inner cell (1, 1) = 12 leave more than one way (the square is
    not fixed), so the hint says "Es gibt mehr als eine Lösung." for Malquadrat 1, and the square is not wrong."""
    typed = [[0, 0, 1, 3], [0, 1, 1, 12]]
    page = editor(mq("d", {**MQ, "typed": typed}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Es gibt mehr als eine Lösung.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(0)


def test_typed_numbers_that_do_not_fit_give_the_hint_and_mark_the_square_wrong(editor):
    """Eigene Zahlen (#826): column number 1 = 2, row number 1 = 3 and cell (1, 1) = 7 fit no square: the hint names
    Malquadrat 1 and that square gets class wrong."""
    page = editor(mq("d", {**MQ, "typed": TYPED_WRONG}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.square[data-square='0'].wrong")).to_have_count(1)


@pytest.mark.parametrize(
    ("op", "size", "typed", "many", "extra"),
    [
        # Plus 2 by 2 with only the total 2: row and column numbers 1, 0 and 0, 0 fit.
        pytest.param("+", 2, [[0, 3, 3, 2]], True, {}, id="plus-total"),
        # Mal 2 by 2 with only the total 7 and row sum 1 is 7: rows 1 and 0, columns 7 and 0 fit.
        pytest.param("*", 2, [[0, 3, 3, 7], [0, 1, 3, 7]], True, {}, id="mal-total-and-row-sum"),
        # Mal 3 by 3 with the cells of one row and one column sum far from the first tries: 3 * 40 = 120, 3 * 50 = 150,
        # column 1 sum 120 + 2 * 40 = 200 with rows 3, 1 and 1.
        pytest.param(
            "*", 3, [[0, 1, 1, 120], [0, 1, 2, 150], [0, 4, 1, 200]], True, {}, id="mal-far"
        ),
        # The issue 951 steps: Größe 4 by 4, Mal, these four numbers; the hint may say "mehr als eine Lösung" or not show.
        pytest.param(
            "*",
            4,
            [[0, 4, 1, 198], [0, 4, 2, 99], [0, 5, 2, 495], [0, 5, 3, 1100]],
            False,
            {},
            id="issue-951-mal-4",
        ),
        # The issue 951 steps: Größe 3, Plus, max 1000, these five numbers.
        pytest.param(
            "+",
            3,
            [[0, 1, 0, 148], [0, 1, 4, 997], [0, 3, 3, 390], [0, 3, 4, 613], [0, 4, 1, 718]],
            False,
            {"max": 1000},
            id="issue-951-plus-3",
        ),
        # The issue 951 steps: Größe 4, Plus, these four numbers.
        pytest.param(
            "+",
            4,
            [[0, 1, 3, 32], [0, 1, 5, 120], [0, 5, 2, 152], [0, 5, 3, 120]],
            False,
            {},
            id="issue-951-plus-4",
        ),
    ],
)
def test_typed_numbers_that_fit_give_no_wrong_hint(editor, op, size, typed, many, extra):
    """Eigene Zahlen (#826, #951): typed numbers that fit some Malquadrat never give "Die Zahlen passen nicht zusammen";
    the square says there is more than one solution instead, or no hint at all. The #951 cases are sets the check
    wrongly called unfit."""
    page = editor(mq("d", {**MQ, "op": op, "size": size, "count": 1, "typed": typed, **extra}))
    pick(page, "d")
    if many:
        expect(hint(page)).to_have_text("Malquadrat 1: Es gibt mehr als eine Lösung.")
    else:
        expect(page.get_by_text("Die Zahlen passen nicht zusammen")).to_have_count(0)
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(0)


def test_a_plus_set_that_does_not_fit_gives_the_hint_and_marks_the_square_wrong(editor):
    """Eigene Zahlen (#826, #951): Plus 2 by 2, column 1 = 4 and column 2 = 5 leave no square (2 · f1 + G = 4 and
    2 · f2 + G = 5 cannot both hold): the hint names Malquadrat 1 and that square gets class wrong."""
    typed = [[0, 3, 1, 4], [0, 3, 2, 5]]
    page = editor(mq("d", {**MQ, "op": "+", "size": 2, "count": 1, "typed": typed}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Malquadrat 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.square.wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen (#826): "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z
    brings them back."""
    client = user()
    page = editor(mq("d", {**MQ, "typed": TYPED_WRONG}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == TYPED_WRONG
    expect(hint(page)).to_have_count(1)


def test_typed_entries_of_a_square_that_is_gone_stay_stored(editor):
    """Typed (#826): with 2 squares and typed numbers for square 1, "Ein Malquadrat weniger" leaves the block with one
    square and the typed entry for the gone square is still stored."""
    client = user()
    typed = [[0, 1, 1, 5], [1, 1, 1, 7]]
    page = editor(mq("d", {**MQ, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Malquadrat weniger").click())
    props = props_of(doc(page, client))
    assert props["count"] == 1
    assert [1, 1, 1, 7] in props["typed"]
