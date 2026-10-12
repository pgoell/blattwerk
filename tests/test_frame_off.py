"""The frame and handles of a picked block lie 8 px outside it (issue 405)."""

import math

import pytest
from test_zoom import of_kind
from ui import LINE, RECT, TEXT, at, box, centre, doc, drag, expect_picked, pick, unpick, user

SENTENCE = "Lies den Text und male ein Bild dazu."
# The frame's distance from the block, in px on the screen.
GAP = 8
# A block with room around it, well inside the page.
PLACE = {"x": 60, "y": 60, "w": 60, "h": 40}
KINDS = ["text", "shape", "picture", "table", "ruling", "maths", "name", "points", "group"]
HANDLES = ".moveable-control:not(.moveable-rotation-control)"


def boxes(page, selector):
    """The screen boxes of the elements, as left, top, right, bottom."""
    return page.evaluate(
        """(selector) => [...document.querySelectorAll(selector)]
            .filter((el) => el.getClientRects().length)
            .map((el) => {
                const r = el.getBoundingClientRect();
                return [r.left, r.top, r.right, r.bottom];
            })""",
        selector,
    )


def meet(a, b):
    """Whether two boxes overlap, edges touching not counted."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def outline(page, names):
    """The box around the named blocks on the screen, as left, top, right, bottom."""
    found = [at(page, name).bounding_box() for name in names]
    left = min(b["x"] for b in found)
    top = min(b["y"] for b in found)
    right = max(b["x"] + b["width"] for b in found)
    bottom = max(b["y"] + b["height"] for b in found)
    return [left, top, right, bottom]


def letters(page, name):
    """The first letter of each line of the block, as boxes on the screen."""
    return page.evaluate(
        """(name) => {
            const block = document.querySelector(`.block[data-id="${name}"]`);
            const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
            const first = new Map();
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
                for (let i = 0; i < node.length; i++) {
                    if (!node.data[i].trim()) continue;
                    const range = document.createRange();
                    range.setStart(node, i);
                    range.setEnd(node, i + 1);
                    const r = range.getBoundingClientRect();
                    const line = Math.round(r.top / 4);
                    if (!first.has(line) || r.left < first.get(line).left) first.set(line, r);
                }
            }
            return [...first.values()].map((r) => [r.left, r.top, r.right, r.bottom]);
        }""",
        name,
    )


def test_no_handle_and_no_frame_lies_on_a_picked_texts_letters(editor):
    """A1"""
    page = editor(box("a", "text", {**TEXT, "text": SENTENCE}, **PLACE))
    pick(page, "a")
    found = letters(page, "a")
    assert len(found) == 2
    for letter in found:
        assert not [h for h in boxes(page, HANDLES) if meet(h, letter)]
        assert not [f for f in boxes(page, ".moveable-line") if meet(f, letter)]


@pytest.mark.parametrize("kind", KINDS)
def test_the_frame_lies_outside_every_kind_of_block(editor, kind):
    """A2"""
    client = user()
    if kind == "name":
        blocks = [box("a", "name", {})]
    elif kind == "points":
        blocks = [box("a", "points", {"max": 10})]
    elif kind == "table":
        blocks = of_kind("table", client)
    else:
        blocks = of_kind(kind, client)
    names = [b["id"] for b in blocks]
    page = editor(*blocks, client=client)
    at(page, "a").click()
    expect_picked(page, *names)
    shape = outline(page, names)
    for handle in boxes(page, HANDLES):
        assert not meet(handle, shape)
    for line in boxes(page, ".moveable-line"):
        assert not meet(line, shape)


def test_a_line_keeps_the_handles_on_its_ends(editor):
    """A2"""
    page = editor(box("a", "shape", LINE, **PLACE))
    pick(page, "a")
    left, top, right, bottom = outline(page, ["a"])
    corners = [(left, top), (right, bottom)]
    ends = page.evaluate(
        "() => [...document.querySelectorAll('.end')].map((el) => {"
        "const r = el.getBoundingClientRect();"
        "return [r.left + r.width / 2, r.top + r.height / 2];})"
    )
    assert len(ends) == 2
    for end, corner in zip(sorted(ends), sorted(corners), strict=True):
        assert end == pytest.approx(corner, abs=1.5)


def test_a_handle_drag_resizes_by_the_mouses_way(editor):
    """I1 (a)"""
    page = editor(box("a", "text", TEXT, **PLACE))
    pick(page, "a")
    was = at(page, "a").bounding_box()
    start = centre(page.locator(".moveable-control.moveable-se"))
    # The loose key, Alt, lets the block take any size: no snap comes in the way.
    drag(page, start, (start[0] + 30, start[1] + 20), keys=["Alt"])
    now = at(page, "a").bounding_box()
    assert now["width"] == pytest.approx(was["width"] + 30, abs=1)
    assert now["height"] == pytest.approx(was["height"] + 20, abs=1)


def test_a_block_snaps_by_its_own_edge(editor):
    """I1 (b)"""
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("b", "shape", RECT, z=2, x=20, y=150, w=40, h=30),
    )
    pick(page, "b")
    scale = page.locator(".sheet.on").bounding_box()["width"] / 210
    x, y = centre(at(page, "b"))
    # The left edge of b is 3 px short of a's left edge: that is within the snap, which takes it.
    drag(page, (x, y), (x + (60 - 20) * scale - 3, y))
    left_a = at(page, "a").bounding_box()["x"]
    assert at(page, "b").bounding_box()["x"] == pytest.approx(left_a, abs=0.2)


def test_the_frame_keeps_its_distance_for_several_blocks(editor):
    """I2"""
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("b", "shape", RECT, z=2, x=60, y=120, w=40, h=20),
    )
    pick(page, "a", "b")
    left, top, right, bottom = outline(page, ["a", "b"])
    nw = centre(page.locator(".moveable-control.moveable-nw"))
    se = centre(page.locator(".moveable-control.moveable-se"))
    assert nw == pytest.approx((left - GAP, top - GAP), abs=1)
    assert se == pytest.approx((right + GAP, bottom + GAP), abs=1)


def test_the_frame_keeps_its_distance_on_a_turned_block(editor):
    """I2"""
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=30, angle=30))
    pick(page, "a")
    block = at(page, "a")
    theta = math.radians(30)
    # The block's size on the screen, from the box round it: the angle undone.
    around = block.bounding_box()
    c, s = math.cos(theta), math.sin(theta)
    det = c * c - s * s
    half_w = (around["width"] * c - around["height"] * s) / det / 2
    half_h = (around["height"] * c - around["width"] * s) / det / 2
    cx, cy = centre(block)
    # The corners of the turned block, with the frame's gap pushed out along its own axes.
    for name, sx, sy in (("nw", -1, -1), ("ne", 1, -1), ("se", 1, 1), ("sw", -1, 1)):
        x, y = sx * (half_w + GAP), sy * (half_h + GAP)
        expected = (
            cx + x * math.cos(theta) - y * math.sin(theta),
            cy + x * math.sin(theta) + y * math.cos(theta),
        )
        assert centre(page.locator(f".moveable-control.moveable-{name}")) == pytest.approx(
            expected, abs=1
        )


def test_the_frame_changes_no_saved_sheet_and_no_block_on_the_screen(editor):
    """I3"""
    client = user()
    page = editor(box("a", "text", TEXT, **PLACE), client=client)
    loaded = doc(page, client)
    unpicked = at(page, "a").bounding_box()
    pick(page, "a")
    picked = at(page, "a").bounding_box()
    unpick(page)
    pick(page, "a")
    assert at(page, "a").bounding_box() == pytest.approx(picked, abs=0.5)
    assert picked == pytest.approx(unpicked, abs=0.5)
    assert doc(page, client) == loaded


def test_a_click_in_the_band_picks_what_lies_there(editor):
    """I4"""
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("b", "text", TEXT, z=2, x=20, y=60, w=39, h=40),
    )
    pick(page, "a")
    a = at(page, "a").bounding_box()
    # 4 px left of a's left edge, and a quarter down: in the band, with b under it and no handle.
    page.mouse.click(a["x"] - 4, a["y"] + a["height"] / 4)
    expect_picked(page, "b")


def test_a_click_in_the_band_over_empty_paper_clears_the_selection(editor):
    """I4"""
    page = editor(box("a", "text", TEXT, **PLACE))
    pick(page, "a")
    a = at(page, "a").bounding_box()
    page.mouse.click(a["x"] - 4, a["y"] + a["height"] / 4)
    expect_picked(page)
