"""The iPad held upright, 834 by 1194: the sheet takes the window's width, the panels are drawers.

On its side, on a desktop and on a phone the editor lies as it did before (#262).
"""

import json
from contextlib import suppress

import pytest
from conftest import IPAD, TURNED
from playwright.sync_api import TimeoutError as Late
from playwright.sync_api import expect
from test_menu import HELD, props
from ui import (
    BROWSER,
    FIELD,
    RECT,
    TEXT,
    at,
    bar,
    box,
    centre,
    drawer,
    expect_picked,
    saved,
    swipe,
    user,
)

THEMES = pytest.mark.parametrize("theme", [None, ""], ids=["blattform", "plain"])
PARTS = ["header", ".left", ".stage", ".panel", ".sheet", ".dock"]
MEASURE = """(parts) => Object.fromEntries(parts.map((css) => {
    const box = document.querySelector("main.editor " + css)?.getBoundingClientRect();
    const tenths = (n) => Math.round(n * 10) / 10;
    return [css, box ? [box.x, box.y, box.width, box.height].map(tenths) : null];
}))"""
# Where the editor's parts lay before the drawers came, as x, y, width and height: on a desktop of
# 1400 by 1000, on a phone of 600 by 900 and, with fingers, on the iPad on its side. Blattform's
# green panel runs the window's height beside the bar.
DESKTOP = {
    None: {
        "header": [236, 0, 1164, 44],
        ".left": [0, 0, 236, 1000],
        ".stage": [236, 44, 900, 956],
        ".panel": [1136, 44, 264, 956],
        ".sheet": [268, 76, 821, 1161.1],
        ".dock": [252, 938, 172, 46],
    },
    "": {
        "header": [0, 0, 1400, 44],
        ".left": [0, 44, 236, 956],
        ".stage": [236, 44, 900, 956],
        ".panel": [1136, 44, 264, 956],
        ".sheet": [268, 76, 821, 1161.1],
        ".dock": [295, 938, 782, 46],
    },
}
PHONE = {
    "header": [0, 0, 600, 67],
    ".left": None,
    ".stage": [0, 67, 600, 741.9],
    ".panel": [0, 808.9, 600, 91.1],
    ".sheet": [32, 99, 521, 736.8],
    ".dock": [12, 746.9, 576, 46],
}
ON_ITS_SIDE = {
    None: {
        "header": [236, 0, 958, 91],
        ".left": [0, 0, 236, 834],
        ".stage": [236, 91, 694, 743],
        ".panel": [930, 91, 264, 743],
        ".sheet": [268, 123, 615, 869.8],
        ".dock": [252, 760, 208, 58],
    },
    "": {
        "header": [0, 0, 1194, 91],
        ".left": [0, 91, 236, 743],
        ".stage": [236, 91, 694, 743],
        ".panel": [930, 91, 264, 743],
        ".sheet": [268, 123, 615, 869.8],
        ".dock": [248, 760, 670, 58],
    },
}


def places(page):
    return page.evaluate(MEASURE, PARTS)


def expect_places(page, want, sheet):
    """Waits until the editor's parts lie in these boxes: the sheet takes its width a frame late.

    `sheet` is the sheet's box in WebKit, which keeps no room free for the desk's scrollbar: the
    sheet is 15 px wider there.
    """
    if BROWSER == "webkit":
        want = {**want, ".sheet": sheet}
    same = f"(want) => JSON.stringify(({MEASURE})(Object.keys(want))) === JSON.stringify(want)"
    # A window that never gets there fails below, where the boxes that differ are shown.
    with suppress(Late):
        page.wait_for_function(same, arg=want, timeout=2000)
    assert json.dumps(places(page)) == json.dumps(want)


def sheet(page):
    return page.locator(".sheet").first


def expect_wide(page):
    """Waits until the sheet has the window's width, less the desk's edges."""
    expect(page.locator("aside.left, aside.panel")).to_have_count(0)
    page.wait_for_function("document.querySelector('.sheet').getBoundingClientRect().width >= 700")


def inside(page, locator):
    """Whether what the locator finds lies in the window, all of it."""
    place, window = locator.bounding_box(), page.viewport_size
    right, bottom = place["x"] + place["width"], place["y"] + place["height"]
    return (
        place["x"] >= 0
        and place["y"] >= 0
        and right <= window["width"]
        and bottom <= window["height"]
    )


