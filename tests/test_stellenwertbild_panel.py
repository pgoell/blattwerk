"""The Stellenwert-Bild panel: typed numbers, the settings, and one undo step per change (#1076).

The docstrings name the checklist line that each test proves.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_stellenwertbild import drawn, props_of, sw
from test_stellenwertbild import editor as editor
from test_words import redo, undo
from ui import doc, pick, user

NOTE_WRONG = "Aufgabe 1: Die Zahl passt nicht zu den Einstellungen."


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def test_typing_zahl_is_one_undo_step_and_keeps_focus_and_digits(editor):
    """Eigene Zahlen (#1076): typing "12" into "Zahl" keeps the focus and both digits; one undo takes the number back."""
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


def test_a_typed_number_wins_over_the_drawn_one(editor):
    """Eigene Zahlen (#1076): a typed 37 on a Zahlenraum to 100 is the task's number: its pieces show 37."""
    page = editor(sw({"max": 100, "count": 1, "typed": [[0, 37]]}))
    pick(page, "k")
    found = (
        drawn(page)
        .locator("g.task[data-task='0'] g.piece")
        .evaluate_all("els => els.map(e => +e.dataset.v)")
    )
    assert sum(found) == 37, found


def test_a_typed_number_that_does_not_fit_gives_the_hint_and_no_pieces(editor):
    """Eigene Zahlen (#1076): 50 on "bis 1000" does not fit: the hint says so, no piece, and the key box is empty."""
    page = editor(sw({"count": 1, "typed": [[0, 50]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(drawn(page).locator("g.task[data-task='0'] g.piece")).to_have_count(0)
    expect(drawn(page).locator("g.task[data-task='0'] g.slot text")).to_have_count(0)


def test_a_bundle_task_with_100_does_not_fit_and_gives_the_hint(editor):
    """Eigene Zahlen (#1076): 100 with Bündeln has no task: the hint says so and no piece shows."""
    page = editor(sw({"count": 1, "bundle": True, "typed": [[0, 100]]}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_WRONG)
    expect(drawn(page).locator("g.task[data-task='0'] g.piece")).to_have_count(0)


def test_eigene_zahlen_entfernen_is_one_undo_step(editor):
    """Eigene Zahlen (#1076): "Eigene Zahlen entfernen" drops the typed numbers in one undo step."""
    client = user()
    page = editor(sw({"count": 1, "typed": [[0, 345]]}), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eigene Zahlen entfernen").click())
    assert "typed" not in props_of(doc(page, client))
    undo(page)
    assert props_of(doc(page, client))["typed"] == [[0, 345]]


def test_a_change_of_zahlenraum_drops_typed_in_one_undo_step(editor):
    """Zahlenraum (#1076): changing "Zahlenraum" drops the typed numbers in the same undo step."""
    client = user()
    page = editor(sw({"count": 1, "typed": [[0, 345]]}), client=client)
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
            "draw",
            lambda p: field(p, "Aufgabentyp").select_option(label="Zahl gegeben, Bild zeichnen"),
        ),
        ("table", False, lambda p: field(p, "Stellenwerttafel").uncheck()),
        ("zero", True, lambda p: field(p, "Stellen mit 0").check()),
        ("bundle", True, lambda p: field(p, "Bündeln (mehr als 9)").check()),
        ("count", 5, lambda p: panel(p, "Eine Aufgabe mehr").click()),
        ("columns", 1, lambda p: panel(p, "Weniger Aufgaben nebeneinander").click()),
    ],
)
def test_each_setting_is_one_undo_step_and_redo_brings_it_back(editor, key, after, act):
    """Settings (#1076): each setting stores its prop in one step; one undo brings the old, one redo the new."""
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
    """Neu würfeln (#1076): the button changes the seed and nothing else in the props."""
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
    """Layout (#1076): "Eine Aufgabe mehr" near the paper's foot grows the block past the margin, the foot hint shows;
    one undo takes the height and the hint back."""
    client = user()
    # y 110: the block is 119 mm high with 2 rows; a fifth task makes 3 rows (181 mm), ending at 291 mm, between the margin's foot and the paper's edge.
    page = editor(sw({"count": 4}, y=110), client=client)
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


def test_the_task_select_sets_the_zahl_of_each_task(editor):
    """Eigene Zahlen (#1076): with 2 or more tasks "Aufgabe" picks the task the "Zahl" field sets."""
    page = editor(sw({"count": 2}))
    pick(page, "k")
    field(page, "Aufgabe").select_option(label="Aufgabe 2")
    expect(field(page, "Zahl")).to_be_visible()
    expect(hint(page)).to_have_count(0)
