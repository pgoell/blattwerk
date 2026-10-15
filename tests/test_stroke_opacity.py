"""See-through outlines, lines and pictures, in Chromium."""

import re

from playwright.sync_api import expect
from ui import LINE, RECT, at, box, pick, picture, saved, upload, user

# The one that draws the dashes of a box's border.
DASHES = "svg.dashes > *"
HALF_RED = re.compile(r"rgba\(255, 0, 0, 0\.5\)")
FULL_RED = re.compile(r"rgb\(255, 0, 0\)")


def stroke_slider(page):
    """The line's only slider, and a shape's slider for its border."""
    return page.get_by_label("Transparenz", exact=True)


def border_slider(page):
    return page.get_by_label("Transparenz Linie", exact=True)


def test_the_slider_makes_a_line_see_through(editor):
    client = user()
    page = editor(
        box("l", "shape", {**LINE, "stroke": "#ff0000"}, x=20, y=60, w=100, h=40),
        client=client,
    )
    pick(page, "l")
    stroke_slider(page).fill("50")
    # The first line is the see-through grip, the second is the one drawn.
    drawn = at(page, "l").locator("svg line").nth(1)
    expect(drawn).to_have_css("stroke-opacity", "0.5")
    (a,) = saved(page, client)
    assert a["props"]["strokeOpacity"] == 0.5


def test_the_border_slider_makes_a_solid_border_see_through(editor):
    client = user()
    page = editor(
        box("r", "shape", {**RECT, "stroke": "#ff0000"}, x=20, y=60, w=60, h=40),
        client=client,
    )
    pick(page, "r")
    border_slider(page).fill("50")
    expect(at(page, "r").locator(".frame")).to_have_css("box-shadow", HALF_RED)
    (a,) = saved(page, client)
    assert a["props"]["strokeOpacity"] == 0.5


def test_the_border_slider_makes_a_circle_and_a_dashed_border_see_through(editor):
    client = user()
    page = editor(
        box("c", "shape", {**RECT, "kind": "circle", "stroke": "#ff0000"}, x=20, y=60, w=40, h=40),
        box(
            "d",
            "shape",
            {**RECT, "stroke": "#ff0000", "dash": "dashed"},
            z=2,
            x=20,
            y=160,
            w=60,
            h=40,
        ),
        client=client,
    )
    pick(page, "c")
    border_slider(page).fill("50")
    expect(at(page, "c").locator(".frame")).to_have_css("box-shadow", HALF_RED)
    pick(page, "d")
    border_slider(page).fill("50")
    expect(at(page, "d").locator(DASHES).first).to_have_css("stroke-opacity", "0.5")


def test_the_slider_makes_a_picture_see_through(editor):
    client = user()
    page = editor(picture(upload(client)), client=client)
    pick(page, "image")
    page.get_by_label("Transparenz", exact=True).fill("50")
    expect(at(page, "image").locator("img")).to_have_css("opacity", "0.5")
    (a,) = saved(page, client)
    assert a["props"]["opacity"] == 0.5


def test_a_saved_border_without_stroke_opacity_stays_solid(editor):
    client = user()
    page = editor(
        box("r", "shape", {**RECT, "stroke": "#ff0000"}, x=20, y=60, w=60, h=40),
        client=client,
    )
    expect(at(page, "r").locator(".frame")).to_have_css("box-shadow", FULL_RED)


def test_the_border_slider_goes_to_all_selected(editor):
    client = user()
    page = editor(
        box("a", "shape", {**RECT, "stroke": "#ff0000"}, x=20, y=60, w=60, h=40),
        box("b", "shape", {**RECT, "stroke": "#ff0000"}, z=2, x=20, y=160, w=60, h=40),
        client=client,
    )
    pick(page, "a", "b")
    border_slider(page).fill("50")
    expect(at(page, "a").locator(".frame")).to_have_css("box-shadow", HALF_RED)
    expect(at(page, "b").locator(".frame")).to_have_css("box-shadow", HALF_RED)
    a, b = saved(page, client)
    assert (a["props"]["strokeOpacity"], b["props"]["strokeOpacity"]) == (0.5, 0.5)
