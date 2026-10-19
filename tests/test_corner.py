"""The yellow handle that sets a rounded box's corner radius."""

import pytest
from playwright.sync_api import expect
from test_adjust import handle, mm
from ui import RECT, at, box, centre, drag, pick, saved, sheet, user

from blattwerk import pdf

ROUNDED = {**RECT, "kind": "rounded"}


def radius(page, name):
    """The corner radius of a block on the screen, in mm."""
    px = at(page, name).evaluate(
        "el => [...el.querySelectorAll('*')].map(e => parseFloat(getComputedStyle(e).borderTopLeftRadius)).find(r => r > 0) || 0"
    )
    return px / mm(page)


def test_a_rounded_box_has_a_corner_handle(editor):
    page = editor(box("a", "shape", ROUNDED, x=60, y=60, w=60, h=40))
    pick(page, "a")
    grab = centre(handle(page, "a"))
    b = at(page, "a").bounding_box()
    expect(handle(page, "a")).to_be_visible()
    assert b["x"] < grab[0] < b["x"] + b["width"] / 2
    assert b["y"] < grab[1] < b["y"] + b["height"] / 2


def test_a_drag_sets_the_corner(editor):
    client = user()
    page = editor(box("a", "shape", ROUNDED, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    left = at(page, "a").bounding_box()["x"]
    start = centre(handle(page, "a"))
    # 10 mm along the top edge of a 40 mm box: a quarter of its shorter side.
    drag(page, start, (left + 10 * k, start[1]))
    (a,) = saved(page, client)
    assert a["props"]["corner"] == pytest.approx(0.25, abs=0.02)
    # Past the middle of the shorter side the corner stops at half of it.
    drag(page, centre(handle(page, "a")), (left + 100 * k, start[1]))
    (a,) = saved(page, client)
    assert a["props"]["corner"] == 0.5


def test_a_corner_drag_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "shape", ROUNDED, x=60, y=60, w=60, h=40), client=client)
    k = mm(page)
    pick(page, "a")
    start = centre(handle(page, "a"))
    drag(page, start, *[(start[0] + 3 * k * i, start[1]) for i in range(1, 6)])
    (a,) = saved(page, client)
    corner = a["props"]["corner"]
    assert corner > 0
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert a["props"].get("corner") is None
    page.keyboard.press("Control+y")
    (a,) = saved(page, client)
    assert a["props"]["corner"] == pytest.approx(corner, abs=0.001)


def test_the_pdf_prints_the_corner(browser, server):
    client = user()
    square = sheet(
        client,
        [box("a", "shape", {**ROUNDED, "corner": 0, "dash": "dashed"}, x=60, y=60, w=60, h=40)],
    )["id"]
    round_ = sheet(
        client,
        [box("a", "shape", {**ROUNDED, "corner": 0.5, "dash": "dashed"}, x=60, y=60, w=60, h=40)],
    )["id"]

    def printed(mine):
        # The page the PDF is printed from, with the box and its dashes as the print draws them.
        page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
        page.goto(f"{server}/druck/{mine}")
        page.wait_for_selector("body.ready", state="attached")
        found = page.locator('[data-block="a"] .frame').evaluate(
            "el => getComputedStyle(el).borderTopLeftRadius"
        )
        # The dashes go along the way round the corner: a plain rect where it is square.
        way = page.locator('[data-block="a"] svg :is(path, rect)').evaluate(
            "el => el.tagName + ' ' + (el.getAttribute('d') ?? '')"
        )
        page.close()
        return found, way

    # A square corner prints square, and a corner at half the shorter side prints round, as the screen does.
    radius_, way = printed(square)
    assert radius_ == "0px"
    assert way == "rect "
    radius_, way = printed(round_)
    # Half of the 40 mm shorter side, at the print's scale of 226.772 px per 60 mm of width.
    assert float(radius_[:-2]) == pytest.approx(0.5 * 40 * 226.772 / 60, abs=1)
    # The way of the dashes turns round the corners: 45 short lines to a quarter turn.
    assert way.startswith("path M")
    assert len(way.split("L")) > 100


def test_no_corner_keeps_4_mm(editor):
    page = editor(box("a", "shape", ROUNDED, x=60, y=60, w=60, h=40))
    pick(page, "a")
    assert radius(page, "a") == pytest.approx(4, abs=0.2)


def test_the_corner_scales_with_the_box(editor):
    page = editor(
        box("a", "shape", {**ROUNDED, "corner": 0.25}, x=20, y=20, w=60, h=40),
        box("b", "shape", {**ROUNDED, "corner": 0.25}, x=120, y=20, w=30, h=20),
    )
    # A quarter of the shorter side: 10 mm for the 40 mm box, 5 mm for the 20 mm one.
    assert radius(page, "a") == pytest.approx(10, abs=0.4)
    assert radius(page, "b") == pytest.approx(5, abs=0.4)


def test_the_corner_drag_sets_each_picked(editor):
    client = user()
    page = editor(
        box("a", "shape", ROUNDED, x=20, y=20, w=40, h=40),
        box("b", "shape", ROUNDED, x=100, y=20, w=40, h=40),
        client=client,
    )
    pick(page, "a", "b")
    expect(page.locator(".sheet .adjust")).to_have_count(2)
    k = mm(page)
    left = at(page, "a").bounding_box()["x"]
    start = centre(handle(page, "a"))
    drag(page, start, (left + 10 * k, start[1]))
    corners = {b["id"]: b["props"]["corner"] for b in saved(page, client)}
    assert corners["a"] == corners["b"] == pytest.approx(0.25, abs=0.02)
