"""The look of a shape: a flip, an arrow, the frame, and dashes on the border.

The helpers live in test_shapes.py.
"""

import io
import re

import pytest
from PIL import Image
from pixels import as_png, diff
from playwright.sync_api import expect
from test_border import shadow
from test_shapes import (
    FLIPS,
    OUTLINE,
    RED,
    ROOM,
    button,
    drawn,
    expect_no_box,
    frame,
    slider,
)
from ui import (
    LINE,
    RECT,
    TEXT,
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

# The one that draws the dashes of a box's border.
DASHES = "svg.dashes > *"


def expect_readable(page, name):
    """Nothing the text stands in is mirrored."""
    assert "scale" not in at(page, name).evaluate("el => el.style.transform")
    expect(at(page, name).locator(".frame")).to_have_css("transform", "none")
    expect(at(page, name).locator(".frame p")).to_have_css("transform", "none")


@pytest.mark.parametrize("kind", ["triangle", "star", "bubble"])
def test_the_look_goes_to_the_outline(editor, kind):
    client = user()
    page = editor(box("a", "shape", {**RECT, "kind": kind}, **ROOM), client=client)
    pick(page, "a")
    shape = at(page, "a").locator(OUTLINE)
    expect(shape).to_have_attribute("fill", "none")
    expect(shape).to_have_attribute("stroke", "#222222")
    expect(shape).to_have_attribute("stroke-width", "0.5")
    assert shape.get_attribute("stroke-dasharray") is None
    button(page, "Füllung").fill("#ff0000")
    expect(shape).to_have_attribute("fill", "#ff0000")
    expect(shape).to_have_attribute("fill-opacity", "1")
    button(page, "Rand").fill("#0000ff")
    expect(shape).to_have_attribute("stroke", "#0000ff")
    button(page, "Randstärke").fill("2")
    expect(shape).to_have_attribute("stroke-width", "2")
    for label in ("Gestrichelt", "Gepunktet"):
        button(page, label).click()
        expect(shape).to_have_attribute("stroke-dasharray", re.compile(r"\d"))
    # The box itself stays bare, whatever the look.
    expect_no_box(page)
    page.get_by_role("button", name="Kein Rand").click()
    expect(shape).to_have_attribute("stroke", "none")
    (a,) = saved(page, client)
    assert a["props"] == {
        "kind": kind,
        "fill": "#ff0000",
        "stroke": "none",
        "strokeWidth": 2,
        "dash": "dotted",
    }


def test_flip_mirrors_an_outline_and_not_its_text(editor):
    client = user()
    page = editor(
        box("blase", "shape", {**RED, "kind": "bubble", "text": "Hallo"}, **ROOM),
        box(
            "dreieck",
            "shape",
            {**RED, "kind": "triangle", "text": "Hallo"},
            x=20,
            y=150,
            w=40,
            h=40,
        ),
        box("stern", "shape", {**RED, "kind": "star"}, x=120, y=150, w=40, h=40),
        box("eck", "shape", RED, x=20, y=220, w=40, h=20),
        client=client,
    )

    def flags():
        return {
            b["id"]: (b.get("flipX", False), b.get("flipY", False)) for b in saved(page, client)
        }

    pick(page, "blase")
    assert drawn(page, "blase") == (1, 1)
    button(page, FLIPS[0]).click()
    # The tail now hangs on the right, and the words read as before.
    assert drawn(page, "blase") == (-1, 1)
    expect(at(page, "blase").locator("svg.outline")).to_have_attribute(
        "style", re.compile(r"scale\(-1, 1\)")
    )
    expect_readable(page, "blase")
    assert flags()["blase"] == (True, False)
    # A second flip of the same axis takes the first back.
    button(page, FLIPS[0]).click()
    assert drawn(page, "blase") == (1, 1)
    assert flags()["blase"] == (False, False)
    pick(page, "dreieck")
    button(page, FLIPS[1]).click()
    # The tip points down.
    assert drawn(page, "dreieck") == (1, -1)
    expect_readable(page, "dreieck")
    pick(page, "stern", "eck")
    for label in FLIPS:
        button(page, label).click()
    assert drawn(page, "stern") == (-1, -1)
    # A box looks the same either way and keeps no flip.
    assert flags() == {
        "blase": (False, False),
        "dreieck": (False, True),
        "stern": (True, True),
        "eck": (False, False),
    }
    page.keyboard.press("Control+z")
    assert drawn(page, "stern") == (-1, 1)


def test_an_arrow_with_two_heads_is_a_line(editor):
    client = user()
    page = editor(
        box("pfeil", "shape", {**LINE, "kind": "double"}, x=60, y=100, w=60, h=20), client=client
    )
    k = page.locator(".sheet").bounding_box()["width"] / 210
    pick(page, "pfeil")
    # Each end has a head, so each has the ring that leaves the head in sight. No handle turns it.
    ends = page.locator(".sheet .end")
    expect(ends).to_have_count(2)
    expect(page.locator(".sheet .end.tip")).to_have_count(2)
    expect(page.locator(".moveable-rotation-control")).to_have_count(0)
    # The start goes down by 40 mm, below the end, and the end right by 20 mm. The other end stays
    # each time.
    left, right = sorted((centre(end) for end in ends.all()), key=lambda at: at[0])
    drag(page, left, (left[0], left[1] + 40 * k))
    drag(page, right, (right[0] + 20 * k, right[1]))
    (arrow,) = saved(page, client)
    assert (arrow["x"], arrow["y"]) == (60, 120)
    assert arrow["w"] == pytest.approx(80, abs=1)
    assert arrow["h"] == pytest.approx(20, abs=1)
    assert arrow["props"]["from"] == "sw"
    expect(at(page, "pfeil").locator("svg polygon")).to_have_count(2)
    # A flip moves the start to another corner and mirrors nothing.
    for label, corner in zip(FLIPS, ("se", "ne"), strict=True):
        button(page, label).click()
        (arrow,) = saved(page, client)
        assert arrow["props"]["from"] == corner
        assert not arrow.get("flipX") and not arrow.get("flipY")
    button(page, "Rand").fill("#0000ff")
    button(page, "Randstärke").fill("2")
    button(page, "Gestrichelt").click()
    drawing = at(page, "pfeil").locator("svg g")
    expect(drawing).to_have_attribute("stroke", "#0000ff")
    expect(drawing).to_have_attribute("stroke-width", "2")
    expect(drawing.locator("line[stroke-dasharray]")).to_have_count(1)
    # A line has no frame to change and no fill: its one Transparenz is the line's own (#129).
    expect(frame(page, "Dreieck")).to_have_count(0)
    expect(slider(page)).to_have_count(1)
    expect(slider(page)).to_be_enabled()


@pytest.mark.parametrize("kind", ["shape", "text"])
def test_the_frame_switch_offers_the_new_shapes(editor, kind):
    client = user()
    look = {"fill": "#ff0000", "stroke": "#0000ff", "strokeWidth": 1, "dash": "dashed"}
    props = {**TEXT, **look} if kind == "text" else {**RECT, "text": "Hallo", **look}
    page = editor(box("a", kind, props, **ROOM), client=client)
    pick(page, "a")
    expect(at(page, "a").locator("svg.outline")).to_have_count(0)
    for label, name, tag in [
        # Dashed, each is a path: its dashes are fitted to its way round (#309).
        ("Dreieck", "triangle", "path"),
        ("Stern", "star", "path"),
        ("Sprechblase", "bubble", "path"),
    ]:
        frame(page, label).click()
        expect(frame(page, label)).to_have_class("on")
        shape = at(page, "a").locator(OUTLINE)
        expect(shape).to_have_count(1)
        assert shape.evaluate("el => el.tagName") == tag
        # The look and the words are the ones it had.
        expect(shape).to_have_attribute("fill", "#ff0000")
        expect(shape).to_have_attribute("stroke", "#0000ff")
        expect(shape).to_have_attribute("stroke-width", "1")
        expect(shape).to_have_attribute("stroke-dasharray", re.compile(r"\d"))
        expect(at(page, "a").locator(".frame")).to_have_text("Hallo")
        (a,) = saved(page, client)
        # A kind picked now takes the inside rule of #128, and the 10 pt floor of a shape the
        # teacher changed (#682), which stays on.
        assert a["props"] == {**props, "kind": name, "inside": True, "floor": True}
    # And back to a box.
    frame(page, "Eckig").click()
    expect(at(page, "a").locator("svg.outline")).to_have_count(0)
    expect(at(page, "a").locator(DASHES)).to_have_attribute("stroke", "#0000ff")


def pixels(locator):
    return Image.open(io.BytesIO(locator.screenshot())).convert("RGB")


def test_a_solid_border_is_the_boxes_own_and_dashes_lie_over_the_fill(editor):
    """I5"""
    look = {**RECT, "fill": "#ffd43b", "strokeWidth": 2, "text": "Hallo", "valign": "top"}
    low = {**ROOM, "y": 140}
    dash = {**look, "dash": "dashed"}
    page = editor(box("a", "shape", look, **ROOM), box("b", "shape", dash, **low))
    solid, dashed = (at(page, name).locator(".frame") for name in "ab")
    expect(solid.locator("svg")).to_have_count(0)
    expect(solid).to_have_css("border-top-style", "none")
    expect(solid).to_have_css("box-shadow", shadow(2))
    expect(dashed.locator(DASHES)).to_have_count(1)
    expect(dashed).to_have_css("background-color", "rgb(255, 212, 59)")
    # In the middle of the top stroke: the first dash, 8 mm long from the corner, then the fill.
    shot = pixels(at(page, "b"))
    row = round(shot.height / ROOM["h"])
    assert shot.getpixel((round(shot.width * 4 / ROOM["w"]), row)) == (34, 34, 34)
    assert shot.getpixel((round(shot.width * 11.5 / ROOM["w"]), row)) == (255, 212, 59)


@pytest.mark.parametrize("w, h, kind", [(2, 2, "rect"), (3, 20, "rounded"), (40, 2.5, "circle")])
def test_a_box_too_small_for_drawn_dashes_keeps_a_border(editor, w, h, kind):
    """A3: the stroke's middle line has no length there, and a drawn one would show nothing."""
    look = {**RECT, "kind": kind, "strokeWidth": 3, "dash": "dashed"}
    page = editor(box("a", "shape", look, x=50, y=50, w=w, h=h))
    frame = at(page, "a").locator(".frame")
    expect(frame.locator("svg")).to_have_count(0)
    expect(frame).to_have_css("border-top-style", "dashed")
    expect(frame).to_have_css("border-top-color", "rgb(34, 34, 34)")


LINES = """els => els.map((el) => {
    const box = el.getBoundingClientRect();
    const words = document.createRange();
    words.selectNodeContents(el.querySelector("p"));
    const lines = [...words.getClientRects()];
    return lines.flatMap((l) => [l.x - box.x, l.y - box.y, l.width, l.height]);
})"""


@pytest.mark.parametrize("width", [0.5, 2, 3])
def test_a_text_in_a_dashed_box_prints_where_a_solid_border_has_it(browser, server, width):
    """I5"""
    client = user()
    words = "Der Igel sucht im Herbst nach Futter und baut sich ein Nest aus Laub."
    look = {**TEXT, "text": words, "stroke": "#222222", "strokeWidth": width}
    low = {**ROOM, "y": 140}
    blocks = [box("a", "text", look, **ROOM), box("b", "text", {**look, "dash": "dashed"}, **low)]
    mine = sheet(client, blocks)["id"]
    # The page the PDF is printed from, at one pixel to a pixel as Chromium prints it. A border is
    # rounded down to whole pixels there, and a narrower box could break a line elsewhere.
    page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    solid, dashed = page.locator(".frame").evaluate_all(LINES)
    page.close()
    # Each line of the text, from the box's corner: more than one, and the same in both.
    assert len(solid) > 4
    assert dashed == pytest.approx(solid, abs=0.01)


@pytest.mark.parametrize("kind", ["rect", "rounded", "circle", "text"])
def test_dashes_grow_with_the_zoom_and_are_the_same_in_a_thumbnail(editor, kind):
    """I6"""
    look = {**RECT, "strokeWidth": 2, "dash": "dashed"}
    props = {**TEXT, **look} if kind == "text" else {**look, "kind": kind}
    # With the panel Seiten open.
    page = editor(box("a", "text" if kind == "text" else "shape", props, **ROOM), theme="")
    stroke = at(page, "a").locator(DASHES)
    wide = "el.closest('.sheet, .paper').getBoundingClientRect().width"
    mm = f"el => el.getScreenCTM().a * 210 / {wide}"
    small = page.locator(f".pages {DASHES}")
    expect(small).to_have_attribute("stroke-dasharray", stroke.get_attribute("stroke-dasharray"))
    # A mm of the stroke is a mm of its page, on the desk and in the thumbnail.
    assert stroke.evaluate(mm) == pytest.approx(1, abs=0.001)
    assert small.evaluate(mm) == pytest.approx(1, abs=0.001)
    px = page.locator(".sheet.on").bounding_box()["width"]
    before = pixels(at(page, "a"))
    page.get_by_label("Größer", exact=True).first.click()
    page.wait_for_function(
        "(w) => document.querySelector('.sheet.on').getBoundingClientRect().width > w - 2",
        arg=px * 1.25,
    )
    # The larger picture, made as small as the first, has each dash where the first has it.
    after = pixels(at(page, "a")).resize(before.size)
    assert diff(as_png(before), as_png(after))[0] < 0.01
    # And a pattern that kept its size on the screen would not: the first, cut out of the larger.
    kept = pixels(at(page, "a")).crop((0, 0, *before.size))
    assert diff(as_png(before), as_png(kept))[0] > 0.01
