"""The Rechendreieck on screen and on paper: the triangles, the given and hidden numbers, the key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

DREI = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 7}
RED = "rgb(192, 57, 43)"
# Each triangle's fields by index, each with its text or None when hidden, and the text's class.
TRIANGLES = """els => els.map(t => [...t.querySelectorAll('.field')].map(f => {
    const x = f.querySelector('text');
    return [+f.dataset.field, x ? x.textContent : null];
}))"""
# Each field that shows a text: the centre of its text less the centre of its shape, in px.
CENTRES = """els => els.filter(f => f.querySelector('text')).map(f => {
    const s = f.querySelector('circle, rect').getBoundingClientRect();
    const t = f.querySelector('text').getBoundingClientRect();
    return [t.x + t.width / 2 - (s.x + s.width / 2), t.y + t.height / 2 - (s.y + s.height / 2)];
})"""
# Whether every shape of the block lies inside the block's box.
INSIDE = """el => { const b = el.getBoundingClientRect();
    return [...el.querySelectorAll('.field circle, .field rect')].every(r => {
        const q = r.getBoundingClientRect();
        return q.left >= b.left - 0.5 && q.right <= b.right + 0.5
            && q.top >= b.top - 0.5 && q.bottom <= b.bottom + 0.5;
    }); }"""


def fields_of(locator):
    """Each triangle as a dict of field index to its text, or None when hidden."""
    return [{j: t for j, t in tri} for tri in locator.evaluate_all(TRIANGLES)]


def test_the_pupils_sheet_shows_only_the_given_numbers(editor, browser, server):
    """Given inner: the pupils' page has the three inner numbers of each triangle, the answer key
    also the hidden three in red (#c0392b)."""
    client = user()
    page = editor(box("d", "rechendreieck", DREI, w=180, h=50), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".rechendreieck text")).to_have_count(12)
    expect(paper.locator(".rechendreieck text.given")).to_have_count(12)
    expect(paper.locator(".rechendreieck text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechendreieck text")).to_have_count(24)
    expect(paper.locator(".rechendreieck text.answer")).to_have_count(12)
    fills = paper.locator(".rechendreieck text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 12
    paper.context.close()


def test_the_print_has_the_editors_numbers_and_outers_add_up(editor, browser, server):
    """The print shows the editor's numbers in the same fields. On the answer key each outer
    number is the sum of the two inner numbers beside it."""
    client = user()
    page = editor(box("d", "rechendreieck", DREI, w=180, h=50), client=client)
    mine = sheet_id(page)
    shown = fields_of(at(page, "d").locator(".triangle"))
    paper = printed(browser, server, mine)
    assert fields_of(paper.locator(".rechendreieck .triangle")) == shown
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = fields_of(paper.locator(".rechendreieck .triangle"))
    paper.context.close()
    for t, tri in enumerate(key):
        n = [int(tri[j]) for j in range(6)]
        sums = (n[0] + n[1], n[1] + n[2], n[2] + n[0])
        assert tuple(n[3:]) == sums, (t, n)
        assert all(key[t][j] == shown[t][j] for j in range(6) if shown[t][j] is not None)


def test_the_empty_block_shows_no_number_and_still_draws_six_fields(editor, browser, server):
    """Empty: no text in the editor, on the sheet or on the key, but all 6 fields of each triangle
    are drawn."""
    client = user()
    page = editor(box("d", "rechendreieck", {**DREI, "empty": True}, w=180, h=50), client=client)
    expect(at(page, "d").locator(".field")).to_have_count(24)
    expect(at(page, "d").locator(".rechendreieck text")).to_have_count(0)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".rechendreieck .field")).to_have_count(24)
    expect(paper.locator(".rechendreieck text")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechendreieck .field")).to_have_count(24)
    expect(paper.locator(".rechendreieck text")).to_have_count(0)
    paper.context.close()


def test_the_numbers_stay_centred_in_their_fields_at_three_sizes(editor):
    """Wide, tall and small: each number sits in the middle of its circle or box."""
    for w, h in [(180, 50), (60, 120), (40, 30)]:
        page = editor(box("d", "rechendreieck", DREI, w=w, h=h), client=user())
        centres = at(page, "d").locator(".field").evaluate_all(CENTRES)
        assert len(centres) == 12
        for dx, dy in centres:
            assert abs(dx) < 1.5 and abs(dy) < 1.5, (w, h, dx, dy)


def test_a_block_with_a_mark_shows_its_numbering(editor, browser, server):
    """A mark "1." on the block shows as the number 1 in the editor and on the sheet."""
    client = user()
    page = editor(box("d", "rechendreieck", DREI, w=180, h=50, mark="1."), client=client)
    expect(at(page, "d").locator(".mark")).to_have_text("1.")
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".mark")).to_have_text("1.")
    paper.context.close()


def test_twelve_triangles_in_four_columns_stay_inside_the_dock_size(editor):
    """Own: twelve triangles at the dock's 180 by 50 mm: every field lies inside the block's box."""
    big = {**DREI, "count": 12, "columns": 4, "max": 1000}
    page = editor(box("d", "rechendreieck", big, w=180, h=50), client=user())
    expect(at(page, "d").locator(".triangle")).to_have_count(12)
    assert at(page, "d").evaluate(INSIDE)


def test_a_four_digit_number_fits_its_circle_and_its_box(editor):
    """Own: a typed 9999 in an inner circle and in an outer box stays inside its shape."""
    typed = [[0, 0, 9999], [0, 3, 9999]]
    props = {**DREI, "given": "free", "free": [True] * 6, "max": 1000, "typed": typed}
    page = editor(box("d", "rechendreieck", props, w=180, h=50), client=user())
    fields = at(page, "d").locator(".triangle[data-triangle='0'] .field")
    for j in (0, 3):
        field = fields.nth(j)
        assert field.evaluate(
            """f => { const s = f.querySelector('circle, rect').getBoundingClientRect();
                const t = f.querySelector('text').getBoundingClientRect();
                return t.left >= s.left && t.right <= s.right; }"""
        ), j
