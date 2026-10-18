"""The written sums of a Rechnen block on squared paper: each character stands in the square its
cell names, on the screen and in the PDF (issue #446).

The docstrings name the lines of the checklist that each test proves. The checks read pixels, not
the svg's own numbers: a square holds ink when the inner 70 % of it has a dark pixel.
"""

import io
import math

import httpx
import pypdfium2
import pytest
from PIL import Image
from pixels import over, screen_and_print
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_gap_lines_zoom import at_zoom
from ui import at, box, maths, sheet, tool, user

# Darker than this is ink: digits are #222, answers #c0392b (about 95 in grey), the paper's lines
# about 175. A small carry 1 in red is two pixels wide on the screen and smoothed to about 130.
DARK = 150
# How many dark pixels a square needs to count as written in: the dot of 234 · 6 has no more.
INK = 1
# The page's width in mm.
PAGE_MM = 210

# The rAF loop of line_shows: the element's place once it has stood still for five frames.
STILL = """async el => {
    const place = () => {
        const r = el.getBoundingClientRect();
        return [r.x, r.y, r.width, r.height];
    };
    let [was, still] = [place(), 0];
    while (still < 5) {
        await new Promise(requestAnimationFrame);
        const now = place();
        still = now.every((n, i) => n === was[i]) ? still + 1 : 0;
        was = now;
    }
    return { x: was[0], y: was[1], width: was[2], height: was[3] };
}"""

# The sheet's first page and the block's svgs, each as [x, y, width, height] in CSS pixels.
RECTS = """() => {
    const rect = (el) => {
        const r = el.getBoundingClientRect();
        return [r.x, r.y, r.width, r.height];
    };
    return {
        sheet: rect(document.querySelector('.sheet[data-page="0"]')),
        svgs: [...document.querySelectorAll('.block[data-id="m"] svg')].map(rect),
    };
}"""


def block(props):
    """The maths block at 20 mm from the top: (rows + 1) * 5 mm for each line of three tasks."""
    lines = math.ceil(len(props["exercises"]) / 3)
    rows = paper(props)[1]
    return box("m", "maths", props, y=20, h=lines * (rows + 1) * 5 + 5)


def paper(props):
    """The paper's columns and rows (the largest of the grids) and the grids of each task."""
    grids = [e["grid"] for e in props["exercises"]]
    cols = max(g["cols"] for g in grids)
    rows = max(g["rows"] for g in grids)
    return cols, rows, grids


def inked(picture, cols, rows):
    """The squares of the paper that hold ink, as (column, row), of a picture of the paper alone."""
    width, height = picture.size
    found = set()
    for r in range(rows):
        for c in range(cols):
            x0, x1 = width * c / cols, width * (c + 1) / cols
            y0, y1 = height * r / rows, height * (r + 1) / rows
            # The inner 70 %: the paper's lines and the ruled lines lie on the squares' edges.
            inner = picture.crop(
                (
                    round(x0 + 0.15 * (x1 - x0)),
                    round(y0 + 0.15 * (y1 - y0)),
                    round(x0 + 0.85 * (x1 - x0)),
                    round(y0 + 0.85 * (y1 - y0)),
                )
            )
            if sum(p < DARK for p in inner.tobytes()) >= INK:
                found.add((c, r))
    return found


def assert_squares(found, grid, key, label):
    """The squares that hold ink are the cells shown: all of them on the answer key, the pupil's
    kind 0 only otherwise."""
    shown = {(x, y) for x, y, _, kind in grid["cells"] if key or kind == 0}
    assert found == shown, (
        f"{label}: shown but not inked {sorted(shown - found)}, "
        f"inked but not shown {sorted(found - shown)}"
    )


def screen_squares(page, svg, cols, rows):
    """The inked squares of one svg on the screen, cut from the window at the svg's place."""
    # The svg is scrolled in first, and the place read once it stands still: at a large zoom a
    # svg may lie out of the window.
    svg.scroll_into_view_if_needed()
    cut = svg.evaluate(STILL)
    return inked(Image.open(io.BytesIO(page.screenshot(clip=cut))).convert("L"), cols, rows)


def printed_picture(server, client, mine, solved):
    """The first page of the sheet's PDF, grey, at 8 times the size of a point."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(
        f"{server}/api/sheets/{mine}/pdf", params={"solved": solved}, headers=cookie, timeout=60
    )
    assert res.status_code == 200
    return pypdfium2.PdfDocument(res.content)[0].render(scale=8).to_pil().convert("L")


def pdf_squares(page, picture, cols, rows):
    """The inked squares of each svg in the PDF: the svg's place is read in the editor, in mm from
    the sheet's corner, then cut from the picture of the page."""
    page.evaluate("document.fonts.ready.then(() => 0)")
    found = page.evaluate(RECTS)
    sx, sy, sw, _ = found["sheet"]
    per_mm = picture.width / PAGE_MM
    out = []
    for x, y, w, h in found["svgs"]:
        mm = PAGE_MM / sw
        left, top = (x - sx) * mm, (y - sy) * mm
        cut = picture.crop(
            (
                round(left * per_mm),
                round(top * per_mm),
                round((left + w * mm) * per_mm),
                round((top + h * mm) * per_mm),
            )
        )
        out.append(inked(cut, cols, rows))
    return out


def placed(props, i, cols, grids):
    """Task i's grid where it stands on the paper: a task narrower than the paper moves right to its last column, a division does not (issue #811)."""
    grid = grids[i]
    if props["exercises"][i]["op"] == "/":
        return grid
    dx = cols - grid["cols"]
    # The sign of a plus or a minus stays in the first column.
    sign = props["exercises"][i]["op"] in "+-"
    return {
        **grid,
        "cells": [
            [0 if sign and x == 0 else x + dx, y, ch, kind] for x, y, ch, kind in grid["cells"]
        ],
    }


