"""The dock of insert tools in a window of a phone's width (#274).

For a mouse it wraps, as it does in a wider window, so nothing cuts off the name over a tool. For
a finger it still scrolls.
"""

import pytest
from playwright.sync_api import expect
from test_bar import THEMES, TIP, text
from ui import at, expect_picked, pick

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


def narrow(editor, width, touch=False, theme="", more=()):
    """The editor in a window of that width, opened anew at it, with fingers or a mouse."""
    page = editor(text("a"), theme=theme, touch=touch, more=more)
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
@pytest.mark.parametrize("width", [360, 600, 701])
def test_a_tools_name_stays_in_the_window_and_over_its_tool_where_it_has_room(editor, theme, width):
    """A2, I2, I3"""
    page = narrow(editor, width, theme=theme)
    tools = page.locator(TOOLS).all()
    assert len(tools) > 10
    last = {360: "Namenszeile", 701: "Sprechblase"}.get(width)
    shifted = []
    for button in tools:
        button.hover()
        tip = button.evaluate(TIP)
        name = button.get_attribute("aria-label")
        assert tip and tip["content"] == f'"{name}"', tip
        assert tip["cut"] is None, tip
        on = button.bounding_box()
        middle = on["x"] + on["width"] / 2
        half = (tip["box"]["right"] - tip["box"]["left"]) / 2
        # Centred where that leaves it clear of the window's edges, else as near to it as it gets.
        want = min(max(middle, 4 + half), width - 4 - half)
        assert abs(tip["box"]["left"] + half - want) < 0.5, (name, tip)
        if want != middle:
            shifted.append(name)
    # The tool at the end of the first row is one that has no room.
    assert last is None or last in shifted, shifted
    assert len(shifted) < len(tools) / 2, shifted


@THEMES
def test_a_name_in_the_bar_and_in_the_shapes_stands_centred_under_its_button(editor, theme):
    """I3"""
    page = editor(text("a"), theme=theme)
    # Only Blattform has the shapes in a panel, at the window's left.
    shapes = page.locator(".insert .shapes .ib")
    assert (shapes.count() > 1) == (theme is None)
    for button in (page.locator(".top").get_by_label("Einfügen", exact=True), *shapes.all()[1:]):
        button.hover()
        tip = button.evaluate(TIP)
        assert tip, button
        on = button.bounding_box()
        middle = (tip["box"]["left"] + tip["box"]["right"]) / 2
        assert abs(middle - on["x"] - on["width"] / 2) < 0.5, tip
        assert button.evaluate("(el) => getComputedStyle(el, '::after').marginLeft") == "0px"


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


# The desk scrolled to its end: how far the last sheet reaches under the highest dock, the room
# each of the three keeps free of the dock, and what the dock needs from the desk's lower edge.
ROOM = """() => {
    const desk = document.querySelector(".desk");
    desk.scrollTop = desk.scrollHeight;
    const tops = (css) => [...document.querySelectorAll(css)]
        .map((el) => el.getBoundingClientRect().top);
    const top = Math.min(...tops(".stage .dock"));
    const px = (el, key) => el ? parseFloat(getComputedStyle(el)[key]) : null;
    return {
        over: [...desk.querySelectorAll(".sheet")].at(-1).getBoundingClientRect().bottom - top,
        desk: px(desk, "paddingBottom"),
        block: px(desk.querySelector(".block"), "scrollMarginBottom"),
        drawer: px(document.querySelector(".left, .panel"), "paddingBottom"),
        needs: desk.getBoundingClientRect().bottom - top,
        rows: new Set(tops(".stage .dock .ib").map(Math.round)).size,
    };
}"""


@THEMES
@pytest.mark.parametrize("width", [360, 701])
def test_for_a_mouse_the_dock_lies_over_no_part_of_the_sheet_scrolled_to_its_end(
    editor, theme, width
):
    """A1, I2"""
    # A second page, so the desk has an end to scroll to and Blattform shows its page number.
    got = narrow(editor, width, theme=theme, more=[text("b")]).evaluate(ROOM)
    assert got["over"] <= 0 and got["desk"] >= got["needs"], got


def test_the_room_under_the_sheet_follows_the_dock_as_the_window_narrows(editor):
    """I1"""
    page = editor(text("a"), theme="", more=[text("b")])
    wide = page.evaluate(ROOM)
    assert wide["rows"] == 1 and wide["desk"] == 88, wide
    page.set_viewport_size({"width": 360, "height": 900})
    page.wait_for_function(f"({ROOM})().rows > 2")
    page.wait_for_function(f"({ROOM})().over <= 0")


def test_for_a_finger_the_desk_keeps_the_room_it_had_under_a_dock_of_one_row(editor):
    """I4"""
    got = narrow(editor, 360, touch=True, more=[text("b")]).evaluate(ROOM)
    assert got["rows"] == 1 and got["desk"] == 88 and got["over"] <= 0, got


def test_all_that_keeps_clear_of_the_dock_follows_its_height(editor):
    """I8"""
    # An upright window with a mouse: the panels are drawers, and the dock has two rows.
    page = narrow(editor, 701)
    page.get_by_role("button", name="Seiten und Vorlagen").click()
    got = page.evaluate(ROOM)
    assert got["rows"] == 2 and got["desk"] > 88, got
    assert got["desk"] == got["block"] == got["drawer"] >= got["needs"], got
    got = narrow(editor, 1400).evaluate(ROOM)
    assert got["rows"] == 1 and got["desk"] == got["block"] == 88, got


def test_of_blattforms_two_docks_the_higher_one_sets_the_room(editor):
    """I2, I8"""
    page = editor(text("a"), more=[text("b")])
    expect(page.locator(".stage .dock")).to_have_count(2)
    assert page.evaluate(ROOM)["desk"] == 88
    # The page number is the lower of the two, so it is made the higher here.
    page.locator(".stage .dock.at").evaluate("el => el.style.minHeight = '90px'")
    page.wait_for_function(f"({ROOM})().desk === 120")


def test_tab_brings_a_block_at_the_pages_end_into_view_clear_of_the_wrapped_dock(editor):
    """I8"""
    page = narrow(editor, 360, more=[text("b"), {**text("c", z=2), "y": 277}])
    # A block is picked first: the panel under the desk has opened, and the desk has its height.
    pick(page, "b")
    expect(at(page, "c")).not_to_be_in_viewport()
    page.keyboard.press("Tab")
    expect_picked(page, "c")
    expect(at(page, "c")).to_be_in_viewport(ratio=1)
    got = page.evaluate("""() => ({
        block: document.querySelector('.block[data-id="c"]').getBoundingClientRect().bottom,
        dock: document.querySelector(".stage .dock").getBoundingClientRect().top,
    })""")
    assert got["block"] <= got["dock"], got
