"""A text or a shape that grows for its text stops at the page's foot, and the panel warns."""

import math

import pytest
from playwright.sync_api import expect
from ui import FIELD, RECT, TEXT, at, box, saved, user

FOOT = 297
SENTENCE = "Der Igel sucht im Herbst nach Laub und baut sich ein warmes Nest unter der Hecke."
LONG = " ".join([SENTENCE] * 4)
FULL = '.panel [data-foot="full"]'
OVER = '.panel [data-foot="over"]'


def type_into(page, text):
    """Types the text in place of the old one, then ends the edit: the block stays picked."""
    at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.type(text)
    page.keyboard.press("Escape")
    expect(page.locator(FIELD)).to_have_count(0)


def test_a_text_stops_at_the_foot_and_the_panel_warns(editor):
    client = user()
    page = editor(box("a", "text", TEXT, x=15, y=270, w=180, h=12), client=client)
    type_into(page, LONG)
    (a,) = saved(page, client)
    expect(page.locator(FULL)).to_be_visible()
    expect(page.locator(OVER)).to_have_count(0)
    assert a["y"] + a["h"] <= FOOT + 0.05
    assert a["h"] > 12


def test_a_circle_near_the_foot_stops_and_stays_round(editor):
    client = user()
    circle = {**RECT, "kind": "circle", "inside": True, "text": "Hallo"}
    page = editor(box("a", "shape", circle, x=100, y=250, w=40, h=40), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_be_visible()
    (a,) = saved(page, client)
    assert a["y"] + a["h"] <= FOOT + 0.05
    assert a["w"] == a["h"]


def test_a_triangle_near_the_foot_stops(editor):
    client = user()
    triangle = {**RECT, "kind": "triangle", "inside": True, "text": "Hallo"}
    page = editor(box("a", "shape", triangle, x=100, y=250, w=60, h=40), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_be_visible()
    (a,) = saved(page, client)
    assert a["y"] + a["h"] <= FOOT + 0.05


def test_undo_takes_text_and_height_back_in_one_step(editor):
    client = user()
    page = editor(box("a", "text", TEXT, x=15, y=270, w=180, h=12), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_be_visible()
    page.keyboard.press("Control+z")
    (a,) = saved(page, client)
    assert (a["y"], a["h"], a["props"]["text"]) == (270, 12, "Hallo")


def test_the_warning_goes_when_the_text_fits_again(editor):
    client = user()
    page = editor(box("a", "text", TEXT, x=15, y=270, w=180, h=12), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_be_visible()
    type_into(page, "Hallo")
    expect(page.locator(FULL)).to_have_count(0)


def test_a_block_already_past_the_foot_does_not_shrink(editor):
    client = user()
    page = editor(box("a", "text", TEXT, x=15, y=290, w=180, h=20), client=client)
    type_into(page, LONG)
    expect(page.locator(OVER)).to_be_visible()
    expect(page.locator(FULL)).to_have_count(0)
    (a,) = saved(page, client)
    assert a["y"] == 290
    assert a["h"] >= 20


@pytest.mark.xfail(strict=True, reason="open: the stop holds the turned text, but no warning shows")
def test_a_turned_text_near_the_foot_stops(editor):
    # Extra: a text box a teacher tilts near the foot. Turned by 30 degrees, its lowest corner is
    # its centre plus half its width and height, each leaning. At 90 degrees words grow sideways.
    client = user()
    page = editor(box("a", "text", TEXT, x=100, y=250, w=60, h=12, angle=30), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_be_visible()
    (a,) = saved(page, client)
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    assert a["y"] + a["h"] / 2 + (a["w"] * s + a["h"] * c) / 2 <= FOOT + 0.05


def test_a_short_text_in_the_middle_of_the_page_shows_no_warning(editor):
    # Extra: a line typed high on the page grows as before and never warns.
    client = user()
    page = editor(box("a", "text", TEXT, x=15, y=40, w=180, h=12), client=client)
    type_into(page, LONG)
    expect(page.locator(FULL)).to_have_count(0)
    (a,) = saved(page, client)
    assert a["h"] > 12
