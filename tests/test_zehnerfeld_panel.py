"""The Zehnerfeld panel: hand-set dots, typed numbers, and one undo step per change."""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from test_zehnerfeld import NOTE_WRONG, ZEH, drawn, field, hint, props_of, zeh
from test_zehnerfeld import editor as editor
from ui import at, doc, pick, reload, user


def test_punkte_selbst_setzen_cycles_the_mark_of_a_dot_and_rückgängig_takes_one_back(editor):
    """Punkte (#829): with "Punkte selbst setzen" a click on "Punkt 1" cycles data-mark 0, 1, 2, 3, 0 on the button and
    on circle.dot[data-k=0] of the sheet; "Rückgängig" takes one click back."""
    client = user()
    page = editor(zeh({"manual": True, "count": 1}), client=client)
    pick(page, "k")
    expect(page.locator(".panel .punkte")).to_be_visible()
    button = page.locator(".panel").get_by_role("button", name="Punkt 1", exact=True)
    for mark in (1, 2, 3, 0):
        step(page, lambda: button.click())
        expect(button).to_have_attribute("data-mark", str(mark))
        expect(drawn(page).locator("circle.dot[data-k='0']")).to_have_attribute(
            "data-mark", str(mark)
        )
    step(page, lambda: button.click())
    undo(page)
    expect(button).to_have_attribute("data-mark", "0")


@pytest.mark.parametrize("field_type", ["zehn", "zwanzig", "hundert"])
def test_the_dots_set_by_hand_fit_in_the_panel_and_take_the_blocks_colours(editor, field_type):
    """Punkte (#829, review): the grid of "Punkt n" buttons fits in the panel with no sideways scroll, its last
    column inside the panel, and a set dot shows the colour of the block's Farben (here Graustufen)."""
    page = editor(zeh({"manual": True, "count": 1, "field": field_type, "colors": "grey"}))
    pick(page, "k")
    panel = page.locator(".panel")
    expect(panel.locator(".punkte")).to_be_visible()
    assert panel.evaluate("p => p.scrollWidth <= p.clientWidth")
    last = panel.get_by_role("button", name="Punkt 10", exact=True)
    right = panel.bounding_box()
    assert last.bounding_box()["x"] + last.bounding_box()["width"] <= right["x"] + right["width"]
    first = panel.get_by_role("button", name="Punkt 1", exact=True)
    step(page, lambda: first.click())
    expect(first).to_have_css("background-color", "rgb(34, 34, 34)")


