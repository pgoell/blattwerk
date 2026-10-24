"""The Halbschriftlich block on screen: its drawing and its panel.

The docstrings name the lines of the checklist (#828) and of the contract (top of frontend/src/halbschriftlich.ts)
that each test proves. The numbers are read from the page, never pinned: the generator may change. The pupils' sheet
and the answer key are in test_halbschriftlich_print.py.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gaps import panel, step
from test_suchsel_print import key_print
from test_words import redo, undo
from ui import at, box, doc, insert, pick, reload, user

HAL = {
    "count": 6,
    "columns": 2,
    "op": "+",
    "max": 1000,
    "digits": 3,
    "einer": "any",
    "zehner": "any",
    "grid": True,
    "head": False,
    "tint": False,
    "ops": True,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in HAL.items() if k != "seed"}
MINUS = "\N{MINUS SIGN}"
H = 86  # the default height: 3 rows of 25 mm, 2 gaps of 5 mm and 1 mm of stroke, at 146 mm wide
NOTE = "Auch andere Lösungen sind richtig."
NO_TASK = "Mit diesen Einstellungen gibt es keine Aufgabe."


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Halbschriftlich settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def hal(name="k", props=None, **more):
    """A Halbschriftlich block of 146 mm wide."""
    return box(name, "halbschriftlich", {**HAL, **(props or {})}, w=146, h=H, **more)


def block_of(stored):
    """The one Halbschriftlich block of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "halbschriftlich"]
    return block