def text(name, z, **more):
    return box(name, "text", TEXT, z=z, **more)


@THEMES
def test_upright_both_panels_start_shut_and_the_sheet_is_wide(editor, theme):
    """A1"""
    page = editor(text("a", 1), theme=theme, touch=True)
    expect_wide(page)
    for side in ("left", "right"):
        expect(bar(page, side)).to_have_attribute("aria-pressed", "false")
    # Blattform's own layout is for a wide window: its tools stand in the bar at the lower edge.
    expect(page.locator(".dock[role=toolbar]")).to_be_visible()
    expect(page.locator(".insert, .modes")).to_have_count(0)


@pytest.mark.parametrize("side", ["left", "right"])
def test_a_drawer_opens_and_shuts_by_its_button_and_lies_over_the_sheet(editor, side):
    """A2"""
    page = editor(text("a", 1), theme="", touch=True)
    expect_wide(page)
    panel = page.locator("aside.left" if side == "left" else "aside.panel")
    before = sheet(page).bounding_box()
    drawer(page, side)
    expect(panel).to_be_visible()
    assert sheet(page).bounding_box() == before
    # Under the bar, down to the window's lower edge, at the window's own edge and over the sheet.
    head, place, window = page.locator("header").bounding_box(), panel.bounding_box(), IPAD
    assert place["y"] == head["y"] + head["height"]
    assert place["y"] + place["height"] == window["height"]
    if side == "left":
        assert place["x"] == 0
        x = place["width"] - 5
        assert x > before["x"]
    else:
        assert place["x"] + place["width"] == window["width"]
        x = place["x"] + 5
        assert x < before["x"] + before["width"]
    y = before["y"] + 5
    assert page.evaluate("([x, y]) => !!document.elementFromPoint(x, y).closest('aside')", [x, y])
    bar(page, side).tap()
    expect(panel).to_have_count(0)
    expect(bar(page, side)).to_have_attribute("aria-pressed", "false")
    assert sheet(page).bounding_box() == before


@THEMES
def test_upright_the_bar_is_one_row_and_keeps_both_drawer_buttons_in_view(editor, theme):
    """A3"""
    page = editor(text("a", 1), theme=theme, touch=True)
    expect_wide(page)
    top = page.locator("header .top")
    # Two rows of buttons would be twice a button's height.
    assert top.bounding_box()["height"] < 2 * bar(page, "left").bounding_box()["height"]
    # The rest of the bar scrolls sideways under the two buttons, which stay where they are.
    assert top.evaluate("el => el.scrollWidth > el.clientWidth")
    for end in (0, 99999):
        top.evaluate("(el, x) => el.scrollTo(x, 0)", end)
        for side in ("left", "right"):
            assert inside(page, bar(page, side))
            hit = "([x, y]) => document.elementFromPoint(x, y).closest('button').ariaLabel"
            label = bar(page, side).get_attribute("aria-label")
            assert page.evaluate(hit, centre(bar(page, side))) == label
    expect(page.get_by_role("button", name="PDF", exact=True)).to_be_in_viewport()


@THEMES
def test_on_its_side_the_ipad_keeps_three_columns(editor, theme):
    """A4"""
    page = editor(text("a", 1), theme=theme, touch="landscape")
    expect(page.locator("aside.left")).to_be_visible()
    expect(page.locator("aside.panel")).to_be_visible()
    expect_places(page, ON_ITS_SIDE[theme], [268, 123, 630, 891])


@THEMES
def test_a_desktop_window_lies_as_before(editor, theme):
    """A5"""
    page = editor(text("a", 1), theme=theme)
    expect_places(page, DESKTOP[theme], [268, 76, 836, 1182.3])


def middle(page, kind, name):
    """The middle of the block or of its group. A table's is a column's bar: a cell's instead."""
    if kind == "table":
        return centre(at(page, name).locator("[data-cell]").first)
    if kind != "group":
        return centre(at(page, name))
    (x, y), (far, _) = (centre(at(page, name + half)) for half in "12")
    return (x + far) / 2, y


# With a group selected, Chromium gives the tap on the next group's middle to the handle that turns
# the selected one. The handle's area for a finger ends 7 px short of that point, 63 of the 72 px
# from the group's edge, and `elementFromPoint` finds the block there. WebKit gives the tap to it.
GROUP = pytest.param(
    "group",
    marks=pytest.mark.xfail(
        BROWSER != "webkit", strict=True, reason="#260: the tap lands on the turn handle"
    ),
)


