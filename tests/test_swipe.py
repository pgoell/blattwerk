"""The iPad held upright: a swipe in from the left edge opens the page list, and back shuts it.

On its side nothing opens by a swipe, and a mouse drag from the edge opens nothing either.
"""

import pytest
from playwright.sync_api import expect
from ui import (
    RECT,
    TEXT,
    at,
    bar,
    box,
    centre,
    drag,
    drawer,
    expect_lit,
    expect_picked,
    finger,
    saved,
    swipe,
    tool,
    user,
)

SIDES = pytest.mark.parametrize("side", ["left", "right"])
# How wide the rail of tools is at the window's left.
RAIL = 76


def text(name, z):
    return box(name, "text", TEXT, z=z)


def shut(page):
    """Both drawers are shut, as the bar's buttons say."""
    expect_lit(bar(page, "left"), "false")
    expect_lit(bar(page, "right"), "false")


def to_edge(page, name, left):
    """Scrolls the desk until the block's left edge lies `left` px from the window's edge."""
    place = at(page, name).bounding_box()
    scroll = "(dx) => { document.querySelector('.desk').scrollLeft += dx; }"
    page.evaluate(scroll, place["x"] - left)


@SIDES
def test_f_a_swipe_from_the_left_edge_opens_the_pages_and_one_from_the_right_nothing(editor, side):
    """F: a swipe in from the left edge opens the page list. The Format panel comes from below
    (#1187): a swipe in from the right edge opens nothing."""
    page = editor(text("a", 1), touch=True)
    shut(page)
    if side == "left":
        swipe(page, (3, 600), (30, 600), (60, 600), (100, 600), (160, 600))
        expect_lit(bar(page, "left"), "true")
        expect(page.locator("aside.left")).to_be_visible()
    else:
        swipe(page, (831, 600), (800, 600), (760, 600), (720, 600), (680, 600))
        shut(page)
        expect(page.locator("aside.panel")).to_have_count(0)


def test_g_a_swipe_back_to_its_edge_shuts_the_open_pages(editor):
    """G: the open page list shuts when a finger swipes it back towards its edge. The Format panel
    shuts by a swipe down: tests/test_tablet.py."""
    page = editor(text("a", 1), touch=True)
    drawer(page, "left")
    swipe(page, (200, 600), (160, 600), (120, 600), (80, 600), (40, 600))
    expect_lit(bar(page, "left"), "false")


