"""The yellow handle that adjusts a bubble's tail, a star's inner points and a triangle's tip."""

import math
import re

import pytest
from playwright.sync_api import expect
from test_foot_cut import LINES, LONG, assert_whole_lines
from ui import (
    RECT,
    TEXT,
    at,
    box,
    centre,
    drag,
    expect_picked,
    pick,
    reload,
    saved,
    sheet,
    swipe,
    unpick,
    user,
)

from blattwerk import pdf

SENTENCE = "Wir lesen heute eine schöne Geschichte."
BUBBLE = {**RECT, "kind": "bubble"}
STAR = {**RECT, "kind": "star"}
TRI = {**RECT, "kind": "triangle"}
# The one element that draws a triangle, a star or a bubble.
OUTLINE = "svg.outline > *"
TEN = box("ten", "text", {"text": "zehn", "size": 10, "align": "left"}, x=150)
NUMBER = re.compile(r"[A-Za-z]|-?\d+(?:\.\d+)?(?:e-?\d+)?")


def mm(page):
    """Sheet pixels per mm."""
    return page.locator(".sheet").bounding_box()["width"] / 210


def handle(page, name):
    return page.locator(f'.sheet .adjust[data-id="{name}"]')


def font_px(block):
    return float(block.locator(".frame").evaluate("el => getComputedStyle(el).fontSize")[:-2])


def overlap(a, b):
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def same_path(found, want):
    """Two outlines with the same commands, and numbers equal to a millionth."""
    got, expected = NUMBER.findall(found), NUMBER.findall(want)
    assert len(got) == len(expected), (found, want)
    for g, w in zip(got, expected, strict=True):
        if w.isalpha():
            assert g == w, (found, want)
        else:
            assert float(g) == pytest.approx(float(w), abs=1e-6), (found, want)


def test_one_handle_on_bubble_star_triangle(editor):
    page = editor(
        box("bubble", "shape", BUBBLE, x=10, y=20, w=40, h=30),
        box("star", "shape", STAR, x=60, y=20, w=40, h=30),
        box("tri", "shape", TRI, x=110, y=20, w=40, h=30),
        box("text", "text", {**TEXT, "kind": "bubble"}, x=10, y=80, w=40, h=30),
        box("rect", "shape", RECT, x=60, y=80, w=40, h=30),
        box("circle", "shape", {**RECT, "kind": "circle"}, x=110, y=80, w=40, h=30),
        box("locked", "shape", TRI, x=10, y=140, w=40, h=30, locked=True),
    )
    shown = {"bubble": 1, "star": 1, "tri": 1, "text": 1, "rect": 0, "circle": 0, "locked": 0}
    for name, count in shown.items():
        pick(page, name)
        expect(page.locator(".sheet .adjust")).to_have_count(count)
        if count:
            expect(handle(page, name)).to_be_visible()


