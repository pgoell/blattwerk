"""The yellow handle moves a bubble's tail, a star's inner points and a triangle's tip."""

import math

import pytest
from playwright.sync_api import expect
from test_adjust import (
    BUBBLE,
    OUTLINE,
    SENTENCE,
    STAR,
    TEN,
    TRI,
    font_px,
    handle,
    mm,
    overlap,
    same_path,
)
from ui import (
    BROWSER,
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
    user,
)

from blattwerk import pdf


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


@pytest.mark.xfail(
    BROWSER == "webkit",
    raises=KeyError,
    strict=False,
    reason="#932: once in CI the swipe saved a change that was not the tail; no cause found yet",
)
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
