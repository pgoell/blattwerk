"""The Stellenwert-Bild block on screen and in the key: its drawing and its settings (#1076).

The docstrings name the checklist line that each test proves. The numbers are read from the page, never pinned:
the generator may change. The panel is in test_stellenwertbild_panel.py, the block as a box in
test_stellenwertbild_block.py, the print in test_stellenwertbild_print.py.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_suchsel_print import key_print
from ui import at, box, doc, insert, pick, user

SW = {
    "count": 4,
    "columns": 2,
    "max": 1000,
    "task": "read",
    "table": True,
    "zero": False,
    "bundle": False,
    "seed": 7,
}
DEFAULTS = {k: v for k, v in SW.items() if k != "seed"}
W = 175  # the default width: 2 tasks of 82.8 mm and a gap of 8 mm, at scale 1
H = 119  # the default height: 2 rows of 56 mm and a gap of 6 mm, at scale 1


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Stellenwert-Bild settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def sw(props=None, name="k", **more):
    """A Stellenwert-Bild block with the default props, or the given ones over them."""
    return box(name, "stellenwertbild", {**SW, **(props or {})}, w=W, h=H, **more)


def drawn(page, name="k"):
    return at(page, name).locator(".stellenwertbild")


def props_of(stored):
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "stellenwertbild"]
    return block["props"]


def pieces(locator, task):
    """The value (data-v) of each piece of the task, in order."""
    return locator.locator(f"g.task[data-task='{task}'] g.piece").evaluate_all(
        "els => els.map(e => +e.dataset.v)"
    )


def answer(paper, task):
    """The number the key writes in the task's number box, as an int."""
    return int(
        paper.locator(
            f".stellenwertbild g.task[data-task='{task}'] g.slot text.answer"
        ).text_content()
    )


