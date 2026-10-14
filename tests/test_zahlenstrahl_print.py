"""The Zahlenstrahl on screen and on paper: its ticks, its numbers, its boxes, arcs and key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
tasks of a random block may change with the model.
"""

import pytest
from pixels import LIMITS, measures, over, screen_and_print
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, sheet, user

# The geometry of frontend/src/zahlenstrahl.ts, in mm.
LEFT, RIGHT = 6, 10
# 12 pt in mm: the font size the labels keep at any width.
PT12 = 12 * 25.4 / 72

PROPS = {
    "start": 0,
    "end": 20,
    "minor": 1,
    "major": 5,
    "labels": "major",
    "size": 12,
    "cut": False,
    "tasks": "random",
    "boxes": 3,
    "arrows": 0,
    "jumps": False,
    "seed": 7,
}
RED = "rgb(192, 57, 43)"
# The x of each tick, in mm, as the svg holds it.
TICKS = (
    "el => [...el.querySelectorAll('g.tick')].map(g => +g.querySelector('line').getAttribute('x1'))"
)
# Each label's text and font size.
LABELS = """el => [...el.querySelectorAll('text.label')].map(
    t => [t.textContent, t.getAttribute('font-size')])"""
# The whole line as the print and the editor must draw it alike: ticks, labels and boxes.
PICTURE = """el => ({
    ticks: [...el.querySelectorAll('g.tick')].map(g => g.querySelector('line').getAttribute('x1')),
    labels: [...el.querySelectorAll('text.label')].map(
        t => [t.textContent, t.getAttribute('font-size')]),
    boxes: [...el.querySelectorAll('g.box rect')].map(
        r => ['x', 'y', 'width', 'height'].map(a => r.getAttribute(a))),
})"""
FILLS = "els => els.map(e => getComputedStyle(e).fill)"


def line_of(page, name="z"):
    return at(page, name).locator(".zahlenstrahl")


def test_the_ticks_spread_over_the_block_width_and_the_numbers_keep_their_size(editor):
    """Stored widths 120, 180 and 250 mm: tick i of 21 stands at xOf(i, 21, w), and each label's
    font size is 12 pt in mm whatever the width."""
    for w in (120, 180, 250):
        page = editor(box("z", "zahlenstrahl", PROPS, w=w, h=40), client=user())
        xs = line_of(page).evaluate(TICKS)
        assert len(xs) == 21
        for i, x in enumerate(xs):
            assert x == pytest.approx(LEFT + i * (w - LEFT - RIGHT) / 20, abs=0.01), (w, i)
        labels = line_of(page).evaluate(LABELS)
        assert labels
        assert all(float(size) == pytest.approx(PT12, abs=0.01) for _, size in labels)


def test_the_print_has_the_editors_line(editor, browser, server):
    """The print shows the editor's ticks, numbers, font size and boxes in the same places."""
    client = user()
    page = editor(box("z", "zahlenstrahl", {**PROPS, "boxes": 2}, w=180, h=40), client=client)
    shown = line_of(page).evaluate(PICTURE)
    paper = printed(browser, server, sheet_id(page))
    assert paper.locator(".zahlenstrahl").evaluate(PICTURE) == shown
    paper.context.close()


@pytest.mark.parametrize("solved", [False, True])
def test_the_pupils_and_the_key_print_as_the_screen_shows_them(browser, server, solved):
    """The screen and the PDF of the line, the pupil's sheet and the answer key, within limits."""
    client = user()
    # A gap in a text: the helper waits for its answer colour, which a line alone never shows.
    gap = {
        "text": "Der Hund bellt",
        "size": 14,
        "align": "left",
        "bank": 1,
        "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
    }
    line = box(
        "z",
        "zahlenstrahl",
        {**PROPS, "cut": True, "start": 5, "end": 25, "jumps": True, "arrows": 2},
        z=3,
        w=180,
        h=40,
    )
    mine = sheet(client, [box("t", "text", gap, z=1, h=20), line])["id"]
    screen, printed_png = screen_and_print(
        browser, server, client, mine, hide_gaps=not solved, solved=solved
    )
    found, _ = measures(screen, printed_png)
    assert not over(screen, printed_png), {name: found[name] for name in LIMITS}


