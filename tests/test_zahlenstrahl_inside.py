"""A Zahlenstrahl's drawing stays inside its block at any font size: a box lowered over a number
shown beside it does not hang out under the block's bottom (#585).

The check reads the screen: the rectangle of every rect, line, text and path of the line's svg
lies inside the block's own rectangle. The line's place below the block is not pinned here, only
that its drawing fits.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from test_words import undo
from ui import at, box, doc, pick, user

# Tasks free: one box on 362, the numbers every 10 from 340 to 420, ticks every 2.
PROPS = {
    "start": 340,
    "end": 420,
    "minor": 2,
    "major": 10,
    "labels": "major",
    "size": 20,
    "cut": False,
    "tasks": "free",
    "boxes": 0,
    "arrows": 0,
    "jumps": False,
    "marks": [[362, "box"]],
    "seed": 7,
}
# The union of the screen rectangles of the drawn parts, next to the block's own.
EDGES = """block => {
    const parts = [...block.querySelectorAll('.zahlenstrahl svg :is(rect, line, text, path)')];
    const rects = parts.map(e => e.getBoundingClientRect());
    const b = block.getBoundingClientRect();
    return {
        drawn: {
            left: Math.min(...rects.map(r => r.left)),
            top: Math.min(...rects.map(r => r.top)),
            right: Math.max(...rects.map(r => r.right)),
            bottom: Math.max(...rects.map(r => r.bottom)),
        },
        block: { left: b.left, top: b.top, right: b.right, bottom: b.bottom },
    };
}"""


@pytest.mark.parametrize(
    "size, width, height, more",
    [
        (20, 180, 30, {}),
        (14, 180, 30, {}),
        (24, 180, 30, {}),
        (20, 120, 30, {}),
        (20, 180, 30, {"marks": [[362, "box"], [380, "arrow"]], "jumps": True}),
        (24, 180, 22, {"marks": [[362, "box"], [380, "arrow"]], "jumps": True}),
    ],
    ids=["20pt", "14pt", "24pt", "narrow", "arrow-arcs", "short-block"],
)
def test_the_drawing_of_a_lowered_box_stays_inside_the_block(editor, size, width, height, more):
    """A box on 362 among the numbers of 340 to 420: its line and its box, at font size `size` in a
    block `width` by `height` mm, lie within the block: top, bottom and right to half a pixel,
    left to 1 mm. With an arrow and arcs above the line, and in a block too short for it all."""
    page = editor(
        box("z", "zahlenstrahl", {**PROPS, "size": size, **more}, w=width, h=height),
        client=user(),
    )
    expect(at(page, "z").locator(".zahlenstrahl g.box rect")).to_have_count(1)
    edges = at(page, "z").evaluate(EDGES)
    drawn, block = edges["drawn"], edges["block"]
    # The label "340" centred on the first tick overhangs the left edge by about 0.2 mm (its glyph
    # box): a fault of the numbers, not of the box. Allowed here at 1 mm, about 4 px.
    assert drawn["left"] >= block["left"] - 4, edges
    assert drawn["top"] >= block["top"] - 0.5, edges
    assert drawn["right"] <= block["right"] + 0.5, edges
    assert drawn["bottom"] <= block["bottom"] + 0.5, edges


def line_y(page):
    """Where the line lies on the screen: the top of the axis's rectangle."""
    axis = at(page, "z").locator(".zahlenstrahl line.axis")
    return axis.evaluate("e => e.getBoundingClientRect().top")


def height(page, client):
    [b] = [b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "z"]
    return b["h"]


@pytest.mark.parametrize("size", ["20", "24"])
def test_a_larger_size_grows_the_block_and_the_line_keeps_its_place(editor, size):
    """#585: Schriftgröße typed in the panel grows the block downward so the lowered box fits; the
    line stays where it was on the page, and one undo takes back size and height together."""
    client = user()
    page = editor(box("z", "zahlenstrahl", {**PROPS, "size": 12}, w=180, h=30), client=client)
    pick(page, "z")
    before = line_y(page)
    number = page.locator(".panel").get_by_label("Schriftgröße", exact=True)
    step(page, lambda: number.fill(size))
    assert height(page, client) > 30
    edges = at(page, "z").evaluate(EDGES)
    assert edges["drawn"]["bottom"] <= edges["block"]["bottom"] + 0.5, edges
    assert edges["drawn"]["top"] >= edges["block"]["top"] - 0.5, edges
    assert abs(line_y(page) - before) < 1
    step(page, lambda: undo(page))
    assert height(page, client) == 30
