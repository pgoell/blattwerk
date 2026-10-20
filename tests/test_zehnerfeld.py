"""The Zehnerfeld block on screen: its drawing and its panel (#829).

The docstrings name the lines of the checklist and of the contract (top of frontend/src/zehnerfeld.ts) that each
test proves. The numbers are read from the page, never pinned: the generator may change. The pupils' sheet and the
answer key are in test_zehnerfeld_print.py; the block as a box is in test_zehnerfeld_block.py.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

ZEH = {
    "count": 4,
    "columns": 2,
    "field": "zwanzig",
    "op": "+",
    "task": "dots",
    "max": 20,
    "cross": "any",
    "lines": True,
    "colors": "color",
    "manual": False,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in ZEH.items() if k != "seed"}
MINUS = "\N{MINUS SIGN}"
H = 53  # the default height: 2 rows of 23 mm, 1 gap of 6 mm and 1 mm of stroke, at 127 mm wide
NOTE_NONE = "Mit diesen Einstellungen gibt es keine Aufgabe."
NOTE_WRONG = "Aufgabe 1: Die Zahlen passen nicht ins Feld."


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zehnerfeld settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zeh(props=None, name="k", **more):
    """A Zehnerfeld block of 127 mm wide with the default props, or the given ones over them."""
    return box(name, "zehnerfeld", {**ZEH, **(props or {})}, w=127, h=H, **more)


def drawn(page, name="k"):
    return at(page, name).locator(".zehnerfeld")


def props_of(stored):
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zehnerfeld"]
    return block["props"]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def numbers(locator, task):
    """The number at each position of the task's line 0 (the task line), only the boxes that show a number."""
    found = locator.locator(f"g.task[data-task='{task}'] g.slot text").evaluate_all(
        "els => els.map(t => [t.closest('g.slot').dataset.pos, t.textContent])"
    )
    return {int(pos): int(text.replace(MINUS, "-")) for pos, text in found}


def marks(locator, task):
    """The data-mark of each dot of the task, in dot order."""
    return locator.locator(f"g.task[data-task='{task}'] circle.dot").evaluate_all(
        "els => els.map(e => +e.dataset.mark)"
    )


