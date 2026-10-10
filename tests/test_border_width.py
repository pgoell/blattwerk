"""A border prints as wide as it is set, and the screen shows that width (#297)."""

import math

import pytest
from pixels import LOADED, dark, grey, measures, runs, screen_and_print
from ui import BROWSER, RECT, TEXT, at, box, expect_picked, pick, sheet, unpick, user

from blattwerk import pdf

# How dark a border of #222222 is, from 0 to 1.
BLACK = 1 - 0x22 / 255
K = 96 / 25.4
WIDTHS = [0.2, 0.5, 1, 3]
LOOKS = [(width, dash) for dash in (None, "dashed", "dotted") for width in WIDTHS]
SIZE = {"w": 60, "h": 30}
WORDS = "Der Igel sucht im Herbst nach Futter und baut sich ein Nest aus Laub."


def look(width, dash=None):
    return {"stroke": "#222222", "strokeWidth": width, **({"dash": dash} if dash else {})}


def page(width, dash):
    """Each kind of block that takes a border: level, turned by a right angle, and in a group."""
    edge = look(width, dash)
    shape = {**RECT, **edge}
    text = {**TEXT, **edge}
    places = {
        "rect": ("shape", shape, 20, 15, {}),
        "rounded": ("shape", {**shape, "kind": "rounded"}, 110, 15, {}),
        "circle": ("shape", {**shape, "kind": "circle"}, 20, 55, {}),
        "bubble": ("shape", {**shape, "kind": "bubble"}, 110, 55, {}),
        "text": ("text", text, 20, 95, {}),
        "rect in a group": ("shape", shape, 110, 95, {"group": ["g"]}),
        "text in a group": ("text", text, 20, 135, {"group": ["g"]}),
        "rect turned": ("shape", shape, 30, 190, {"angle": 90}),
        "text turned": ("text", text, 120, 190, {"angle": 90}),
    }
    return [
        box(name, kind, props, x=x, y=y, **SIZE, **more)
        for name, (kind, props, x, y, more) in places.items()
    ]


def strip(block, width, dash, foot):
    """A part of the block's box across its border, clear of its corners and its text.

    From the box's corner: left, top, right, bottom. Across the top edge, or the `foot`.
    """
    w, h = block["w"], block["h"]
    if foot:
        return w / 2 - 1, h - width - 1, w / 2 + 1, h + 2
    # Where the stroke starts, along the top edge: after the corner, or at the top of a circle.
    corner = {"rounded": 4, "bubble": 4 + width / 2, "circle": w / 2}
    start = corner.get(block["props"].get("kind"), width / 2)
    if dash == "dashed":
        # Within the first dash, which is four widths long.
        return start + 1.25 * width, -2, start + 2.75 * width, width + 1
    if dash == "dotted":
        # The first dot whole. The next ones start two widths from its middle.
        return start - 1.2 * width, -0.5, start + 1.2 * width, 1.5 * width
    return w / 2 - 1, -2, w / 2 + 1, width + 1


def measured(picture, block, width, dash, foot):
    """The width in mm of the block's border in the picture."""
    x, y, w, h = (block[side] for side in "xywh")
    left, top, right, low = strip(block, width, dash, foot)
    level = block.get("angle") != 90
    if level:
        part = (x + left, y + top, x + right, y + low)
    else:
        # Turned about its middle, the top edge is the right one.
        edge, start = x + w / 2 + h / 2, y + h / 2 - w / 2
        part = (edge - low, start + left, edge - top, start + right)
    mm = picture.width / 210
    rows = dark(picture, part, level)
    if dash == "dotted":
        # A dot's ink is its area: a strip through its middle would have to hit it to a pixel.
        across = round(part[2 if level else 3] * mm) - round(part[0 if level else 1] * mm)
        return (4 * sum(rows) * across / BLACK / math.pi) ** 0.5 / mm
    # The ink of the run is the border's width in pixels times its darkness.
    return runs(rows)[0 if level != foot else -1][2] / mm / BLACK


def widths(browser, server, width, dash):
    """Each border in mm on the screen and in the PDF, by the block's name."""
    client = user()
    blocks = page(width, dash)
    pictures = grey(browser, server, client, blocks)
    found = {}
    for block in blocks:
        kind = block["props"].get("kind")
        # No dot of these two stands alone in a strip: a round box prints its first dot with a part
        # of the last one over it, as on master, and a bubble's dots turn its corner too close by.
        tops = [] if dash == "dotted" and kind in ("rounded", "bubble") else [False]
        # The top edge, and the foot of a solid border: a dash need not lie on the foot's middle.
        # An outline's foot, a bubble's tail, is not level.
        for foot in tops + [True] * (not dash and kind != "bubble"):
            name = block["id"] + " foot" * foot
            found[name] = tuple(measured(p, block, width, dash, foot) for p in pictures)
    return found


@pytest.mark.parametrize("width, dash", LOOKS)
def test_a_border_prints_as_wide_as_it_is_set(browser, server, width, dash):
    """A5, I2, I3"""
    for name, (_, printed) in widths(browser, server, width, dash).items():
        # pdfium smooths the edge of a stroke over the pixel it ends in.
        assert printed == pytest.approx(width, abs=0.06), (name, printed)


@pytest.mark.parametrize("width, dash", LOOKS)
def test_the_screen_shows_a_border_as_wide_as_it_prints(browser, server, width, dash):
    """A6, I2"""
    for name, (screen, printed) in widths(browser, server, width, dash).items():
        # Less than a pixel of an iPad, 0.13 mm: WebKit lays a border's inner edge on a whole one.
        assert screen == pytest.approx(printed, abs=0.1), (name, screen, printed)


