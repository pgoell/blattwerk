"""The lines of a table in a style, a width and Schneidelinien, drawn in svgs laid over the cells.

The boxes of the checklist (#80) are in each docstring. The props are seeded directly: the panel is
another test's.
"""

import io

import pytest
from PIL import Image
from playwright.sync_api import expect
from ui import TABLE, box

INK = "#222222"
THREE = {
    "cells": [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]],
    "cols": [1, 1, 1],
    "size": 14,
    "align": "center",
}
# The block is 180 mm wide, so its width in pixels is the scale: pixels per mm.
MM = 180

# The table's box and each cell's box, relative to the table's, flat.
GEOMETRY = """(t) => {
    const o = t.getBoundingClientRect();
    return [o.width, o.height, ...[...t.querySelectorAll(':scope > div')].flatMap((d) => {
        const b = d.getBoundingClientRect();
        return [b.x - o.x, b.y - o.y, b.width, b.height];
    })];
}"""


def scale(page):
    return page.locator('.block[data-id="t"]').bounding_box()["width"] / MM


def test_a9_a_table_without_the_keys_draws_as_before(editor):
    """A9: a table with none of the four keys has no `edged` class and no svg.edge, and its cells
    take the line colour as the border colour."""
    page = editor(box("t", "table", {**TABLE, "line": INK}))
    expect(page.locator('[data-cell="1"]')).to_be_visible()
    expect(page.locator(".table.edged")).to_have_count(0)
    expect(page.locator(".table svg.edge")).to_have_count(0)
    colour = page.locator('[data-cell="1"]').evaluate("el => getComputedStyle(el).borderRightColor")
    assert colour == "rgb(34, 34, 34)"


def test_a1_a_table_takes_a_line_style(editor):
    """A1: dashed, dotted and solid give their lines as `data-style`: two halves per dashed or
    dotted line, one per solid line. A 2 x 2 table has 12 solid lines."""
    for style, count in (("solid", 12), ("dashed", 24), ("dotted", 24)):
        page = editor(box("t", "table", {**TABLE, "line": INK, "lineStyle": style}))
        expect(page.locator(".table.edged")).to_have_count(1)
        expect(page.locator(".table svg.edge line")).to_have_count(count)
        expect(page.locator(f'.table svg.edge line[data-style="{style}"]')).to_have_count(count)
        page.close()


def test_a1_no_style_draws_no_lines(editor):
    """A1: the style none draws no line at all, and the table still counts as edged."""
    page = editor(box("t", "table", {**TABLE, "line": INK, "lineStyle": "none"}))
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator(".table svg.edge line")).to_have_count(0)


def test_a1_a_line_width_is_in_mm(editor):
    """A1: a lineWidth of 1 gives stroke-width 1 mm."""
    page = editor(box("t", "table", {**TABLE, "line": INK, "lineStyle": "solid", "lineWidth": 1}))
    expect(page.locator(".table svg.edge line")).to_have_count(12)
    widths = page.locator(".table svg.edge line").evaluate_all(
        "els => els.map((e) => +e.getAttribute('stroke-width'))"
    )
    assert all(abs(w - scale(page)) < 0.5 for w in widths)


def test_a_solid_line_among_dashed_ones_has_no_dashes(editor):
    """A1: a solid line stays whole when the dashes of the lines around it are fitted."""
    solid = {"style": "solid", "width": 2}
    edges = {"h": [[None, None], [solid, None], [None, None]], "v": [[None] * 3, [None] * 3]}
    look = {"lineStyle": "dashed", "lineWidth": 1, "edges": edges}
    page = editor(box("t", "table", {**TABLE, "line": INK, **look}))
    whole = page.locator('.table svg.edge line[data-style="solid"]')
    expect(whole).to_have_count(1)
    # The fit has run by now: it has given the dashed lines the lengths of their edges.
    dashed = page.locator('.table svg.edge line[data-style="dashed"]').first
    expect(dashed).not_to_have_attribute("stroke-dasharray", f"{3 * scale(page)} {4 * scale(page)}")
    assert whole.get_attribute("stroke-dasharray") is None
    assert whole.get_attribute("data-period") is None


