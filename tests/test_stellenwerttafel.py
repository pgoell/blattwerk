"""The Stellenwerttafel mit Plättchen on screen and in the key: its drawing and its settings (#1077).

The docstrings name the checklist line that each test proves. The numbers are read from the page, never pinned:
the generator may change. The panel is in test_stellenwerttafel_panel.py, the block as a box in
test_stellenwerttafel_block.py, the print in test_stellenwerttafel_print.py.
"""

from collections import Counter

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_suchsel_print import key_print
from ui import at, box, doc, insert, pick, user

SWT = {
    "count": 4,
    "columns": 2,
    "max": 1000,
    "task": "read",
    "dots": 9,
    "zero": False,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in SWT.items() if k != "seed"}
W = 147  # the default width: 2 tasks side by side at scale 1
H = 47  # the default height: 2 rows at scale 1


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Stellenwerttafel settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def sw(props=None, name="k", **more):
    """A Stellenwerttafel block with the default props, or the given ones over them."""
    return box(name, "stellenwerttafel", {**SWT, **(props or {})}, w=W, h=H, **more)


def drawn(page, name="k"):
    return at(page, name).locator(".stellenwerttafel")


def props_of(stored):
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "stellenwerttafel"]
    return block["props"]


def cells(shown, task):
    """The dots of each column of a task: {column value: number of dots}. A dot sits beside its g.cell, by data-v."""
    got = shown.locator(f"g.task[data-task='{task}'] circle.dot").evaluate_all(
        "els => els.map(e => +e.dataset.v)"
    )
    return Counter(got)


def empty_columns(shown):
    """The dots of each column of each task, one number per g.cell: 0 for an empty column."""
    return shown.locator("g.task g.cell").evaluate_all(
        "els => els.map(c => c.closest('g.task').querySelectorAll(`circle.dot[data-v='${c.dataset.v}']`).length)"
    )


def key_number(paper, task):
    """The number the key writes in the task's number box, as an int."""
    return int(
        paper.locator(
            f".stellenwerttafel g.task[data-task='{task}'] g.slot text.answer"
        ).text_content()
    )


def digits(n):
    """The digits of n per place, highest first, as three places (Hunderter, Zehner, Einer)."""
    return [n // 100, (n // 10) % 10, n % 10]


def moves_of(counts):
    """Every number one dot moved to another column makes, rising. counts: the dots of H, Z, E."""
    res = []
    for i in range(3):
        if counts[i] < 1:
            continue
        for j in range(3):
            if j == i or counts[j] > 8:
                continue
            e = list(counts)
            e[i] -= 1
            e[j] += 1
            res.append(e[0] * 100 + e[1] * 10 + e[2])
    return sorted(res)


def test_stellenwerttafel_is_inserted_from_the_maths_menu_with_the_defaults(editor):
    """Insert (#1077): "Stellenwerttafel" adds a block with the default props and a whole seed, 4 tasks in 2 columns, the heads H Z E."""
    client = user()
    page = editor(client=client)
    insert(page, "Stellenwerttafel")
    expect(
        page.locator(".panel").get_by_role("heading", name="Stellenwerttafel", exact=True)
    ).to_be_visible()
    found = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "stellenwerttafel"]
    assert len(found) == 1
    props = found[0]["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    shown = page.locator(".stellenwerttafel").first
    expect(shown.locator("g.task")).to_have_count(4)
    heads = shown.locator("g.table text.head").evaluate_all("els => els.map(e => e.textContent)")
    assert heads[:3] == ["H", "Z", "E"], heads


def test_max_10000_adds_the_t_column(editor):
    """Zahlenraum (#1077): "bis 10 000" adds the T column in front: the heads T H Z E."""
    page = editor(sw({"max": 10000, "count": 2}))
    pick(page, "k")
    heads = (
        drawn(page).locator("g.table text.head").evaluate_all("els => els.map(e => e.textContent)")
    )
    assert heads[:4] == ["T", "H", "Z", "E"], heads


def test_read_shows_dots_and_the_key_writes_the_number(editor, browser, server):
    """Plättchen gegeben (#1077): the dots per column are the digits of the key's number; the digit sum is at most the dots; no 0 digit with Leere Stellen off."""
    page = editor(sw({"count": 6}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.task")).to_have_count(6)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        found = cells(shown, task)
        n = key_number(paper, task)
        assert 1 <= n <= 999, n
        assert [found[100], found[10], found[1]] == digits(n), (found, n)
        assert sum(found.values()) <= 9, found
        assert all(c >= 1 for c in found.values()), found
    paper.context.close()


def test_lay_shows_the_number_and_the_key_draws_its_dots(editor, browser, server):
    """Zahl gegeben (#1077): the sheet shows the number and no dot; the key draws the dots of each column as the digits."""
    page = editor(sw({"task": "lay", "count": 4}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("circle.dot")).to_have_count(0)
    given = [
        int(shown.locator(f"g.task[data-task='{t}'] text.given").first.text_content())
        for t in range(4)
    ]
    assert all(1 <= n <= 999 for n in given), given
    paper = key_print(browser, server, sheet_id(page))
    for task, n in enumerate(given):
        found = paper.locator(
            f".stellenwerttafel g.task[data-task='{task}'] circle.dot.answer"
        ).count()
        assert found == sum(digits(n)), (n, found)
        for v, want in zip((100, 10, 1), digits(n), strict=True):
            got = paper.locator(
                f".stellenwerttafel g.task[data-task='{task}'] circle.dot.answer[data-v='{v}']"
            ).count()
            assert got == want, (n, v, got)
    paper.context.close()


def test_move_key_lists_every_number_one_move_makes(editor, browser, server):
    """Ein Plättchen verschieben (#1077): the key lists every number one move makes, in the boxes in order, rising."""
    page = editor(sw({"task": "move", "count": 8}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.task")).to_have_count(8)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(8):
        found = cells(shown, task)
        counts = [found[100], found[10], found[1]]
        want = moves_of(counts)
        assert len(want) >= 1, counts
        boxes = paper.locator(f".stellenwerttafel g.task[data-task='{task}'] rect.box").count()
        assert boxes == 6, boxes
        got = paper.locator(
            f".stellenwerttafel g.task[data-task='{task}'] text.answer"
        ).evaluate_all("els => els.map(e => +e.textContent)")
        assert got == want, (counts, got, want)
    paper.context.close()


def test_dots_caps_the_dots_of_every_task(editor):
    """Plättchen (#1077): with dots 4, every task has at least 1 and at most 4 dots."""
    page = editor(sw({"dots": 4, "count": 12, "zero": True}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.task")).to_have_count(12)
    for task in range(12):
        total = shown.locator(f"g.task[data-task='{task}'] circle.dot").count()
        assert 1 <= total <= 4, (task, total)


def test_zero_on_lets_columns_be_empty(editor):
    """Leere Stellen (#1077): with Leere Stellen on some column of the drawn tasks is empty; off, none is."""
    page = editor(sw({"zero": True, "count": 12, "dots": 9}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.task")).to_have_count(12)
    assert 0 in empty_columns(shown), empty_columns(shown)
    other = editor(sw({"zero": False, "count": 12, "dots": 9}))
    pick(other, "k")
    assert 0 not in empty_columns(drawn(other)), empty_columns(drawn(other))