def foot(picture, block, width):
    """The width in mm of the stroke along a block's foot, where it is widest: on a dash."""
    x, y, w, h = (block[side] for side in "xywh")
    found = []
    # Strips of half a mm over the middle 20 mm: the widest lies on a dash.
    for step in range(40):
        left = x + w / 2 - 10 + step / 2
        rows = dark(picture, (left, y + h - width - 1, left + 0.5, y + h + 2))
        found.append(sum(rows) / (picture.width / 210) / BLACK)
    return max(found)


@pytest.mark.parametrize("width", [0.2, 0.5, 1])
def test_the_foot_of_an_outline_and_of_dashes_is_as_wide_as_it_is_set(browser, server, width):
    """A5, A6: a drawn stroke lies flush with the box's foot, which is seldom on a whole pixel."""
    client = user()
    shape = {**RECT, **look(width)}
    blocks = [
        box("triangle", "shape", {**shape, "kind": "triangle"}, x=20, y=55, **SIZE),
        box("dashed", "shape", {**shape, "dash": "dashed"}, x=20, y=95, **SIZE),
        box("dashed text", "text", {**TEXT, **look(width, "dashed")}, x=110, y=95, **SIZE),
        box("triangle below", "shape", {**shape, "kind": "triangle"}, x=20, y=181, **SIZE),
    ]
    screen, printed = (
        [foot(picture, block, width) for block in blocks]
        for picture in grey(browser, server, client, blocks)
    )
    # Cut at a whole pixel, 0.5 mm printed 0.44 to 0.46 wide and showed 0.36 to 0.39.
    assert printed == pytest.approx([width] * 4, abs=0.03)
    # WebKit still cuts an outline's foot on the screen at some places, by a pixel of an iPad:
    # 0.06 for 0.2 mm and 0.38 for 0.5 mm, as before.
    assert screen == pytest.approx(printed, abs=0.15 if BROWSER == "webkit" else 0.05)


@pytest.mark.parametrize("width", [0.5, 1])
def test_a_turned_border_is_on_the_screen_as_it_prints(browser, server, width):
    """A5, A6: turned by 30 degrees no strip crosses a border squarely, so by the ink of a tile."""
    client = user()
    edge = look(width)
    blocks = [
        box("a", "shape", {**RECT, **edge}, x=40, y=40, **SIZE, angle=30),
        box("b", "text", {**TEXT, **edge}, x=40, y=120, **SIZE, angle=30),
    ]
    found, _ = measures(*screen_and_print(browser, server, client, sheet(client, blocks)["id"]))
    # A border of 0.5 mm that prints at 0.26 mm is 0.37 in WebKit.
    assert found["ink"][0] < 0.15, found


# Each frame's text from the frame's corner, in the page's own pixels: left, top, width, height.
PLACES = """() => {
    const page = document.querySelector('.scaled');
    const k = page.getBoundingClientRect().width / parseFloat(getComputedStyle(page).width);
    return [...page.querySelectorAll('.frame')].map((frame) => {
        const from = frame.getBoundingClientRect();
        const r = frame.querySelector('p').getBoundingClientRect();
        return [(r.x - from.x) / k, (r.y - from.y) / k, r.width / k, r.height / k];
    });
}"""
# The rows the words break into in a box 60 mm wide, as sheets saved before this change have them.
ROWS = {0.5: 4, 2: 4, 3: 4}


@pytest.mark.parametrize("width", ROWS)
def test_a_text_in_a_border_keeps_its_place_and_its_rows(browser, server, width):
    """I1"""
    client = user()
    edge = look(width)
    words = {**TEXT, "text": WORDS}
    blocks = [
        box("solid", "text", {**words, **edge}, x=20, y=20, w=60, h=60),
        box("dashed", "text", {**words, **edge, "dash": "dashed"}, x=20, y=90, w=60, h=60),
        box("shape", "shape", {**RECT, **words, **edge, "valign": "top"}, x=20, y=160, w=60, h=60),
    ]
    mine = sheet(client, blocks)["id"]
    # A sharp screen, as an iPad has.
    context = browser.new_context(device_scale_factor=2)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    places = [tab.evaluate(f"{LOADED}.then({PLACES})") for tab in (shown, paper)]
    paper.close()
    context.close()
    # Where a CSS border had the text: the print laid that border out on whole pixels, rounded
    # down, and the room of a PowerPoint text box, 2.5 mm across and 1.3 mm down, inside it.
    border = max(1, int(width * K))
    left, top = border + 2.5 * K, border + 1.3 * K
    row = 14 / 72 * 96 * 1.3
    for tab in places:
        assert len(tab) == 3
        for *place, height in tab:
            # A browser lays a box out on 64ths of a pixel.
            assert place == pytest.approx([left, top, 60 * K - 2 * left], abs=0.02)
            assert round(height / row) == ROWS[width]


@pytest.mark.parametrize("width", [0.5, 3])
def test_a_click_on_the_border_or_inside_picks_a_shape_with_no_fill(editor, width):
    """I5"""
    page = editor(box("a", "shape", {**RECT, **look(width)}, x=40, y=60, **SIZE))
    block = at(page, "a")
    size = block.bounding_box()
    at(page, "a").click(position={"x": 1, "y": size["height"] / 2})
    expect_picked(page, "a")
    unpick(page)
    # As before this change: a click inside picks it too.
    pick(page, "a")