@pytest.mark.parametrize("kind", [*(kind for kind in HELD if kind != "group"), GROUP])
def test_a_tap_on_the_middle_of_the_block_next_to_the_selected_one_selects_it(editor, kind):
    """A6, #260"""
    client = user()
    if kind == "group":
        # Two groups, each of two shapes side by side that fill a box of 180 by 20 mm.
        blocks = [
            box(name + half, "shape", RECT, z=z, x=x, w=90, group=[name])
            for z, name in ((1, "a"), (2, "b"))
            for half, x in (("1", 15), ("2", 105))
        ]
    else:
        made = props(client, kind)
        blocks = [
            box(name, "shape" if kind == "line" else kind, made, z=z)
            for z, name in ((1, "a"), (2, "b"))
        ]
    page = editor(*blocks, client=client, touch=True)
    expect_wide(page)
    for name in "aba":
        page.touchscreen.tap(*middle(page, kind, name))
        expect_picked(page, *((name + "1", name + "2") if kind == "group" else name))


@THEMES
def test_a_turn_upright_shuts_the_panels_and_a_turn_back_shows_them_as_before(editor, theme):
    """I1"""
    page = editor(text("a", 1), theme=theme, touch="landscape")
    # Blattform's left panel holds the insert tools and has no button of its own.
    shut, other = ("aside.left", "aside.panel") if theme == "" else ("aside.panel", "aside.left")
    bar(page, "left" if theme == "" else "right").tap()
    expect(page.locator(shut)).to_have_count(0)
    at(page, "a").tap()
    expect_picked(page, "a")
    page.set_viewport_size(IPAD)
    expect_wide(page)
    expect_picked(page, "a")
    expect(page.locator(".dock[role=toolbar]")).to_be_visible()
    page.set_viewport_size(TURNED)
    expect(page.locator(other)).to_be_visible()
    expect(page.locator(shut)).to_have_count(0)
    expect(page.locator(".insert")).to_have_count(0 if theme == "" else 1)
    expect_picked(page, "a")
    # A drawer left open upright is shut again after the next turn upright.
    page.set_viewport_size(IPAD)
    drawer(page, "right")
    page.set_viewport_size(TURNED)
    expect(page.locator(shut)).to_have_count(0)
    page.set_viewport_size(IPAD)
    expect_wide(page)


def test_a_number_typed_in_the_format_drawer_lands_when_its_button_shuts_the_drawer(editor):
    """Review: the bar's button took no focus from the field, which went with the drawer."""
    client = user()
    page = editor(text("a", 1), client=client, touch=True)
    at(page, "a").tap()
    drawer(page, "right")
    field = page.locator(".panel").get_by_label("X", exact=True)
    field.tap()
    field.fill("25")
    bar(page, "right").tap()
    expect(page.locator("aside.panel")).to_have_count(0)
    assert saved(page, client)[0]["x"] == 25


def test_opening_one_drawer_shuts_the_other(editor):
    """I2"""
    page = editor(text("a", 1), touch=True)
    for side, other in (("left", "right"), ("right", "left"), ("left", "right")):
        drawer(page, side)
        expect(page.locator("aside")).to_have_count(1)
        expect(page.locator("aside.left" if side == "left" else "aside.panel")).to_be_visible()
        expect(bar(page, other)).to_have_attribute("aria-pressed", "false")


