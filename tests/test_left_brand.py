"""The logo stays at the top of the left sidebar of the leaf theme while the sidebar's content scrolls (#1084)."""

import re

import pytest
from playwright.sync_api import expect
from ui import TEXT, box


@pytest.mark.parametrize("tab", ["Start", "Ansicht", "Vorlagen"])
def test_the_logo_stays_at_the_top_while_the_left_sidebar_scrolls(editor, tab):
    """#1084"""
    page = editor(box("a", "text", TEXT), theme="leaf")
    page.set_viewport_size({"width": 1280, "height": 400})
    page.get_by_role("tab", name=tab, exact=True).click()
    left = page.locator(".left")
    brand = left.locator("a.brand")
    expect(brand).to_be_visible()
    overflow = left.evaluate("e => e.scrollHeight > e.clientHeight")
    assert overflow
    left.evaluate("e => e.scrollTop = e.scrollHeight")
    page.wait_for_function(
        "() => { const e = document.querySelector('.left'); return e.scrollTop + e.clientHeight >= e.scrollHeight - 1; }"
    )
    assert abs(brand.bounding_box()["y"] - left.bounding_box()["y"]) <= 1
    expect(brand).to_be_visible()
    centre = brand.bounding_box()
    hit = page.evaluate(
        """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            return !!el && !!el.closest('a.brand');
        }""",
        [centre["x"] + centre["width"] / 2, centre["y"] + centre["height"] / 2],
    )
    assert hit
    brand.click()
    expect(page).to_have_url(re.compile(r"^https?://[^/]+/?$"))