def test_4_a_sideways_swipe_on_the_open_panel_leaves_it_open(editor):
    """Implied 4: a swipe across the Format panel, as over a row of its buttons, leaves it open."""
    page = editor(box("a", "shape", RECT, z=1, x=20, y=20, w=50), touch=True)
    shut(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    expect_lit(bar(page, "right"), "true")
    y = page.locator("aside.panel").bounding_box()["y"] + 200
    swipe(page, (640, y), (680, y), (720, y), (760, y), (800, y))
    expect_lit(bar(page, "right"), "true")


def test_h_a_swipe_from_the_edge_over_a_block_moves_nothing_and_opens_nothing(editor):
    """H: a zoomed sheet reaches under the rail. A swipe from the desk's left edge over a block
    opens no drawer and moves no block."""
    page = editor(text("a", 1), touch=True)
    for _ in range(3):
        tool(page, "Größer").tap()
    to_edge(page, "a", RAIL - 20)
    assert page.locator(".sheet").first.bounding_box()["x"] < RAIL
    y = centre(at(page, "a"))[1]
    before = at(page, "a").evaluate("el => [el.style.left, el.style.top]")
    swipe(page, (RAIL + 3, y), (RAIL + 30, y), (RAIL + 60, y), (RAIL + 100, y))
    shut(page)
    assert at(page, "a").evaluate("el => [el.style.left, el.style.top]") == before


def test_i_a_finger_drag_of_a_picked_block_at_the_edge_moves_it_and_opens_nothing(editor):
    """I: a picked block at the desk's left edge, dragged by a finger rightwards: it moves, no drawer."""
    page = editor(text("a", 1), touch=True)
    for _ in range(3):
        tool(page, "Größer").tap()
    # The block's left edge lies under the rail: the finger comes down at the desk's edge.
    to_edge(page, "a", RAIL - 10)
    at(page, "a").tap()
    expect_picked(page, "a")
    y = centre(at(page, "a"))[1]
    before = at(page, "a").bounding_box()["x"]
    swipe(page, (RAIL + 12, y), (RAIL + 52, y), (RAIL + 92, y), (RAIL + 132, y), (RAIL + 172, y))
    assert at(page, "a").bounding_box()["x"] > before + 20
    # The pick brought the Format panel up, and the drag opened no pages.
    expect_lit(bar(page, "left"), "false")


def test_j_a_brush_drag_from_the_edge_paints_and_opens_nothing(editor):
    """J: the brush paints a text at the desk's left edge by a mouse drag across it, no pages open."""
    client = user()
    # "a" is bold and "b" is not; "b" lies at the desk's left edge, "a" lies far to the right.
    a = {**box("a", "text", {**TEXT, "bold": True}, z=2), "y": 120}
    page = editor(a, text("b", 1), touch=True, client=client)
    for _ in range(3):
        tool(page, "Größer").tap()
    to_edge(page, "b", RAIL + 6)
    at(page, "a").click()
    expect_picked(page, "a")
    tool(page, "Format übertragen").click()
    # The pick brought the panel up and the desk scrolled to "a": back to "b".
    page.locator(".desk").evaluate("el => (el.scrollTop = 0)")
    y = centre(at(page, "b"))[1]
    drag(page, (RAIL + 12, y), (RAIL + 60, y), (RAIL + 120, y))
    expect_lit(bar(page, "left"), "false")
    looks = {b["id"]: b["props"].get("bold", False) for b in saved(page, client)}
    assert looks["b"] is True


def test_k_a_mouse_drag_from_the_edge_opens_no_drawer(editor):
    """K: a mouse drag from the window's left edge opens no drawer: only fingers swipe."""
    page = editor(text("a", 1), touch=True)
    drag(page, (3, 600), (60, 600), (160, 600))
    shut(page)


def test_5_the_pages_opened_by_a_swipe_stay_open_when_a_pick_brings_the_panel_up(editor):
    """5: the Format panel is none of the drawers (#1187): the pages stay open beside it."""
    page = editor(box("a", "text", TEXT, z=1, x=120, y=20, w=60), touch=True)
    swipe(page, (3, 600), (30, 600), (60, 600), (100, 600), (160, 600))
    expect_lit(bar(page, "left"), "true")
    at(page, "a").tap()
    expect_picked(page, "a")
    expect_lit(bar(page, "right"), "true")
    expect_lit(bar(page, "left"), "true")


def test_6_a_vertical_swipe_on_the_open_drawer_leaves_it_open(editor):
    """6: a vertical swipe on the open page list, a scroll, leaves the drawer open."""
    page = editor(text("a", 1), touch=True)
    drawer(page, "left")
    swipe(page, (120, 500), (120, 600), (120, 700), (120, 800))
    expect_lit(bar(page, "left"), "true")


def test_8_on_its_side_an_edge_swipe_changes_nothing(editor):
    """8: the iPad on its side has no drawers: an edge swipe opens none."""
    page = editor(text("a", 1), touch="landscape")
    panels = "aside.left, aside.panel"
    before = page.locator(panels).evaluate_all("els => els.map((el) => el.className)")
    swipe(page, (3, 400), (30, 400), (60, 400), (100, 400), (160, 400))
    swipe(page, (1191, 400), (1160, 400), (1120, 400), (1080, 400), (1040, 400))
    assert page.locator(panels).evaluate_all("els => els.map((el) => el.className)") == before


def test_a_held_thumbnail_dragged_sideways_keeps_the_drawer_open(editor):
    """A thumbnail held for the long press, then dragged sideways, keeps the Seiten drawer open."""
    page = editor(text("a", 1), pages=[{"blocks": [text("b", 1)]}], touch=True)
    drawer(page, "left")
    # The strip's thumbnails are not buttons here, so they are found by their number.
    second = page.locator('.pages [data-thumb="1"]')
    x, y = centre(second)
    with finger(page, (x, y)) as touch:
        # The long press needs real time: the strip's own timer starts the drag after 500 ms.
        page.wait_for_timeout(800)
        touch("touchMove", (x - 30, y))
        touch("touchMove", (x - 60, y))
        touch("touchMove", (x - 90, y))
    expect_lit(bar(page, "left"), "true")
