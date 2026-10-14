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
        assert page.locator(".scissors").get_attribute("stroke") == red
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


def test_beyond_broken_edges_are_ignored_and_the_width_holds(editor):
    """Beyond the brief: edges of the wrong shape are left out whole; every line then takes the
    table's style and width."""
    broken = {"h": [[None, None]], "v": [[None] * 3, [None] * 3]}
    page = editor(box("t", "table", {**TABLE, "line": INK, "lineWidth": 1, "edges": broken}))
    expect(page.locator(".table.edged")).to_have_count(1)
    expect(page.locator(".table svg.edge line")).to_have_count(12)
    expect(page.locator(".table svg.edge line[data-style='solid']")).to_have_count(12)
    widths = page.locator(".table svg.edge line").evaluate_all(
        "els => els.map((e) => +e.getAttribute('stroke-width'))"
    )
    assert all(abs(w - scale(page)) < 0.5 for w in widths)