def test_a_change_in_the_format_drawer_is_one_step_of_undo(editor):
    """I3"""
    client = user()
    page = editor(text("a", 1), client=client, touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    drawer(page, "right")
    bold = page.locator(".panel").get_by_label("Fett", exact=True)
    undo, redo = (page.get_by_label(label, exact=True) for label in ("Rückgängig", "Wiederholen"))
    expect(undo).to_be_disabled()
    bold.tap()
    expect(bold).to_have_attribute("aria-pressed", "true")
    assert saved(page, client)[0]["props"]["bold"] is True
    undo.tap()
    expect(bold).to_have_attribute("aria-pressed", "false")
    expect(undo).to_be_disabled()
    redo.tap()
    expect(bold).to_have_attribute("aria-pressed", "true")
    expect(redo).to_be_disabled()
    assert saved(page, client)[0]["props"]["bold"] is True


def test_the_format_drawer_opens_and_sets_a_look_while_a_text_stays_open(editor):
    """I4"""
    page = editor(text("a", 1), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    # A second tap on the selected text opens it. A finger that lifts as it would in the same
    # instant as it came down leaves Moveable waiting for a second finger, and the next tap anywhere
    # is then that one: it would close the text and press nothing.
    swipe(page, centre(at(page, "a")))
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    drawer(page, "right")
    expect(page.locator(FIELD)).to_be_focused()
    bold = page.locator(".panel").get_by_label("Fett", exact=True)
    bold.tap()
    expect(bold).to_have_attribute("aria-pressed", "true")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("y")
    expect(page.locator(FIELD)).to_contain_text("xy")


def test_a_tap_on_a_block_beside_the_open_format_drawer_selects_it(editor):
    """I5"""
    page = editor(text("a", 1), box("b", "shape", RECT, z=2), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    drawer(page, "right")
    what = page.locator(".panel .what")
    expect(what).to_contain_text("Text")
    # The drawer lies over the block's right end: the finger comes down left of it.
    place, edge = at(page, "b").bounding_box(), page.locator("aside.panel").bounding_box()["x"]
    assert place["x"] + 40 < edge < place["x"] + place["width"]
    page.touchscreen.tap(place["x"] + 40, place["y"] + place["height"] / 2)
    expect_picked(page, "b")
    expect(what).to_contain_text("Form")
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")


@THEMES
def test_upright_a_tap_in_the_dock_inserts_a_block(editor, theme):
    """I6"""
    page = editor(text("a", 1), theme=theme, touch=True)
    expect_wide(page)
    dock = page.locator(".dock")
    assert inside(page, dock)
    dock.get_by_label("Text", exact=True).tap()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    # So does a tool at the bar's far end, which scrolls to it.
    last = dock.get_by_label("Doppelpfeil", exact=True)
    expect(last).not_to_be_in_viewport()
    last.tap()
    expect(page.locator(".block[data-id]")).to_have_count(3)
    assert inside(page, dock)


def test_upright_the_tour_opens_the_drawer_its_step_is_about(editor):
    """I7"""
    page = editor(text("a", 1), touch=True)
    # After the fixture's own script, which says the tour was seen.
    page.context.add_init_script("localStorage.removeItem('tour')")
    page.reload()
    tour, ring = page.locator(".tour"), page.locator(".tour-ring")
    step = tour.locator("h2")
    expect(step).to_have_text("Willkommen bei Blattomat")
    expect(page.locator("aside")).to_have_count(0)

    def on(title):
        """Steps on until the tour is at this step."""
        for _ in range(15):
            if step.inner_text() == title:
                return
            before = tour.locator("small").inner_text()
            tour.locator(".primary").tap()
            expect(tour.locator("small")).not_to_have_text(before)
        raise AssertionError(f"no step {title}")

    def expect_ringed(panel):
        """Waits until the ring lies round the panel, which lies in the window."""
        expect(panel).to_be_visible()
        assert inside(page, panel)
        place = panel.bounding_box()
        page.wait_for_function(
            """([x, y]) => {
                const ring = document.querySelector(".tour-ring").getBoundingClientRect();
                return ring.width > 0 && Math.abs(ring.x - x) <= 4 && Math.abs(ring.y - y) <= 4;
            }""",
            arg=[place["x"], place["y"]],
        )
        assert inside(page, ring)

    on("Format")
    expect_ringed(page.locator("aside.panel"))
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")
    # The next step's tool stands in the dock, which lies over the open drawer.
    on("Rechenaufgaben")
    page.locator(".dock").get_by_label("Rechnen", exact=True).tap()
    expect(step).to_have_text("Aufgaben einstellen")
    expect(page.locator(".panel .what")).to_contain_text("Rechnen")
    on("Seiten und Vorlagen")
    expect_ringed(page.locator("aside.left"))
    expect(page.locator("aside.panel")).to_have_count(0)


@THEMES
def test_a_phone_lies_as_before(editor, theme):
    """I8"""
    page = editor(text("a", 1), theme=theme)
    # The panels a window starts with go by its width as the editor opens.
    page.set_viewport_size({"width": 600, "height": 900})
    page.reload()
    expect_places(page, PHONE, [32, 99, 536, 758])
