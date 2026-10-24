"""A number typed into an Operatorfeld: the links, the hint, and taking the numbers back.

The helpers live in test_operatorfeld.py.
"""

# The fixture is imported, and each test names it as its argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_gaps import panel, step
from test_operatorfeld import (
    OF,
    editor,  # noqa: F401
    field,
    given_numbers,
    hint,
    of,
    op_labels,
    props_of,
)
from test_words import undo
from ui import at, doc, pick, user


def test_typing_a_number_into_a_box_changes_the_labels_of_its_links_in_one_undo(editor):
    """Eigene Zahlen: typing 12 into "Zahl in Kästchen 1" stores [[0, 0, 12]], the links at that box change their
    operators, and one Ctrl+Z removes both."""
    client = user()
    page = editor(of("d", OF), client=client)
    pick(page, "d")
    before = op_labels(page)
    number = field(page, "Zahl in Kästchen 1")

    def type_twelve():
        number.press("Control+a")
        number.press_sequentially("1")
        number.press_sequentially("2")

    step(page, type_twelve)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 12]]
    assert given_numbers(page)[0] == 12
    assert op_labels(page) != before
    number.press("Control+z")
    assert "typed" not in props_of(doc(page, client))
    assert op_labels(page) == before


def test_a_box_field_keeps_focus_and_digits_while_the_block_redraws(editor):
    """Eigene Zahlen: typing "17" into "Zahl in Kästchen 3" keeps the focus and the digits, and stores [0, 2, 17]."""
    client = user()
    page = editor(of("d", OF), client=client)
    pick(page, "d")
    number = field(page, "Zahl in Kästchen 3")
    number.click()
    step(page, lambda: page.keyboard.type("17"))
    expect(number).to_be_focused()
    expect(number).to_have_value("17")
    assert props_of(doc(page, client))["typed"] == [[0, 2, 17]]


def test_mit_zentrum_names_the_centre_field_first(editor):
    """Eigene Zahlen: with Mit Zentrum the first input is "Zahl im Zentrum", and it stores box 0."""
    client = user()
    page = editor(of("d", {**OF, "centre": True}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Zahl im Zentrum").fill("9"))
    assert props_of(doc(page, client))["typed"] == [[0, 0, 9]]


def test_a_typed_box_that_breaks_the_operators_gives_the_hint_and_marks_the_field_wrong(editor):
    """Eigene Zahlen: with Mal only, box 1 typed 9999 against box 0 typed 5 fits no operator: the hint says so and the field is marked wrong."""
    client = user()
    page = editor(of("d", {**OF, "ops": ["*"], "typed": [[0, 0, 5], [0, 1, 9999]]}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_text("Operatorfeld 1: kein Operator passt zu diesen Zahlen.")
    expect(at(page, "d").locator("g.field[data-field='0'].wrong")).to_have_count(1)


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen: "Eigene Zahlen entfernen" clears every typed number in one step; one Ctrl+Z brings them back."""
    client = user()
    typed = [[0, 0, 5], [0, 1, 8]]
    page = editor(of("d", {**OF, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed
