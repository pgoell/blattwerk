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


def test_the_keys_number_fits_its_box_at_24_pt(editor, browser, server):
    """Found by the review of #570: the box was 6 mm high at any font size, so a number of 24 pt
    spilled out of it in the answer key."""
    client = user()
    big = {**PROPS, "start": 340, "end": 360, "size": 24, "boxes": 2}
    page = editor(box("z", "zahlenstrahl", big, w=180, h=40), client=client)
    paper = key_print(browser, server, sheet_id(page))
    fits = paper.locator(".zahlenstrahl g.box").evaluate_all(
        """gs => gs.map(g => {
            const r = g.querySelector('rect').getBBox(), t = g.querySelector('text').getBBox();
            return t.x >= r.x && t.x + t.width <= r.x + r.width
                && t.y >= r.y - 0.5 && t.y + t.height <= r.y + r.height + 0.5;
        })"""
    )
    paper.context.close()
    assert fits == [True, True]


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


# The lines of a box and of an arrow, and the numbers, in the svg's mm; the stubs' and the ticks' x.
CROSSES = """el => {
    const segs = [...el.querySelectorAll('g.box line, g.arrow line')].map(l => {
        const [x1, y1, x2, y2] = ['x1', 'y1', 'x2', 'y2'].map(a => +l.getAttribute(a));
        return {x: Math.min(x1, x2), y: Math.min(y1, y2),
            w: Math.abs(x2 - x1), h: Math.abs(y2 - y1)};
    });
    // The digits' band: a getBBox also takes the font's descent, which no digit reaches.
    const texts = [...el.querySelectorAll('text.label, text.given')].map(t => {
        const b = t.getBBox(), fs = +t.getAttribute('font-size'), y = +t.getAttribute('y');
        const top = t.getAttribute('class') === 'given' ? y - 0.75 * fs : y;
        return {x: b.x, width: b.width, y: top, height: 0.75 * fs};
    });
    const hit = (s, b) => s.x <= b.x + b.width && b.x <= s.x + s.w
        && s.y <= b.y + b.height && b.y <= s.y + s.h;
    const boxes = [...el.querySelectorAll('text.given')].map(t => t.getBBox());
    return {
        crossings: segs.flatMap(s => texts.filter(b => hit(s, b))).length,
        stubs: [...el.querySelectorAll('g.arrow > line')].map(l => +l.getAttribute('x1')),
        ticks: [...el.querySelectorAll('g.tick > line')].map(l => +l.getAttribute('x1')),
        numbers: boxes.map(b => [b.x, b.y, b.width, b.height]),
    };
}"""


def assert_clear(paper):
    found = paper.locator(".zahlenstrahl").evaluate(CROSSES)
    assert found["crossings"] == 0, found
    return found


@pytest.mark.parametrize("size", [12, 20])
def test_issue_576_no_line_runs_through_a_number(editor, browser, server, size):
    """#576: on 340 to 420 in steps of 2 a box's leader ran through a neighbour's number, and an
    arrow's stub through its own. No line of a box or an arrow crosses a number, on screen and
    in print."""
    client = user()
    props = {
        **PROPS,
        "start": 340,
        "end": 420,
        "minor": 2,
        "major": 10,
        "cut": True,
        "size": size,
        "tasks": "free",
        "boxes": 0,
        "marks": [[362, "box"], [378, "box"], [352, "arrow"], [396, "arrow"]],
    }
    page = editor(box("z", "zahlenstrahl", props, w=180, h=40), client=client)
    found = line_of(page).evaluate(CROSSES)
    assert found["crossings"] == 0, found
    paper = printed(browser, server, sheet_id(page))
    assert_clear(paper)
    paper.context.close()


def test_issue_577_an_arrow_number_stands_over_a_gap(editor, browser, server):
    """#577: arrow 13 of 0 to 20 stood right above tick 10 with its stub at 10, so it read as the
    label of 10. Its stub stands at least 1 mm from every tick, on screen and in print."""
    client = user()
    props = {**PROPS, "tasks": "free", "boxes": 0, "marks": [[13, "arrow"]]}
    page = editor(box("z", "zahlenstrahl", props, w=120, h=30), client=client)
    found = line_of(page).evaluate(CROSSES)
    assert (
        found["stubs"] and min(abs(s - t) for s in found["stubs"] for t in found["ticks"]) >= 1
    ), found
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    found = paper.locator(".zahlenstrahl").evaluate(CROSSES)
    assert min(abs(s - t) for s in found["stubs"] for t in found["ticks"]) >= 1, found
    paper.context.close()


def test_six_arrows_keep_distinct_gaps_and_no_number_overlaps(editor):
    """Own: six arrows on 0 to 20 each stand over a gap of their own; no two numbers overlap."""
    marks = [[2, "arrow"], [5, "arrow"], [9, "arrow"], [12, "arrow"], [15, "arrow"], [18, "arrow"]]
    props = {**PROPS, "tasks": "free", "boxes": 0, "marks": marks}
    page = editor(box("z", "zahlenstrahl", props, w=180, h=40), client=user())
    found = line_of(page).evaluate(CROSSES)
    assert found["crossings"] == 0, found
    assert len(set(found["stubs"])) == 6, found
    nums = found["numbers"]
    for i, a in enumerate(nums):
        for b in nums[i + 1 :]:
            apart = (
                a[0] >= b[0] + b[2]
                or b[0] >= a[0] + a[2]
                or a[1] >= b[1] + b[3]
                or b[1] >= a[1] + a[3]
            )
            assert apart, (a, b)


@pytest.mark.parametrize("size", [20, 24])
def test_an_arrow_number_is_not_cut_off_at_the_top_of_the_dock_block(editor, browser, server, size):
    """Own: on the dock's 180 by 30 mm block the line is at 12 mm, and a number of 20 or 24 pt
    keeps its digits inside the svg, on screen and in print, and clear of its stub."""
    client = user()
    props = {**PROPS, "tasks": "free", "boxes": 0, "size": size, "marks": [[13, "arrow"]]}
    page = editor(box("z", "zahlenstrahl", props, w=180, h=30), client=client)
    band = """el => [...el.querySelectorAll('text.given')].map(t => {
        const fs = +t.getAttribute('font-size');
        return +t.getAttribute('y') - 0.75 * fs;
    })"""
    assert line_of(page).evaluate(band) and min(line_of(page).evaluate(band)) >= 0
    assert line_of(page).evaluate(CROSSES)["crossings"] == 0
    paper = printed(browser, server, sheet_id(page))
    assert min(paper.locator(".zahlenstrahl").evaluate(band)) >= 0
    assert_clear(paper)
    paper.context.close()


def test_size_24_arrow_number_stays_clear_of_its_stub(editor):
    """Own: at 24 pt the arrow's number still ends above its stub."""
    props = {**PROPS, "tasks": "free", "boxes": 0, "size": 24, "marks": [[5, "arrow"]]}
    page = editor(box("z", "zahlenstrahl", props, w=180, h=40), client=user())
    assert line_of(page).evaluate(CROSSES)["crossings"] == 0
