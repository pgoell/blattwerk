"""The Zahlenhaus on screen and on paper: the roofs, the given and hidden numbers, the key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

HAUS = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side", "seed": 7}
RED = "rgb(192, 57, 43)"
# Each house's boxes by index: the text in each box, or None when the box shows none.
HOUSES = """els => els.map(h => [...h.querySelectorAll('g.house')].map(g =>
    [...g.querySelectorAll('g.box')].map(b => {
        const t = b.querySelector('text');
        return [+b.dataset.box, t ? t.textContent : null];
    })))"""
# Whether every shape of the block lies inside the block's box.
INSIDE = """el => { const b = el.getBoundingClientRect();
    return [...el.querySelectorAll('g.box rect, g.box circle, g.box polygon, g.box path')].every(r => {
        const q = r.getBoundingClientRect();
        return q.left >= b.left - 0.5 && q.right <= b.right + 0.5
            && q.top >= b.top - 0.5 && q.bottom <= b.bottom + 0.5;
    }); }"""


def houses_of(locator):
    """Each house of the page as a dict of box index to its text, or None when the box shows none."""
    return [{j: t for j, t in house} for block in locator.evaluate_all(HOUSES) for house in block]


def test_the_pupils_sheet_shows_only_the_given_numbers(editor, browser, server):
    """Given side: the pupils' page has the roof and the left box of each floor, 5 per house. The
    answer key has all 9 boxes per house, the 4 hidden ones in red (#c0392b)."""
    client = user()
    page = editor(box("h", "zahlenhaus", HAUS, w=120, h=55), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenhaus text")).to_have_count(20)
    expect(paper.locator(".zahlenhaus text.given")).to_have_count(20)
    expect(paper.locator(".zahlenhaus text.answer")).to_have_count(0)
    for i in range(4):
        expect(paper.locator(f".zahlenhaus g.house[data-house='{i}'] text.given")).to_have_count(5)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenhaus text")).to_have_count(36)
    expect(paper.locator(".zahlenhaus text.answer")).to_have_count(16)
    fills = paper.locator(".zahlenhaus text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 16
    paper.context.close()


def test_on_the_key_each_floor_adds_up_to_its_roof(editor, browser, server):
    """Every house in the answer key: each floor's left and right box add up to the roof."""
    client = user()
    page = editor(box("h", "zahlenhaus", HAUS, w=120, h=55), client=client)
    paper = key_print(browser, server, sheet_id(page))
    key = houses_of(paper.locator(".zahlenhaus"))
    paper.context.close()
    assert len(key) == 4
    for i, house in enumerate(key):
        assert len(house) == 9, (i, house)
        roof = int(house[0])
        for f in range(4):
            left, right = int(house[1 + 2 * f]), int(house[2 + 2 * f])
            assert left + right == roof, (i, f, roof, left, right)


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print shows the editor's numbers in the same boxes of each house."""
    client = user()
    page = editor(box("h", "zahlenhaus", HAUS, w=120, h=55), client=client)
    shown = houses_of(at(page, "h").locator(".zahlenhaus"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_houses = houses_of(paper.locator(".zahlenhaus"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = houses_of(paper.locator(".zahlenhaus"))
    paper.context.close()
    for i in range(len(shown)):
        for j in shown[i]:
            if shown[i][j] is not None:
                assert printed_houses[i][j] == shown[i][j], (i, j)
                assert key[i][j] == shown[i][j], (i, j)


def test_a_typed_wrong_floor_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: house 0 has roof 9 and floor 0 typed 3 and 3, which do not add up. On the key that
    floor shows no answer in red, and the house is marked wrong."""
    client = user()
    typed = {**HAUS, "typed": [[0, 0, 9], [0, 1, 3], [0, 2, 3]]}
    page = editor(box("h", "zahlenhaus", typed, w=120, h=55), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenhaus g.house[data-house='0'].wrong")).to_have_count(1)
    expect(
        paper.locator(".zahlenhaus g.house[data-house='0'] g.box[data-box='1'] text.answer")
    ).to_have_count(0)
    expect(
        paper.locator(".zahlenhaus g.house[data-house='0'] g.box[data-box='2'] text.answer")
    ).to_have_count(0)
    paper.context.close()


def test_the_numbers_stay_inside_the_block_at_three_sizes(editor):
    """Wide, tall and small: every shape of every house lies inside the block's box."""
    for w, h in [(180, 50), (60, 120), (40, 30)]:
        page = editor(box("h", "zahlenhaus", HAUS, w=w, h=h), client=user())
        expect(at(page, "h").locator("g.house")).to_have_count(4)
        assert at(page, "h").evaluate(INSIDE), (w, h)
