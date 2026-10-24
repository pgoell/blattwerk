"""Numbers a teacher types into a Zerlegungsfeld, and the panel steps around them."""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import undo
from test_zerlegungsfeld import (
    NOTE,
    TYPED_FIRST,
    TYPED_MANY,
    TYPED_WRONG,
    ZF,
    block_of,
    field,
    given_positions,
    hint,
    props_of,
    values,
    zf,
)
from test_zerlegungsfeld import editor as editor
from ui import at, doc, pick, reload, user


def test_typing_a_number_is_one_undo_step_and_the_box_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#827): typing "12" into "Erste Zahl" keeps the focus and both digits while the block redraws,
    stores a typed entry, and one Ctrl+Z in the box takes the whole number back."""
    client = user()
    page = editor(zf("d", ZF), client=client)
    pick(page, "d")
    number = field(page, "Erste Zahl")
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    assert [0, 0, 12] in props_of(doc(page, client))["typed"]
    step(page, lambda: number.press("Control+z"))
    assert "typed" not in props_of(doc(page, client))


def test_rechenart_uebergang_and_zahlenraum_changes_drop_typed_in_one_undo_step(editor):
    """Panel (#827): a change of Rechenart, of Übergang or a Zahlenraum change from 1000 with Hunderter drops the
    typed numbers in the same undo step."""
    client = user()
    typed = [[0, 0, 7]]
    page = editor(zf("d", {**ZF, "typed": typed}), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Rechenart").select_option(label="Minus"))
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed
    page2 = editor(zf("e", {**ZF, "max": 1000, "step": "hunderter", "typed": typed}), client=client)
    pick(page2, "e")
    step(page2, lambda: field(page2, "Zahlenraum").select_option(label="bis 100"))
    assert "typed" not in props_of(doc(page2, client))
    undo(page2)
    assert props_of(doc(page2, client))["typed"] == typed
    step(page2, lambda: field(page2, "Übergang").select_option(label="Zehner"))
    assert "typed" not in props_of(doc(page2, client))
    undo(page2)
    assert props_of(doc(page2, client))["typed"] == typed
    # To bis 1000 with Hunderter stored: the unit changes from 10 to 100, so the typed numbers go.
    page3 = editor(zf("f", {**ZF, "max": 100, "step": "hunderter", "typed": typed}), client=client)
    pick(page3, "f")
    step(page3, lambda: field(page3, "Zahlenraum").select_option(label="bis 1000"))
    assert "typed" not in props_of(doc(page3, client))
    undo(page3)
    assert props_of(doc(page3, client))["typed"] == typed
    # A change that keeps the unit keeps the typed numbers.
    step(page3, lambda: field(page3, "Zahlenraum").select_option(label="bis 20"))
    assert props_of(doc(page3, client))["typed"] == typed
    page4 = editor(zf("g", {**ZF, "typed": typed}), client=client)
    pick(page4, "g")
    step(page4, lambda: field(page4, "Zahlenraum").select_option(label="bis 1000"))
    assert props_of(doc(page4, client))["typed"] == typed


def test_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel (#827): the steppers say "6 Aufgaben" and "3 nebeneinander" at the start, and stop at 1 and 12 tasks,
    and 1 and 3 tasks side by side."""
    page = editor(zf("d", ZF))
    pick(page, "d")
    expect(page.locator(".panel").get_by_text("6 Aufgaben", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("3 nebeneinander", exact=True)).to_be_visible()
    top = editor(zf("d", {**ZF, "count": 12, "columns": 3}))
    pick(top, "d")
    expect(panel(top, "Eine Aufgabe mehr")).to_be_disabled()
    expect(panel(top, "Mehr Aufgaben nebeneinander")).to_be_disabled()
    low = editor(zf("d", {**ZF, "count": 1, "columns": 1}))
    pick(low, "d")
    expect(panel(low, "Eine Aufgabe weniger")).to_be_disabled()
    expect(panel(low, "Weniger Aufgaben nebeneinander")).to_be_disabled()


def test_one_more_task_grows_the_block_in_one_undo_step(editor):
    """Panel (#827): "Eine Aufgabe mehr" from 6 to 7 tasks grows the block's stored height; one Ctrl+Z gives back
    the task and the height."""
    client = user()
    page = editor(zf("d", ZF), client=client)
    pick(page, "d")
    h0 = block_of(doc(page, client))["h"]
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())
    grown = block_of(doc(page, client))
    assert grown["props"]["count"] == 7
    assert grown["h"] > h0
    undo(page)
    back = block_of(doc(page, client))
    assert back["props"]["count"] == 6
    assert abs(back["h"] - h0) < 0.2, back["h"]


def test_typed_numbers_win_and_the_rest_is_worked_out(editor, browser, server):
    """Eigene Zahlen (#827): Erste Zahl 7 and Zweite Zahl 6 in task 1 win over the seed: the key gives r 13, b1 3,
    b2 3 and t 10."""
    client = user()
    page = editor(zf("d", {**ZF, "typed": TYPED_FIRST}), client=client)
    paper = key_print(browser, server, sheet_id(page))
    v = values(paper.locator(".zerlegungsfeld"), 0)
    assert (v[0], v[1], v[2], v[3], v[4], v[5]) == (7, 6, 13, 3, 3, 10), v
    paper.context.close()


def test_the_first_typed_number_keeps_the_drawn_given_numbers_as_typed_entries(editor):
    """Eigene Zahlen (#827): the first number typed into a drawn task stores the task's drawn given positions as
    typed entries too, so that nothing the sheet showed goes away."""
    client = user()
    page = editor(zf("d", ZF), client=client)
    pick(page, "d")
    drawn = given_positions(at(page, "d").locator(".zerlegungsfeld")).get(0, set())
    assert drawn == {0, 1}
    b = values(at(page, "d").locator(".zerlegungsfeld"), 0)[1]
    field(page, "Erste Zahl").click()
    step(page, lambda: page.keyboard.type("7"))
    stored = [e for e in props_of(doc(page, client))["typed"] if e[0] == 0]
    assert sorted(stored) == [[0, 0, 7], [0, 1, b]], (b, stored)
    expect(field(page, "Zweite Zahl")).to_have_value(str(b))
    assert values(at(page, "d").locator(".zerlegungsfeld"), 0)[1] == b


@pytest.mark.parametrize(
    "typed",
    [
        pytest.param(TYPED_WRONG, id="erste-zahl-ten"),
        pytest.param([[0, 0, 8], [0, 3, 3]], id="zerlegung-links-3"),
    ],
)
def test_typed_numbers_that_do_not_fit_give_the_hint_and_no_answer_in_the_key(
    editor, browser, server, typed
):
    """Eigene Zahlen (#827): typed numbers that do not fit (Erste Zahl 10, or Erste Zahl 8 with Zerlegung links 3)
    give "Aufgabe 1: Die Zahlen passen nicht zusammen.", class wrong, and no answer in the key."""
    page = editor(zf("d", {**ZF, "typed": typed}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Aufgabe 1: Die Zahlen passen nicht zusammen.")
    expect(at(page, "d").locator("g.task[data-task='0'].wrong")).to_have_count(1)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zerlegungsfeld g.task[data-task='0'] text.answer")).to_have_count(0)
    paper.context.close()


def test_typed_numbers_that_fit_with_only_ergebnis_and_zwischenergebnis_say_many_solutions(editor):
    """Eigene Zahlen (#827): Ergebnis 13 and Zwischenergebnis 10 fit more than one task: the panel says "Aufgabe 1: Es
    gibt mehr als eine Lösung.", and the task is not wrong."""
    page = editor(zf("d", {**ZF, "typed": TYPED_MANY}))
    pick(page, "d")
    expect(hint(page)).to_have_text("Aufgabe 1: Es gibt mehr als eine Lösung.")
    expect(at(page, "d").locator("g.task[data-task='0'].wrong")).to_have_count(0)


def test_a_fully_determined_typed_task_has_no_note_in_the_key(editor, browser, server):
    """Eigene Zahlen (#827): Erste Zahl 7 and Zweite Zahl 6 fix the task: no hint and no note in the key."""
    page = editor(zf("d", {**ZF, "typed": TYPED_FIRST}))
    pick(page, "d")
    expect(hint(page)).to_have_count(0)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zerlegungsfeld text.note")).to_have_count(0)
    assert NOTE not in paper.content()
    paper.context.close()


def test_eigene_zahlen_entfernen_is_one_undo_step_and_removes_the_hint(editor):
    """Eigene Zahlen (#827): "Eigene Zahlen entfernen" clears every typed number and the hint in one step; one
    Ctrl+Z brings them back."""
    client = user()
    typed = TYPED_WRONG
    page = editor(zf("d", {**ZF, "typed": typed}), client=client)
    pick(page, "d")
    expect(hint(page)).to_have_count(1)
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    expect(hint(page)).to_have_count(0)
    undo(page)
    assert props_of(doc(page, client))["typed"] == typed
    expect(hint(page)).to_have_count(1)


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Panel (#827): "Neu würfeln" stores another seed and keeps the other props; undo brings the old seed back."""
    client = user()
    page = editor(zf("d", {**ZF, "typed": [[0, 0, 7]]}), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != ZF["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == ZF["seed"]


def test_typed_entries_of_a_task_that_is_gone_stay_stored(editor):
    """Eigene Zahlen (#827): an entry of task 6 stays stored after the block goes down to 3 tasks, and plays no
    part."""
    client = user()
    page = editor(zf("d", {**ZF, "typed": [[5, 0, 7]]}), client=client)
    pick(page, "d")
    for _ in range(3):
        step(page, lambda: panel(page, "Eine Aufgabe weniger").click())
    stored = props_of(doc(page, client))
    assert stored["count"] == 3
    assert [5, 0, 7] in stored["typed"]


def test_a_reload_keeps_the_tasks_the_settings_and_the_typed_numbers(editor):
    """Old sheets (#827): a reload keeps the tasks, the settings and the typed numbers."""
    client = user()
    props = {**ZF, "op": "-", "big": True, "typed": TYPED_FIRST}
    page = editor(zf("d", props), client=client)
    reload(page, page.url)
    expect(at(page, "d").locator(".zerlegungsfeld")).to_be_visible()
    assert {k: v for k, v in props_of(doc(page, client)).items()} == props
