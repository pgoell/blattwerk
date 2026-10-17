"""The iPad held upright: a swipe in from an edge opens that side's drawer, and back shuts it.

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
    expect_picked,
    saved,
    swipe,
    tool,
    user,
)

SIDES = pytest.mark.parametrize("side", ["left", "right"])


def text(name, z):
    return box(name, "text", TEXT, z=z)


def shut(page):
    """Both drawers are shut, as the bar's buttons say."""
    expect(bar(page, "left")).to_have_attribute("aria-pressed", "false")
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "false")


def to_edge(page, name, left):
    """Scrolls the desk until the block's left edge lies `left` px from the window's edge."""
    place = at(page, name).bounding_box()
    scroll = "(dx) => { document.querySelector('.desk').scrollLeft += dx; }"
    page.evaluate(scroll, place["x"] - left)


@SIDES
def test_f_an_edge_swipe_opens_the_drawer_on_its_side(editor, side):
    """F: a swipe in from the left edge opens the page list, one from the right the format panel."""
    page = editor(text("a", 1), touch=True)
    shut(page)
    if side == "left":
        swipe(page, (3, 600), (30, 600), (60, 600), (100, 600), (160, 600))
    else:
        swipe(page, (831, 600), (800, 600), (760, 600), (720, 600), (680, 600))
    expect(bar(page, side)).to_have_attribute("aria-pressed", "true")
    expect(page.locator(f"aside.{'left' if side == 'left' else 'panel'}")).to_be_visible()


@SIDES
def test_g_a_swipe_back_to_its_edge_shuts_the_open_drawer(editor, side):
    """G: an open drawer shuts when a finger swipes it back towards its edge."""
    page = editor(text("a", 1), touch=True)
    drawer(page, side)
    if side == "left":
        swipe(page, (200, 600), (160, 600), (120, 600), (80, 600), (40, 600))
    else:
        swipe(page, (640, 600), (680, 600), (720, 600), (760, 600), (800, 600))
    expect(bar(page, side)).to_have_attribute("aria-pressed", "false")


def test_4_a_swipe_opens_the_format_drawer_beside_the_picked_block(editor):
    """Implied 4: a swipe opens the Format drawer beside the picked block, as its button does."""
    page = editor(box("a", "shape", RECT, z=1, x=150, w=50), touch=True)
    shut(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    y = at(page, "a").bounding_box()["y"] + 400
    swipe(page, (831, y), (800, y), (760, y), (720, y), (680, y))
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")
    page.wait_for_function("document.querySelector('.desk').scrollLeft > 0")
    place = at(page, "a").bounding_box()
    assert place["x"] + place["width"] <= page.locator("aside.panel").bounding_box()["x"]


def test_h_a_swipe_from_the_edge_over_a_block_moves_nothing_and_opens_nothing(editor):
    """H: a zoomed sheet covers the left edge. A swipe from the edge over a block opens no drawer
    and moves no block."""
    page = editor(text("a", 1), touch=True)
    for _ in range(3):
        tool(page, "Größer").tap()
    to_edge(page, "a", -20)
    assert page.locator(".sheet").first.bounding_box()["x"] < 0
    y = centre(at(page, "a"))[1]
    before = at(page, "a").evaluate("el => [el.style.left, el.style.top]")
    swipe(page, (3, y), (30, y), (60, y), (100, y))
    shut(page)
    assert at(page, "a").evaluate("el => [el.style.left, el.style.top]") == before


def test_i_a_finger_drag_of_a_picked_block_at_the_edge_moves_it_and_opens_nothing(editor):
    """I: a picked block at the left edge, dragged by a finger rightwards: it moves, no drawer."""
    page = editor(text("a", 1), touch=True)
    for _ in range(3):
        tool(page, "Größer").tap()
    # The block's left edge lies left of the window's: the finger comes down in the edge zone.
    to_edge(page, "a", -10)
    at(page, "a").tap()
    expect_picked(page, "a")
    y = centre(at(page, "a"))[1]
    before = at(page, "a").bounding_box()["x"]
    swipe(page, (12, y), (52, y), (92, y), (132, y), (172, y))
    assert at(page, "a").bounding_box()["x"] > before + 20
    shut(page)


def test_j_a_brush_drag_from_the_edge_paints_and_opens_nothing(editor):
    """J: the brush paints a text at the left edge by a mouse drag across it, no drawer opens."""
    client = user()
    # "a" is bold and "b" is not; "b" lies at the window's left edge, "a" lies far to the right.
    a = {**box("a", "text", {**TEXT, "bold": True}, z=2), "y": 120}
    page = editor(a, text("b", 1), touch=True, client=client)
    for _ in range(3):
        tool(page, "Größer").tap()
    to_edge(page, "b", 6)
    at(page, "a").click()
    expect_picked(page, "a")
    tool(page, "Format übertragen").click()
    y = centre(at(page, "b"))[1]
    drag(page, (12, y), (60, y), (120, y))
    expect(bar(page, "left")).to_have_attribute("aria-pressed", "false")
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "false")
    looks = {b["id"]: b["props"].get("bold", False) for b in saved(page, client)}
    assert looks["b"] is True


def test_k_a_mouse_drag_from_the_edge_opens_no_drawer(editor):
    """K: a mouse drag from the window's left edge opens no drawer: only fingers swipe."""
    page = editor(text("a", 1), touch=True)
    drag(page, (3, 600), (60, 600), (160, 600))
    shut(page)


def test_5_a_drawer_opened_by_swipe_shuts_when_the_other_opens(editor):
    """5: one drawer opened by a swipe shuts when a swipe opens the other."""
    page = editor(text("a", 1), touch=True)
    swipe(page, (3, 600), (30, 600), (60, 600), (100, 600), (160, 600))
    expect(bar(page, "left")).to_have_attribute("aria-pressed", "true")
    swipe(page, (831, 600), (800, 600), (760, 600), (720, 600), (680, 600))
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")
    expect(bar(page, "left")).to_have_attribute("aria-pressed", "false")


def test_6_a_vertical_swipe_on_the_open_drawer_leaves_it_open(editor):
    """6: a vertical swipe on the open page list, a scroll, leaves the drawer open."""
    page = editor(text("a", 1), touch=True)
    drawer(page, "left")
    swipe(page, (120, 500), (120, 600), (120, 700), (120, 800))
    expect(bar(page, "left")).to_have_attribute("aria-pressed", "true")


def test_8_on_its_side_an_edge_swipe_changes_nothing(editor):
    """8: the iPad on its side has no drawers: an edge swipe opens none."""
    page = editor(text("a", 1), touch="landscape")
    panels = "aside.left, aside.panel"
    before = page.locator(panels).evaluate_all("els => els.map((el) => el.className)")
    swipe(page, (3, 400), (30, 400), (60, 400), (100, 400), (160, 400))
    swipe(page, (1191, 400), (1160, 400), (1120, 400), (1080, 400), (1040, 400))
    assert page.locator(panels).evaluate_all("els => els.map((el) => el.className)") == before
