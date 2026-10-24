"""A deep star warns when its word does not fit, and typing does not grow it back."""

import math

import pytest
from playwright.sync_api import expect
from test_adjust import (
    BUBBLE,
    DEEP,
    SENTENCE,
    STAR,
    TRI,
    WHOLE,
    handle,
    mm,
    type_at_end,
)
from ui import (
    at,
    box,
    centre,
    drag,
    pick,
    saved,
    sheet,
    user,
)

from blattwerk import pdf


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


@pytest.mark.parametrize("size", [40, 60])
def test_a_plain_star_whose_word_prints_whole_does_not_warn(editor, size):
    # At 40 mm the word is a pixel wider than its room at the least type, in the padding.
    page = editor(
        box("a", "shape", DEEP, x=40, y=40, w=size, h=size),
        box("b", "shape", {**DEEP, "inner": 0.1}, x=120, y=40, w=40, h=40),
    )
    # The deep star warns once picked, so the frames have told the panel.
    pick(page, "b")
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    pick(page, "a")
    expect(page.locator('[data-shape="full"]')).to_have_count(0)
    assert at(page, "a").locator("p").first.evaluate(WHOLE)


@pytest.mark.parametrize("inner", [0.1, 0.15, 0.2, 0.25, 0.3])
def test_typing_in_a_deep_star_keeps_its_size_and_warns(editor, inner):
    # Its room is narrower than the ink's padding: no size holds the word, so it does not grow.
    client = user()
    star = {**DEEP, "inner": inner}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40), client=client)
    pick(page, "a")
    page.mouse.dblclick(*centre(at(page, "a")))
    page.keyboard.press("End")
    page.keyboard.type("x")
    page.keyboard.press("Escape")
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Superx"
    assert (a["w"], a["h"]) == (40, 40), a


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


@pytest.mark.parametrize("inner", [0.2, 0.25, 0.35])
def test_the_print_sizes_a_deep_stars_word_as_the_screen_does(editor, browser, server, inner):
    client = user()
    star = {**DEEP, "inner": inner}
    page = editor(box("a", "shape", star, x=40, y=40, w=60, h=60), client=client)
    pick(page, "a")
    # The word's width, its room and its type: shrunk at 0.35, too wide at 0.25 (the panel warns).
    words = "p => [p.scrollWidth, p.clientWidth, getComputedStyle(p).fontSize]"
    shown = at(page, "a").locator("p").first.evaluate(words)
    whole = at(page, "a").locator("p").first.evaluate(WHOLE)
    expect(page.locator('[data-shape="full"]')).to_have_count(0 if whole else 1)
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


def test_undo_and_redo_of_typing_in_a_deep_star_keep_its_size(editor):
    client = user()
    star = {**DEEP, "inner": 0.2}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40), client=client)
    pick(page, "a")
    # The word does not fit even before the typing: the star warns once picked.
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    type_at_end(page, "a", "x")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Superx" and (a["w"], a["h"]) == (40, 40), a
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Super" and (a["w"], a["h"]) == (40, 40), a
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    page.keyboard.press("Control+y")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Superx" and (a["w"], a["h"]) == (40, 40), a
    expect(page.locator('[data-shape="full"]')).to_be_visible()


def test_two_deep_stars_picked_keep_their_size_when_the_type_grows(editor):
    client = user()
    star = {**DEEP, "inner": 0.2}
    page = editor(
        box("a", "shape", star, x=20, y=40, w=40, h=40),
        box("b", "shape", star, x=100, y=40, w=40, h=40),
        client=client,
    )
    pick(page, "a", "b")
    page.get_by_label("Schrift größer", exact=True).click()
    expect(page.locator('[data-shape="full"]')).to_be_visible()
    blocks = saved(page, client)
    assert len(blocks) == 2, blocks
    for blk in blocks:
        assert (blk["w"], blk["h"]) == (40, 40), blk


def test_typing_in_a_dragged_triangle_or_bubble_grows_no_more_than_an_undragged_one(editor):
    client = user()
    word = {"text": "Superschön", "size": 18, "align": "center", "inside": True, "floor": True}
    page = editor(
        box("t", "shape", {**TRI, **word}, x=10, y=20, w=40, h=40),
        box("td", "shape", {**TRI, **word, "tip": 0}, x=60, y=20, w=40, h=40),
        box("b", "shape", {**BUBBLE, **word}, x=110, y=20, w=60, h=40),
        box("bd", "shape", {**BUBBLE, **word, "tail": [1.5, 1.8]}, x=110, y=100, w=60, h=40),
        client=client,
    )
    for name in ("t", "td", "b", "bd"):
        pick(page, name)
        type_at_end(page, name, " Superschön")
    got = {blk["id"]: (blk["w"], blk["h"]) for blk in saved(page, client)}
    assert got["td"] == got["t"], got
    assert got["bd"] == got["b"], got


def test_a_deep_star_with_many_lines_keeps_its_height(editor):
    client = user()
    star = {**DEEP, "inner": 0.2}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40), client=client)
    pick(page, "a")
    type_at_end(page, "a", " " + SENTENCE)
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Super " + SENTENCE and (a["w"], a["h"]) == (40, 40), a


def test_a_turned_deep_star_keeps_its_size_when_typed_in(editor):
    client = user()
    star = {**DEEP, "inner": 0.2}
    page = editor(box("a", "shape", star, x=40, y=40, w=40, h=40, angle=45), client=client)
    pick(page, "a")
    type_at_end(page, "a", "x")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Superx" and (a["w"], a["h"]) == (40, 40), a
    expect(page.locator('[data-shape="full"]')).to_be_visible()


def test_a_deep_star_at_the_foot_warns_and_keeps_its_size(editor):
    client = user()
    star = {**DEEP, "inner": 0.2}
    page = editor(box("a", "shape", star, x=40, y=250, w=40, h=40), client=client)
    pick(page, "a")
    type_at_end(page, "a", "x")
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Superx" and (a["w"], a["h"]) == (40, 40), a
    expect(page.locator('[data-shape="full"]')).to_be_visible()