def test_drag_moves_the_bubble_tail(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    before = at(page, "a").locator(OUTLINE).get_attribute("d")
    start = centre(handle(page, "a"))
    drag(page, start, (start[0] + 30 * k, start[1]))
    (a,) = saved(page, client)
    # The tail starts at a fifth of the box and moves 30 mm of its 60.
    assert a["props"]["tail"][0] == pytest.approx(0.2 + 30 / 60, abs=0.02)
    assert at(page, "a").locator(OUTLINE).get_attribute("d") != before


def test_drag_deepens_the_star(editor):
    client = user()
    star = {**STAR, "inside": True, "text": SENTENCE, "size": 14, "align": "center"}
    page = editor(box("a", "shape", star, x=60, y=60, w=60, h=60), client=client)
    pick(page, "a")
    wide = at(page, "a").locator("p").first.bounding_box()["width"]
    start = centre(handle(page, "a"))
    middle = centre(at(page, "a"))
    # Half way from the handle to the middle of the star.
    target = ((start[0] + middle[0]) / 2, (start[1] + middle[1]) / 2)
    drag(page, start, target)
    (a,) = saved(page, client)
    assert a["props"]["inner"] < 0.38
    # Fewer and nearer inner points leave the text less room.
    assert at(page, "a").locator("p").first.bounding_box()["width"] < wide - 1


def test_drag_moves_the_triangle_tip(editor):
    client = user()
    tri = {**TRI, "inside": True, "text": SENTENCE, "size": 14, "align": "center"}
    page = editor(box("a", "shape", tri, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    text_x = centre(at(page, "a").locator("p").first)[0]
    points = at(page, "a").locator(OUTLINE).get_attribute("points")
    start = centre(handle(page, "a"))
    drag(page, start, (start[0] - 15 * k, start[1]))
    (a,) = saved(page, client)
    assert a["props"]["tip"] == pytest.approx(0.5 - 15 / 60, abs=0.02)
    # The first point of the triangle is its tip.
    first = at(page, "a").locator(OUTLINE).get_attribute("points").split()[0]
    assert float(first.split(",")[0]) < float(points.split()[0].split(",")[0]) - 1
    assert centre(at(page, "a").locator("p").first)[0] < text_x - 1


def test_the_pdf_prints_the_adjusted_outline(browser, server):
    client = user()
    tip0 = sheet(client, [box("a", "shape", {**TRI, "tip": 0}, x=60, y=60, w=60, h=40)])["id"]
    absent = sheet(client, [box("a", "shape", TRI, x=60, y=60, w=60, h=40)])["id"]

    def printed(mine):
        # The page the PDF is printed from, with the outline as the print draws it.
        page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
        page.goto(f"{server}/druck/{mine}")
        page.wait_for_selector("body.ready", state="attached")
        found = page.locator(OUTLINE).get_attribute("points")
        page.close()
        return found

    # A tip at the corner prints a different outline than the middle of the top.
    assert printed(tip0) != printed(absent)


def test_a_drag_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "shape", TRI, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    # Five moves, each its own step for the pointer, but one drag for the editor.
    drag(page, start, *[(start[0] - 3 * k * i, start[1]) for i in range(1, 6)])
    (a,) = saved(page, client)
    tip = a["props"]["tip"]
    assert tip < 0.5
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert a["props"].get("tip", 0.5) == 0.5
    page.keyboard.press("Control+y")
    (a,) = saved(page, client)
    assert a["props"]["tip"] == pytest.approx(tip, abs=0.001)


def test_escape_lets_go_of_the_handle(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    page.mouse.move(*start)
    page.mouse.down()
    page.mouse.move(start[0] + 10 * k, start[1], steps=5)
    page.keyboard.press("Escape")
    outline = at(page, "a").locator(OUTLINE)
    before = outline.get_attribute("d")
    # Let go away from the handle, then pass over it with no button down: the tail stays.
    page.mouse.move(start[0] + 10 * k, start[1] + 40 * k, steps=5)
    page.mouse.up()
    there = centre(handle(page, "a"))
    page.mouse.move(*there)
    page.mouse.move(there[0] + 20 * k, there[1], steps=5)
    expect(outline).to_have_attribute("d", before)


def test_the_value_survives_reload_and_copy(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    drag(page, start, (start[0] + 30 * k, start[1]))
    (a,) = saved(page, client)
    tail, outline = a["props"]["tail"], at(page, "a").locator(OUTLINE).get_attribute("d")
    reload(page, page.url)
    pick(page, "a")
    expect(handle(page, "a")).to_have_count(1)
    assert at(page, "a").locator(OUTLINE).get_attribute("d") == outline
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    blocks = saved(page, client)
    assert len(blocks) == 2
    assert [b["props"]["tail"] for b in blocks] == [tail, tail]


def test_the_drag_applies_to_each_picked(editor):
    client = user()
    page = editor(
        box("a", "shape", STAR, x=20, y=20, w=40, h=40),
        box("b", "shape", STAR, x=100, y=20, w=40, h=40),
        client=client,
    )
    pick(page, "a", "b")
    expect(page.locator(".sheet .adjust")).to_have_count(2)
    k = mm(page)
    start = centre(handle(page, "a"))
    drag(page, start, (start[0] + 6 * k, start[1] + 6 * k))
    inner = {b["id"]: b["props"]["inner"] for b in saved(page, client)}
    assert inner["a"] == inner["b"] < 0.38


def test_the_handle_follows_the_pointer_turned_and_flipped(editor):
    client = user()
    page = editor(
        box("a", "shape", TRI, x=20, y=60, w=40, h=40, angle=90),
        box("b", "shape", TRI, x=100, y=60, w=40, h=40, flipX=True),
        client=client,
    )
    k = mm(page)
    # Turned a quarter clockwise, the triangle's across runs down the screen.
    pick(page, "a")
    start = centre(handle(page, "a"))
    end = (start[0], start[1] + 15 * k)
    drag(page, start, end)
    (a, b) = saved(page, client)
    assert a["props"]["tip"] > 0.5
    assert math.dist(centre(handle(page, "a")), end) < 3
    # Flipped, the tip of the picture is on the other side: a drag to the right moves it left.
    pick(page, "b")
    start = centre(handle(page, "b"))
    end = (start[0] + 15 * k, start[1])
    drag(page, start, end)
    (a, b) = saved(page, client)
    assert b["props"]["tip"] < 0.5
    assert math.dist(centre(handle(page, "b")), end) < 3


def test_the_handle_keeps_clear_of_the_others(editor):
    client = user()
    page = editor(
        box("bubble", "shape", BUBBLE, x=20, y=20, w=40, h=30),
        box("star", "shape", STAR, x=80, y=20, w=40, h=30),
        box("tri", "shape", TRI, x=140, y=20, w=40, h=30),
        client=client,
    )
    k = mm(page)
    for name in ("bubble", "star", "tri"):
        pick(page, name)
        grab = handle(page, name)
        controls = page.locator(".moveable-control, .moveable-rotation-control").all()
        for control in controls:
            box_control = control.bounding_box()
            if box_control:
                assert not overlap(grab.bounding_box(), box_control), name
                # The finger area leaves the middle of each other handle to that handle.
                x, y = centre(control)
                hit = page.evaluate(
                    "([x, y]) => !!document.elementFromPoint(x, y).closest('.adjust')", [x, y]
                )
                assert not hit, name
        # A small drag changes the shape's value and nothing of the box.
        start = centre(grab)
        drag(page, start, (start[0] + 1 * k, start[1]))
        saved(page, client)
    blocks = {b["id"]: b for b in saved(page, client)}
    for name, x in (("bubble", 20), ("star", 80), ("tri", 140)):
        assert (blocks[name]["x"], blocks[name]["y"], blocks[name]["w"], blocks[name]["h"]) == (
            x,
            20,
            40,
            30,
        )
        assert blocks[name].get("angle", 0) == 0


def test_a_finger_drags_the_handle(editor):
    client = user()
    page = editor(box("a", "shape", BUBBLE, x=60, y=60, w=60, h=40), client=client, touch=True)
    k = mm(page)
    at(page, "a").tap()
    expect_picked(page, "a")
    start = centre(handle(page, "a"))
    swipe(page, start, (start[0] + 15 * k, start[1]), (start[0] + 30 * k, start[1]))
    (a,) = saved(page, client)
    assert a["props"]["tail"][0] == pytest.approx(0.2 + 30 / 60, abs=0.02)


def test_no_value_draws_as_before(editor):
    client = user()
    page = editor(
        box("t", "shape", TRI, x=20, y=20, w=40, h=30),
        box("s", "shape", STAR, x=80, y=20, w=40, h=30),
        box("b", "shape", BUBBLE, x=140, y=20, w=40, h=30),
        client=client,
    )
    # RECT's border is 0.5 mm wide.
    e = 0.5 / 2
    w, h = 40, 30
    # The outlines as the sheet draws them without any value: POINTS and OUTLINES in sheet.tsx.
    triangle = f"{w / 2},{e} {w - e},{h - e} {e},{h - e}"
    star = []
    for i in range(10):
        r, a = (0.38 if i % 2 else 1), i * math.pi / 5
        x = e + (w - 2 * e) * (0.5 + r * math.sin(a) / 1.902)
        y = e + (h - 2 * e) * (1 - r * math.cos(a)) / 1.809
        star.append(f"{x},{y}")
    r = min(4, w / 5, h / 4)
    right, low = w - e, e + 0.75 * (h - 2 * e)
    bubble = (
        f"M{e + r},{e} H{right - r} A{r},{r} 0 0 1 {right},{e + r} V{low - r} "
        f"A{r},{r} 0 0 1 {right - r},{low} H{0.4 * w} L{0.2 * w},{h - e} L{0.25 * w},{low} "
        f"H{e + r} A{r},{r} 0 0 1 {e},{low - r} V{e + r} A{r},{r} 0 0 1 {e + r},{e} Z"
    )
    same_path(at(page, "t").locator(OUTLINE).get_attribute("points"), triangle)
    same_path(at(page, "s").locator(OUTLINE).get_attribute("points"), " ".join(star))
    same_path(at(page, "b").locator(OUTLINE).get_attribute("d"), bubble)


def test_the_floor_holds_after_a_drag(editor):
    client = user()
    star = {**STAR, "inside": True, "floor": True, "text": SENTENCE, "size": 14, "align": "center"}
    page = editor(TEN, box("a", "shape", star, x=20, y=30, w=40, h=40), client=client)
    pick(page, "a")
    start = centre(handle(page, "a"))
    # Dragged to the middle of the star: the inner points go to their least.
    drag(page, start, centre(at(page, "a")))
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert a["props"]["inner"] < 0.2, a
    # The type is no smaller than the 10 pt text beside it.
    assert font_px(at(page, "a")) >= font_px(at(page, "ten")) - 0.05


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


DEEP = {**STAR, "inside": True, "floor": True, "text": "Super", "size": 18, "align": "center"}


@pytest.mark.parametrize("valign", ["top", "middle", "bottom"])
def test_a_deep_star_warns_when_its_word_does_not_fit(editor, valign):
    client = user()
    star = {**DEEP, "valign": valign}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40), client=client)
    pick(page, "a")
    drag(page, centre(handle(page, "a")), centre(at(page, "a")))
    expect(page.locator('[data-shape="full"]')).to_be_visible()


def test_a_deep_star_turned_warns_when_its_word_does_not_fit(editor):
    client = user()
    page = editor(box("a", "shape", DEEP, x=40, y=40, w=40, h=40, angle=45), client=client)
    pick(page, "a")
    drag(page, centre(handle(page, "a")), centre(at(page, "a")))
    expect(page.locator('[data-shape="full"]')).to_be_visible()


@pytest.mark.parametrize("picked", [("a", "b"), ("b",)])
def test_deep_stars_drag_at_once_warn(editor, picked):
    client = user()
    page = editor(
        box("a", "shape", DEEP, x=20, y=40, w=40, h=40),
        box("b", "shape", DEEP, x=100, y=40, w=40, h=40),
        client=client,
    )
    pick(page, *picked)
    drag(page, centre(handle(page, "b")), centre(at(page, "b")))
    expect(page.locator('[data-shape="full"]')).to_be_visible()


def test_undo_of_a_deep_drag_takes_the_warning_away(editor):
    client = user()
    page = editor(box("a", "shape", DEEP, x=40, y=40, w=60, h=60), client=client)
    pick(page, "a")
    expect(page.locator('[data-shape="full"]')).to_have_count(0)
    drag(page, centre(handle(page, "a")), centre(at(page, "a")))
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert "inner" not in a["props"], a
    expect(page.locator('[data-shape="full"]')).to_have_count(0)
    assert at(page, "a").locator("p").first.evaluate("p => p.scrollWidth <= p.clientWidth + 1")


def test_the_warning_goes_when_the_handle_comes_back_out(editor):
    client = user()
    page = editor(box("a", "shape", DEEP, x=40, y=40, w=60, h=60), client=client)
    pick(page, "a")
    start = centre(handle(page, "a"))
    drag(page, start, centre(at(page, "a")))
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    drag(page, centre(handle(page, "a")), start)
    expect(page.locator('[data-shape="full"]')).to_have_count(0)
    (a,) = saved(page, client)
    assert a["props"]["inner"] > 0.3, a
    assert at(page, "a").locator("p").first.evaluate("p => p.scrollWidth <= p.clientWidth + 1")


def test_an_empty_deep_star_does_not_warn(editor):
    deep = {**DEEP, "inner": 0.1}
    page = editor(
        box("a", "shape", {**deep, "text": ""}, x=40, y=40, w=40, h=40),
        box("b", "shape", deep, x=100, y=40, w=40, h=40),
    )
    # The star with its word warns once picked, so the frames have told the panel.
    pick(page, "b")
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    pick(page, "a")
    expect(page.locator('[data-shape="full"]')).to_have_count(0)


def test_a_big_star_dragged_a_little_keeps_its_word_whole(editor):
    client = user()
    page = editor(box("a", "shape", DEEP, x=40, y=40, w=120, h=120), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    middle = centre(at(page, "a"))
    # Two mm of the way from the handle to the middle.
    dist = math.dist(start, middle)
    along = 2 * k / dist
    target = (start[0] + (middle[0] - start[0]) * along, start[1] + (middle[1] - start[1]) * along)
    drag(page, start, target)
    expect(page.locator('[data-shape="full"]')).to_have_count(0)
    assert at(page, "a").locator("p").first.evaluate("p => p.scrollWidth <= p.clientWidth + 1")


def test_a_deep_triangle_or_bubble_keeps_its_word_or_warns(editor):
    client = user()
    word = {"text": "Super", "size": 18, "align": "center"}
    page = editor(
        box("t", "shape", {**TRI, "inside": True, "floor": True, **word}, x=20, y=40, w=40, h=40),
        box("b", "shape", {**BUBBLE, **word}, x=100, y=40, w=60, h=40),
        client=client,
    )
    k = mm(page)
    pick(page, "t")
    drag(page, centre(handle(page, "t")), centre(at(page, "t")))
    pick(page, "b")
    box_ = at(page, "b").bounding_box()
    drag(page, centre(handle(page, "b")), (box_["x"] + 12 * k, box_["y"] + 55 * k))
    for name in ("t", "b"):
        fits = at(page, name).locator("p").first.evaluate("p => p.scrollWidth <= p.clientWidth + 1")
        if not fits:
            expect(page.locator('[data-shape="full"]')).to_be_visible()


@pytest.mark.parametrize("inner", [0.25, 0.35])
def test_the_print_sizes_a_deep_stars_word_as_the_screen_does(editor, browser, server, inner):
    client = user()
    star = {**DEEP, "inner": inner}
    page = editor(box("a", "shape", star, x=40, y=40, w=60, h=60), client=client)
    pick(page, "a")
    # The word's width, its room and its type: shrunk at 0.35, too wide at 0.25 (the panel warns).
    words = "p => [p.scrollWidth, p.clientWidth, getComputedStyle(p).fontSize]"
    shown = at(page, "a").locator("p").first.evaluate(words)
    warning = page.locator('[data-shape="full"]')
    expect(warning).to_have_count(1 if shown[0] > shown[1] + 1 else 0)
    mine = sheet(client, [box("a", "shape", star, x=40, y=40, w=60, h=60)])["id"]
    printed = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    printed.goto(f"{server}/druck/{mine}")
    printed.wait_for_selector("body.ready", state="attached")
    assert printed.locator(".block .frame p").first.evaluate(words) == shown
    printed.close()


def test_a_deep_star_saved_without_floor_warns(editor):
    client = user()
    star = {**STAR, "inside": True, "text": "Super", "size": 18, "align": "center", "inner": 0.1}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40), client=client)
    pick(page, "a")
    expect(page.locator('[data-shape="full"]')).to_be_visible()
