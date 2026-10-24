"""Operators typed into a Pfeilbild: each field, undo, and a hint when they do not fit.

The helpers live in test_pfeilbild.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_pfeilbild import (
    DOT,
    MINUS,
    PF,
    back_labels,
    editor,  # noqa: F401
    field,
    hint,
    op_labels,
    pfeil,
    props_of,
)
from test_words import undo
from ui import at, doc, pick, tool, user


def type_op(field_op, text):
    """Replaces the text of an operator field with text, one key at a time."""
    field_op.press("Control+a")
    field_op.press_sequentially(text)


def test_eigene_operatoren_each_keystroke_stores_but_one_ctrl_z_takes_all_back(editor):
    """Eigene Operatoren: "+", "1", "2" into "Operator an Pfeil 2" store +1 then +12 as one undo step; one Ctrl+Z removes typedOps, Ctrl+Y gives [[0, 1, "+", 12]] back."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    step(
        page,
        lambda: (
            type_op(op_field, "+"),
            op_field.press_sequentially("1"),
            op_field.press_sequentially("2"),
        ),
    )
    assert props_of(doc(page, client))["typedOps"] == [[0, 1, "+", 12]]
    op_field.press("Control+z")
    assert "typedOps" not in props_of(doc(page, client))
    op_field.press("Control+y")
    assert props_of(doc(page, client))["typedOps"] == [[0, 1, "+", 12]]


@pytest.mark.parametrize(
    "text, op, n",
    [(DOT + "2", "*", 2), ("x2", "*", 2), (":2", ":", 2), ("/2", ":", 2), ("4", "+", 4)],
    ids=["mid-dot", "x", "colon", "slash", "bare-digits"],
)
def test_eigene_operatoren_spellings_store_the_normalised_op(editor, text, op, n):
    """Eigene Operatoren: the middle dot 2 and "x2" store "*", ":2" and "/2" store ":", a bare "4" stores "+", all on arrow 1."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, ""), op_field.press_sequentially(text)))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, op, n]]


def test_eigene_operatoren_a_sign_alone_keeps_focus_and_stores_nothing(editor):
    """Eigene Operatoren: a minus sign alone keeps the focus and its text and stores nothing; after blur the field shows the drawn label again."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    op_field.click()
    type_op(op_field, MINUS)
    expect(op_field).to_be_focused()
    expect(op_field).to_have_value(MINUS)
    assert "typedOps" not in props_of(doc(page, client))
    op_field.evaluate("el => el.blur()")
    expect(op_field).to_have_value(op_labels(page)[1])


def test_eigene_zahlen_entfernen_clears_typed_and_typed_ops_in_one_undo_step(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears the typed numbers and the typed operators in one step; one Ctrl+Z brings both back."""
    client = user()
    typed = [[0, 0, 5], [0, 1, 8]]
    typed_ops = [[0, 1, "-", 3]]
    page = editor(pfeil("d", {**PF, "typed": typed, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    props = props_of(doc(page, client))
    assert "typed" not in props and "typedOps" not in props
    undo(page)
    props = props_of(doc(page, client))
    assert props["typed"] == typed
    assert props["typedOps"] == typed_ops


def test_neu_wuerfeln_keeps_the_typed_operators(editor):
    """Eigene Operatoren: "Neu würfeln" stores another seed and keeps typedOps as they are."""
    client = user()
    typed_ops = [[0, 1, "-", 3]]
    page = editor(pfeil("d", {**PF, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Neu würfeln").click())
    props = props_of(doc(page, client))
    assert props["seed"] != PF["seed"]
    assert props["typedOps"] == typed_ops


def test_typed_ops_that_cannot_fit_the_zahlenraum_give_their_own_hint(editor):
    """Eigene Operatoren: three plus 9 at bis 10 cannot fit; the hint says the Operatoren do not fit the Zahlenraum, and picture 1 is marked wrong once."""
    client = user()
    typed_ops = [[0, 0, "+", 9], [0, 1, "+", 9], [0, 2, "+", 9]]
    page = editor(pfeil("d", {**PF, "max": 10, "typedOps": typed_ops}), client=client)
    pick(page, "d")
    expect(hint(page).filter(has_text="Pfeilbild 1:")).to_have_text(
        "Pfeilbild 1: die Operatoren passen nicht in den Zahlenraum."
    )
    expect(at(page, "d").locator("g.picture[data-picture='0'].wrong")).to_have_count(1)


def test_eigene_operatoren_two_fields_are_two_undo_steps(editor):
    """Eigene Operatoren: "+2" into Pfeil 1 then "+3" into Pfeil 2 are two steps; one Ctrl+Z leaves only [[0, 0, "+", 2]]."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    first = field(page, "Operator an Pfeil 1")
    second = field(page, "Operator an Pfeil 2")
    step(page, lambda: (type_op(first, "+"), first.press_sequentially("2")))
    step(page, lambda: (type_op(second, "+"), second.press_sequentially("3")))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 2], [0, 1, "+", 3]]
    undo(page)
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 2]]


