"""Numbers typed into a Halbschriftlich task, and the undo step that types one.

The helpers live in test_halbschriftlich.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_halbschriftlich import (
    NOTE,
    editor,  # noqa: F401
    field,
    hal,
    hint,
    props_of,
    values,
)
from test_suchsel_print import key_print
from test_words import undo
from ui import (
    at,
    doc,
    pick,
    user,
)


def test_typed_numbers_win_and_the_rest_is_worked_out(editor, browser, server):
    """Eigene Zahlen (#828): typed a and b give the task's r and steps; the drawn task of that place is replaced."""
    page = editor(hal(props={"count": 2, "typed": [[0, 0, 345], [0, 1, 103]]}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    assert values(loc, 0, 0) == {0: 345, 1: 103, 2: 448}
    paper.context.close()


def test_one_typed_number_says_there_is_more_than_one_solution(editor, browser, server):
    """Eigene Zahlen (#828): one typed number gives many solutions: the panel says "Es gibt mehr als eine Lösung." and
    the key says "Auch andere Lösungen sind richtig."."""
    page = editor(hal(props={"count": 1, "typed": [[0, 0, 5]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text("Aufgabe 1: Es gibt mehr als eine Lösung.")
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".halbschriftlich text.note")).to_have_text(NOTE)
    paper.context.close()


def test_a_fully_fixed_typed_task_has_no_note(editor, browser, server):
    """Eigene Zahlen (#828): a typed a, b and r that fix the task (one solution) show no hint and no note in the key."""
    page = editor(hal(props={"count": 1, "typed": [[0, 0, 345], [0, 1, 103], [0, 2, 448]]}))
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".halbschriftlich text.note")).to_have_count(0)
    paper.context.close()


def test_typed_numbers_that_do_not_fit_give_the_hint_and_no_answer_in_the_key(
    editor,
    browser,
    server,
):
    """Eigene Zahlen (#828): Minus with a 5 and b 9 does not fit (a minus b is below 0): the hint says "Aufgabe 1: Die Zahlen passen
    nicht zusammen.", the task is marked wrong and its key shows no answer."""
    page = editor(hal(props={"op": "-", "count": 1, "typed": [[0, 0, 5], [0, 1, 9]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text("Aufgabe 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "k").locator("g.task[data-task='0'].wrong")).to_have_count(1)
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    assert values(loc, 0, 0) == {0: 5, 1: 9}
    assert values(loc, 0, 1) == {}
    paper.context.close()


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen (#828): "Eigene Zahlen entfernen" drops the typed numbers and the hint in one undo step."""
    client = user()
    page = editor(hal(props={"count": 1, "typed": [[0, 0, 5]]}), client=client)
    pick(page, "k")
    expect(hint(page)).to_be_visible()
    step(
        page, lambda: page.get_by_role("button", name="Eigene Zahlen entfernen", exact=True).click()
    )
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 5]]


def test_typing_a_number_is_one_undo_step_and_the_box_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#828): typing "12" into "Erste Zahl" keeps the focus and both digits while the block redraws,
    stores a typed entry, and one Ctrl+Z in the box takes the whole number back."""
    client = user()
    page = editor(hal(), client=client)
    pick(page, "k")
    number = field(page, "Erste Zahl")
    drawn_b = field(page, "Zweite Zahl").input_value()
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    typed = props_of(doc(page, client))["typed"]
    # The first number typed keeps the drawn second number as a typed entry, so the sheet still shows it.
    assert [0, 0, 12] in typed and [0, 1, int(drawn_b)] in typed
    expect(field(page, "Zweite Zahl")).to_have_value(drawn_b)
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_rechenart_change_drops_typed_in_one_undo_step(editor):
    """Eigene Zahlen (#828): a change of Rechenart drops the typed numbers in the same undo step."""
    client = user()
    page = editor(hal(props={"typed": [[0, 0, 7]]}), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Rechenart").select_option(label="Minus"))
    stored = props_of(doc(page, client))
    assert stored["op"] == "-" and "typed" not in stored
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 7]]


def test_typed_entries_of_a_task_that_is_gone_stay_stored(editor):
    """Eigene Zahlen (#828): with fewer tasks, the typed entries of a task that is gone stay stored and play no part."""
    client = user()
    page = editor(hal(props={"typed": [[5, 0, 12]]}), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eine Aufgabe weniger").click())
    stored = props_of(doc(page, client))
    assert stored["count"] == 5
    assert [5, 0, 12] in stored["typed"]
