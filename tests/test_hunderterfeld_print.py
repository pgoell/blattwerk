"""The Hunderterfeld on screen and on paper: its cells, numbers, tints, dots and key.

The docstrings name what each test proves. Tints, hidden numbers and the Ausschnitt come from the
model in frontend/src/hunderterfeld.ts; the tests that need them say so.
"""

import pytest
from pixels import LIMITS, measures, over, screen_and_print
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, sheet, user

PROPS = {
    "look": "tafel",
    "from": 1,
    "show": "all",
    "hide": 20,
    "tint": "none",
    "times": 2,
    "line": 1,
    "color": 1,
    "cut": False,
    "fill": "count",
    "dots": 0,
    "seed": 7,
}
RED = "rgb(192, 57, 43)"
# A gap in a text: the helper waits for its answer colour, which a field alone never shows.
GAP = {
    "text": "Der Hund bellt",
    "size": 14,
    "align": "left",
    "bank": 1,
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
}
# Each drawn cell: its index, its number, its tint, its rect and its number's text, in order.
PICTURE = """el => [...el.querySelectorAll('g.cell')].map(g => [
    g.getAttribute('data-i'), g.getAttribute('data-value'), g.getAttribute('data-tint'),
    ...['x', 'y', 'width', 'height', 'fill', 'stroke-width'].map(
        a => g.querySelector('rect').getAttribute(a)),
    [...g.querySelectorAll('text')].map(t => ['class', 'x', 'y', 'font-size', 'fill'].map(
        a => t.getAttribute(a)).concat([t.textContent])),
])"""
FILLS = "els => els.map(e => getComputedStyle(e).fill)"
# The centres of the dots of the first row, and of all dots' classes.
DOTS = """c => [+c.getAttribute('cx'), +c.getAttribute('cy'), c.getAttribute('class')]"""


def field(page, name="h"):
    return at(page, name).locator(".hunderterfeld")


def test_the_print_has_the_editors_field(editor, browser, server):
    """The print shows the editor's cells, numbers, tints and frame in the same places and sizes."""
    client = user()
    page = editor(box("h", "hunderterfeld", {**PROPS, "tint": "even"}, w=100, h=100), client=client)
    shown = field(page).evaluate(PICTURE)
    assert len(shown) == 100
    paper = printed(browser, server, sheet_id(page))
    assert paper.locator(".hunderterfeld").evaluate(PICTURE) == shown
    paper.context.close()


@pytest.mark.parametrize("solved", [False, True])
def test_the_pupils_and_the_key_print_as_the_screen_shows_them(browser, server, solved):
    """The screen and the PDF of the field with tints and hidden numbers, pupil's sheet and key."""
    client = user()
    props = {**PROPS, "show": "random", "hide": 20, "tint": "even"}
    mine = sheet(
        client,
        [box("t", "text", GAP, z=1, h=20), box("h", "hunderterfeld", props, z=3, w=100, h=100)],
    )["id"]
    screen, printed_png = screen_and_print(
        browser, server, client, mine, hide_gaps=not solved, solved=solved
    )
    found, _ = measures(screen, printed_png)
    assert not over(screen, printed_png), {name: found[name] for name in LIMITS}


@pytest.mark.parametrize("solved", [False, True])
def test_the_punkte_print_as_the_screen_shows_them(browser, server, solved):
    """The screen and the PDF of a field of 37 filled dots, the pupil's sheet and the key."""
    client = user()
    props = {**PROPS, "look": "punkte", "dots": 37}
    mine = sheet(
        client,
        [box("t", "text", GAP, z=1, h=20), box("h", "hunderterfeld", props, z=3, w=100, h=100)],
    )["id"]
    screen, printed_png = screen_and_print(
        browser, server, client, mine, hide_gaps=not solved, solved=solved
    )
    found, _ = measures(screen, printed_png)
    assert not over(screen, printed_png), {name: found[name] for name in LIMITS}


