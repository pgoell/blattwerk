"""A number typed into a Rechentabelle: the column, a cell that does not fit, and the hint.

The helpers live in test_rechentabelle.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import re

from playwright.sync_api import expect
from test_gaps import panel, step
from test_rechentabelle import (
    RT,
    editor,  # noqa: F401
    field,
    props_of,
    rt,
    values,
)
from test_words import undo
from ui import at, doc, pick, user


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def test_typing_a_column_value_is_one_undo_step_and_changes_the_column(editor):
    """Eigene Zahlen: typing 7 into "Spaltenwert 1" stores [0, 0, 1, 7], the column shows 7, and one Ctrl+Z in the field takes it back."""
    client = user()
    page = editor(rt("d", RT), client=client)
    pick(page, "d")
    number = field(page, "Spaltenwert 1")
    number.click()
    step(page, lambda: page.keyboard.type("7"))
    assert props_of(doc(page, client))["typed"] == [[0, 0, 1, 7]]
    assert values(page, "col")[0] == 7
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_a_box_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """Eigene Zahlen: typing "17" into "Zeile 1, Spalte 3" keeps the focus and the digits, and stores [0, 1, 3, 17]."""
    client = user()
    page = editor(rt("d", RT), client=client)
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 1, 3, 17]]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_a_typed_cell_that_does_not_fit_gives_the_hint_and_marks_the_table_wrong(editor):
    """Eigene Zahlen: a typed 9999 in row 1, column 1 does not fit its row and column: the hint names Rechentabelle 1 and that table gets class wrong."""
    page = editor(rt("d", {**RT, "typed": [[0, 1, 1, 9999]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechentabelle 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.table.wrong")).to_have_count(1)
    expect(at(page, "d").locator("g.table[data-table='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one Ctrl+Z brings them back."""
    client = user()
    typed = [[0, 1, 1, 9999]]
    page = editor(rt("d", {**RT, "typed": typed}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed
    expect(hint(page)).to_have_count(1)


def test_a_typed_zero_column_with_geteilt_is_wrong_and_shows_no_nan_or_infinity(editor):
    """Eigene Zahlen: with Geteilt a typed column value 0 gives the hint, marks the table wrong, and the drawing has no "NaN" or "Infinity"."""
    page = editor(rt("d", {**RT, "op": ":", "typed": [[0, 0, 1, 0]]}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechentabelle 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.table[data-table='0'].wrong")).to_have_count(1)
    text = at(page, "d").locator(".rechentabelle svg").text_content()
    assert "NaN" not in text and "Infinity" not in text, text


def test_a_typed_column_that_strikes_a_hidden_rows_clue_marks_the_table_wrong(editor):
    """Eigene Zahlen: with Geteilt, one hidden row value and a typed column value 7 that leaves no whole answer for it: the hint names Rechentabelle 1 and the table gets class wrong."""
    page = editor(
        rt("d", {**RT, "op": ":", "count": 1, "hideRows": 1, "seed": 1, "typed": [[0, 0, 1, 7]]})
    )
    pick(page, "d")
    expect(hint(page)).to_have_text("Rechentabelle 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.table.wrong")).to_have_count(1)


def test_the_box_shows_the_number_the_sheet_uses_when_stored_entries_repeat(editor):
    """Eigene Zahlen (review of #930): with two stored entries for one box the field shows the last one, as the sheet takes it; with a typed 12000 (out of range, dropped) the field shows the cell the sheet works out, row plus column, and no "Eigene Zahlen entfernen" button is left."""
    page = editor(rt("d", {**RT, "typed": [[0, 1, 1, 5], [0, 1, 1, 7]]}))
    pick(page, "d")
    expect(field(page, "Zeile 1, Spalte 1")).to_have_value("7")
    page = editor(rt("d", {**RT, "typed": [[0, 1, 1, 12000]]}))
    pick(page, "d")
    number = field(page, "Zeile 1, Spalte 1")
    expect(number).to_have_value(re.compile(r"^\d+$"))
    value = number.input_value()
    assert value != "12000", value
    table = at(page, "d").locator("g.table[data-table='0']")
    row = int(table.locator("g.head[data-row='1'][data-col='0'] text").text_content())
    col = int(table.locator("g.head[data-row='0'][data-col='1'] text").text_content())
    assert int(value) == row + col
    expect(panel(page, "Eigene Zahlen entfernen")).to_have_count(0)