def test_switching_punkte_selbst_setzen_off_brings_the_dots_back_and_keeps_the_marks(editor):
    """Punkte (#829): switching the setting off draws the task's dots again; the marks stay stored."""
    client = user()
    page = editor(zeh({"manual": True, "count": 1, "marks": [[0, 0, 1]]}), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Punkte selbst setzen").uncheck())
    expect(
        drawn(page).locator("g.task[data-task='0'] circle.dot[data-mark='1']").first
    ).to_be_visible()
    assert props_of(doc(page, client))["marks"] == [[0, 0, 1]]


def test_typing_erste_zahl_is_one_undo_step_and_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#829): typing "12" into "Erste Zahl" keeps the focus and both digits, and one Ctrl+Z in the
    box takes the whole number back."""
    client = user()
    page = editor(zeh({"count": 1}), client=client)
    pick(page, "k")
    number = field(page, "Erste Zahl")
    was = number.input_value()
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    # Strg+Z in the box is the sheet's undo: the box shows the drawn number again and nothing typed stays.
    step(page, lambda: number.press("Control+z"))
    expect(number).to_have_value(was)
    assert "typed" not in props_of(doc(page, client))
    step(page, lambda: number.press("Control+y"))
    expect(number).to_have_value("12")


def test_a_typed_number_above_the_field_gives_the_hint_and_no_dots(editor):
    """Eigene Zahlen (#829): 150 typed into "Erste Zahl" on a Hunderterfeld does not fit: the hint, no dot, no
    number in the task, and the box keeps 150."""
    page = editor(zeh({"count": 1, "field": "hundert", "max": 100}))
    pick(page, "k")
    number = field(page, "Erste Zahl")
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("150"))
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(number).to_have_value("150")
    expect(drawn(page).locator("g.task[data-task='0'] text")).to_have_count(2)  # only + and =
    expect(drawn(page).locator("circle.dot:not([data-mark='0'])")).to_have_count(0)


def test_typed_numbers_that_do_not_fit_give_the_hint_and_no_dots(editor):
    """Eigene Zahlen (#829): Erste Zahl 15 and Zweite Zahl 9 on a Zwanzigerfeld Plus do not fit: the hint says
    "Aufgabe 1: Die Zahlen passen nicht ins Feld." and the task draws no dot and no number."""
    page = editor(zeh({"count": 1, "typed": [[0, 0, 15], [0, 1, 9]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(drawn(page).locator("g.task[data-task='0'] text.given")).to_have_count(0)
    expect(drawn(page).locator("g.task[data-task='0'] circle.dot[data-mark='1']")).to_have_count(0)
    expect(drawn(page).locator("g.task[data-task='0'] circle.dot[data-mark='2']")).to_have_count(0)


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen (#829): "Eigene Zahlen entfernen" drops the typed numbers in one undo step."""
    client = user()
    page = editor(zeh({"count": 1, "typed": [[0, 0, 5]]}), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 5]]


def test_neu_wurfeln_changes_only_the_seed(editor):
    """Neu würfeln (#829): the button changes the seed and nothing else in the props; the tasks change."""
    client = user()
    page = editor(zeh(), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != before["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }


@pytest.mark.parametrize(
    "key, after, act",
    [
        ("field", "zehn", lambda p: field(p, "Feld").select_option("zehn")),
        ("op", "-", lambda p: field(p, "Rechenart").select_option("-")),
        ("task", "write", lambda p: field(p, "Aufgabentyp").select_option("write")),
        ("max", 10, lambda p: field(p, "Zahlenraum").select_option("10")),
        ("cross", "yes", lambda p: field(p, "Zehnerübergang").select_option("yes")),
        ("lines", False, lambda p: field(p, "Trennlinien").uncheck()),
        ("colors", "grey", lambda p: field(p, "Farben").select_option("grey")),
        ("manual", True, lambda p: field(p, "Punkte selbst setzen").check()),
    ],
)
def test_each_setting_is_one_undo_step_and_redo_brings_it_back(editor, key, after, act):
    """Settings (#829): each setting stores its prop in one step; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(zeh(), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))[key]
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_feld_and_rechenart_change_drop_typed_in_one_undo_step(editor):
    """Eigene Zahlen (#829): a change of Feld or Rechenart drops the typed numbers in the same undo step."""
    client = user()
    page = editor(zeh({"typed": [[0, 0, 5]]}), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Rechenart").select_option("-"))
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 0, 5]]


def test_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel (#829): the count stepper stops at 1 and 12 tasks, the columns stepper at 1 and 4."""
    page = editor(zeh({"count": 1, "columns": 1}))
    pick(page, "k")
    expect(panel(page, "Eine Aufgabe weniger")).to_be_disabled()
    expect(panel(page, "Weniger Aufgaben nebeneinander")).to_be_disabled()
    page = editor(zeh({"count": 12, "columns": 4}))
    pick(page, "k")
    expect(panel(page, "Eine Aufgabe mehr")).to_be_disabled()
    expect(panel(page, "Mehr Aufgaben nebeneinander")).to_be_disabled()


def test_one_more_task_grows_the_block_in_one_undo_step(editor):
    """Panel (#829): "Eine Aufgabe mehr" from 6 to 7 tasks adds a row; one undo brings the height back."""
    client = user()
    page = editor(zeh({"count": 6}), client=client)
    pick(page, "k")
    before = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"]
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())
    stored = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}
    assert stored["k"]["props"]["count"] == 7
    assert stored["k"]["h"] > before
    undo(page)
    assert {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"] == pytest.approx(
        before
    )


def test_a_reload_keeps_the_tasks_the_settings_the_typed_numbers_and_the_marks(editor):
    """Settings (#829): after a reload the tasks, the settings, the typed numbers and the marks are as they were."""
    client = user()
    props = {
        **ZEH,
        "count": 3,
        "columns": 3,
        "op": "-",
        "max": 10,
        "task": "mixed",
        "typed": [[0, 0, 7]],
        "manual": False,
        "marks": [[0, 3, 1]],
    }
    page = editor(zeh(props), client=client)
    pick(page, "k")
    reload(page, page.url)
    expect(at(page, "k").locator(".zehnerfeld")).to_be_visible()
    assert props_of(doc(page, client)) == props
