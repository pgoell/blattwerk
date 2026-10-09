""" "Seitenbreite" on a turned Lineatur, in Chromium on the built frontend."""

import math

import pytest
from playwright.sync_api import expect
from test_height_turned import MARGIN, corners, ruling
from ui import RULING, at, box, doc, pick, user

UPRIGHT = (210, 297)
# What a block keeps: "Seitenbreite" sets its width and its place alone.
KEPT = ("h", "angle", "props", "z", "locked")


def press(page, client, name="a"):
    """Every block by name, as the server holds it once the button has set a new width."""
    wide = at(page, name).evaluate("e => getComputedStyle(e).width")
    page.get_by_role("button", name="Seitenbreite").click()
    expect(at(page, name)).not_to_have_css("width", wide)
    return held(page, client)


def held(page, client):
    """Every block of every page by name, as the server holds it."""
    return {b["id"]: b for p in doc(page, client)["pages"] for b in p["blocks"]}


def axis(b):
    turn = math.radians(b.get("angle", 0))
    return math.cos(turn), math.sin(turn)


def inside(b, size=UPRIGHT):
    """Whether no corner of the turned block crosses a margin of the page."""
    return all(
        MARGIN - 0.01 <= at <= side - MARGIN + 0.01
        for corner in corners(b, 0)
        for at, side in zip(corner, size, strict=True)
    )


def longer(b, end, by=0.1):
    """The block grown a little the way it lies, at its far end (1) or at its near one (-1)."""
    c, s = axis(b)
    x, y = b["x"] + by / 2 * (end * c - 1), b["y"] + by / 2 * end * s
    return {**b, "w": b["w"] + by, "x": x, "y": y}


def across(b):
    """Where the block's centre lies across the way the block lies."""
    c, s = axis(b)
    return (b["y"] + b["h"] / 2) * c - (b["x"] + b["w"] / 2) * s


def fitted(now, was, size=UPRIGHT):
    """Whether the block fills the room between the margins along the way it lies, and no more."""
    assert {k: now.get(k) for k in KEPT} == {k: was.get(k) for k in KEPT}
    assert across(now) == pytest.approx(across(was), abs=0.02)
    assert inside(now, size)
    assert not inside(longer(now, 1), size)
    assert not inside(longer(now, -1), size)
    return True


@pytest.mark.parametrize("degrees", [90, 180, 270, 30, 200])
def test_a_turned_lineatur_fills_the_room_along_the_way_it_lies(editor, degrees):
    """A1"""
    client = user()
    was = ruling(degrees)
    page = editor(was, client=client)
    pick(page, "a")
    a = press(page, client)["a"]
    assert fitted(a, was)
    # Rows are counted down the block: as many as before.
    expect(page.locator(".panel output", has_text="Zeilen")).to_have_text("2 Zeilen")


@pytest.mark.parametrize("degrees", [90, 270])
def test_a_lineatur_turned_by_a_quarter_runs_from_the_top_margin_to_the_bottom_one(editor, degrees):
    """A1"""
    client = user()
    page = editor(ruling(degrees), client=client)
    pick(page, "a")
    a = press(page, client)["a"]
    assert (a["w"], a["h"]) == (267, 20)
    # The centre is at the middle of the page's height, and still 105 mm from the left.
    assert (a["x"] + a["w"] / 2, a["y"] + a["h"] / 2) == (105, 148.5)


def test_a_level_lineatur_gets_the_width_between_the_margins(editor):
    """A2"""
    client = user()
    was = ruling(0)
    page = editor(was, client=client)
    pick(page, "a")
    a = press(page, client)["a"]
    assert (a["x"], a["y"], a["w"], a["h"]) == (15, was["y"], 180, was["h"])
    assert "angle" not in a


def test_one_undo_takes_the_width_back_and_one_redo_sets_it_again(editor):
    """I1"""
    client = user()
    was = ruling(30)
    page = editor(was, client=client)
    pick(page, "a")
    narrow = at(page, "a").evaluate("e => getComputedStyle(e).width")
    a = press(page, client)["a"]
    wide = at(page, "a").evaluate("e => getComputedStyle(e).width")
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("width", narrow)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert held(page, client)["a"] == was
    page.keyboard.press("Control+y")
    expect(at(page, "a")).to_have_css("width", wide)
    expect(page.get_by_label("Wiederholen")).to_be_disabled()
    assert held(page, client)["a"] == a


def test_each_of_two_lineaturen_is_fitted_on_its_own(editor):
    """I2"""
    client = user()
    a = ruling(30)
    b = box("b", "ruling", RULING, z=2, x=30, y=40, w=60, h=30, angle=200)
    page = editor(a, b, client=client)
    pick(page, "a", "b")
    now = press(page, client)
    assert fitted(now["a"], a)
    assert fitted(now["b"], b)
    assert now["a"]["w"] != now["b"]["w"]


@pytest.mark.parametrize("degrees", [0, 90, 30])
def test_on_a_landscape_page_the_width_is_that_page_s(editor, degrees):
    """I3"""
    client = user()
    was = ruling(degrees)
    page = editor(client=client, pages=[{"blocks": [was], "landscape": True}])
    pick(page, "a")
    a = press(page, client)["a"]
    assert fitted(a, was, (297, 210))
    assert a["w"] == {0: 267, 90: 180}.get(degrees, a["w"])


# At 45 and 202 degrees the rounded place leaves a hundredth of room for a second press to find.
@pytest.mark.parametrize("degrees", [0, 90, 30, 45, 202])
def test_a_second_press_changes_nothing(editor, degrees):
    """I4"""
    client = user()
    page = editor(ruling(degrees), client=client)
    pick(page, "a")
    a = press(page, client)["a"]
    page.get_by_role("button", name="Seitenbreite").click()
    assert held(page, client)["a"] == a
