"""The Zerlegungsfeld on screen: its block in the editor and its format panel.

The docstrings name the lines of the contract (#827, top of frontend/src/zerlegungsfeld.ts) and of the panel that each
test proves. The numbers are read from the page, never pinned: the generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_gaps import step
from test_suchsel_print import key_print
from test_words import redo, undo
from ui import at, box, doc, insert, pick, user

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
