"""See-through outlines, lines and pictures, in Chromium."""

import io
import re

from PIL import Image
from pixels import screen_and_print
from playwright.sync_api import expect
from test_undo_same import steps
from ui import LINE, RECT, at, box, drag, pick, picture, reload, saved, upload, user

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


def test_the_picture_slider_goes_to_both_pictures_picked(editor):
    client = user()
    one = picture(upload(client))
    page = editor(
        {**one, "id": "p1", "y": 20},
        {**one, "id": "p2", "y": 120, "z": 2},
        client=client,
    )
    pick(page, "p1", "p2")
    page.get_by_label("Transparenz", exact=True).fill("50")
    for name in ("p1", "p2"):
        expect(at(page, name).locator("img")).to_have_css("opacity", "0.5")


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


def drag_slider(page, label, share):
    """Drags the slider from its left end to this share of its width, with one press."""
    field = page.get_by_label(label, exact=True)
    field.scroll_into_view_if_needed()
    place = field.bounding_box()
    y = place["y"] + place["height"] / 2
    drag(page, (place["x"] + 2, y), (place["x"] + place["width"] * share, y))


def test_the_pdf_prints_a_half_transparent_line_half_grey(editor, browser, server):
    client = user()
    page = editor(
        box(
            "l",
            "shape",
            {**LINE, "stroke": "#000000", "strokeWidth": 3, "strokeOpacity": 0.5},
            x=20,
            y=60,
            w=100,
            h=0,
        ),
        client=client,
    )
    sheet_id = page.url.rsplit("/", 1)[1]
    _, printed = screen_and_print(browser, server, client, sheet_id)
    image = Image.open(io.BytesIO(printed)).convert("L")
    mm = image.width / 210
    column = round(70 * mm)
    darkest = min(image.crop((column, round(58 * mm), column + 1, round(62 * mm))).tobytes())
    assert 90 < darkest < 170


def test_the_pdf_prints_a_half_transparent_picture_half_see_through(editor, browser, server):
    client = user()
    pic = picture(upload(client))
    pic["props"]["opacity"] = 0.5
    page = editor(pic, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    _, printed = screen_and_print(browser, server, client, sheet_id)
    image = Image.open(io.BytesIO(printed)).convert("RGB")
    mm = image.width / 210
    # The picture is red: half see through, its green and blue lie between red and white.
    x, y = round(105 * mm), round(180 * mm)
    green = image.crop((x, y, x + 1, y + 1)).tobytes()[1]
    assert 90 < green < 170


def test_one_drag_of_the_border_slider_is_one_undo_step_and_redo_brings_it_back(editor):
    client = user()
    page = editor(
        box("r", "shape", {**RECT, "stroke": "#ff0000"}, x=20, y=60, w=60, h=40),
        client=client,
    )
    pick(page, "r")
    drag_slider(page, "Transparenz Linie", 0.5)
    shown = int(border_slider(page).input_value())
    assert shown > 0
    assert steps(page) == 1
    page.get_by_label("Rückgängig", exact=True).click()
    expect(border_slider(page)).to_have_value("0")
    page.get_by_label("Wiederholen", exact=True).click()
    expect(border_slider(page)).to_have_value(str(shown))


def test_one_drag_of_the_picture_slider_is_one_undo_step_and_redo_brings_it_back(editor):
    client = user()
    page = editor(picture(upload(client)), client=client)
    pick(page, "image")
    drag_slider(page, "Transparenz", 0.5)
    shown = int(page.get_by_label("Transparenz", exact=True).input_value())
    assert shown > 0
    assert steps(page) == 1
    page.get_by_label("Rückgängig", exact=True).click()
    expect(page.get_by_label("Transparenz", exact=True)).to_have_value("0")
    page.get_by_label("Wiederholen", exact=True).click()
    expect(page.get_by_label("Transparenz", exact=True)).to_have_value(str(shown))


def test_an_arrow_head_takes_the_line_transparency(editor):
    client = user()
    page = editor(
        box(
            "a",
            "shape",
            {**LINE, "kind": "arrow", "stroke": "#ff0000", "strokeOpacity": 0.5},
            x=20,
            y=60,
            w=100,
            h=40,
        ),
        client=client,
    )
    pick(page, "a")
    expect(at(page, "a").locator("svg polygon").first).to_have_css("fill-opacity", "0.5")


def test_a_picture_transparency_survives_a_reload(editor):
    client = user()
    pic = picture(upload(client))
    pic["props"]["opacity"] = 0.5
    page = editor(pic, client=client)
    saved(page, client)
    reload(page, page.url)
    expect(at(page, "image").locator("img")).to_have_css("opacity", "0.5")