def props_of(stored):
    """The props of the one Halbschriftlich block of the sheet."""
    return block_of(stored)["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def slots(locator):
    """Each number slot of the locator: its task, line, position and the digits it shows (None when empty)."""
    return locator.locator("g.slot").evaluate_all(
        """els => els.map(g => {
            const t = g.querySelector('text');
            return {
                task: +g.closest('g.task').dataset.task,
                line: +g.dataset.line,
                pos: +g.dataset.pos,
                text: t ? t.textContent : null,
            };
        })"""
    )


def values(locator, task, line):
    """The number at each position of one line of one task (only the positions that show a number)."""
    found = {}
    for item in slots(locator):
        if item["task"] == task and item["line"] == line and item["text"] is not None:
            found[item["pos"]] = int(item["text"].replace(MINUS, "-"))
    return found


def step_count(locator, task):
    """How many step lines the task draws (line 0 is the task itself)."""
    lines = [i["line"] for i in slots(locator) if i["task"] == task]
    return max(lines)


def digit(n, place):
    """The digit of n at place 0 (Einer), 1 (Zehner) or 2 (Hunderter)."""
    return (n // 10**place) % 10


def crosses(op, a, b, place):
    """Whether the task crosses a ten (place 0) or a hundred (place 1) on its way: the result leaves the ten or
    hundred of the first number (contract: the Übertrag of written arithmetic, 395 + 7 crosses a hundred)."""
    m = 10 ** (place + 1)
    if op == "+":
        return a % m + b % m >= m
    return a % m < b % m


def test_a_halbschriftlich_is_inserted_from_the_maths_menu_with_the_defaults(editor):
    """Insert (#828, the maths menu): "Halbschriftlich rechnen" adds a 146 mm wide block with the default props and a
    whole seed: 6 tasks in 2 columns, each with a line a + b = r and its own step lines."""
    client = user()
    page = editor(client=client)
    insert(page, "Halbschriftlich rechnen")
    expect(
        page.locator(".panel").get_by_role("heading", name="Halbschriftlich rechnen", exact=True)
    ).to_be_visible()
    stored = doc(page, client)
    block = [b for b in stored["pages"][0]["blocks"] if b["type"] == "halbschriftlich"]
    assert len(block) == 1 and block[0]["w"] == 146
    assert block[0]["h"] == pytest.approx(H)
    props = block[0]["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    drawn = page.locator(".halbschriftlich").first
    expect(drawn.locator("g.task")).to_have_count(6)
    expect(drawn.locator("g.task[data-task='0'] g.slot[data-line='0']")).to_have_count(3)
    expect(drawn.locator("g.task[data-task='0'] text.op").first).to_have_text("+")
    expect(drawn.locator("g.task[data-task='0'] g.slot[data-line='1']")).to_have_count(3)


def test_the_rechenart_minus_shows_the_minus_sign_and_the_steps_go_down(editor, browser, server):
    """Rechenart (#828): "Minus" shows the minus sign (U+2212) on the sheet, and the key's steps go down: each step
    takes its part away and the last step is the result."""
    page = editor(hal(props={"op": "-"}))
    pick(page, "k")
    expect(at(page, "k").locator("text.op").first).to_have_text(MINUS)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        loc = paper.locator(".halbschriftlich")
        a, b, r = (values(loc, task, 0)[p] for p in (0, 1, 2))
        assert a - b == r and r >= 0, (a, b, r)
        for line in range(1, step_count(loc, task) + 1):
            s = values(loc, task, line)
            assert s[0] - s[1] == s[2], s
    paper.context.close()


def test_one_step_per_digit_of_b_that_is_not_0(editor, browser, server):
    """Steps (#828): typed 345 + 103 gives two step lines in the key: 345 + 100 = 445, then 445 + 3 = 448."""
    page = editor(hal(props={"count": 1, "typed": [[0, 0, 345], [0, 1, 103]]}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    assert step_count(loc, 0) == 2
    assert values(loc, 0, 0) == {0: 345, 1: 103, 2: 448}
    assert values(loc, 0, 1) == {0: 345, 1: 100, 2: 445}
    assert values(loc, 0, 2) == {0: 445, 1: 3, 2: 448}
    paper.context.close()


@pytest.mark.parametrize("grid", [True, False])
def test_karo_on_draws_the_squares_and_off_draws_plain_boxes(editor, grid):
    """Karo (#828): Karo on draws g.karo behind the tasks; off draws plain rects, one box per number."""
    page = editor(hal(props={"grid": grid}))
    drawn = at(page, "k").locator(".halbschriftlich")
    if grid:
        expect(drawn.locator("g.karo")).to_have_count(1)
    else:
        expect(drawn.locator("g.karo")).to_have_count(0)
        expect(drawn.locator("g.slot rect")).to_have_count(drawn.locator("g.slot").count())


def test_karo_checkbox_is_one_undo_step(editor):
    """Karo (#828): unticking Karo draws plain boxes, one undo brings the squares back."""
    client = user()
    page = editor(hal(), client=client)
    pick(page, "k")
    step(page, lambda: field(page, "Karo").uncheck())
    expect(at(page, "k").locator("g.karo")).to_have_count(0)
    undo(page)
    expect(at(page, "k").locator("g.karo")).to_have_count(1)


def test_stellenwerte_zeigen_draws_the_place_letters_above_the_numbers(editor):
    """Stellenwerte (#828): with "Stellenwerte zeigen" each of the three number columns of a task shows the letters
    T, H, Z, E left to right (bis 1000, D = 4); without it none."""
    page = editor(hal())
    pick(page, "k")
    expect(at(page, "k").locator("text.head")).to_have_count(0)
    field(page, "Stellenwerte zeigen").check()
    heads = at(page, "k").locator("g.task[data-task='0'] text.head")
    expect(heads.first).to_be_visible()
    assert heads.all_text_contents() == ["T", "H", "Z", "E"] * 3


def test_zweite_zahl_faerben_tints_the_second_number_and_its_parts(editor):
    """Zweite Zahl färben (#828): with "Zweite Zahl färben" the second number and its parts are tinted (rect.tint,
    #9cc3f5 at 0.35); without it none."""
    page = editor(hal())
    pick(page, "k")
    expect(at(page, "k").locator("rect.tint")).to_have_count(0)
    field(page, "Zweite Zahl färben").check()
    tints = at(page, "k").locator("rect.tint")
    expect(tints.first).to_be_visible()
    assert tints.count() > 0
    # See-through, so that the Karo squares stay visible under the tint.
    expect(tints.first).to_have_attribute("fill", "#9cc3f5")
    expect(tints.first).to_have_attribute("fill-opacity", "0.35")


def test_rechenzeichen_der_schritte_drucken_off_leaves_the_signs_out_of_the_step_lines(
    editor, browser, server
):
    """Rechenzeichen (#828): with the signs of the steps off, the pupils' sheet has a sign only in each task line; the
    key still shows the signs of every step."""
    page = editor(hal(props={"ops": False}))
    pick(page, "k")
    expect(at(page, "k").locator("text.op")).to_have_count(6)
    expect(at(page, "k").locator("text.eq")).to_have_count(6)
    paper = key_print(browser, server, sheet_id(page))
    assert paper.locator(".halbschriftlich text.op").count() > 6
    assert paper.locator(".halbschriftlich text.eq").count() > 6
    paper.context.close()


def test_a_task_with_many_answers_gets_room_for_any_of_them(editor):
    """Eigene Zahlen (#828): a task with only its result typed (101: 1 + 100, but also 50 + 51) has many answers, so
    its pupils' sheet gets S step lines (3 with dreistellig), not only the one line of 1 + 100."""
    page = editor(hal(props={"count": 1, "typed": [[0, 2, 101]]}))
    task = at(page, "k").locator('g.task[data-task="0"]')
    expect(task).to_have_class(re.compile(r"\bmany\b"))
    expect(task.locator('g.slot[data-pos="0"]')).to_have_count(1 + 3)


def test_neu_wuerfeln_changes_only_the_seed(editor, browser, server):
    """Neu würfeln (#828): the button changes the seed and nothing else in the props; the tasks change."""
    client = user()
    page = editor(hal(), client=client)
    pick(page, "k")
    before = props_of(doc(page, client))
    step(page, lambda: page.get_by_role("button", name="Neu würfeln", exact=True).click())
    after = props_of(doc(page, client))
    assert after["seed"] != before["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }


@pytest.mark.parametrize(
    ("key", "before", "after", "act"),
    [
        ("op", "+", "-", lambda p: field(p, "Rechenart").select_option(label="Minus")),
        ("max", 1000, 100, lambda p: field(p, "Zahlenraum").select_option(label="bis 100")),
        (
            "digits",
            3,
            2,
            lambda p: field(p, "Stellen der zweiten Zahl").select_option(label="zweistellig"),
        ),
        (
            "einer",
            "any",
            "yes",
            lambda p: field(p, "Übergang bei den Einern").select_option(label="mit Übergang"),
        ),
        (
            "zehner",
            "any",
            "no",
            lambda p: field(p, "Übergang bei den Zehnern").select_option(label="ohne Übergang"),
        ),
        ("grid", True, False, lambda p: field(p, "Karo").uncheck()),
        ("head", False, True, lambda p: field(p, "Stellenwerte zeigen").check()),
        ("tint", False, True, lambda p: field(p, "Zweite Zahl färben").check()),
        ("ops", True, False, lambda p: field(p, "Rechenzeichen der Schritte drucken").uncheck()),
    ],
    ids=[
        "rechenart",
        "zahlenraum",
        "stellen",
        "einer",
        "zehner",
        "karo",
        "stellenwerte",
        "faerben",
        "rechenzeichen",
    ],
)
def test_each_setting_is_one_undo_step_and_redo_brings_it_back(editor, key, before, after, act):
    """Settings (#828): each setting stores its prop in one step; one Ctrl+Z brings the old, one redo the new."""
    client = user()
    page = editor(hal(), client=client)
    pick(page, "k")
    if key == "zehner":
        expect(field(page, "Übergang bei den Zehnern")).to_be_visible()
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_steppers_show_their_counts_and_stop_at_their_limits(editor):
    """Panel (#828): "6 Aufgaben" and "2 nebeneinander" show the counts; the steppers stop at 1 and 12 tasks and at 1
    and 3 columns."""
    page = editor(hal(props={"count": 12, "columns": 3}))
    pick(page, "k")
    expect(panel(page, "Eine Aufgabe mehr")).to_be_disabled()
    expect(panel(page, "Mehr Aufgaben nebeneinander")).to_be_disabled()
    expect(page.locator(".panel").get_by_text("12 Aufgaben", exact=True)).to_be_visible()
    expect(page.locator(".panel").get_by_text("3 nebeneinander", exact=True)).to_be_visible()
    page2 = editor(hal(props={"count": 1, "columns": 1}))
    pick(page2, "k")
    expect(panel(page2, "Eine Aufgabe weniger")).to_be_disabled()
    expect(panel(page2, "Weniger Aufgaben nebeneinander")).to_be_disabled()
    expect(page2.locator(".panel").get_by_text("1 Aufgabe", exact=True)).to_be_visible()


def test_one_more_task_grows_the_block_in_one_undo_step(editor):
    """Panel (#828): "Eine Aufgabe mehr" from 6 to 7 tasks adds a row (4 rows, 116 mm high at 146 mm wide); one undo
    brings the height back to 86."""
    client = user()
    page = editor(hal(), client=client)
    pick(page, "k")
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())
    stored = {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}
    assert stored["k"]["props"]["count"] == 7
    assert stored["k"]["h"] == pytest.approx(116)
    undo(page)
    assert {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}["k"]["h"] == pytest.approx(
        H
    )


def test_a_reload_keeps_the_tasks_the_settings_and_the_typed_numbers(editor):
    """Settings (#828): after a reload the tasks, the settings and the typed numbers are as they were."""
    client = user()
    props = {
        **HAL,
        "count": 4,
        "columns": 3,
        "op": "-",
        "max": 100,
        "digits": 2,
        "head": True,
        "typed": [[0, 0, 40]],
    }
    page = editor(hal(props=props), client=client)
    pick(page, "k")
    reload(page, page.url)
    expect(at(page, "k").locator(".halbschriftlich")).to_be_visible()
    assert props_of(doc(page, client)) == props
