"""The iPad on its side: a finger on the turn handle, and the plain dock.

The iPad helpers live in test_ipad.py."""

import json

import pytest
from test_ipad import (
    text,
)
from test_rotate import HANDLE
from ui import (
    RECT,
    angle,
    arc,
    at,
    box,
    centre,
    expect_picked,
    swipe,
)


def test_on_its_side_a_finger_turns_a_block_by_its_handle(editor):
    """I7, #269"""
    page = editor(box("a", "shape", RECT, x=75, y=80, w=60, h=20), touch="landscape")
    at(page, "a").tap()
    expect_picked(page, "a")
    about = centre(at(page, "a"))
    swipe(page, *arc(centre(page.locator(HANDLE)), about, 90))
    # A finger is less exact than a mouse: the browser may keep its first few pixels to itself.
    assert abs(angle(page, "a") - 90) <= 5
    assert centre(at(page, "a")) == pytest.approx(about, abs=1)


@pytest.mark.parametrize("window", [(1400, 1000), (700, 1200)], ids=["wide", "narrow"])
def test_with_a_mouse_a_dock_tool_shows_its_whole_name(editor, window):
    """I8, #270. A narrow dock scrolled for a mouse too since #267. The upright tablet has a rail
    with each name drawn (#1187): tests/test_tablet.py."""
    page = editor(text("a", 1))
    page.set_viewport_size({"width": window[0], "height": window[1]})
    tool = page.locator(".dock .ib").first
    tool.hover()
    tip = "el => getComputedStyle(el, '::after').content"
    assert tool.evaluate(tip) == json.dumps(tool.get_attribute("aria-label"))
    # The name stands over the dock: a dock that scrolls would cut it off.
    clips = """el => {
        const found = [];
        for (let up = el.parentElement; !up.matches(".stage"); up = up.parentElement) {
            const { overflowX, overflowY } = getComputedStyle(up);
            found.push(overflowX, overflowY);
        }
        return found.filter((overflow) => overflow !== "visible");
    }"""
    assert tool.evaluate(clips) == []