def test_a_zehnerfeld_is_inserted_from_the_maths_menu_with_the_defaults(editor):
    """Insert (#829, the maths menu): "Zehnerfeld" adds a 127 mm wide block with the default props and a whole seed:
    4 tasks in 2 columns, each with a task line under its field."""
    client = user()
    page = editor(client=client)
    insert(page, "Zehnerfeld")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zehnerfeld", exact=True)
    ).to_be_visible()
    stored = doc(page, client)
    block = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zehnerfeld"]
    assert len(block) == 1 and block[0]["w"] == 127
    assert block[0]["h"] == pytest.approx(H)
    props = block[0]["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    shown = page.locator(".zehnerfeld").first
    expect(shown.locator("g.task")).to_have_count(4)
    expect(shown.locator("g.task[data-task='0'] g.slot")).to_have_count(3)
    expect(shown.locator("g.task[data-task='0'] text.op").first).to_have_text("+")


@pytest.mark.parametrize(
    "field_type, dots",
    [("zehn", 10), ("zehn2", 10), ("zwanzig", 20), ("hundert", 100)],
)
def test_each_feld_gives_rows_times_cols_dots_in_a_task(editor, field_type, dots):
    """Field (#829): each Typ draws its field: Zehnerfeld 1 x 10, 2 x 5, Zwanzigerfeld 2 x 10, Hunderterfeld 10 x 10,
    so the first task has 10, 10, 20 or 100 dots."""
    page = editor(zeh({"field": field_type, "count": 1}))
    pick(page, "k")
    expect(drawn(page).locator("g.task[data-task='0'] circle.dot")).to_have_count(dots)


def test_plus_dots_task_counts_a_and_b_as_colour_one_and_colour_two(editor, browser, server):
    """Plus (#829): in a "dots" task the dots with data-mark 1 count a and those with data-mark 2 count b; the key
    gives the same a and b as text.answer of the same task."""
    page = editor(zeh({"count": 3}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    shown = paper.locator(".zehnerfeld")
    for task in range(3):
        a, b, r = numbers(shown, task)[0], numbers(shown, task)[1], numbers(shown, task)[2]
        found = marks(shown, task)
        assert found.count(1) == a and found.count(2) == b, (a, b, found)
        assert r == a + b
    paper.context.close()


def test_minus_strikes_the_dots_of_b_and_keeps_no_colour_two(editor):
    """Minus (#829): a Minus task shows a dots in colour 1, the last b of them struck through (data-mark 3), a line
    of strike shows, and no dot has data-mark 2."""
    page = editor(zeh({"op": "-", "count": 2}))
    pick(page, "k")
    expect(drawn(page).locator("line.strike").first).to_be_visible()
    expect(drawn(page).locator("circle.dot[data-mark='2']")).to_have_count(0)
    expect(drawn(page).locator("circle.dot[data-mark='3']").first).to_be_visible()


def test_aufgabentyp_write_shows_a_and_b_and_the_key_shows_the_dots(editor, browser, server):
    """Task (#829): "Aufgabe gegeben, Punkte malen" shows a and b as given numbers and no filled dot on the sheet; the
    key shows the dots and r."""
    page = editor(zeh({"task": "write", "count": 2}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.task[data-task='0'] text.given")).to_have_count(2)
    expect(
        shown.locator(
            "circle.dot[data-mark='1'], circle.dot[data-mark='2'], circle.dot[data-mark='3']"
        )
    ).to_have_count(0)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zehnerfeld circle.dot[data-mark='1']").first).to_be_visible()
    assert (
        numbers(paper.locator(".zehnerfeld"), 0)[2]
        == numbers(paper.locator(".zehnerfeld"), 0)[0] + numbers(paper.locator(".zehnerfeld"), 0)[1]
    )
    paper.context.close()


def test_gemischt_gives_task_0_dots_and_task_1_numbers(editor):
    """Task (#829): "Gemischt" makes task 0 a dots task and task 1 a write task, by turns."""
    page = editor(zeh({"task": "mixed", "count": 2}))
    pick(page, "k")
    expect(
        drawn(page).locator("g.task[data-task='0'] circle.dot[data-mark='1']").first
    ).to_be_visible()
    expect(drawn(page).locator("g.task[data-task='1'] text.given")).to_have_count(2)


def test_zahlenraum_bis_10_on_a_zwanzigerfeld_keeps_every_result_at_most_10(
    editor, browser, server
):
    """Zahlenraum (#829): "bis 10" on the Zwanzigerfeld keeps every Plus result, drawn and in the key, at most 10."""
    page = editor(zeh({"max": 10, "count": 6}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        assert numbers(paper.locator(".zehnerfeld"), task)[2] <= 10
    paper.context.close()


@pytest.mark.parametrize("cross, crossing", [("yes", True), ("no", False)])
def test_zehnerubergang_mit_and_ohne_hold_in_every_drawn_task(
    editor, browser, server, cross, crossing
):
    """Zehnerübergang (#829): "mit" every drawn Plus task crosses a ten, "ohne" none does: (a mod 10) + (b mod 10)
    is above 10 or at most 10, as read from the key."""
    page = editor(zeh({"cross": cross, "count": 6}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        a, b = (
            numbers(paper.locator(".zehnerfeld"), task)[0],
            numbers(paper.locator(".zehnerfeld"), task)[1],
        )
        assert ((a % 10) + (b % 10) > 10) is crossing, (a, b)
    paper.context.close()


def test_the_zehnerubergang_select_is_absent_for_zehnerfeld_1_x_10(editor):
    """Zehnerübergang (#829): on the Zehnerfeld 1 x 10 the select "Zehnerübergang" is not offered."""
    page = editor(zeh({"field": "zehn"}))
    pick(page, "k")
    expect(field(page, "Zehnerübergang")).to_have_count(0)


def test_zwanzigerfeld_bis_10_mit_zehnerubergang_gives_the_hint_and_no_dots(editor):
    """Zahlenraum (#829): "bis 10" with "mit Zehnerübergang" on the Zwanzigerfeld has no task: the hint says so and no
    field draws a dot: every field stays empty, with no number and no sign."""
    page = editor(zeh({"max": 10, "cross": "yes"}))
    pick(page, "k")
    expect(hint(page)).to_have_text(NOTE_NONE)
    expect(drawn(page).locator("circle.dot")).to_have_count(80)
    expect(drawn(page).locator("circle.dot:not([data-mark='0'])")).to_have_count(0)
    expect(drawn(page).locator("g.task text")).to_have_count(0)


def test_trennlinien_on_draws_the_lines_and_off_draws_none(editor):
    """Trennlinien (#829): with the checkbox on, the fields draw line.trenn; off, none."""
    page = editor(zeh({"lines": True}))
    pick(page, "k")
    # One line after the fifth column of each of the four Zwanzigerfelder.
    expect(drawn(page).locator("line.trenn")).to_have_count(4)
    field(page, "Trennlinien").uncheck()
    expect(drawn(page).locator("line.trenn")).to_have_count(0)


def test_graustufen_fill_the_dots_with_222222_and_9a9a9a(editor):
    """Farben (#829): "Graustufen" fills colour 1 dots with #222222 and colour 2 dots with #9a9a9a."""
    page = editor(zeh({"colors": "grey"}))
    pick(page, "k")
    expect(drawn(page).locator("circle.dot[data-mark='1']").first).to_have_attribute(
        "fill", "#222222"
    )
    expect(drawn(page).locator("circle.dot[data-mark='2']").first).to_have_attribute(
        "fill", "#9a9a9a"
    )


def test_eigene_farben_show_two_colour_inputs_and_a_set_colour_reaches_the_dots(editor):
    """Farben (#829): "Eigene Farben" shows "Erste Farbe" and "Zweite Farbe"; a set colour fills the dots of its
    colour, and the change is one undo step."""
    client = user()
    page = editor(zeh(), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Farben").select_option("own"))
    expect(field(page, "Erste Farbe")).to_be_visible()
    expect(field(page, "Zweite Farbe")).to_be_visible()
    step(page, lambda: field(page, "Erste Farbe").fill("#00aa00"))
    expect(drawn(page).locator("circle.dot[data-mark='1']").first).to_have_attribute(
        "fill", "#00aa00"
    )


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
    number.click()
    number.press("Control+A")
    step(page, lambda: page.keyboard.type("12"))
    expect(number).to_be_focused()
    expect(number).to_have_value("12")
    step(page, lambda: number.press("Control+z"))
    expect(number).not_to_have_value("12")


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