def test_layout_is_the_same_with_the_new_keys(editor):
    """Layout rule: the cells lie where they lie without the keys, to 0.01 px, at 3 mm dashed.
    The edges take no room in the grid."""
    page = editor(
        box("a", "table", {**TABLE, "line": INK}, z=1),
        box("b", "table", {**TABLE, "line": INK, "lineWidth": 3, "lineStyle": "dashed"}, z=4),
    )
    expect(page.locator(".table.edged")).to_have_count(1)
    plain, keyed = (page.locator(".table").nth(i).evaluate(GEOMETRY) for i in (0, 1))
    assert len(plain) == len(keyed) == 2 + 4 * 4
    assert keyed == pytest.approx(plain, abs=0.01)


def test_each_edge_svg_lies_over_its_own_cell(editor):
    """Grid: each position's svg is the box of its cell, to 1.01 px, with no merged cell. Without an
    end line the svg runs on to the table's edge, over the cells below it."""
    page = editor(box("t", "table", {**THREE, "line": INK, "lineStyle": "dashed"}))
    expect(page.locator(".table svg.edge")).to_have_count(9)
    for i in range(9):
        svg = page.locator(f'.table svg.edge[data-edge="{i}"]').bounding_box()
        cell = page.locator(f'[data-cell="{i}"]').bounding_box()
        for key in ("x", "y", "width", "height"):
            assert svg[key] == pytest.approx(cell[key], abs=1.01), (i, key)


def test_a_merged_edge_svg_is_as_wide_as_the_column_below(editor):
    """Grid: the svg of a merged-over cell is as wide as the cell under it, not the table."""
    page = editor(
        box(
            "t",
            "table",
            {
                **THREE,
                "cells": [["a", "", "c"], ["d", "e", "f"], ["g", "h", "i"]],
                "line": INK,
                "lineStyle": "dashed",
                "spans": [[0, 0, 1, 2]],
            },
        )
    )
    expect(page.locator(".table svg.edge")).to_have_count(9)
    svg = page.locator('.table svg.edge[data-edge="1"]').bounding_box()
    below = page.locator('[data-cell="4"]').bounding_box()
    assert svg["width"] == pytest.approx(below["width"], abs=1.01)


PERIODS = """els => els.map((line) => {
    const svg = line.closest('svg.edge');
    const across = ['top', 'bottom'].includes(line.dataset.side);
    const table = svg.parentElement, box = svg.getBoundingClientRect();
    const zoom = table.getBoundingClientRect().width / table.offsetWidth;
    const length = (across ? box.width : box.height) / zoom;
    const [dash, gap] = line.getAttribute('stroke-dasharray').split(' ').map(Number);
    return length / (dash + gap);
})"""


def test_dashes_fit_a_whole_number_of_periods_on_every_edge(editor):
    """Fit: each dashed edge is a whole number of dash periods, to 0.01, also when narrower."""
    for width, mm in ((None, 0.25), (143, 0.75)):
        more = {} if width is None else {"w": width}
        page = editor(
            box(
                "t",
                "table",
                {**THREE, "line": INK, "lineStyle": "dashed", "lineWidth": 2 * mm},
                **more,
            )
        )
        expect(page.locator(".table line[data-period]")).to_have_count(48)
        counts = page.locator(".table line[data-period]").evaluate_all(PERIODS)
        for v in counts:
            assert v == pytest.approx(round(v), abs=0.01), counts
        page.close()


