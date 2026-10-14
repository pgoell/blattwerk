"""A template's name breaks before its tag, not over it (#601)."""

import pytest
from playwright.sync_api import expect
from ui import TEXT, bar, box, reload, user

# Where the name's own text ends and where its tag starts, both as the screen draws them.
MEASURE = """(name) => {
    const panel = document.querySelector("aside.left");
    const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) if (node.textContent.trim() === name) break;
    const tpl = node.parentElement.closest(".tpl");
    const text = document.createRange();
    text.selectNodeContents(node);
    const tag = tpl.querySelector("small");
    const lines = new Set();
    if (tag) {
        const drawn = document.createRange();
        drawn.selectNodeContents(tag);
        for (const rect of drawn.getClientRects()) lines.add(Math.round(rect.top));
    }
    return {
        textRight: text.getBoundingClientRect().right,
        nextLeft: tpl.lastElementChild.getBoundingClientRect().left,
        tagLines: lines.size,
    };
}"""

WIDTHS = [1280, 820]
NAMES = ["Beschriftungsblatt", "Klassenarbeit"]


def open_panel(page, width):
    page.set_viewport_size({"width": width, "height": 1024})
    # On a portrait iPad the panels are drawers: the bar's button opens the one on the left.
    if width < 1000:
        bar(page, "left").click()
        expect(page.locator(".tpl").first).to_be_visible()
        return
    page.get_by_role("tab", name="Vorlagen").click()
    expect(page.get_by_role("heading", name="Vorlagen", exact=True)).to_be_visible()


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", NAMES)
def test_the_name_ends_before_its_tag(editor, width, name):
    page = editor(box("a", "text", TEXT))
    open_panel(page, width)
    measured = page.evaluate(MEASURE, name)
    assert measured["textRight"] <= measured["nextLeft"]


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", NAMES)
def test_the_tag_stays_on_one_line(editor, width, name):
    page = editor(box("a", "text", TEXT))
    open_panel(page, width)
    assert page.evaluate(MEASURE, name)["tagLines"] == 1


def test_a_long_own_template_name_ends_before_its_delete_button(editor):
    client = user()
    own = {
        "pages": [{"blocks": [box("a", "text", TEXT)]}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    long_name = "Wochenplan mit sehr vielen Wörtern für die ganze Klasse"
    client.post("/api/templates", json={"name": long_name, "doc": own})
    page = editor(box("a", "text", TEXT), client=client)
    reload(page, page.url)
    open_panel(page, 820)
    expect(page.get_by_role("button", name=long_name, exact=True)).to_be_visible()
    measured = page.evaluate(MEASURE, long_name)
    assert measured["textRight"] <= measured["nextLeft"]


def test_the_thumbnail_keeps_its_width_beside_a_long_name(editor):
    page = editor(box("a", "text", TEXT))
    open_panel(page, 820)
    thumb = page.locator(".tpl", has=page.get_by_text("Beschriftungsblatt", exact=True))
    width = thumb.locator(".tpl-thumb").evaluate("el => el.getBoundingClientRect().width")
    assert width == 48
