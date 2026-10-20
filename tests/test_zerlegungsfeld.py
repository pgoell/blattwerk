"""The Zerlegungsfeld on screen: its block in the editor and its format panel.

The docstrings name the lines of the contract (#827, top of frontend/src/zerlegungsfeld.ts) and of the panel that each
test proves. The numbers are read from the page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

ZF = {
    "count": 6,
    "columns": 3,
    "op": "+",
    "max": 20,
    "step": "zehner",
    "big": False,
    "task": "task",
    "seed": 7,
}
DEFAULTS = {k: v for k, v in ZF.items() if k != "seed"}
MINUS = "\N{MINUS SIGN}"
H = 128.9  # the default height at 180 mm wide: 111 * 180 / 155
NOTE = "Auch andere Lösungen sind richtig."
# Positions of the contract: 0 a, 1 b, 2 r, 3 b1, 4 b2, 5 t. Which positions show, per Aufgabentyp.
GIVEN = {"task": {0, 1}, "split": {0, 1, 3, 4}, "result": {0, 2}}
TYPED_FIRST = [[0, 0, 7], [0, 1, 6]]  # task 1: Erste Zahl 7, Zweite Zahl 6
TYPED_WRONG = [[0, 0, 10]]  # a multiple of ten is no first number of a Zehnerübergang
TYPED_MANY = [[0, 2, 13], [0, 5, 10]]  # Ergebnis 13 and Zwischenergebnis 10: a from 1 to 9 all fit


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zerlegungsfeld's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zf(name, props, **more):
    """A Zerlegungsfeld block of 180 mm wide."""
    return box(name, "zerlegungsfeld", props, w=180, h=H, **more)


def block_of(stored):
    """The one Zerlegungsfeld of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zerlegungsfeld"]
    return block


def props_of(stored):
    """The props of the one Zerlegungsfeld of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def boxes(locator):
    """Each box of the locator's tasks: its task, position, line and the text it shows (None when empty)."""
    return locator.locator("g.box").evaluate_all(
        """els => els.map(g => {
            const t = g.querySelector('text');
            return {
                task: +g.closest('g.task').dataset.task,
                pos: +g.dataset.pos,
                line: +g.dataset.line,
                text: t ? t.textContent : null,
            };
        })"""
    )


def given_positions(locator):
    """Per task, the positions whose box shows a given number on the sheet."""
    out = {}
    for item in boxes(locator):
        if item["text"] is not None:
            out.setdefault(item["task"], set()).add(item["pos"])
    return out


def values(locator, task):
    """The number at each position of one task in the key (None where the box is empty)."""
    found = {}
    for item in boxes(locator):
        if item["task"] == task and item["text"] is not None:
            found[item["pos"]] = int(item["text"].replace(MINUS, "-"))
    return found


