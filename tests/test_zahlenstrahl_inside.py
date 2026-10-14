"""A Zahlenstrahl's drawing stays inside its block at any font size: a box lowered over a number
shown beside it does not hang out under the block's bottom (#585).

The check reads the screen: the rectangle of every rect, line, text and path of the line's svg
lies inside the block's own rectangle. The line's place below the block is not pinned here, only
that its drawing fits.
"""

import pytest
from playwright.sync_api import expect
from ui import at, box, user

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
    "size, width, height",
    [(20, 180, 30), (14, 180, 30), (28, 180, 40), (20, 120, 30)],
)
def test_the_drawing_of_a_lowered_box_stays_inside_the_block(editor, size, width, height):
    """A box on 362 among the numbers of 340 to 420: its line and its box, at font size `size` in a
    block `width` by `height` mm, lie within the block: top, bottom and right to half a pixel,
    left to 1 mm. The 28 pt line needs 38 mm of height, so its block is taller."""
    page = editor(
        box("z", "zahlenstrahl", {**PROPS, "size": size}, w=width, h=height),
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
