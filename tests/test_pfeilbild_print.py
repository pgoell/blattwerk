"""The Pfeilbild on screen and on paper: the given boxes, the hidden boxes and operators, the key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

PF = {
    "count": 4,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "arrows": "one",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}
ENDS = {**PF, "given": "ends"}
MINUS = "\N{MINUS SIGN}"
DOT = "\N{MIDDLE DOT}"
RED = "rgb(192, 57, 43)"
# Each picture's boxes in order: the number in each box, or None for an empty box.
PICTURES = """els => els.map(p => [...p.querySelectorAll('g.box')].map(b => {
    const t = b.querySelector('text.given, text.answer');
    return t ? Number(t.textContent) : null;
}))"""
# Each picture's arrows in order: the operator text of each arrow, or None for an empty place.
ARROWS = """els => els.map(p => [...p.querySelectorAll('g.arrow')].map(a => {
    const t = a.querySelector('text.op, text.answer');
    return t ? t.textContent : null;
}))"""


def apply(label, x):
    """The number that an arrow's label gives from x."""
    n = int(label[1:])
    return {"+": x + n, MINUS: x - n, DOT: x * n, ":": x // n}[label[0]]


def pictures_of(locator):
    """Each picture's box numbers of the locator's block, None for an empty box."""
    return locator.locator("g.picture").evaluate_all(PICTURES)


def arrows_of(locator):
    """Each picture's arrow labels of the locator's block, None for an empty place."""
    return locator.locator("g.picture").evaluate_all(ARROWS)


def test_the_pupils_sheet_shows_only_the_given_boxes(editor, browser, server):
    """Given start: the pupils' page shows box 0 of each picture and every operator, and no answer;
    the key fills the other 12 boxes in red."""
    client = user()
    page = editor(box("k", "pfeilbild", PF, w=180, h=53.9), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".pfeilbild text.given")).to_have_count(4)
    expect(paper.locator(".pfeilbild text.answer")).to_have_count(0)
    expect(paper.locator(".pfeilbild text.op")).to_have_count(12)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".pfeilbild.solved")).to_have_count(1)
    expect(paper.locator(".pfeilbild text.answer")).to_have_count(12)
    fills = paper.locator(".pfeilbild text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 12
    paper.context.close()


def test_the_key_fills_the_empty_boxes_and_operators_in_red(editor, browser, server):
    """Given ends: the key fills the 2 hidden boxes and the 3 operators of each picture with text.answer,
    20 in all, in red; the pupils' page shows the first and last box only."""
    client = user()
    page = editor(box("k", "pfeilbild", ENDS, w=180, h=53.9), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".pfeilbild text.given")).to_have_count(8)
    expect(paper.locator(".pfeilbild text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".pfeilbild text.answer")).to_have_count(20)
    fills = paper.locator(".pfeilbild text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 20
    paper.context.close()


def test_on_the_key_each_arrow_gives_the_next_box(editor, browser, server):
    """Every picture on the key: applying each arrow's operator to a box gives the box after it."""
    client = user()
    page = editor(box("k", "pfeilbild", PF, w=180, h=53.9), client=client)
    paper = key_print(browser, server, sheet_id(page))
    key = pictures_of(paper.locator(".pfeilbild"))
    labels = arrows_of(paper.locator(".pfeilbild"))
    paper.context.close()
    assert len(key) == PF["count"]
    for numbers, ops in zip(key, labels, strict=True):
        assert all(n is not None for n in numbers), numbers
        for j, op in enumerate(ops):
            assert apply(op, numbers[j]) == numbers[j + 1], (numbers, ops, j)


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print shows the editor's numbers in the same boxes of each picture."""
    client = user()
    page = editor(box("k", "pfeilbild", PF, w=180, h=53.9), client=client)
    shown = pictures_of(at(page, "k").locator(".pfeilbild"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_numbers = pictures_of(paper.locator(".pfeilbild"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = pictures_of(paper.locator(".pfeilbild"))
    paper.context.close()
    for i, picture in enumerate(shown):
        for j, n in enumerate(picture):
            if n is not None:
                assert printed_numbers[i][j] == n, (i, j)
                assert key[i][j] == n, (i, j)


def test_a_wrong_typed_picture_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: picture 0 has 5 in box 0 and 9999 in box 1, which no operator fits. On the key that
    picture is marked wrong and shows no answer in red."""
    client = user()
    typed = {**PF, "typed": [[0, 0, 5], [0, 1, 9999]]}
    page = editor(box("k", "pfeilbild", typed, w=180, h=53.9), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".pfeilbild g.picture[data-picture='0'].wrong")).to_have_count(1)
    expect(paper.locator(".pfeilbild g.picture[data-picture='0'] text.answer")).to_have_count(0)
    # The other pictures keep their answers: picture 1 has 3 hidden boxes, its operators are given.
    expect(paper.locator(".pfeilbild g.picture[data-picture='1'] text.answer")).to_have_count(3)
    paper.context.close()
