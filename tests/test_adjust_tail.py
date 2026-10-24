"""A bubble tail dragged outside its box is drawn, picked, printed and undone."""

import math
import re

import pytest
from playwright.sync_api import expect
from test_adjust import (
    BUBBLE,
    OUTLINE,
    handle,
    mm,
    same_path,
)
from test_foot_cut import (
    LINES,
    LONG,
    assert_whole_lines,
)
from ui import (
    at,
    box,
    centre,
    drag,
    expect_picked,
    pick,
    saved,
    sheet,
    unpick,
    user,
)

from blattwerk import pdf


def test_the_tail_goes_out_past_each_edge(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    # Each drag starts on the handle the last one left, and ends 15 mm past the box.
    # The four ends: below, left, right, above.
    box_ = at(page, "a").bounding_box()
    ends = [(12, 55), (-15, 12), (75, 12), (12, -15)]
    checks = [
        lambda tx, ty: ty > 1,
        lambda tx, ty: tx < 0,
        lambda tx, ty: tx > 1,
        lambda tx, ty: ty < 0,
    ]
    for (x, y), check in zip(ends, checks, strict=True):
        start = centre(handle(page, "a"))
        end = (box_["x"] + x * k, box_["y"] + y * k)
        drag(page, start, end)
        # The editor saves 1.1 s after a change; until then "Gespeichert" still shows.
        page.wait_for_timeout(1500)
        (a,) = saved(page, client)
        assert math.dist(centre(handle(page, "a")), end) < 3
        assert check(*a["props"]["tail"]), a["props"]


def test_a_click_on_the_tail_outside_picks_the_bubble(editor):
    tail = {**BUBBLE, "tail": [0.2, 1.5], "fill": "#ffffff"}
    page = editor(box("a", "shape", tail, x=60, y=60, w=60, h=40))
    k = mm(page)
    b = at(page, "a").bounding_box()
    # 4 mm up from the tip at 1.5 of the height and 1 mm right: in the narrow tail, below the box.
    page.mouse.click(b["x"] + (0.2 * 60 + 1) * k, b["y"] + (1.5 * 40 - 4) * k)
    expect_picked(page, "a")


def test_the_selection_frame_takes_the_tail_in(editor):
    page = editor(box("a", "shape", {**BUBBLE, "tail": [0.2, 1.5]}, x=60, y=60, w=60, h=40))
    k = mm(page)
    pick(page, "a")
    b = at(page, "a").bounding_box()
    tip = b["y"] + 1.5 * 40 * k
    # A frame round the box and the tail reaches the tip.
    reach = page.locator('.sheet .reach[data-id="a"]').bounding_box()
    assert reach["y"] + reach["height"] >= tip - 2, reach
    assert abs(reach["y"] - b["y"]) < 2, reach
    # The resize handle at the lower right stays on the box's corner, not on the tail's reach.
    se = page.locator(".moveable-direction.moveable-se")
    corner = (b["x"] + b["width"], b["y"] + b["height"])
    # Moveable sets it a few px out of the corner; a frame grown by the tail would set it 20 mm off.
    assert math.dist(centre(se), corner) < 15, se.bounding_box()


def test_the_pdf_prints_a_tail_outside_the_box(browser, server):
    client = user()
    shape = {**BUBBLE, "tail": [0.2, 1.5]}
    tail = sheet(client, [box("a", "shape", shape, x=60, y=60, w=60, h=40)])["id"]

    # The printed tip lies below the box's foot, 40 mm high.
    page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(tail)})
    page.goto(f"{server}/druck/{tail}")
    page.wait_for_selector("body.ready", state="attached")
    d = page.locator(OUTLINE).get_attribute("d")
    page.close()
    tip = re.search(r"L([-\d.e]+),([-\d.e]+)", d)
    assert tip is not None
    assert float(tip.group(2)) > 40


def test_a_tail_inside_the_box_draws_as_before(editor):
    client = user()
    shape = {**BUBBLE, "tail": [0.6, 0.9]}
    page = editor(box("a", "shape", shape, x=60, y=60, w=60, h=40), client=client)
    # The old formula at 0.6 and 0.9: the tip at (36, 36), the base 29 mm along the foot, 9 mm wide.
    e, w, h, r = 0.25, 60, 40, 4
    low, right = e + 0.75 * (h - 2 * e), w - e
    base = 29
    bubble = (
        f"M{e + r},{e} H{right - r} A{r},{r} 0 0 1 {right},{e + r} V{low - r} "
        f"A{r},{r} 0 0 1 {right - r},{low} H{base + 0.15 * w} L36,36 L{base},{low} "
        f"H{e + r} A{r},{r} 0 0 1 {e},{low - r} V{e + r} A{r},{r} 0 0 1 {e + r},{e} Z"
    )
    same_path(at(page, "a").locator(OUTLINE).get_attribute("d"), bubble)


