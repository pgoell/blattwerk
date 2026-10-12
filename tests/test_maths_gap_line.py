"""A Lücke block of the maths generator draws its lines at its gaps only, never across the block.

The root of the block is a div of the maths class, and the rules for the gap and the written text
of a text took it too (issue #445). Each test names the line of the checklist it proves.
"""

import io

import httpx
import pypdfium2
import pytest
from PIL import Image
from pixels import over, screen_and_print
from playwright.sync_api import expect
from test_feed_print import sheet_id
from ui import TEXT, at, box, maths, sheet, user

# A line is clearly dark: the editor draws it in #222 (34), a gap's words in grey #999 (153).
DARK = 200
# The rectangles of the elements, in the window's pixels.
RECTS = (
    "els => els.map((el) => { const r = el.getBoundingClientRect();"
    " return [r.x, r.y, r.width, r.height]; })"
)


def gap_props(client, **more):
    """Lücke with six tasks: two rows of three, so six gaps with a line each."""
    return maths(client, format="gap", max=100, ops=["+", "-"], count=6, **more)


def still(locator):
    """The element's box, read once it has stood still for five frames.

    A new window size or zoom moves the page a frame or two later, so a box read at once can be
    wrong.
    """
    locator.scroll_into_view_if_needed()
    return locator.evaluate("""async el => {
        const place = () => {
            const r = el.getBoundingClientRect();
            return [r.x, r.y, r.width, r.height];
        };
        let [was, steady] = [place(), 0];
        while (steady < 5) {
            await new Promise(requestAnimationFrame);
            const now = place();
            steady = now.every((n, i) => n === was[i]) ? steady + 1 : 0;
            was = now;
        }
        return was;
    }""")


def dark_row(img, box, share):
    """The first row in the box of the picture that is dark across the share of its width, or None.

    A row of letters never fills that much, so only a line can.
    """
    left, top, right, bottom = (round(v) for v in box)
    crop = img.crop((left, top, right, bottom))
    grey, (width, height) = crop.tobytes(), crop.size
    for y in range(height):
        if sum(grey[y * width + x] < DARK for x in range(width)) >= share * width:
            return y
    return None


def check_screen(page, name, gaps):
    """The screen: no row of the block is dark across half its width, and each gap shows its line.

    One screenshot holds the block and its gaps, so the rows are read at one moment.
    """
    page.evaluate("document.fonts.ready.then(() => 0)")
    x, y, w, h = still(at(page, name))
    found = at(page, name).locator("u")
    expect(found).to_have_count(gaps)
    rects = found.evaluate_all(RECTS)
    shot = Image.open(io.BytesIO(page.screenshot())).convert("L")
    # A line the whole block's width runs across it: the faulty rule of the Lücke text.
    row = dark_row(shot, (x, y, x + w, y + h), 0.5)
    assert row is None, f"{name}: a line runs across the block on screen at row {row}"
    for i, (ux, uy, uw, uh) in enumerate(rects):
        # An empty gap is its bottom border and nothing else, a pixel high: a pixel of room above
        # it and two below.
        line = dark_row(shot, (ux, uy - 1, ux + uw, uy + uh + 2), 0.8)
        assert line is not None, f"{name}: gap {i} shows no line on screen"


def print_picture(server, client, mine):
    """Page 0 of the PDF, at 8 times the size of a point, in grey."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return pypdfium2.PdfDocument(res.content)[0].render(scale=8).to_pil().convert("L")


def mm_boxes(page, locator):
    """The elements' boxes in mm from the sheet's corner: the sheet is 210 mm wide."""
    sheet_box = page.locator('.sheet[data-page="0"]').bounding_box()
    scale = 210 / sheet_box["width"]
    return [
        ((x - sheet_box["x"]) * scale, (y - sheet_box["y"]) * scale, w * scale, h * scale)
        for x, y, w, h in locator.evaluate_all(RECTS)
    ]


def check_print(page, server, client, name, gaps):
    """The PDF: no row of the block is dark across half its width, and each gap shows its line."""
    page.evaluate("document.fonts.ready.then(() => 0)")
    (bx, by, bw, bh) = mm_boxes(page, at(page, name))[0]
    gap_boxes = mm_boxes(page, at(page, name).locator("u"))
    assert len(gap_boxes) == gaps
    picture = print_picture(server, client, sheet_id(page))
    per_mm = picture.width / 210
    row = dark_row(picture, [v * per_mm for v in (bx, by, bx + bw, by + bh)], 0.5)
    assert row is None, f"{name}: a line runs across the block in the PDF at row {row}"
    for i, (x, y, w, h) in enumerate(gap_boxes):
        # Half a millimetre of room around the gap's box, as the PDF lays it out.
        mm = (x - 0.5, y - 0.5, x + w + 0.5, y + h + 0.5)
        line = dark_row(picture, [v * per_mm for v in mm], 0.8)
        assert line is not None, f"{name}: gap {i} shows no line in the PDF"


def test_a5_a_gap_block_draws_lines_at_its_gaps_only_on_screen(editor):
    """A5: a Lücke block has no line across the block; only the gaps have lines."""
    client = user()
    page = editor(box("m", "maths", gap_props(client), y=20, h=40), client=client)
    check_screen(page, "m", gaps=6)


def test_a6_a_gap_block_draws_lines_at_its_gaps_only_in_the_pdf(editor, server):
    """A6: a Lücke block in the PDF has no line across the block; only the gaps have lines."""
    client = user()
    page = editor(box("m", "maths", gap_props(client), y=20, h=40), client=client)
    check_print(page, server, client, "m", gaps=6)


@pytest.mark.parametrize("format", ["row", "gap", "written", "compare"])
def test_i4_no_maths_format_takes_a_rule_of_a_text(editor, format):
    """I4: no maths format has a background on its root, and its root is not positioned."""
    client = user()
    # The written format needs more room for its tasks: 60 mm high.
    height = 60 if format == "written" else 40
    props = maths(client, format=format, max=100, ops=["+", "-"], count=6)
    page = editor(box("m", "maths", props, y=20, h=height), client=client)
    root = at(page, "m").locator(".maths")
    expect(at(page, "m").locator(".maths > div")).not_to_have_count(0)
    expect(root).to_have_css("background-image", "none")
    expect(root).to_have_css("position", "static")


def test_i5_a_gap_block_in_a_group_draws_lines_at_its_gaps_only_on_screen(editor):
    """I5: a Lücke block inside a group has no line across it; only the gaps have lines."""
    client = user()
    page = editor(
        box("m", "maths", gap_props(client), y=20, h=40, group=["g"]),
        box("t", "text", TEXT, z=3, group=["g"]),
        client=client,
    )
    check_screen(page, "m", gaps=6)


def test_i6_a_gap_block_looks_the_same_on_screen_and_in_the_pdf(browser, server):
    """I6: the screen and the PDF of a Lücke block agree pixel by pixel."""
    client = user()
    sheet_id_ = sheet(client, [box("m", "maths", gap_props(client), y=20, h=40)])["id"]
    screen, printed = screen_and_print(browser, server, client, sheet_id_)
    assert not over(screen, printed)
