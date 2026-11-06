"""The Zahlzerlegung block on screen and in the key: the seven Aufgabentypen, the Zahlenraum and the answers (#1078).

The docstrings name the checklist line that each test proves. The numbers are read from the page, never pinned:
the generator may change. The panel is in test_zahlzerlegung_panel.py, the block as a box in
test_zahlzerlegung_block.py, the print in test_zahlzerlegung_print.py.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_suchsel_print import key_print
from ui import at, box, doc, insert, pick, user

ZZ = {"count": 6, "columns": 2, "max": 1000, "task": "split", "seed": 7}
DEFAULTS = {k: v for k, v in ZZ.items() if k != "seed"}
TASKS = ["split", "join", "shuffled", "places", "gap", "zero", "bundle"]
PV = {"T": 1000, "H": 100, "Z": 10, "E": 1}


def fit(props):
    """The width and height a block of these props takes at insert, from layout() in zahlzerlegung/props.ts."""
    k = len(str(props["max"] if props["max"] in (100, 10000) else 1000)) - 1
    NW, DW, LT, SW, LH, CG, RG = 3 * k + 4, 8, 5, 5, 8, 10, 5
    if props["task"] == "split":
        TW = NW + SW + k * NW + (k - 1) * SW
    elif props["task"] in ("join", "shuffled", "gap"):
        TW = (k + 1) * NW + k * SW
    else:
        TW = k * (DW + LT) + SW + NW
    across = min(props["columns"], props["count"])
    rows = -(-props["count"] // props["columns"])
    vbW = across * TW + (across - 1) * CG + 1
    vbH = rows * LH + (rows - 1) * RG + 1
    return min(vbW, 180), vbH


W, H = fit(ZZ)

# The items of one task, left to right, as (kind, text); a gap has no text on the sheet.
GRID = """(root, task) => [...root.querySelectorAll(`g.task[data-task='${task}'] text.given, g.task[data-task='${task}'] rect.gap, g.task[data-task='${task}'] text.eq, g.task[data-task='${task}'] text.letter`)]
  .sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left)
  .map((e) => [
    e.matches('text.given') ? 'given' : e.matches('rect.gap') ? 'gap' : e.matches('text.eq') ? 'sign' : 'letter',
    e.matches('rect.gap') ? '' : e.textContent,
  ])"""


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlzerlegung settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zz(props=None, name="k", **more):
    """A Zahlzerlegung block with the default props, or the given ones over them."""
    return box(name, "zahlzerlegung", {**ZZ, **(props or {})}, w=W, h=H, **more)


def drawn(page, name="k"):
    return at(page, name).locator(".zahlzerlegung")


def props_of(stored):
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlzerlegung"]
    return block["props"]


def grid(root, task):
    """The items of a task as (kind, text) pairs, left to right."""
    return [tuple(item) for item in root.evaluate(GRID, task)]


def answers(paper, task):
    """The texts the key writes in the task's gaps, in order."""
    return paper.locator(f".zahlzerlegung g.task[data-task='{task}'] text.answer").evaluate_all(
        "els => els.map(e => e.textContent)"
    )


def filled(paper, task):
    """The task's items as the key fills them in: every gap with its answer."""
    gaps = iter(answers(paper, task))
    return [
        (kind, next(gaps) if kind == "gap" else text)
        for kind, text in grid(paper.locator(".zahlzerlegung"), task)
    ]


def total(items):
    """The sum of one side of the equation: a number with a place letter after it counts that letter's value."""
    values = []
    for kind, text in items:
        if kind == "letter":
            values[-1] *= PV[text]
        elif kind in ("given", "gap"):
            values.append(int(text))
    return sum(values)


def holds(items):
    """Whether the left of the "=" sums to the right of it."""
    cut = [i for i, (kind, text) in enumerate(items) if kind == "sign" and text == "="]
    assert len(cut) == 1, items
    return total(items[: cut[0]]) == total(items[cut[0] + 1 :])