@pytest.mark.parametrize(
    ("tail", "base", "tip"),
    [
        # On the box's corner: the tip keeps inside the stroke, (e, h - e), as it did.
        ([0, 1], 4.25, (0.25, 39.75)),
        # In the body: the tip goes down to the body's foot, as the old range kept it.
        ([0.5, 0.5], 25.5, (30, 30)),
    ],
)
def test_a_tail_on_the_box_edge_or_in_the_body_draws_as_before(editor, tail, base, tip):
    page = editor(box("a", "shape", {**BUBBLE, "tail": tail}, x=60, y=60, w=60, h=40))
    e, w, h, r = 0.25, 60, 40, 4
    low, right = e + 0.75 * (h - 2 * e), w - e
    bubble = (
        f"M{e + r},{e} H{right - r} A{r},{r} 0 0 1 {right},{e + r} V{low - r} "
        f"A{r},{r} 0 0 1 {right - r},{low} H{base + 0.15 * w} L{tip[0]},{tip[1]} L{base},{low} "
        f"H{e + r} A{r},{r} 0 0 1 {e},{low - r} V{e + r} A{r},{r} 0 0 1 {e + r},{e} Z"
    )
    same_path(at(page, "a").locator(OUTLINE).get_attribute("d"), bubble)


def test_a_bubble_cut_at_the_page_foot_keeps_its_cut_with_a_tail_out(editor):
    shape = {**BUBBLE, "text": LONG, "size": 14, "tail": [0.3, 1.5]}
    page = editor(box("a", "shape", shape, x=15, y=280, w=180, h=17))
    unpick(page)
    frame = at(page, "a").locator(".frame")
    expect(frame).to_have_attribute("data-cut", "true")
    # The foot of the clip is the cut, not grown by the tail: no line below it shows in part.
    assert_whole_lines(frame.evaluate(LINES))


def test_a_drag_out_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    drag(page, start, *[(start[0], start[1] + 3 * k * i) for i in range(1, 6)])
    (a,) = saved(page, client)
    tail = a["props"]["tail"]
    assert tail[1] > 1
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert a["props"].get("tail") is None
    page.keyboard.press("Control+y")
    (a,) = saved(page, client)
    assert a["props"]["tail"] == pytest.approx(tail, abs=0.001)


def test_the_tail_handle_follows_turned_and_flipped(editor):
    client = user()
    page = editor(
        box("a", "shape", BUBBLE, x=20, y=60, w=60, h=40, angle=90),
        box("b", "shape", BUBBLE, x=120, y=60, w=60, h=40, flipX=True),
        client=client,
    )
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    # Turned a quarter clockwise, the bubble's foot faces left: out past it is to the left.
    end = (start[0] - 30 * k, start[1])
    drag(page, start, end)
    assert math.dist(centre(handle(page, "a")), end) < 3
    pick(page, "b")
    start = centre(handle(page, "b"))
    end = (start[0] - 30 * k, start[1] + 10 * k)
    drag(page, start, end)
    assert math.dist(centre(handle(page, "b")), end) < 3


def test_a_wild_tail_is_kept_in_range(editor):
    page = editor(box("a", "shape", {**BUBBLE, "tail": [50, -50]}, x=60, y=60, w=60, h=40))
    d = at(page, "a").locator(OUTLINE).get_attribute("d")
    tip = re.search(r"L([-\d.e]+),([-\d.e]+)", d)
    assert tip is not None
    # One box beyond each edge: across from -60 to 120 mm, down from -40 to 80 mm.
    assert -60 <= float(tip.group(1)) <= 120
    assert -40 <= float(tip.group(2)) <= 80


def test_a_drag_out_applies_to_each_picked_bubble(editor):
    client = user()
    page = editor(
        box("a", "shape", BUBBLE, x=20, y=60, w=60, h=40),
        box("b", "shape", BUBBLE, x=120, y=60, w=60, h=40),
        client=client,
    )
    k = mm(page)
    pick(page, "a", "b")
    start = centre(handle(page, "a"))
    drag(page, start, (start[0], start[1] + 15 * k))
    saved_now = {b["id"]: b for b in saved(page, client)}
    assert saved_now["a"]["props"]["tail"][1] > 1
    assert saved_now["b"]["props"]["tail"][1] > 1


def test_a_tip_above_takes_the_base_to_the_top(editor):
    shape = {**BUBBLE, "tail": [0.5, -0.5]}
    page = editor(box("a", "shape", shape, x=60, y=60, w=60, h=40))
    d = at(page, "a").locator(OUTLINE).get_attribute("d")
    pairs = [(float(x), float(y)) for x, y in re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", d)]
    # Only the tip lies out of the box: the base is on the top, so no line runs through the body.
    outside = [p for p in pairs if not (0 <= p[0] <= 60 and 0 <= p[1] <= 40)]
    assert outside == [(30.0, -20.0)], d
