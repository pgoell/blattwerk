"""The Stellenwerttafel panel: typed numbers, the settings, and one undo step per change (#1077).

The docstrings name the checklist line that each test proves.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_stellenwerttafel import drawn, props_of, sw
from test_stellenwerttafel import editor as editor
from test_suchsel_print import key_print
from test_words import redo, undo
from ui import doc, pick, user

NOTE_WRONG = "Aufgabe 1: Die Zahl passt nicht zu den Einstellungen."
NOTE_NONE = "Mit diesen Einstellungen gibt es keine Aufgabe."


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def per_value(shown, task):
    """The dots in each column of a task: [H, Z, E]."""
    got = shown.locator(f"g.task[data-task='{task}'] circle.dot").evaluate_all(
        "els => els.map(e => +e.dataset.v)"
    )
    return [got.count(100), got.count(10), got.count(1)]


def number_of(shown, task):
    h, z, e = per_value(shown, task)
    return h * 100 + z * 10 + e


def test_typing_zahl_is_one_undo_step_and_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#1077): typing "12" into "Zahl" keeps the focus and both digits; one undo takes the number back."""
    client = user()
    page = editor(sw({"count": 1}), client=client)
    pick(page, "k")
    number = field(page, "Zahl")
    was = number.input_value()
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    step(page, lambda: number.press("Control+z"))
    expect(number).to_have_value(was)
    assert "typed" not in props_of(doc(page, client))
    # The sheet's redo, as the bar's "Wiederholen" button.
    step(page, lambda: redo(page))
    expect(number).to_have_value("12")


def test_a_typed_number_wins_over_the_seed(editor):
    """Eigene Zahlen (#1077): a typed 36 is the task's number whatever the seed drew: 0 H, 3 Z, 6 E dots."""
    page = editor(sw({"count": 1, "typed": [[0, 36]]}))
    pick(page, "k")
    assert per_value(drawn(page), 0) == [0, 3, 6]


def test_306_fits_with_leere_stellen_off_and_the_key_writes_it(editor, browser, server):
    """Eigene Zahlen (#1077): 306 fits with Leere Stellen off: 3, 0, 6 dots, the key writes 306, no hint."""
    client = user()
    page = editor(sw({"count": 1, "typed": [[0, 306]]}), client=client)
    pick(page, "k")
    assert per_value(drawn(page), 0) == [3, 0, 6]
    expect(hint(page)).to_have_count(0)
    mine = sheet_id(page)
    paper = key_print(browser, server, mine)
    expect(
        paper.locator(".stellenwerttafel g.task[data-task='0'] g.slot text.answer")
    ).to_have_text("306")
    paper.context.close()


def test_a_typed_number_that_does_not_fit_gives_the_hint_and_an_empty_task(editor, browser, server):
    """Eigene Zahlen (#1077): 3065 on "bis 1000" does not fit: the hint says so, no dot, no number in the key; the boxes stay."""
    page = editor(sw({"count": 1, "typed": [[0, 3065]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(drawn(page).locator("g.task[data-task='0'] circle.dot")).to_have_count(0)
    expect(drawn(page).locator("g.task[data-task='0'] g.slot")).to_have_count(1)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".stellenwerttafel g.task[data-task='0'] text.answer")).to_have_count(0)
    expect(paper.locator(".stellenwerttafel g.task[data-task='0'] g.slot")).to_have_count(1)
    paper.context.close()


def test_a_typed_number_with_too_many_dots_gives_the_hint(editor):
    """Eigene Zahlen (#1077): 999 has 27 dots, more than the 9 allowed: the hint says so and no dot shows."""
    page = editor(sw({"count": 1, "typed": [[0, 999]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(drawn(page).locator("g.task[data-task='0'] circle.dot")).to_have_count(0)


def test_no_task_gives_the_none_hint(editor):
    """Plättchen (#1077): with Leere Stellen off and 2 dots at most no task fits: the hint says so and no dot shows."""
    page = editor(sw({"count": 1}))
    pick(page, "k")
    for _ in range(7):
        step(page, lambda: panel(page, "Weniger Plättchen").click())
    expect(hint(page)).to_have_text(NOTE_NONE)
    expect(drawn(page).locator("circle.dot")).to_have_count(0)


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen (#1077): "Eigene Zahlen entfernen" drops the typed numbers in one undo step."""
    client = user()
    page = editor(sw({"count": 1, "typed": [[0, 345]]}), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 345]]


def test_a_change_of_zahlenraum_drops_typed_in_one_undo_step(editor):
    """Zahlenraum (#1077): changing "Zahlenraum" drops the typed numbers in the same undo step."""
    client = user()
    page = editor(sw({"count": 1, "typed": [[0, 345]]}), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Zahlenraum").select_option(label="bis 10 000"))
    stored = props_of(doc(page, client))
    assert stored["max"] == 10000
    assert "typed" not in stored
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 345]]


@pytest.mark.parametrize(
    "key, after, act",
    [
        ("count", 5, lambda p: panel(p, "Eine Aufgabe mehr").click()),
        ("columns", 1, lambda p: panel(p, "Weniger Aufgaben nebeneinander").click()),
        ("max", 10000, lambda p: field(p, "Zahlenraum").select_option(label="bis 10 000")),
        (
            "task",
            "lay",
            lambda p: field(p, "Aufgabentyp").select_option(label="Zahl gegeben, Plättchen legen"),
        ),
        ("dots", 8, lambda p: panel(p, "Weniger Plättchen").click()),
        ("zero", True, lambda p: field(p, "Leere Stellen").check()),
    ],
)
def test_each_setting_is_one_undo_step_and_redo_brings_it_back(editor, key, after, act):
    """Settings (#1077): each setting stores its prop in one step; one undo brings the old, one redo the new."""
    client = user()
    page = editor(sw({"count": 4}), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))[key]
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Neu würfeln (#1077): the button changes the seed and nothing else in the props."""
    client = user()
    page = editor(sw(), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != before["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }


def test_one_more_task_grows_the_block_and_the_foot_hint_shows_then_one_undo_takes_both_back(
    editor,
):
    """Layout (#1077): "Eine Aufgabe mehr" near the paper's foot grows the block past the margin, the foot hint shows;
    one undo takes the height and the hint back."""
    client = user()
    # y 215: the block is 47 mm high with 2 rows; a fifth task makes 3 rows (73 mm), ending at 288 mm, between the margin's foot and the paper's edge.
    page = editor(sw({"count": 4}, y=215), client=client)
    pick(page, "k")
    before = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"]
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())
    stored = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}
    assert stored["k"]["h"] > before
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_be_visible()
    undo(page)
    assert {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"] == before
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_have_count(0)


def test_the_task_select_sets_the_zahl_of_each_task(editor):
    """Aufgabe (#1077): the "Aufgabe" select sets the "Zahl" field to the number of the task it names."""
    page = editor(sw({"count": 3}))
    pick(page, "k")
    shown = drawn(page)
    for task in range(3):
        field(page, "Aufgabe").select_option(label=f"Aufgabe {task + 1}")
        expect(field(page, "Zahl")).to_have_value(str(number_of(shown, task)))