def test_a7_dashes_meet_at_every_corner_and_crossing(editor):
    """A7: a dashed 3 x 3 table at 1 mm has ink at its 16 corners and crossings, on screen."""
    page = editor(
        box("t", "table", {**THREE, "line": "#000000", "lineStyle": "dashed", "lineWidth": 1})
    )
    expect(page.locator(".table.edged")).to_have_count(1)
    shot = Image.open(io.BytesIO(page.screenshot())).convert("L")
    factor = shot.width / page.viewport_size["width"]
    cells = [page.locator(f'[data-cell="{i}"]').bounding_box() for i in range(9)]
    xs = [cells[c]["x"] for c in range(3)] + [cells[2]["x"] + cells[2]["width"]]
    ys = [cells[r * 3]["y"] for r in range(3)] + [cells[6]["y"] + cells[6]["height"]]
    lost = []
    for x in xs:
        for y in ys:
            px, py = round(x * factor), round(y * factor)
            # Some pixel in the 5 x 5 square around the point is dark (under 128).
            if not any(shot.crop((px - 2, py - 2, px + 3, py + 3)).histogram()[:128]):
                lost.append((round(x, 1), round(y, 1)))
    assert not lost, (factor, lost)


def test_a8_the_line_colour_colours_every_style_and_the_scissors(editor):
    """A8: with a red line colour the dashed and dotted lines and the scissors are red."""
    red = "#e02424"
    for style in ("dashed", "dotted"):
        page = editor(box("t", "table", {**TABLE, "line": red, "lineStyle": style, "cut": True}))
        expect(page.locator(".scissors")).to_have_count(1)
        strokes = page.locator(".table svg.edge line").evaluate_all(
            "els => els.map((e) => e.getAttribute('stroke'))"
        )
        assert strokes and set(strokes) == {red}
        assert page.locator(".scissors svg").get_attribute("stroke") == red
        page.close()


def test_a5_schneidelinien_shows_scissors_at_the_top_left(editor):
    """A5: cut true shows the scissors left of the table's left edge, its middle on the top line,
    to 1 px. Without cut there are none."""
    page = editor(
        box(
            "t",
            "table",
            {**TABLE, "line": INK, "cut": True, "lineStyle": "dashed", "lineWidth": 0.25},
        )
    )
    scissors = page.locator(".scissors")
    expect(scissors).to_have_count(1)
    table = page.locator(".table").bounding_box()
    s = scissors.bounding_box()
    assert s["x"] + s["width"] <= table["x"] + 1
    assert abs(s["y"] + s["height"] / 2 - table["y"]) <= 1


def test_a5_no_cut_no_scissors(editor):
    """A5: without `cut` the table has no scissors."""
    page = editor(box("t", "table", {**TABLE, "line": INK, "lineStyle": "dashed"}))
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator(".scissors")).to_have_count(0)


def test_i4_no_line_runs_through_a_merged_cell(editor):
    """I4: a cell merged over two columns draws no line between them, not even one with an edges
    entry of its own."""
    edge = {"style": "dashed", "width": 1}
    page = editor(
        box(
            "t",
            "table",
            {
                **TABLE,
                "cells": [["H", ""], ["3", "7"]],  # a merge takes only empty cells
                "line": INK,
                "lineStyle": "dashed",
                "spans": [[0, 0, 1, 2]],
                "edges": {"h": [[None, None]] * 3, "v": [[None, edge, None], [None, None, None]]},
            },
        )
    )
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator('.table svg.edge[data-edge="1"]')).to_have_count(1)
    expect(page.locator('.table svg.edge[data-edge="1"] line[data-side="left"]')).to_have_count(0)
    expect(page.locator('.table svg.edge[data-edge="0"] line[data-side="left"]')).to_have_count(2)


def test_i8_the_box_of_solution_words_takes_the_style(editor):
    """I8: the box of solution words is drawn in the table's style: dotted on its left, right and
    bottom, and nothing on its top."""
    page = editor(
        box(
            "t",
            "table",
            {
                **TABLE,
                "line": INK,
                "lineStyle": "dotted",
                "gaps": [[False, True], [False, True]],
                "bank": 1,
            },
        )
    )
    expect(page.locator('.table svg.edge[data-edge="bank"] line')).to_have_count(6)
    sides = page.locator('.table svg.edge[data-edge="bank"] line').evaluate_all(
        "els => els.map((e) => [e.dataset.side, e.dataset.style])"
    )
    assert set(map(tuple, sides)) == {("left", "dotted"), ("right", "dotted"), ("bottom", "dotted")}


