"""The iPad on its side: a finger on the turn handle, and the plain dock.

The iPad helpers live in test_ipad.py."""

import json

import pytest
from playwright.sync_api import expect
from test_ipad import (
    THEMES,
    text,
    within,
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


def test_on_its_side_the_plain_dock_scrolls_and_keeps_off_the_format_panel(editor):
    """A8, #270"""
    page = editor(text("a", 1), theme="", touch="landscape")
    dock, panel = page.locator(".dock"), page.locator("aside.panel")
    assert within(dock.bounding_box(), page.locator(".stage").bounding_box())
    # The panel's left part at the dock's height is the panel's own, with the dock at either end.
    edge = panel.bounding_box()["x"] + 20
    hit = "([x, y]) => !!document.elementFromPoint(x, y).closest('aside.panel')"
    for end in (0, 99999):
        dock.evaluate("(el, x) => el.scrollTo(x, 0)", end)
        assert page.evaluate(hit, [edge, centre(dock)[1]])
    # Each tool comes into the dock by scrolling it.
    tools = dock.get_by_role("button").all()
    assert len(tools) > 15
    for tool in tools:
        tool.scroll_into_view_if_needed()
        assert within(tool.bounding_box(), dock.bounding_box())
    dock.evaluate("el => el.scrollTo(0, 0)")
    last = dock.get_by_label("Doppelpfeil", exact=True)
    assert not within(last.bounding_box(), dock.bounding_box())
    last.tap()
    expect(page.locator(".block[data-id]")).to_have_count(2)


@THEMES
@pytest.mark.parametrize("window", [(1400, 1000), (900, 1200)], ids=["wide", "upright"])
def test_with_a_mouse_a_dock_tool_shows_its_whole_name(editor, theme, window):
    """I8, #270. Upright the dock scrolled for a mouse too since #267."""
    page = editor(text("a", 1), theme=theme)
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