def test_a_zerlegungsfeld_is_inserted_from_the_maths_menu_with_the_default_props(editor):
    """Insert (#827, the maths menu): "Zerlegungsfeld" adds a 180 mm wide block with the default props and a whole
    seed, 6 tasks in 3 columns, each with 4 lines of boxes and 2 branches for the split."""
    client = user()
    page = editor(client=client)
    insert(page, "Zerlegungsfeld")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zerlegungsfeld", exact=True)
    ).to_be_visible()
    stored = block_of(doc(page, client))
    assert stored["w"] == 180
    props = stored["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".zerlegungsfeld").first
    expect(drawn.locator("g.task")).to_have_count(6)
    expect(drawn.locator("g.task[data-task='0'] line.branch")).to_have_count(2)
    expect(drawn.locator("g.task[data-task='0'] text.op")).to_have_text(["+", "+", "+"])


@pytest.mark.parametrize(
    "start, key, before, after, act",
    [
        (
            {},
            "op",
            "+",
            "-",
            lambda p: field(p, "Rechenart").select_option(label="Minus"),
        ),
        (
            {},
            "max",
            20,
            100,
            lambda p: field(p, "Zahlenraum").select_option(label="bis 100"),
        ),
        (
            {"max": 1000},
            "step",
            "zehner",
            "hunderter",
            lambda p: field(p, "Übergang").select_option(label="Hunderter"),
        ),
        (
            {},
            "big",
            False,
            True,
            lambda p: field(p, "Zweite Zahl mehrstellig").check(),
        ),
        (
            {},
            "task",
            "task",
            "split",
            lambda p: field(p, "Aufgabentyp").select_option(label="Aufgabe und Zerlegung"),
        ),
    ],
    ids=["rechenart", "zahlenraum", "uebergang", "mehrstellig", "aufgabentyp"],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(
    editor, start, key, before, after, act
):
    """Panel (#827): each setting changes its stored prop; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    props = {**ZF, **start}
    page = editor(zf("d", props), client=client)
    pick(page, "d")
    if key == "step":
        expect(field(page, "Übergang")).to_be_visible()
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_rechenart_minus_shows_the_minus_sign_and_keeps_the_rule(editor, browser, server):
    """Rechenart (#827): "Minus" shows the minus sign (U+2212) at every operator and draws a task that keeps the
    rule: the key's first number minus the second is the result."""
    page = editor(zf("d", {**ZF, "op": "-"}))
    pick(page, "d")
    expect(at(page, "d").locator("text.op").first).to_have_text(MINUS)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        v = values(paper.locator(".zerlegungsfeld"), task)
        assert v[0] - v[1] == v[2], v
        assert v[0] - v[5] == v[3], v
        assert v[5] - v[4] == v[2], v
        assert v[1] - v[3] == v[4] and v[4] >= 1, v
    paper.context.close()


def test_zahlenraum_and_uebergang_selects_show_as_the_rule_says(editor):
    """Zahlenraum (#827): "Übergang" shows only with bis 1000; "Hunderter" then appears as the choice."""
    page = editor(zf("d", ZF))
    pick(page, "d")
    expect(field(page, "Übergang")).to_have_count(0)
    field(page, "Zahlenraum").select_option(label="bis 1000")
    expect(field(page, "Übergang")).to_be_visible()
    field(page, "Übergang").select_option(label="Hunderter")
    expect(field(page, "Übergang")).to_have_value("hunderter")


def test_hunderter_gives_multiples_of_ten_that_cross_a_hundred(editor, browser, server):
    """Übergang (#827): with bis 1000 and Hunderter every number of the key is a multiple of ten, and the first step
    reaches the full hundred."""
    page = editor(zf("d", {**ZF, "max": 1000, "step": "hunderter"}))
    pick(page, "d")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        v = values(paper.locator(".zerlegungsfeld"), task)
        assert all(v[p] % 10 == 0 for p in range(6)), v
        # a is no multiple of the hundred, and the first step reaches the next full hundred above it.
        assert v[0] % 100 != 0 and v[5] % 100 == 0 and 0 < v[5] - v[0] < 100, v
    paper.context.close()


def test_zweite_zahl_mehrstellig_gives_b_of_at_least_ten(editor, browser, server):
    """Panel (#827): "Zweite Zahl mehrstellig" draws the second number at least 10 in the key."""
    page = editor(zf("d", {**ZF, "big": True}))
    pick(page, "d")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        assert values(paper.locator(".zerlegungsfeld"), task)[1] >= 10
    paper.context.close()


@pytest.mark.parametrize(
    ("task", "expected"),
    [("task", GIVEN["task"]), ("split", GIVEN["split"]), ("result", GIVEN["result"])],
    ids=["task", "split", "result"],
)
def test_each_aufgabentyp_gives_exactly_its_given_positions_on_the_pupils_sheet(
    editor, browser, server, task, expected
):
    """Aufgabentyp (#827): the pupils' sheet shows exactly the given positions: task 0 and 1, split 0, 1, 3 and 4,
    result 0 and 2; every drawn task gives the same ones."""
    page = editor(zf("d", {**ZF, "task": task}))
    paper = printed(browser, server, sheet_id(page))
    shown = given_positions(paper.locator(".zerlegungsfeld"))
    assert set(shown) == set(range(6))
    assert all(positions == expected for positions in shown.values()), shown
    paper.context.close()


@pytest.mark.parametrize(
    "act",
    [
        lambda p: field(p, "Zahlenraum").select_option(label="bis 100"),
        lambda p: field(p, "Rechenart").select_option(label="Minus"),
        lambda p: field(p, "Zweite Zahl mehrstellig").check(),
        lambda p: field(p, "Aufgabentyp").select_option(label="Erste Zahl und Ergebnis"),
    ],
    ids=["zahlenraum", "rechenart", "mehrstellig", "aufgabentyp"],
)
def test_a_setting_is_one_undo_step_and_redo_brings_it_back(editor, act):
    """Panel (#827): one Ctrl+Z takes one setting back and one redo brings it again."""
    client = user()
    page = editor(zf("d", ZF), client=client)
    pick(page, "d")
    before = props_of(doc(page, client))
    step(page, lambda: act(page))
    after = props_of(doc(page, client))
    assert after != before
    undo(page)
    assert props_of(doc(page, client)) == before
    redo(page)
    assert props_of(doc(page, client)) == after


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
    assert drawn
    field(page, "Erste Zahl").click()
    step(page, lambda: page.keyboard.type("7"))
    stored = [e for e in props_of(doc(page, client))["typed"] if e[0] == 0]
    assert {e[1] for e in stored} >= drawn, (drawn, stored)


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


def test_odd_stored_props_still_draw_and_the_panel_opens(editor):
    """Old sheets (#827): odd stored props still draw, the panel opens and no fault shows."""
    client = user()
    odd = {
        "count": -3,
        "columns": 99,
        "op": "x",
        "max": None,
        "step": "x",
        "big": "x",
        "task": 7,
        "typed": [[9, 9, 9], "a"],
        "seed": "s",
    }
    page = editor(zf("odd", odd), client=client)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    expect(at(page, "odd").locator(".zerlegungsfeld")).to_be_visible()
    expect(page.locator(".fault")).to_have_count(0)
    pick(page, "odd")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zerlegungsfeld", exact=True)
    ).to_be_visible()
    assert not errors, errors
