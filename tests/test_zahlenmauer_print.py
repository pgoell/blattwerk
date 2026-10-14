"""The Zahlenmauer on screen and on paper: the walls, the given and hidden numbers, the answer key.

The docstrings name the lines of the checklist that each test proves. The numbers are read from
the page, never pinned: the generator may change.
"""

from playwright.sync_api import expect
from test_feed_print import pdf_text, printed, sheet_id
from test_suchsel_print import key_print, red_pixels
from ui import at, box, user

BASE = 3
WALL = {
    "base": BASE,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
# The wall's stones by (row, col), each with its text or None, read from the DOM of one block.
WALLS = """els => els.map(w => [...w.querySelectorAll('.stone')].map(s => [
    +s.dataset.row, +s.dataset.col, s.querySelector('text')?.textContent ?? null]))"""
RED = "rgb(192, 57, 43)"


def walls_of(locator):
    """Each wall as a dict of (row, col) to its text, or None when hidden."""
    return [{(r, c): t for r, c, t in wall} for wall in locator.evaluate_all(WALLS)]


def test_the_editor_draws_each_wall_in_its_columns_and_adds_up(editor, browser, server):
    """P1 (A1): 4 walls of 6 stones in 2 columns, each stone the sum of the two under it."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    walls = at(page, "w").locator(".wall")
    expect(walls).to_have_count(4)
    expect(at(page, "w").locator(".stone")).to_have_count(24)
    top = [w.bounding_box() for w in walls.all()]
    assert top[0]["y"] == top[1]["y"]
    assert top[2]["y"] > top[0]["y"] and top[2]["x"] == top[0]["x"]
    paper = key_print(browser, server, sheet_id(page))
    for d in walls_of(paper.locator(".zahlenmauer .wall")):
        assert len(d) == 6
        for r in range(1, BASE):
            for c in range(BASE - r):
                assert int(d[(r, c)]) == int(d[(r - 1, c)]) + int(d[(r - 1, c + 1)])
    paper.context.close()


def test_the_pupils_sheet_shows_only_the_given_numbers(editor, browser, server):
    """P2 (A6, A14): the pupils' page has the base row only, the answer key has every stone with
    its text, and the hidden ones in red."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer text")).to_have_count(12)
    expect(paper.locator(".zahlenmauer text.given")).to_have_count(12)
    expect(paper.locator(".zahlenmauer text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer text")).to_have_count(24)
    expect(paper.locator(".zahlenmauer text.answer")).to_have_count(12)
    fills = paper.locator(".zahlenmauer text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 12
    paper.context.close()


def test_the_print_has_the_editors_numbers_and_the_pdfs_hold_them(editor, browser, server):
    """P3 (A16): the print shows the editor's numbers in the same stones, the PDF holds the given
    numbers, and the answer key's PDF has red where the pupils' PDF has none."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=60), client=client)
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    editors = walls_of(at(page, "w").locator(".zahlenmauer .wall"))
    assert walls_of(paper.locator(".zahlenmauer .wall")) == editors
    givens = paper.locator(".zahlenmauer text.given").all_text_contents()
    paper.context.close()
    assert len(givens) == 12
    tokens = pdf_text(server, client, mine).split()
    assert all(g in tokens for g in givens)
    assert red_pixels(server, client, mine, solved=False) == 0
    assert red_pixels(server, client, mine, solved=True) > 50


def test_the_empty_block_shows_no_number(editor, browser, server):
    """P4 (A10): with "leer" no stone has a text: not in the editor, on the sheet, on the key."""
    client = user()
    page = editor(box("w", "zahlenmauer", {**WALL, "empty": True}, w=180, h=60), client=client)
    expect(at(page, "w").locator(".stone")).to_have_count(24)
    expect(at(page, "w").locator(".zahlenmauer text")).to_have_count(0)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer .stone")).to_have_count(24)
    expect(paper.locator(".zahlenmauer text")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer text")).to_have_count(0)
    paper.context.close()


def test_the_numbers_stay_centred_and_the_stones_keep_their_shape(editor, browser, server):
    """P5 (A13): at 180 by 60 and at 90 by 120 each number sits in the middle of its stone, each
    stone is twice as wide as high, and the stones of the larger block are larger."""
    sizes = []
    for w, h in [(180, 60), (90, 120)]:
        page = editor(box("w", "zahlenmauer", WALL, w=w, h=h), client=user())
        stones = (
            at(page, "w")
            .locator(".stone")
            .evaluate_all(
                """els => els.map(s => {
                const r = s.querySelector('rect').getBoundingClientRect();
                const t = s.querySelector('text')?.getBoundingClientRect();
                return { w: r.width, h: r.height, cx: r.x + r.width / 2, cy: r.y + r.height / 2,
                    tx: t ? t.x + t.width / 2 : null, ty: t ? t.y + t.height / 2 : null };
            })"""
            )
        )
        for s in stones:
            assert abs(s["w"] / s["h"] - 2) < 0.06
            if s["tx"] is not None:
                assert abs(s["tx"] - s["cx"]) < 1.5 and abs(s["ty"] - s["cy"]) < 1.5
        sizes.append(stones[0]["w"])
    assert sizes[0] > sizes[1]


def test_a_block_of_five_base_stones_and_twelve_walls_stays_in_its_box(editor):
    """Own: base 5 with 12 walls in 4 columns: every stone lies inside the block's box."""
    big = {**WALL, "base": 5, "count": 12, "columns": 4, "max": 1000}
    page = editor(box("w", "zahlenmauer", big, w=180, h=60), client=user())
    expect(at(page, "w").locator(".wall")).to_have_count(12)
    inside = at(page, "w").evaluate(
        """el => { const b = el.getBoundingClientRect();
            return [...el.querySelectorAll('.stone rect')].every(r => {
                const q = r.getBoundingClientRect();
                return q.left >= b.left - 0.5 && q.right <= b.right + 0.5
                    && q.top >= b.top - 0.5 && q.bottom <= b.bottom + 0.5;
            }); }"""
    )
    assert inside


def test_free_flags_show_exactly_the_flagged_stones(editor, browser, server):
    """Own: with "Freie Wahl" the pupils' sheet shows one number per wall, the one flagged stone."""
    client = user()
    flags = [False, False, False, False, True, False]
    props = {**WALL, "given": "free", "free": flags}
    page = editor(box("w", "zahlenmauer", props, w=180, h=60), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenmauer text.given")).to_have_count(4)
    paper.context.close()
