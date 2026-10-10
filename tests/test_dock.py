"""The dock of insert tools in a window of a phone's width (#274).

For a mouse it wraps, as it does in a wider window, so nothing cuts off the name over a tool. For
a finger it still scrolls.
"""

import pytest
from playwright.sync_api import expect
from test_bar import THEMES, TIP, text

TOOLS = ".stage .dock .ib"
# What the dock says of itself: how it lays out its tools, whether they need more room than it
# has, the rows they stand in, and whether each lies in the window and in the dock.
DOCK = """() => {
    const dock = document.querySelector(".stage .dock");
    const look = getComputedStyle(dock);
    const around = dock.getBoundingClientRect();
    const boxes = [...dock.querySelectorAll(".ib")].map((el) => el.getBoundingClientRect());
    const within = (box, left, top, right, bottom) => box.width > 0
        && box.left >= left && box.top >= top && box.right <= right && box.bottom <= bottom;
    return {
        wrap: look.flexWrap,
        flow: look.overflowX,
        scrolls: dock.scrollWidth > dock.clientWidth,
        rows: new Set(boxes.map((box) => Math.round(box.top))).size,
        inside: boxes.every((box) => within(box, 0, 0, innerWidth, innerHeight)
            && within(box, around.left, around.top, around.right, around.bottom)),
        dock: within(around, 0, 0, innerWidth, innerHeight),
    };
}"""


def narrow(editor, width, touch=False, theme=""):
    """The editor in a window of that width, opened anew at it, with fingers or a mouse."""
    page = editor(text("a"), theme=theme, touch=touch)
    # The panels a window starts with go by its width as the editor opens.
    page.set_viewport_size({"width": width, "height": 900})
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    expect(page.locator(TOOLS).first).to_be_visible()
    return page


def test_a_tools_name_shows_whole_over_it_on_hover_in_a_narrow_window(editor):
    """B1"""
    page = narrow(editor, 600)
    tools = page.locator(TOOLS).all()
    assert len(tools) > 10
    for button in tools:
        button.hover()
        tip = button.evaluate(TIP)
        assert tip and tip["content"] == f'"{button.get_attribute("aria-label")}"', tip
        assert tip["cut"] is None, tip
        assert tip["box"]["left"] >= 0 and tip["box"]["right"] <= tip["window"][0], tip
        assert tip["box"]["top"] >= 0 and tip["box"]["bottom"] <= tip["window"][1], tip


@THEMES
def test_for_a_mouse_the_dock_wraps_in_a_narrow_window_as_in_a_wider_one(editor, theme):
    """B2"""
    wide = narrow(editor, 701, theme=theme).evaluate(DOCK)
    small = narrow(editor, 600, theme=theme).evaluate(DOCK)
    for got in (wide, small):
        assert got["wrap"] == "wrap" and got["flow"] == "visible" and not got["scrolls"], got
        # The tools need more than one row there.
        assert got["rows"] > 1, got


@THEMES
@pytest.mark.parametrize("width", [600, 360])
def test_for_a_finger_the_dock_still_scrolls_in_a_narrow_window(editor, theme, width):
    """I5"""
    page = narrow(editor, width, touch=True, theme=theme)
    assert page.evaluate("matchMedia('(pointer: coarse)').matches")
    got = page.evaluate(DOCK)
    assert got["wrap"] == "nowrap" and got["flow"] == "auto" and got["scrolls"], got
    assert got["rows"] == 1 and got["dock"], got
    # The last tool lies outside the dock until the dock is scrolled to it.
    last = page.locator(TOOLS).last
    expect(last).not_to_be_in_viewport()
    page.locator(".stage .dock").evaluate("el => el.scrollLeft = el.scrollWidth")
    expect(last).to_be_in_viewport(ratio=1)


@THEMES
@pytest.mark.parametrize("width", [600, 360])
def test_for_a_mouse_every_tool_of_the_wrapped_dock_lies_in_the_window(editor, theme, width):
    """I6"""
    page = narrow(editor, width, theme=theme)
    got = page.evaluate(DOCK)
    assert got["inside"] and got["dock"], got
    for button in page.locator(TOOLS).all():
        expect(button).to_be_in_viewport(ratio=1)