def digits(n):
    """The digits of n per place, highest first, as three places."""
    return [n // 100, (n // 10) % 10, n % 10]


def test_stellenwertbild_is_inserted_from_the_maths_menu_with_the_defaults(editor):
    """Insert (#1076): "Stellenwert-Bild" adds a block with the default props and a whole seed, 4 tasks in 2 columns."""
    client = user()
    page = editor(client=client)
    insert(page, "Stellenwert-Bild")
    expect(
        page.locator(".panel").get_by_role("heading", name="Stellenwert-Bild", exact=True)
    ).to_be_visible()
    stored = doc(page, client)
    block = [b for b in stored["pages"][0]["blocks"] if b["type"] == "stellenwertbild"]
    assert len(block) == 1
    props = block[0]["props"]
    assert {k: v for k, v in props.items() if k != "seed"} == DEFAULTS
    assert isinstance(props["seed"], int)
    shown = page.locator(".stellenwertbild").first
    expect(shown.locator("g.task")).to_have_count(4)


def test_max_1000_read_draws_a_three_digit_number_of_plates_rods_and_cubes(editor, browser, server):
    """Zahlenraum (#1076): "bis 1000" read: each task's pieces make a 3-digit number, 1 to 9 plates, and the key has it."""
    page = editor(sw({"count": 6}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    shown = drawn(page)
    for task in range(6):
        found = pieces(shown, task)
        plates = found.count(100)
        assert 1 <= plates <= 9, found
        n = answer(paper, task)
        assert 100 <= n <= 999, n
        assert sum(found) == n, (found, n)
    paper.context.close()


def test_max_100_read_draws_no_plate(editor):
    """Zahlenraum (#1076): "bis 100" draws no Hunderterplatte in any task."""
    page = editor(sw({"max": 100, "count": 6}))
    pick(page, "k")
    expect(drawn(page).locator("g.piece[data-v='10']").first).to_be_visible()
    expect(drawn(page).locator("g.piece[data-v='100']")).to_have_count(0)


def test_read_with_table_shows_the_table_with_heads_and_the_key_fills_it(editor, browser, server):
    """Stellenwerttafel (#1076): "read" with the table shows H Z E over the cells; the key fills the cells and the box."""
    page = editor(sw({"count": 2}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("g.table").first).to_be_visible()
    heads = shown.locator("g.table text.head").evaluate_all("els => els.map(e => e.textContent)")
    assert heads[:3] == ["H", "Z", "E"], heads
    paper = key_print(browser, server, sheet_id(page))
    for task in range(2):
        expect(
            paper.locator(f".stellenwertbild g.task[data-task='{task}'] text.answer").first
        ).to_be_visible()
        n = answer(paper, task)
        cells = paper.locator(
            f".stellenwertbild g.task[data-task='{task}'] g.cell text.answer"
        ).evaluate_all("els => els.map(e => +e.textContent)")
        assert cells == digits(n), (cells, n)
    paper.context.close()


def test_read_without_table_has_no_table(editor):
    """Stellenwerttafel (#1076): "read" with the table off draws no g.table, only the number box."""
    page = editor(sw({"table": False, "count": 2}))
    pick(page, "k")
    expect(drawn(page).locator("g.slot").first).to_be_visible()
    expect(drawn(page).locator("g.table")).to_have_count(0)


def test_draw_shows_the_frame_and_the_number_and_the_key_the_symbols(editor, browser, server):
    """Aufgabentyp (#1076): "draw" shows an empty frame and the given number, no symbol on the sheet; the key shows
    one symbol per digit: squares for H, strokes for Z, dots for E."""
    page = editor(sw({"task": "draw", "count": 2}))
    pick(page, "k")
    shown = drawn(page)
    expect(shown.locator("rect.frame").first).to_be_visible()
    expect(shown.locator(".sym")).to_have_count(0)
    # The given number is text.given in the key too, not text.answer, and the sheet shows it as well.
    given = [
        int(shown.locator(f"g.task[data-task='{t}'] g.slot text.given").text_content())
        for t in range(2)
    ]
    assert all(100 <= n <= 999 for n in given), given
    paper = key_print(browser, server, sheet_id(page))
    for task, number in enumerate(given):
        key = paper.locator(f".stellenwertbild g.task[data-task='{task}']")
        h, z, e = digits(number)
        expect(key.locator(".sym[data-v='100']")).to_have_count(h)
        expect(key.locator(".sym[data-v='10']")).to_have_count(z)
        expect(key.locator(".sym[data-v='1']")).to_have_count(e)
    paper.context.close()


def test_zero_on_gives_every_number_a_zero_in_a_place_that_is_not_the_first(
    editor, browser, server
):
    """Stellen mit 0 (#1076): with the checkbox on, every drawn number has a 0 in a place that is not the leading one."""
    page = editor(sw({"zero": True, "count": 6}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        n = answer(paper, task)
        assert "0" in str(n)[1:], n
    paper.context.close()


def test_bundle_has_one_place_of_10_to_19_and_the_key_shows_the_exchange(editor, browser, server):
    """Bündeln (#1076): with the checkbox on, exactly one place has 10 to 19 pieces, and the key shows the exchanged form."""
    page = editor(sw({"bundle": True, "count": 4}))
    pick(page, "k")
    shown = drawn(page)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(4):
        found = pieces(shown, task)
        counts = [found.count(v) for v in (100, 10, 1)]
        assert sum(1 for c in counts if 10 <= c <= 19) == 1, counts
        n = answer(paper, task)
        h, z, e = digits(n)
        expect(
            paper.locator(f".stellenwertbild g.task[data-task='{task}'] text.answer.exchanged")
        ).to_have_text(f"= {h} H {z} Z {e} E")
    paper.context.close()


def test_the_pieces_add_up_to_the_key_number_in_every_read_task(editor, browser, server):
    """Summe (#1076): the pieces of each read task add up to its number in the key: Σ pieces times value."""
    page = editor(sw({"count": 4}))
    pick(page, "k")
    shown = drawn(page)
    paper = key_print(browser, server, sheet_id(page))
    for task in range(4):
        assert sum(pieces(shown, task)) == answer(paper, task)
    paper.context.close()
