"""The Operatorfeld on screen and on paper: the given boxes, the hidden boxes and operators, the key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

OF = {
    "centre": False,
    "count": 2,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "only": "none",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}
OPS = {**OF, "given": "ops"}
MINUS = "\N{MINUS SIGN}"
DOT = "\N{MIDDLE DOT}"
RED = "rgb(192, 57, 43)"
H = 85.99  # the default height: 75 * 180 / 157, rounded as insert.ts does
# Each field's boxes in order: the number in each box, or None for an empty box.
BOXES = """els => els.map(f => [...f.querySelectorAll('g.box')].map(b => {
    const t = b.querySelector('text.given, text.answer');
    return t ? Number(t.textContent) : null;
}))"""
# Each field's link labels in order: the operator text of each link, or None for an empty place.
LINKS = """els => els.map(f => [...f.querySelectorAll('g.link')].map(a => {
    const t = a.querySelector('text.op, text.answer');
    return t ? t.textContent : null;
}))"""


def apply(label, x):
    """The number that a link's label gives from x."""
    n = int(label[1:])
    return {"+": x + n, MINUS: x - n, DOT: x * n, ":": x // n}[label[0]]


def fields_of(locator):
    """Each field's box numbers of the locator's block, None for an empty box."""
    return locator.locator("g.field").evaluate_all(BOXES)


def links_of(locator):
    """Each field's link labels of the locator's block, None for an empty place."""
    return locator.locator("g.field").evaluate_all(LINKS)


def test_the_pupils_sheet_shows_only_the_given_boxes(editor, browser, server):
    """Given start: the pupils' page shows box 0 of each field and every operator, and no answer; the key
    fills the other boxes in red."""
    client = user()
    page = editor(box("k", "operatorfeld", OF, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".operatorfeld text.given")).to_have_count(2)
    expect(paper.locator(".operatorfeld text.answer")).to_have_count(0)
    expect(paper.locator(".operatorfeld text.op")).to_have_count(8)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    # 2 fields of 4 boxes, box 0 given: 6 boxes to fill.
    expect(paper.locator(".operatorfeld text.answer")).to_have_count(6)
    fills = paper.locator(".operatorfeld text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 6
    paper.context.close()


def test_the_key_fills_the_missing_boxes_and_ops_in_red_and_the_pupils_sheet_shows_only_given(
    editor, browser, server
):
    """Given ops: the pupils' page shows every box and no operator; the key fills the 8 operators in red."""
    client = user()
    page = editor(box("k", "operatorfeld", OPS, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".operatorfeld text.given")).to_have_count(8)
    expect(paper.locator(".operatorfeld text.op")).to_have_count(0)
    expect(paper.locator(".operatorfeld text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    # 2 fields of 4 links each: every operator hidden.
    expect(paper.locator(".operatorfeld text.answer")).to_have_count(8)
    fills = paper.locator(".operatorfeld text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 8
    paper.context.close()


def test_with_ops_hidden_and_several_rechenarten_the_key_says_other_answers_count_too(
    editor, browser, server
):
    """Given ops ohne Zentrum with Plus and Mal: a hidden operator may be "+4" or "·2", so the key carries the
    note "Auch andere Lösungen sind richtig." in red; the pupils' sheet has no note."""
    client = user()
    page = editor(
        box("k", "operatorfeld", {**OPS, "ops": ["+", "*"]}, w=180, h=H + 6),
        client=client,
    )
    note = ".operatorfeld text.note"
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(note)).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(note)).to_have_count(1)
    expect(paper.locator(note)).to_have_text("Auch andere Lösungen sind richtig.")
    expect(paper.locator(note)).to_have_css("fill", RED)
    paper.context.close()


def test_mit_zentrum_never_has_the_note_and_plus_minus_with_ops_hidden_has_none(
    editor, browser, server
):
    """Other answers: mit Zentrum never has the note, and ohne Zentrum with Plus and Minus only (one right
    answer) has none either."""
    client = user()
    page = editor(
        box("c", "operatorfeld", {**OPS, "centre": True}, w=180, h=H),
        box("p", "operatorfeld", OPS, w=180, h=H, y=150),
        client=client,
    )
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".operatorfeld text.note")).to_have_count(0)
    paper.context.close()


def test_on_the_key_each_link_gives_the_next_box(editor, browser, server):
    """Every field on the key: applying each link's operator to one box gives the box it joins, in the
    order the arrow reads (forward or back)."""
    client = user()
    page = editor(box("k", "operatorfeld", OF, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    key = fields_of(paper.locator(".operatorfeld"))
    labels = links_of(paper.locator(".operatorfeld"))
    paper.context.close()
    assert len(key) == OF["count"]
    for numbers, ops in zip(key, labels, strict=True):
        assert all(n is not None for n in numbers), numbers
        k = len(numbers)
        for j, op in enumerate(ops):
            a, b = numbers[j], numbers[(j + 1) % k]
            assert apply(op, a) == b or apply(op, b) == a, (numbers, ops, j)


# Each link of each field on paper: its label, the numbers of the box its line starts at and of the box its arrow
# head points to. The boxes are found from the drawing (the nearest box to the line's start and to the head's tip),
# not from the link's data, so that the test reads the sheet as a pupil does.
ARROWS = """els => els.map(f => {
    const boxes = [...f.querySelectorAll('g.box')].map(b => {
        const r = b.querySelector('rect');
        const t = b.querySelector('text.given, text.answer');
        return { x: +r.getAttribute('x') + 5, y: +r.getAttribute('y') + 5, n: t ? Number(t.textContent) : null };
    });
    const near = (x, y) => boxes.reduce((a, b) => Math.hypot(b.x - x, b.y - y) < Math.hypot(a.x - x, a.y - y) ? b : a).n;
    return [...f.querySelectorAll('g.link')].map(a => {
        const [line, head] = a.querySelectorAll('path');
        const s = line.getAttribute('d').match(/M([-\\d.e]+) ([-\\d.e]+)/);
        const h = head.getAttribute('d').match(/M([-\\d.e]+) ([-\\d.e]+)/);
        const t = a.querySelector('text.op, text.answer');
        return [t ? t.textContent : null, near(+s[1], +s[2]), near(+h[1], +h[2])];
    });
})"""


@pytest.mark.parametrize(
    "ops, centre",
    [
        (["+"], False),
        (["-"], False),
        (["+", "-"], False),
        (["*"], False),
        ([":"], False),
        (["+"], True),
    ],
    ids=["plus", "minus", "plus-minus", "mal", "geteilt", "zentrum-plus"],
)
def test_every_arrow_points_the_way_its_task_reads(editor, browser, server, ops, centre):
    """On the key every task reads along its arrow: the box at the line's start, the label, the box at the
    arrow head (with Plus only a step down is a "+" whose arrow points back against the ring)."""
    client = user()
    props = {**OF, "ops": ops, "centre": centre, "count": 6, "columns": 3, "boxes": 8, "max": 100}
    page = editor(box("k", "operatorfeld", props, w=180, h=200), client=client)
    paper = key_print(browser, server, sheet_id(page))
    fields = paper.locator(".operatorfeld g.field").evaluate_all(ARROWS)
    paper.context.close()
    assert len(fields) == 6
    for links in fields:
        assert len(links) == 8
        for label, start, end in links:
            assert apply(label, start) == end, (label, start, end, links)


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print shows the editor's numbers in the same boxes of each field."""
    client = user()
    page = editor(box("k", "operatorfeld", OF, w=180, h=H), client=client)
    shown = fields_of(at(page, "k").locator(".operatorfeld"))
    ops_shown = links_of(at(page, "k").locator(".operatorfeld"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_numbers = fields_of(paper.locator(".operatorfeld"))
    assert links_of(paper.locator(".operatorfeld")) == ops_shown
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = fields_of(paper.locator(".operatorfeld"))
    paper.context.close()
    for i, field in enumerate(shown):
        for j, n in enumerate(field):
            if n is not None:
                assert printed_numbers[i][j] == n, (i, j)
                assert key[i][j] == n, (i, j)


def test_a_wrong_typed_field_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: with Mal only, field 0 has 5 in box 0 and 9999 in box 1, which no operator fits. On the key that field
    is marked wrong and shows no answer in red; the other field keeps its answers."""
    client = user()
    typed = {**OF, "ops": ["*"], "typed": [[0, 0, 5], [0, 1, 9999]]}
    page = editor(box("k", "operatorfeld", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".operatorfeld g.field[data-field='0'].wrong")).to_have_count(1)
    expect(paper.locator(".operatorfeld g.field[data-field='0'] text.answer")).to_have_count(0)
    # Field 1 has 3 hidden boxes and no hidden operator.
    expect(paper.locator(".operatorfeld g.field[data-field='1'] text.answer")).to_have_count(3)
    paper.context.close()