def check_screen(page, props, key):
    """Each task's svg on the screen, against its grid."""
    cols, rows, grids = paper(props)
    svgs = at(page, "m").locator("svg")
    expect(svgs).to_have_count(len(grids))
    for i in range(len(grids)):
        found = screen_squares(page, svgs.nth(i), cols, rows)
        assert_squares(found, placed(props, i, cols, grids), key, f"screen, exercise {i}")


def check_pdf(page, server, client, props, key):
    """Each task's svg in the PDF, against its grid."""
    cols, rows, grids = paper(props)
    picture = printed_picture(server, client, sheet_id(page), key)
    for i, found in enumerate(pdf_squares(page, picture, cols, rows)):
        assert_squares(found, placed(props, i, cols, grids), key, f"PDF, exercise {i}")


def test_a1_the_screen_writes_each_character_in_its_square(editor):
    """A1: on the screen, the first number stands in the first row, the sign and the second number
    in the second."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    assert props["exercises"]
    page = editor(block(props), client=client)
    at_zoom(page, "opening")
    check_screen(page, props, key=False)


def test_a2_the_pdf_writes_each_character_in_its_square(editor, server):
    """A2: the pupils' PDF writes each character in its square, as the screen does."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    assert props["exercises"]
    page = editor(block(props), client=client)
    check_pdf(page, server, client, props, key=False)


def test_i1_the_answer_key_writes_the_result_and_carries_in_their_squares(editor, server):
    """I1: on the answer key the result and the small carry digits stand in their squares, on the
    screen and in the PDF with solved=True."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    assert props["exercises"]
    page = editor(block(props), client=client)
    at_zoom(page, "opening")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator("svg text.answer").first).to_be_visible()
    check_screen(page, props, key=True)
    check_pdf(page, server, client, props, key=True)


@pytest.mark.parametrize("op", ["+", "-", "*", "/"])
def test_i2_every_written_method_writes_in_its_squares(editor, server, op):
    """I2: each written method, plus, minus, times and divide, writes its characters in their
    squares on the screen and in the PDF."""
    client = user()
    # Times and divide need the larger numbers: a method's own sums come out of the limits.
    props = maths(client, format="written", max=1000 if op in "*/" else 100, ops=[op], count=3)
    assert props["exercises"]
    page = editor(block(props), client=client)
    at_zoom(page, "opening")
    check_screen(page, props, key=False)
    check_pdf(page, server, client, props, key=False)


@pytest.mark.parametrize("zoom", ["small", "large"])
def test_i3_the_squares_hold_at_a_small_and_a_large_zoom(editor, zoom):
    """I3: at Ganze Seite (a small zoom) and at about 200 %, each character stands in its square."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    assert props["exercises"]
    page = editor(block(props), client=client)
    if zoom == "small":
        at_zoom(page, "Ganze Seite")
    else:
        at_zoom(page, "opening")
        # Größer until the zoom reads 200 %, or as near as the steps come.
        for _ in range(20):
            if int(page.locator("button.zoom").first.inner_text().split()[0]) >= 200:
                break
            before = page.locator("button.zoom").first.inner_text()
            page.get_by_label("Größer", exact=True).first.click()
            expect(page.locator("button.zoom").first).not_to_have_text(before)
    check_screen(page, props, key=False)


def test_i4_a_written_tasks_paper_stands_at_the_top_of_its_row(editor):
    """I4: the block lays out as before: in a block taller than its papers, each paper stands at
    the top of its row, the first at the block's top, not in the row's middle."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    page = editor(box("m", "maths", props, y=20, h=120), client=client)
    tops = at(page, "m").evaluate(
        """el => [el, ...el.querySelectorAll("svg")].map((e) => e.getBoundingClientRect().top)"""
    )
    high = at(page, "m").bounding_box()["height"]
    # Two rows of three papers, each row half the block high.
    assert [round(top - tops[0]) for top in tops[1:]] == [0] * 3 + [round(high / 2)] * 3


def test_i6_the_pdf_draws_the_papers_right_and_lower_edge(editor, server):
    """I6: the paper's outer lines on the right and below are in the PDF, as WebKit's screen has
    them: Chromium cut them away with the half that lies outside the svg."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=3)
    page = editor(block(props), client=client)
    picture = printed_picture(server, client, sheet_id(page), False)
    found = page.evaluate(RECTS)
    sx, sy, sw, _ = found["sheet"]
    scale = picture.width / sw
    x, y, w, h = found["svgs"][0]
    left, top, right, low = (round(v * scale) for v in (x - sx, y - sy, x - sx + w, y - sy + h))
    # 0.2 mm around each edge, so half a line is not enough. The lines are pale, about 175 in
    # grey; white is 255.
    room = round(0.2 * picture.width / PAGE_MM)
    side = picture.crop((right - room, top, right + room, low)).resize((1, low - top))
    below = picture.crop((left, low - room, right, low + room)).resize((right - left, 1))
    for name, strip in (("right", side), ("lower", below)):
        pale = sum(p < 240 for p in strip.tobytes()) / len(strip.tobytes())
        assert pale > 0.9, f"the paper's {name} edge shows along {pale:.0%} of its length"


def test_i6_the_screen_and_the_print_agree_for_a_written_block(browser, server):
    """I6: the screen and the PDF of a Schriftlich block agree by pixels (a guard)."""
    client = user()
    props = maths(client, format="written", max=100, ops=["+", "-"], count=6)
    assert props["exercises"]
    mine = sheet(client, [block(props)])["id"]
    screen, printed = screen_and_print(browser, server, client, mine)
    assert not over(screen, printed)