def test_the_field_stays_square_and_its_numbers_scale_with_the_block(editor):
    """At 100 by 100 mm and at 150 by 150 mm the number 50 grows 1.5 times in each direction."""
    sizes = []
    for side in (100, 150):
        page = editor(box("h", "hunderterfeld", PROPS, w=side, h=side), client=user())
        bb = field(page).locator("text.given", has_text="50").bounding_box()
        sizes.append(bb)
    assert sizes[1]["width"] == pytest.approx(sizes[0]["width"] * 1.5, rel=0.02)
    assert sizes[1]["height"] == pytest.approx(sizes[0]["height"] * 1.5, rel=0.02)


def test_a_wide_block_draws_a_square_field_centred(editor):
    """A stored block of 150 by 100 mm draws the field square, centred in the block."""
    page = editor(box("h", "hunderterfeld", PROPS, w=150, h=100), client=user())
    box_ = field(page).bounding_box()
    first = at(page, "h").locator("g.cell[data-i='0'] rect").bounding_box()
    last = at(page, "h").locator("g.cell[data-i='99'] rect").bounding_box()
    width = last["x"] + last["width"] - first["x"]
    height = last["y"] + last["height"] - first["y"]
    assert width == pytest.approx(height, rel=0.01)
    centre_x = first["x"] + width / 2
    centre_y = first["y"] + height / 2
    assert centre_x == pytest.approx(box_["x"] + box_["width"] / 2, abs=1)
    assert centre_y == pytest.approx(box_["y"] + box_["height"] / 2, abs=1)


def test_the_answer_key_writes_the_hidden_numbers_in_red(editor, browser, server):
    """The pupil's sheet has no number where the field hides it; the key writes it in #c0392b."""
    client = user()
    page = editor(box("h", "hunderterfeld", {**PROPS, "show": "none"}, w=100, h=100), client=client)
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    expect(paper.locator(".hunderterfeld text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, mine)
    expect(paper.locator(".hunderterfeld text.answer")).to_have_count(100)
    assert paper.locator(".hunderterfeld text.answer").evaluate_all(FILLS) == [RED] * 100
    paper.context.close()


def test_the_dots_stand_ten_to_a_row_with_a_wider_gap_after_the_fifth(editor):
    """Dots 0 to 9 share one row; the gap between column 4 and 5 is wider than between 3 and 4."""
    page = editor(
        box("h", "hunderterfeld", {**PROPS, "look": "punkte"}, w=100, h=100), client=user()
    )
    dots = field(page).locator("circle.dot").evaluate_all(f"els => els.map({DOTS})")
    assert len(dots) == 100
    row = dots[:10]
    assert len({y for _, y, _ in row}) == 1
    xs = [x for x, _, _ in row]
    gap = [xs[i + 1] - xs[i] for i in range(9)]
    assert gap[4] > gap[3]


def test_the_last_number_sits_inside_its_cell(editor):
    """Extra: with 1 to 100 the number 100 sits inside its own cell, not over the cell's line."""
    page = editor(box("h", "hunderterfeld", {**PROPS, "from": 1}, w=100, h=100), client=user())
    g = at(page, "h").locator("g.cell[data-i='99']")
    cell, num = g.evaluate(
        "g => [g.querySelector('rect'), g.querySelector('text')].map(\n"
        "    e => e.getBoundingClientRect().toJSON())"
    )
    assert num["left"] >= cell["left"] and num["right"] <= cell["right"]
    assert num["top"] >= cell["top"] and num["bottom"] <= cell["bottom"]


def test_the_ausschnitt_fills_the_block_with_its_cut_out_cells(editor):
    """Extra: a cut-out draws its five cells, and their square fills the block."""
    page = editor(box("h", "hunderterfeld", {**PROPS, "cut": True}, w=100, h=100), client=user())
    expect(at(page, "h").locator("g.cell")).to_have_count(5)
    cells = (
        at(page, "h")
        .locator("g.cell rect")
        .evaluate_all("els => els.map(e => e.getBoundingClientRect().toJSON())")
    )
    left = min(c["left"] for c in cells)
    right = max(c["right"] for c in cells)
    top = min(c["top"] for c in cells)
    bottom = max(c["bottom"] for c in cells)
    block = at(page, "h").bounding_box()
    assert (right - left) == pytest.approx(block["width"], rel=0.05)
    assert (bottom - top) == pytest.approx(block["height"], rel=0.05)
