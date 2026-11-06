"""The Zahlzerlegung panel: typed numbers, the settings, and one undo step per change (#1078).

The docstrings name the checklist line that each test proves.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import redo, undo
from test_zahlzerlegung import ZZ, drawn, fit, props_of, zz
from ui import box, doc, pick, user

NOTE_WRONG = "Aufgabe 1: Die Zahl passt nicht zu den Einstellungen."


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def test_typing_zahl_is_one_undo_step_and_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#1078): typing "12" into "Zahl" keeps the focus and both digits; one undo takes the number back."""
    client = user()
    page = editor(zz({"count": 1}), client=client)
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
    """Eigene Zahlen (#1078): a typed 37 on "bis 100" is the task's number: its parts sum to 37."""
    page = editor(zz({"max": 100, "count": 1, "typed": [[0, 37]]}))
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    expect(drawn(page).locator("g.task[data-task='0'] text.given").first).to_have_text("37")


def test_a_typed_number_that_does_not_fit_gives_the_hint_and_an_empty_task(editor, browser, server):
    """Eigene Zahlen (#1078): 306 with "Zerlegen" does not fit (a 0 in the middle): the hint says so, the task has
    class wrong, no given number, and its gaps stay empty in the key too."""
    page = editor(zz({"count": 1, "typed": [[0, 306]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    task = drawn(page).locator("g.task[data-task='0']")
    expect(task).to_have_class(re.compile(r"\bwrong\b"))
    expect(task.locator("text.given")).to_have_count(0)
    expect(task.locator("rect.gap").first).to_be_visible()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlzerlegung g.task[data-task='0'] text.answer")).to_have_count(0)
    expect(paper.locator(".zahlzerlegung g.task[data-task='0'] rect.gap").first).to_be_visible()
    paper.context.close()


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen (#1078): "Eigene Zahlen entfernen" drops the typed numbers in one undo step."""
    client = user()
    page = editor(zz({"count": 1, "typed": [[0, 345]]}), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 345]]


def test_a_change_of_zahlenraum_drops_typed_in_one_undo_step(editor):
    """Zahlenraum (#1078): changing "Zahlenraum" drops the typed numbers in the same undo step."""
    client = user()
    page = editor(zz({"count": 1, "typed": [[0, 345]]}), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Zahlenraum").select_option(label="bis 100"))
    stored = props_of(doc(page, client))
    assert stored["max"] == 100
    assert "typed" not in stored
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 345]]


@pytest.mark.parametrize(
    "key, after, act",
    [
        (
            "task",
            "gap",
            lambda p: field(p, "Aufgabentyp").select_option(label="Lücke (600 + __ + 4 = 674)"),
        ),
        ("max", 100, lambda p: field(p, "Zahlenraum").select_option(label="bis 100")),
        ("count", 7, lambda p: panel(p, "Eine Aufgabe mehr").click()),
        ("columns", 1, lambda p: panel(p, "Weniger Aufgaben nebeneinander").click()),
    ],
)
def test_each_setting_is_one_undo_step_and_redo_brings_it_back(editor, key, after, act):
    """Settings (#1078): each setting stores its prop in one step; one undo brings the old, one redo the new."""
    client = user()
    page = editor(zz({"count": 6}), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))[key]
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_neu_wuerfeln_changes_only_the_seed(editor):
    """Neu würfeln (#1078): the button changes the seed and nothing else in the props."""
    client = user()
    page = editor(zz(), client=client)
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
    """Layout (#1078): "Eine Aufgabe mehr" near the paper's foot grows the block past the margin, the foot hint shows;
    one undo takes the height and the hint back."""
    client = user()
    # y 255: a 2-row block of 22 mm ends at 277 mm; a third row makes it 35 mm, ending at 290 mm, past the margin.
    props = {**ZZ, "count": 4}
    w, h = fit(props)
    page = editor(box("k", "zahlzerlegung", props, y=255, w=w, h=h), client=client)
    pick(page, "k")
    before = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"]
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())
    stored = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}
    assert stored["k"]["h"] > before
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_be_visible()
    undo(page)
    assert {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"] == pytest.approx(
        before
    )
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_have_count(0)