def test_zahlzerlegung_is_inserted_from_the_maths_menu_with_the_defaults(editor):
    """Insert (#1078): "Zahlzerlegung" adds a block with the default props and a whole seed, 6 tasks in 2 columns."""
    client = user()
    page = editor(client=client)
    insert(page, "Zahlzerlegung")
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlzerlegung", exact=True)
    ).to_be_visible()
    props = props_of(doc(page, client))
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    expect(page.locator(".zahlzerlegung").first.locator("g.task")).to_have_count(6)


@pytest.mark.parametrize("task", TASKS)
def test_each_task_type_draws_its_shape(editor, task):
    """Aufgabentyp (#1078): every task of a stored block with a fixed seed has the items of its type."""
    page = editor(zz({"task": task}))
    pick(page, "k")
    shown = drawn(page)
    for t in range(6):
        items = grid(shown, t)
        kinds = [kind for kind, _ in items]
        texts = [text for kind, text in items if kind == "given"]
        if task == "split":
            assert kinds == ["given", "sign"] + ["gap", "sign"] * 2 + ["gap"], items
            assert len(texts[0]) == 3 and "0" not in texts[0], items
        elif task == "join":
            assert kinds == ["given", "sign"] * 2 + ["given", "sign", "gap"], items
        elif task == "shuffled":
            assert kinds == ["given", "sign"] * 2 + ["given", "sign", "gap"], items
            values = [int(text) for text in texts]
            assert values != sorted(values, reverse=True), items
        elif task == "places":
            assert kinds[-2:] == ["sign", "gap"], items
            letters = [text for kind, text in items if kind == "letter"]
            assert set(letters) <= set("HZE"), items
            if t % 2 == 0:
                assert letters == [p for p in "HZE" if p in letters], items
            elif len(letters) >= 2:
                assert letters != [p for p in "HZE" if p in letters], items
        elif task == "gap":
            assert kinds.count("gap") == 1 and kinds[-2:] == ["sign", "given"], items
        elif task == "zero":
            assert kinds == ["given", "sign"] + ["gap", "letter"] * 3, items
            assert "0" in texts[0][1:] and "0" not in texts[0][:1], items
        elif task == "bundle":
            assert kinds == ["given", "letter"] * 3 + ["sign", "gap"], items
            counts = texts
            assert sum(1 for c in counts if 10 <= int(c) <= 19) == 1, counts
            assert int(counts[0]) >= 1, counts


def test_max_100_shows_zehner_and_einer_only(editor, browser, server):
    """Zahlenraum (#1078): "bis 100" shows only the places Z and E, and every number has 2 digits."""
    page = editor(zz({"max": 100, "task": "places", "count": 6}))
    pick(page, "k")
    shown = drawn(page)
    paper = key_print(browser, server, sheet_id(page))
    for t in range(6):
        letters = [text for kind, text in grid(shown, t) if kind == "letter"]
        assert set(letters) <= {"Z", "E"}, letters
        [number] = answers(paper, t)
        assert 10 <= int(number) <= 99, number
    paper.context.close()


def test_max_10000_gives_four_digit_numbers(editor, browser, server):
    """Zahlenraum (#1078): "bis 10 000" gives 4-digit numbers in the key."""
    page = editor(zz({"max": 10000, "task": "join", "count": 4}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for t in range(4):
        n = int("".join(answers(paper, t)) or 0)
        assert 1000 <= n <= 9999, n
    paper.context.close()


@pytest.mark.parametrize("task", TASKS)
def test_every_gap_of_a_block_has_the_same_width(editor, task):
    """Lücke (#1078): all rect.gap of one block share one width, so a gap never gives away its answer."""
    page = editor(zz({"task": task}))
    pick(page, "k")
    widths = (
        drawn(page).locator("rect.gap").evaluate_all("els => els.map(e => e.getAttribute('width'))")
    )
    assert widths and len(set(widths)) == 1, widths


@pytest.mark.parametrize("task", TASKS)
def test_the_key_fills_every_gap_and_the_equation_holds(editor, browser, server, task):
    """Lösungen (#1078): the key fills every gap of every task, and each equation holds."""
    page = editor(zz({"task": task}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for t in range(6):
        gaps = answers(paper, t)
        assert gaps and all(gaps), gaps
        assert holds(filled(paper, t)), filled(paper, t)
        if task == "zero":
            assert "0" in gaps, gaps
    paper.context.close()