def test_the_answer_key_writes_the_numbers_into_the_boxes_in_red(editor, browser, server):
    """The pupil's sheet has no answer; the key writes each box's number in #c0392b."""
    client = user()
    page = editor(box("z", "zahlenstrahl", PROPS, w=180, h=40), client=client)
    boxes = at(page, "z").locator("g.box").count()
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    expect(paper.locator(".zahlenstrahl text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, mine)
    expect(paper.locator(".zahlenstrahl g.box text.answer")).to_have_count(boxes)
    assert paper.locator(".zahlenstrahl g.box text.answer").evaluate_all(FILLS) == [RED] * boxes
    paper.context.close()


@pytest.mark.parametrize("start, cut, shown", [(0, True, 0), (5, True, 1), (5, False, 0)])
def test_the_cut_mark_shows_only_with_a_start_above_zero_and_cut_on(editor, start, cut, shown):
    """The break mark is two strokes left of the first tick, and only when start is above 0."""
    page = editor(
        box(
            "z",
            "zahlenstrahl",
            {**PROPS, "start": start, "end": start + 20, "cut": cut},
            w=180,
            h=40,
        ),
        client=user(),
    )
    expect(at(page, "z").locator(".zahlenstrahl g.cut")).to_have_count(shown)
    if shown:
        expect(at(page, "z").locator(".zahlenstrahl g.cut > *")).to_have_count(2)


def test_jump_arcs_are_drawn_with_their_labels(editor):
    """Jumps of 5 over 0 to 20: four arcs, each a path with a label, the first labelled +5."""
    page = editor(box("z", "zahlenstrahl", {**PROPS, "jumps": True}, w=180, h=40), client=user())
    arcs = at(page, "z").locator(".zahlenstrahl g.arc")
    expect(arcs).to_have_count(4)
    for i in range(4):
        expect(arcs.nth(i).locator("path")).to_have_count(1)
        expect(arcs.nth(i).locator("text")).not_to_have_text("")
    expect(arcs.nth(0)).to_have_attribute("data-from", "0")
    expect(arcs.nth(0)).to_have_attribute("data-to", "5")
    expect(arcs.nth(0).locator("text")).to_have_text("+5")


def test_a_block_with_a_mark_shows_its_numbering(editor, browser, server):
    """A mark "1." on the block shows as the number 1 in the editor and on the sheet."""
    client = user()
    page = editor(box("z", "zahlenstrahl", PROPS, w=180, h=40, mark="1."), client=client)
    expect(at(page, "z").locator(".mark")).to_have_text("1.")
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".mark")).to_have_text("1.")
    paper.context.close()


# Each box's and each number's box in the svg's mm, and each arrow stub's lower end and x.
CLASH = """el => {
    const boxes = [...el.querySelectorAll('g.box rect')].map(r => r.getBBox());
    const labels = [...el.querySelectorAll('text.label')].map(t => t.getBBox());
    const hit = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width
        && a.y < b.y + b.height && b.y < a.y + a.height;
    const ends = (sel, y) => [...el.querySelectorAll(sel)].map(
        l => [+l.getAttribute('x1'), +l.getAttribute(y)]);
    const ticks = ends('g.tick > line', 'y1');
    const stubs = ends('g.arrow > line', 'y2');
    const over = ([x, y]) => ticks.map(([tx, ty]) => Math.abs(tx - x) < 0.5 ? ty - y : 99);
    return {
        clashes: boxes.flatMap(b => labels.filter(l => hit(b, l))).length,
        boxes: boxes.length,
        gap: Math.min(...stubs.flatMap(over)),
    };
}"""


def test_no_box_covers_a_number_and_no_arrow_touches_a_tick(editor):
    """Seen in the shot: on 340 to 420 in steps of 2, boxes 11 mm wide covered the numbers beside
    them, and an arrow's stub over a long tick read as an arrow to it. A box that would cover a
    number stands a row lower; a stub ends 2 mm above the ticks."""
    crowded = {**PROPS, "start": 340, "end": 420, "minor": 2, "major": 10, "boxes": 6, "seed": 9}
    page = editor(box("z", "zahlenstrahl", crowded, w=180, h=30), client=user())
    found = line_of(page).evaluate(CLASH)
    assert found["boxes"] == 6 and found["clashes"] == 0, found
    # One arrow on 13 of 0 to 20, at 120 mm: its stub stands right over the long tick 10.
    free = {**PROPS, "tasks": "free", "marks": [[13, "arrow"]], "boxes": 0}
    page = editor(box("z", "zahlenstrahl", free, w=120, h=30), client=user())
    assert line_of(page).evaluate(CLASH)["gap"] >= 1.9


def test_a_large_first_number_is_not_cut_off(editor):
    """I8: "340" at 24 pt is wider than the 12 mm round its tick; the svg lets it reach past the
    block's left edge, whole."""
    page = editor(
        box("z", "zahlenstrahl", {**PROPS, "start": 340, "end": 360, "size": 24}, w=180, h=30),
        client=user(),
    )
    first = line_of(page).locator("text.label").first
    expect(first).to_have_text("340")
    assert first.evaluate("t => t.getBBox().x") < 0
    assert line_of(page).locator("svg").evaluate("s => getComputedStyle(s).overflow") == "visible"


def test_labels_ends_shows_only_the_first_and_the_last_number(editor):
    """Own: labels "ends" with no tasks shows the numbers 0 and 20 and no other."""
    page = editor(
        box("z", "zahlenstrahl", {**PROPS, "labels": "ends", "boxes": 0}, w=180, h=40),
        client=user(),
    )
    expect(line_of(page).locator("text.label")).to_have_count(2)
    labels = line_of(page).evaluate(LABELS)
    assert [text for text, _ in labels] == ["0", "20"]
    assert all(float(size) == pytest.approx(PT12, abs=0.01) for _, size in labels)


def test_a_free_arrow_is_drawn_with_its_stub_and_its_key_path(editor, browser, server):
    """Own: a free arrow on tick 5 shows its number above the line, and the key draws the arrow to
    the tick; the pupil's sheet has no key path."""
    client = user()
    props = {**PROPS, "tasks": "free", "boxes": 0, "marks": [[5, "arrow"]]}
    page = editor(box("z", "zahlenstrahl", props, w=180, h=40), client=client)
    expect(at(page, "z").locator('.zahlenstrahl g.arrow[data-value="5"] text.given')).to_have_count(
        1
    )
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    expect(paper.locator(".zahlenstrahl path.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, mine)
    expect(paper.locator(".zahlenstrahl path.answer")).to_have_count(1)
    paper.context.close()