def test_per_edge_one_line_takes_its_own_style(editor):
    """Per edge: one entry on h[1][0] dashed and 1 mm, the rest solid and 0.25 mm."""
    dashed = {"style": "dashed", "width": 1}
    edges = {"h": [[None, None], [dashed, None], [None, None]], "v": [[None] * 3, [None] * 3]}
    page = editor(box("t", "table", {**TABLE, "line": INK, "edges": edges}))
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator('.table line[data-style="dashed"]')).to_have_count(2)
    expect(page.locator('.table svg.edge[data-edge="2"] line[data-style="dashed"]')).to_have_count(
        2
    )
    k = scale(page)
    dash = page.locator('.table line[data-style="dashed"]').evaluate_all(
        "els => els.map((e) => +e.getAttribute('stroke-width'))"
    )
    solid = page.locator('.table line[data-style="solid"]').evaluate_all(
        "els => els.map((e) => +e.getAttribute('stroke-width'))"
    )
    assert all(abs(w - k) < 0.5 for w in dash)
    assert len(solid) == 11 and all(abs(w - 0.25 * k) < 0.5 for w in solid)


def test_beyond_a_one_by_one_table_with_cut_and_dots(editor):
    """Beyond the brief: a 1 x 1 table has one svg with the rim's four lines, and the scissors."""
    page = editor(
        box(
            "t",
            "table",
            {
                "cells": [["x"]],
                "cols": [1],
                "size": 14,
                "align": "center",
                "line": INK,
                "lineStyle": "dotted",
                "cut": True,
            },
        )
    )
    expect(page.locator(".table svg.edge")).to_have_count(1)
    expect(page.locator(".table svg.edge line")).to_have_count(8)
    expect(page.locator(".table svg.edge line[data-style='dotted']")).to_have_count(8)
    expect(page.locator(".scissors")).to_have_count(1)


def test_a_wide_dashed_line_on_a_short_edge_keeps_a_dash(editor):
    """A7: a column 4 mm wide under a line 3 mm wide: no dash has a length below nothing, which
    a browser would draw as a solid line."""
    look = {**THREE, "cols": [1, 1, 40], "line": INK, "lineStyle": "dashed", "lineWidth": 3}
    page = editor(box("t", "table", look))
    first = page.locator('.table svg.edge[data-edge="0"] line[data-side="top"]').first
    expect(first).not_to_have_attribute("stroke-dasharray", f"{9 * scale(page)} {12 * scale(page)}")
    arrays = page.locator(".table line[data-period]").evaluate_all(
        "els => els.map((e) => e.getAttribute('stroke-dasharray').split(' ').map(Number))"
    )
    assert all(dash >= 0 and gap > 0 for dash, gap in arrays), arrays
    assert any(dash == 0 for dash, _ in arrays)


FRAME = {"style": "solid", "width": 1.25}
# The lines of each cell's svg, with the cell's place in the grid and the side of the cell it is on.
LINES = """(svgs) => svgs.flatMap((s) => [...s.querySelectorAll('line')].map((l) => ({
    edge: +s.dataset.edge, side: l.dataset.side, style: l.dataset.style,
    w: +l.getAttribute('stroke-width') })))"""


def thick_between(locator, cols, line, mm):
    """The rows (or columns) in which a line `mm` wide stands on line `line` between two columns
    (or across, between two rows), as the cells' svgs draw it."""
    table = locator.locator(".table").first
    # The svgs draw in the table's own pixels: `--edge` is 0.25 mm of them.
    per_mm = table.evaluate("t => parseFloat(getComputedStyle(t).getPropertyValue('--edge')) * 4")
    svgs = locator.locator('.table svg.edge[data-edge]:not([data-edge="bank"])')
    lines = svgs.evaluate_all(LINES)
    found = set()
    for one in lines:
        r, c = divmod(one["edge"], cols)
        if abs(one["w"] - mm * per_mm) > 0.5:
            continue
        if line[0] == "v" and (one["side"], c) in (("right", line[1] - 1), ("left", line[1])):
            found.add(r)
        if line[0] == "h" and (one["side"], r) in (("bottom", line[1] - 1), ("top", line[1])):
            found.add(c)
    return found
