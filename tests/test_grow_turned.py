"""A turned text that grows with its words, in Chromium on the built frontend."""

import math

import pytest
from playwright.sync_api import expect
from ui import FIELD, RECT, TEXT, at, box, centre, drag, expect_picked, pick, saved, user

WORDS = {"text": TEXT, "shape": {**RECT, "text": "Hallo"}}
LONG = {**TEXT, "text": "Der Igel sucht im Herbst nach Laub und baut sich ein Nest"}


def corner(b):
    """Where the block's own upper left corner lies on the page, in mm, turned as the block is.

    The words start at the edge through it: a box that grows keeps it, and so does one made
    narrower from its far side.
    """
    turn = math.radians(b.get("angle", 0))
    c, s = math.cos(turn), math.sin(turn)
    w, h = b["w"] / 2, b["h"] / 2
    return b["x"] + w - w * c + h * s, b["y"] + h - w * s - h * c


def stays(now, was):
    """The corner is where it was: a place is kept to the hundredth of a mm."""
    return corner(now) == pytest.approx(corner(was), abs=0.02)


def write(page, *lines):
    """Types the lines into the open text, each a paragraph of its own."""
    expect(page.locator(FIELD)).to_be_focused()
    for i, line in enumerate(lines):
        if i:
            page.keyboard.press("Enter")
        page.keyboard.type(line)


@pytest.mark.parametrize("degrees", [90, 30, 200])
@pytest.mark.parametrize("kind", ["text", "shape"])
def test_a_turned_box_that_grows_keeps_the_edge_its_words_start_at(editor, kind, degrees):
    client = user()
    was = box("a", kind, WORDS[kind], x=75, y=100, w=60, h=10, angle=degrees)
    page = editor(was, client=client)
    at(page, "a").dblclick()
    write(page, "eins", "zwei", "drei")
    (a,) = saved(page, client)
    assert a["h"] > 15
    assert (a["w"], a["angle"]) == (60, degrees)
    assert stays(a, was)


def test_a_flipped_outline_that_grows_keeps_the_edge_its_words_start_at(editor):
    client = user()
    # A flip mirrors the outline alone: the words still start at the block's own top edge.
    star = {**TEXT, "kind": "star", "stroke": "#222222"}
    was = box("a", "text", star, x=75, y=100, w=60, h=10, angle=90, flipY=True)
    page = editor(was, client=client)
    at(page, "a").dblclick()
    write(page, "eins", "zwei", "drei")
    (a,) = saved(page, client)
    assert a["h"] > 15
    assert stays(a, was)


@pytest.mark.parametrize("undo", ["key", "button"])
def test_undo_takes_back_the_growth_of_a_turned_text(editor, undo):
    client = user()
    was = box("a", "text", TEXT, x=75, y=100, w=60, h=10, angle=90)
    page = editor(was, client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    write(page, "eins", "zwei", "drei")
    assert saved(page, client)[0]["h"] > 15
    # The field is left first: there Ctrl+Z is the field's own.
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    back = page.get_by_label("Rückgängig")
    expect(back).to_be_enabled()
    # Each paragraph may be a step of its own.
    while back.is_enabled():
        if undo == "key":
            page.keyboard.press("Control+z")
        else:
            back.click()
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Hallo"
    assert [a[side] for side in "xyh"] == [was[side] for side in "xyh"]


@pytest.mark.parametrize("degrees", [90, 30])
@pytest.mark.parametrize("group", [None, ["g"]])
@pytest.mark.parametrize("kind", ["text", "shape"])
def test_a_larger_font_grows_a_turned_box_from_the_edge_its_words_start_at(
    editor, kind, group, degrees
):
    client = user()
    props = {**WORDS[kind], "text": LONG["text"]}
    was = box("a", kind, props, x=75, y=100, w=60, h=20, angle=degrees, group=group)
    other = box("b", "shape", RECT, z=2, x=20, y=200, w=30, h=20, group=group)
    page = editor(was, other, client=client)
    # No text in a group opens: there the panel alone makes a box grow. One click picks the group.
    at(page, "a").click()
    expect_picked(page, *(["a", "b"] if group else ["a"]))
    for _ in range(2):
        page.get_by_label("Schrift größer").click()
    a = saved(page, client)[0]
    assert a["props"]["size"] == 18
    assert a["h"] > 25
    assert stays(a, was)


@pytest.mark.parametrize("degrees", [90, 30])
def test_a_narrower_turned_text_grows_from_the_edge_its_words_start_at(editor, degrees):
    client = user()
    was = box("a", "text", LONG, x=75, y=100, w=60, h=20, angle=degrees)
    page = editor(was, client=client)
    k = page.locator(".sheet").bounding_box()["width"] / 210
    pick(page, "a")
    # The right edge's handle, pushed 30 mm in along the block's own width.
    x, y = centre(page.locator(".moveable-control.moveable-e"))
    turn = math.radians(degrees)
    drag(page, (x, y), (x - 30 * k * math.cos(turn), y - 30 * k * math.sin(turn)))
    (a,) = saved(page, client)
    assert a["w"] == pytest.approx(30, abs=1)
    assert a["h"] > 25
    assert stays(a, was)
