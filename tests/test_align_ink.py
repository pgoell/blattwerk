"""Aligning a thing to the page by what it draws: a line's stroke and arrow head count (#677)."""

import pytest
from test_align import button
from test_fields import enter
from test_group_scale_turned import SHAPES, pick_group
from ui import user

# Every drawn element of the block, as the page shows it, and the page's own sides.
INK = """(name) => {
    const page = document.querySelector('.sheet').getBoundingClientRect();
    // The drawn shapes only. A rotated box is wider than its ink, so a polygon's
    // points are moved onto the screen one by one.
    const drawn = [...document.querySelectorAll(`.sheet .block[data-id="${name}"] *`)]
        .filter((el) => !["svg", "g"].includes(el.tagName))
        .flatMap((el) => {
            if (el.tagName === "polygon") {
                const m = el.getScreenCTM();
                return [...el.points].map((p) => {
                    const q = new DOMPoint(p.x, p.y).matrixTransform(m);
                    return { left: q.x, right: q.x, top: q.y, bottom: q.y };
                });
            }
            const r = el.getBoundingClientRect();
            const box = { left: r.left, right: r.right, top: r.top, bottom: r.bottom };
            return r.width > 0 || r.height > 0 ? [box] : [];
        });
    const mm = page.width / 210;
    return {
        left: (Math.min(...drawn.map((r) => r.left)) - page.left) / mm,
        right: (page.right - Math.max(...drawn.map((r) => r.right))) / mm,
        top: (Math.min(...drawn.map((r) => r.top)) - page.top) / mm,
        bottom: (page.bottom - Math.max(...drawn.map((r) => r.bottom))) / mm,
    };
}"""


def ink(page, *names):
    """The gap in mm from each page edge to the nearest thing the blocks draw."""
    gaps = [page.evaluate(INK, name) for name in names]
    return {side: min(gap[side] for gap in gaps) for side in ("left", "right", "top", "bottom")}


@pytest.mark.parametrize(
    "name, side",
    [
        ("Links", "left"),
        ("Rechts", "right"),
        ("Oben", "top"),
        ("Unten", "bottom"),
    ],
)
def test_a_turned_group_with_a_line_lines_up_by_what_it_draws(editor, name, side):
    page = editor(*SHAPES, client=user())
    pick_group(page, "a", "b")
    enter(page, "Drehung", "30")
    button(page, name).click()
    gap = ink(page, "a", "b")
    assert gap[side] == pytest.approx(0, abs=0.5)
    assert all(v >= -0.5 for v in gap.values())
