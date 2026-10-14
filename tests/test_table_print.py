"""A table's lines print as the screen shows them: each style, width, cut line and edge."""

import io

import pytest
from PIL import Image
from pixels import INK, LOADED, dark, grey
from playwright.sync_api import expect
from test_pixels import PLACES, faults, planted
from test_zoom import expect_width, wheel, width
from ui import TEXT, block, sheet, user

from blattwerk import pdf

WORDS = [["Hund", "Katze", "Maus"], ["Igel", "Reh", "Fuchs"], ["Eule", "Dachs", "Biber"]]
MERGED = [["Hund und Katze", "", "Maus"], ["Igel", "Reh", "Fuchs"], ["Eule", "Dachs", "Biber"]]
LOOK = {"cells": WORDS, "cols": [1, 1, 1], "size": 14, "align": "center", "line": "#222222"}
DASH = {"style": "dashed", "width": 1}
BARE = {"cells": [["", "", ""] for _ in range(3)]}
GAPPED = {"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}]}


def table(props, h=40):
    """One table of 3 by 3 in the middle of the page, 180 mm wide, with `props` on it."""
    return [block("table", 40, h, {**LOOK, **props})]


def edges(rows, cols, *marked):
    """The `edges` of a table: null but for each (side, row, column, entry) in `marked`."""
    grid = {
        "h": [[None] * cols for _ in range(rows + 1)],
        "v": [[None] * (cols + 1) for _ in range(rows)],
    }
    for side, row, column, entry in marked:
        grid[side][row][column] = entry
    return grid


# The outline of the middle cell: the line above and below it, and left and right of it.
OUTLINE = edges(3, 3, ("h", 1, 1, DASH), ("h", 2, 1, DASH), ("v", 1, 1, DASH), ("v", 1, 2, DASH))
# A table with merged cells and set row and column sizes, 180 mm by 40 mm.
SIZED = {"cells": MERGED, "spans": [[0, 0, 1, 2]], "cols": [70, 50, 60], "rows": [20, 10, 10]}
CASES = {
    "dashed": ({"lineStyle": "dashed"}, {}),
    "dotted": ({"lineStyle": "dotted"}, {}),
    "none": ({"lineStyle": "none"}, {}),
    "dashed wide": ({"lineStyle": "dashed", "lineWidth": 1}, {}),
    "solid wide": ({"lineWidth": 3}, {}),
    "cut": ({"cut": True, "lineStyle": "dashed", "lineWidth": 0.25}, {}),
    "per cell": ({"edges": OUTLINE}, {}),
    "merged": ({"cells": MERGED, "spans": [[0, 0, 1, 2]], "lineStyle": "dashed"}, {}),
    "sized": ({**SIZED, "lineStyle": "dotted"}, {}),
    "coloured": ({"line": "#e02424", "lineStyle": "dashed"}, {}),
    # Two more: a table of one cell, and the answer key with its lines dotted.
    "one cell": ({"cells": [["Wort"]], "cols": [1], "lineStyle": "dashed"}, {}),
    "answer key": ({"lineStyle": "dotted"}, {"solved": True}),
}


def open_both(browser, server, client, page):
    """The sheet of `page` in the editor and on its print page, as two tabs of one client."""
    mine = sheet(client, page)["id"]
    context = browser.new_context(device_scale_factor=2)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    return context, shown, paper


def spans(darkness):
    """Each stretch of columns or rows with ink in it: its first and the one after its last."""
    found, start = [], None
    for i, v in enumerate([*darkness, 0]):
        if v > 0.3 and start is None:
            start = i
        elif v <= 0.3 and start is not None:
            found.append((start, i))
            start = None
    return found


def at_mark(mm):
    """Whether a place across a table, in mm from its left, lies at a cell's corner or middle."""
    return abs(mm % 30) < 1.5 or abs(mm % 30 - 30) < 1.5


def dashes(found, image, left):
    """The lengths in mm of the dashes along a line, leaving out the ends and the middles."""
    scale = 210 / image.width
    kept = []
    for start, end in found:
        here, there = start * scale - left, end * scale - left
        if not (at_mark(here) or at_mark(there)):
            kept.append((end - start) * scale)
    return kept


@pytest.mark.parametrize("case", CASES)
def test_a_table_prints_as_the_screen_shows_it(browser, server, case):
    """A11: one table of 3 by 3 and each case of its lines, on the screen and in print."""
    props, look = CASES[case]
    client = user()
    # The answer key shows a gap's word on the screen and in print alike: it needs a gap.
    gap = [block("text", 120, 20, {**TEXT, "text": "Der Hund", "rich": [GAPPED]})] if look else []
    assert not faults(browser, server, client, table(props) + gap, **look)


def test_a_dashed_table_printed_solid_is_over_a_limit(browser, server):
    """A11 sound: the same width, dashed on the screen and solid in print."""
    # Empty cells: the letters would hold the ink of a tile, and a line is what is to be told.
    found = planted(
        browser,
        server,
        table({**BARE, "lineStyle": "dashed", "lineWidth": 3}),
        table({**BARE, "lineWidth": 3}),
    )
    assert found["ink"] > INK, found


def test_a_table_without_lines_printed_with_them_is_over_a_limit(browser, server):
    """A11 sound: no lines on the screen and the plain table in print."""
    found = planted(
        browser,
        server,
        table({**BARE, "lineStyle": "none"}),
        table({**BARE, "lineWidth": 3}),
    )
    assert found["ink"] > INK, found


def test_dashes_are_as_long_in_print_as_on_the_screen(browser, server):
    """A6: each dash of the top line is 4 mm long, on the screen and in print."""
    client = user()
    page = table({"lineStyle": "dashed", "lineWidth": 1})
    screen, printed = grey(browser, server, client, page)
    x, y, w, _ = (page[0][side] for side in "xywh")
    # A strip along the top line, clear of the letters: 1 mm tall, and the line is 1 mm wide.
    part = (x + 3, y - 0.4, x + w - 3, y + 0.4)
    shown, paper = (spans(dark(picture, part, down=False)) for picture in (screen, printed))
    assert len(shown) == len(paper), (shown, paper)
    for (here, _), (there, _) in zip(shown, paper, strict=True):
        assert abs(here - there) <= 2, (shown, paper)
    for picture, found in ((screen, shown), (printed, paper)):
        lengths = dashes(found, picture, x)
        assert len(lengths) >= 6, lengths
        assert all(abs(v - 4) < 0.4 for v in lengths), lengths


def test_dashes_keep_their_length_at_zoom(editor):
    """A6 at zoom: the dashes of the top line are 4 mm long at 100 % and zoomed in."""
    page = editor(*table({"lineStyle": "dashed", "lineWidth": 1}))
    wide = width(page)
    before = top_line_dashes(page)
    wheel(page, -100)
    expect_width(page, wide * 1.25)
    after = top_line_dashes(page)
    for lengths in (before, after):
        assert len(lengths) >= 6, lengths
        assert all(abs(v - 4) < 0.45 for v in lengths), lengths


def top_line_dashes(page):
    """The dashes of the table's top line on the screen, in mm, from a strip of 6 px at its top."""
    table_box = page.locator(".table")
    table_box.scroll_into_view_if_needed()
    box = table_box.bounding_box()
    clip = {"x": box["x"], "y": box["y"] - 3, "width": box["width"], "height": 6}
    picture = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("L")
    row = picture.resize((picture.width, 1), Image.Resampling.BOX).tobytes()
    darkness = [1 - v / 255 for v in row]
    scale = 180 / picture.width
    found = spans(darkness)
    kept = []
    for start, end in found:
        here, there = start * scale, end * scale
        if not (at_mark(here) or at_mark(there)):
            kept.append((end - start) * scale)
    return kept


def test_ink_at_every_crossing_and_corner_in_print(browser, server):
    """A7: the pixel at each of the 16 crossings and corners of a dashed table is dark."""
    client = user()
    page = table({"lineStyle": "dashed", "lineWidth": 1}, h=90)
    _, printed = grey(browser, server, client, page)
    per_mm = printed.width / 210
    # The grid lines of three equal columns of 60 mm and three rows of 30 mm, from the block's
    # corner: the four lines across and the four down.
    pale = []
    for i in range(4):
        for j in range(4):
            x, y = 15 + 60 * i, 40 + 30 * j
            if printed.getpixel((round(x * per_mm), round(y * per_mm))) > 128:
                pale.append((x, y))
    assert not pale, pale


def test_a_table_without_the_new_keys_is_drawn_as_before(browser, server):
    """A9: no edged table and no edge on the screen or in print, and the line colour on a cell."""
    client = user()
    context, shown, paper = open_both(browser, server, client, table({}))
    for tab in (shown, paper):
        expect(tab.locator(".table.edged")).to_have_count(0)
        expect(tab.locator("svg.edge")).to_have_count(0)
        colours = tab.evaluate(
            "() => [...document.querySelectorAll('.table > div')]"
            ".map((el) => getComputedStyle(el).borderRightColor)"
        )
        assert "rgb(34, 34, 34)" in colours, colours
    paper.close()
    context.close()


def test_merged_and_sized_cells_lie_where_they_print_with_lines(browser, server):
    """A12: the cells of a merged, sized table lie in the same places with the lines as without."""
    client = user()
    lined = {**SIZED, "lineStyle": "dashed", "lineWidth": 3, "edges": OUTLINE}
    places = []
    for props in (SIZED, lined):
        context, _, paper = open_both(browser, server, client, table(props))
        places.append(paper.evaluate(f"{LOADED}.then({PLACES})"))
        paper.close()
        context.close()
    assert places[0], places
    for here, there in zip(*places, strict=True):
        assert here == pytest.approx(there, abs=0.01)


def test_merged_and_sized_cells_with_lines_print_as_the_screen_shows_them(browser, server):
    """A12: a merged, sized table with dashed lines per cell prints as the screen shows it."""
    client = user()
    lined = {**SIZED, "lineStyle": "dashed", "lineWidth": 3, "edges": OUTLINE}
    assert not faults(browser, server, client, table(lined))