def test_eigene_operatoren_with_pfeile_both_show_the_back_arrow_inverse(editor):
    """Eigene Operatoren: with Pfeile both, the middle dot 2 into Pfeil 1 draws the forward "·2" and the back arrow ":2"."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100, "arrows": "both"}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, DOT), op_field.press_sequentially("2")))
    assert back_labels(page)[0] == ":2"
    assert op_labels(page)[0] == DOT + "2"


def test_eigene_operatoren_ctrl_z_in_the_field_shows_the_undone_operator(editor):
    """Eigene Operatoren: Ctrl+Z inside the field after "+5" shows the text from before, and the field keeps focus."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    before = op_field.input_value()
    step(page, lambda: (type_op(op_field, "+"), op_field.press_sequentially("5")))
    op_field.press("Control+z")
    expect(op_field).to_have_value(before)
    expect(op_field).to_be_focused()


def test_eigene_operatoren_a_click_selects_the_whole_text(editor):
    """Eigene Operatoren: a click on "Operator an Pfeil 1" selects its whole text, so "7" alone replaces it and stores [[0, 0, "+", 7]] (no Control+a)."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 1")
    op_field.click()
    step(page, lambda: op_field.press_sequentially("7"))
    assert props_of(doc(page, client))["typedOps"] == [[0, 0, "+", 7]]


def test_eigene_operatoren_field_keeps_focus_and_text_while_the_block_redraws(editor):
    """Eigene Operatoren: typing "+1" then "2" keeps the focus, and the field shows "+12" while the block redraws."""
    client = user()
    page = editor(pfeil("d", {**PF, "max": 100}), client=client)
    pick(page, "d")
    op_field = field(page, "Operator an Pfeil 2")
    op_field.click()
    step(
        page,
        lambda: (
            type_op(op_field, "+"),
            op_field.press_sequentially("1"),
            op_field.press_sequentially("2"),
        ),
    )
    expect(op_field).to_be_focused()
    expect(op_field).to_have_value("+12")


def test_a_typed_operator_against_the_typed_numbers_gives_the_hint_and_no_key(editor):
    """Eigene Operatoren: boxes 5 and 7 typed, "+3" typed between them: the hint says the numbers do
    not fit the operators, the picture is marked wrong, and the key shows no answer for it."""
    client = user()
    props = {**PF, "typed": [[0, 0, 5], [0, 1, 7]], "typedOps": [[0, 0, "+", 3]]}
    page = editor(pfeil("d", props), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Pfeilbild 1: die Zahlen passen nicht zu den Operatoren.")
    first = at(page, "d").locator("g.picture[data-picture='0']")
    expect(first).to_have_class("picture wrong")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "d").locator("g.picture[data-picture='1'] text.answer").first).to_be_attached()
    expect(first.locator("text.answer")).to_have_count(0)


def test_eigene_operatoren_of_pfeilbild_2_store_under_picture_1(editor):
    """Eigene Operatoren: with Pfeilbild 2 picked, "-" then "3" into "Operator an Pfeil 1" store [1, 0, "-", 3]."""
    client = user()
    page = editor(pfeil("d", PF), client=client)
    pick(page, "d")
    field(page, "Pfeilbild für eigene Zahlen").select_option("1")
    op_field = field(page, "Operator an Pfeil 1")
    step(page, lambda: (type_op(op_field, "-"), op_field.press_sequentially("3")))
    assert props_of(doc(page, client))["typedOps"] == [[1, 0, "-", 3]]
