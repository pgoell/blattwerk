"""Triangle, star, speech bubble, double arrow and a see-through fill, in Chromium."""

import io
import re

import pytest
from PIL import Image
from pixels import as_png, diff
from playwright.sync_api import expect
from test_border import shadow
from ui import (
    FIELD,
    LINE,
    RECT,
    TEXT,
    at,
    box,
    centre,
    drag,
    drawer,
    expect_picked,
    pick,
    saved,
    sheet,
    unpick,
    user,
)

from blattwerk import pdf

FLIPS = ("Horizontal spiegeln", "Vertikal spiegeln")
RED = {**RECT, "fill": "#ff0000"}
# A shape of 60 by 40 mm with room around it.
ROOM = {"x": 75, "y": 80, "w": 60, "h": 40}
# The one element that draws a triangle, a star or a bubble.
OUTLINE = "svg.outline > *"
# The one that draws the dashes of a box's border.
DASHES = "svg.dashes > *"
CLEAR = "rgba(0, 0, 0, 0)"


def insert(page, label):
    """The button of the insert bar that makes a new shape."""
    return page.locator(".insert").get_by_label(label, exact=True)


def button(page, label):
    return page.get_by_label(label, exact=True)


def frame(page, label):
    """A button of the switch between the frames."""
    return page.locator(".panel .seg").get_by_role("button", name=label, exact=True)


def slider(page):
    return page.get_by_label("Transparenz", exact=True)


def slide(page, share):
    """Drags the slider from its left end to this share of its width. Gives what it then shows."""
    place = slider(page).bounding_box()
    y = place["y"] + place["height"] / 2
    drag(page, (place["x"] + 2, y), (place["x"] + place["width"] * share, y))
    return int(slider(page).input_value())


def numbers(text):
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", text)]


def alpha(locator):
    """How solid the background is that the browser draws: 1 with no alpha."""
    parts = numbers(locator.evaluate("el => getComputedStyle(el).backgroundColor"))
    return parts[3] if len(parts) > 3 else 1


def drawn(page, name):
    """How the block's outline lies on the screen across and down: -1 when mirrored, else 1."""
    ctm = (
        at(page, name).locator(OUTLINE).evaluate("el => [el.getScreenCTM().a, el.getScreenCTM().d]")
    )
    return tuple(1 if n > 0 else -1 for n in ctm)


def expect_readable(page, name):
    """Nothing the text stands in is mirrored."""
    assert "scale" not in at(page, name).evaluate("el => el.style.transform")
    expect(at(page, name).locator(".frame")).to_have_css("transform", "none")
    expect(at(page, name).locator(".frame p")).to_have_css("transform", "none")


def inside(page, name, x, y):
    """Whether the point, as shares of the box, lies in what the block's outline fills."""
    return (
        at(page, name)
        .locator(OUTLINE)
        .evaluate(
            """(el, [x, y]) => {
            const { width, height } = el.ownerSVGElement.viewBox.baseVal;
            return el.isPointInFill(new DOMPoint(x * width, y * height));
        }""",
            [x, y],
        )
    )


def expect_no_box(page):
    """The frame of the one block draws no box of its own: the outline is all there is."""
    box = page.locator(".block .frame")
    expect(box).to_have_css("background-color", CLEAR)
    expect(box).to_have_css("border-top-width", "0px")
    expect(box).to_have_css("box-shadow", "none")


def test_the_bar_inserts_a_triangle(editor):
    client = user()
    page = editor(client=client)
    insert(page, "Dreieck").click()
    expect(page.locator(".block.sel")).to_have_count(1)
    shape = page.locator(f".block {OUTLINE}")
    expect(shape).to_have_count(1)
    assert shape.evaluate("el => el.tagName") == "polygon"
    points = numbers(shape.get_attribute("points"))
    corners = sorted(zip(points[::2], points[1::2], strict=True), key=lambda p: p[1])
    assert len(corners) == 3
    # The tip stands over the middle of the base, which runs along the bottom.
    assert corners[0][0] == pytest.approx(20, abs=0.01)
    assert corners[1][1] == corners[2][1] > 35
    expect_no_box(page)
    (a,) = saved(page, client)
    assert (a["type"], a["props"]["kind"], a["w"], a["h"]) == ("shape", "triangle", 40, 40)


def test_the_bar_inserts_a_star(editor):
    client = user()
    page = editor(client=client)
    insert(page, "Stern").click()
    shape = page.locator(f".block.sel {OUTLINE}")
    expect(shape).to_have_count(1)
    assert shape.evaluate("el => el.tagName") == "polygon"
    # Five points and the five corners between them.
    assert len(numbers(shape.get_attribute("points"))) == 20
    expect_no_box(page)
    (a,) = saved(page, client)
    assert (a["props"]["kind"], a["w"], a["h"]) == ("star", 40, 40)
    # The top point reaches the upper edge, and between two points the star is hollow.
    assert inside(page, a["id"], 0.5, 0.1)
    assert not inside(page, a["id"], 0.2, 0.1)


def test_the_bar_inserts_a_speech_bubble(editor):
    client = user()
    page = editor(client=client)
    insert(page, "Sprechblase").click()
    shape = page.locator(f".block.sel {OUTLINE}")
    expect(shape).to_have_count(1)
    assert shape.evaluate("el => el.tagName") == "path"
    # Its corners are round.
    assert shape.get_attribute("d").count("A") == 4
    expect_no_box(page)
    (a,) = saved(page, client)
    assert (a["props"]["kind"], a["w"], a["h"]) == ("bubble", 60, 40)
    # The tail hangs under the bubble on the left, and the bubble itself ends above it.
    assert inside(page, a["id"], 0.5, 0.4)
    assert inside(page, a["id"], 0.27, 0.85)
    assert not inside(page, a["id"], 0.73, 0.85)


def test_the_bar_inserts_an_arrow_with_two_heads(editor):
    client = user()
    page = editor(client=client)
    insert(page, "Pfeil").click()
    expect(page.locator(".block.sel svg polygon")).to_have_count(1)
    insert(page, "Doppelpfeil").click()
    expect(page.locator(".block")).to_have_count(2)
    expect(page.locator(".block.sel svg polygon")).to_have_count(2)
    double = saved(page, client)[1]
    assert (double["props"]["kind"], double["w"], double["h"]) == ("double", 60, 0)
    # One head lies at each end of the line.
    heads = [
        numbers(head.get_attribute("points"))[0]
        for head in page.locator(".block.sel svg polygon").all()
    ]
    assert sorted(heads) == [0, 60]


def test_the_slider_makes_a_fill_see_through(editor):
    client = user()
    page = editor(
        box("a", "shape", {**RED, "text": "Hallo"}, **ROOM),
        # Below "a": a text that ends on its middle line takes the click there in WebKit.
        box("b", "text", {**TEXT, "fill": "#00ff00", "stroke": "#222222"}, z=2, y=140),
        box("c", "shape", {**RED, "kind": "star"}, z=3, x=20, y=200, w=40, h=40),
        client=client,
    )
    pick(page, "a")
    expect(slider(page)).to_have_value("0")
    assert alpha(at(page, "a").locator(".frame")) == 1
    slider(page).fill("75")
    filled = at(page, "a").locator(".frame")
    expect(filled).to_have_css("background-color", "rgba(255, 0, 0, 0.25)")
    # The text and the border stay solid.
    expect(filled).to_have_css("opacity", "1")
    expect(filled).to_have_css("box-shadow", shadow(0.5))
    assert "rgba" not in filled.locator("p").evaluate("el => getComputedStyle(el).color")
    pick(page, "b")
    slider(page).fill("55")
    expect(at(page, "b").locator(".frame")).to_have_css("background-color", "rgba(0, 255, 0, 0.45)")
    expect(at(page, "b").locator(".frame")).to_have_css("box-shadow", shadow(0.5))
    pick(page, "c")
    slider(page).fill("100")
    star = at(page, "c").locator(OUTLINE)
    expect(star).to_have_attribute("fill-opacity", "0")
    expect(star).to_have_attribute("fill", "#ff0000")
    assert star.get_attribute("stroke-opacity") is None
    # A fill nobody sees is still a fill: "Keine Füllung" is a state of its own.
    expect(page.get_by_role("button", name="Keine Füllung")).to_be_enabled()
    a, b, c = saved(page, client)
    # What is stored has two places and no more.
    assert (a["props"]["opacity"], b["props"]["opacity"], c["props"]["opacity"]) == (0.25, 0.45, 0)
    assert (a["props"]["fill"], a["props"]["text"], a["props"]["stroke"]) == (
        "#ff0000",
        "Hallo",
        "#222222",
    )
    assert c["props"]["fill"] == "#ff0000"
    page.get_by_role("button", name="Keine Füllung").click()
    c = saved(page, client)[2]
    assert c["props"] == {**RED, "kind": "star", "fill": "none"}


def test_a_fill_after_none_is_solid(editor):
    client = user()
    page = editor(
        box("a", "shape", {**RED, "opacity": 0.25}, **ROOM),
        box("b", "shape", RED, z=2, x=20, y=200, w=40, h=20),
        client=client,
    )
    # Another colour for a fill keeps how far it lets through.
    pick(page, "a")
    button(page, "Füllung").fill("#0000ff")
    expect(at(page, "a").locator(".frame")).to_have_css("background-color", "rgba(0, 0, 255, 0.25)")
    # "Keine Füllung" forgets it: the next fill is solid, as in PowerPoint.
    pick(page, "b")
    slider(page).fill("100")
    page.get_by_role("button", name="Keine Füllung").click()
    expect(slider(page)).to_be_disabled()
    expect(slider(page)).to_have_value("0")
    button(page, "Füllung").fill("#0000ff")
    expect(at(page, "b").locator(".frame")).to_have_css("background-color", "rgb(0, 0, 255)")
    expect(slider(page)).to_have_value("0")
    a, b = saved(page, client)
    assert (a["props"]["fill"], a["props"]["opacity"]) == ("#0000ff", 0.25)
    assert b["props"] == {**RED, "fill": "#0000ff"}


def test_a_text_as_a_bubble_flips(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "stroke": "#222222"}, **ROOM, angle=30),
        box("b", "text", {**TEXT, "stroke": "#222222"}, z=2, x=20, y=200, w=60, h=20),
        client=client,
    )
    pick(page, "a")
    # A text in a box looks the same either way: it has nothing to flip.
    for label in FLIPS:
        expect(button(page, label)).to_be_disabled()
    frame(page, "Sprechblase").click()
    assert drawn(page, "a") == (1, 1)
    for label in FLIPS:
        expect(button(page, label)).to_be_enabled()
    button(page, FLIPS[0]).click()
    # The outline mirrors and the angle with it, as a shape's do. The words read as before.
    assert drawn(page, "a") == (-1, 1)
    expect(at(page, "a").locator(".frame")).to_have_css("transform", "none")
    expect(at(page, "a").locator(".frame p")).to_have_css("transform", "none")
    expect(at(page, "a").locator(".frame")).to_have_text("Hallo")
    a = saved(page, client)[0]
    assert (a["type"], a["angle"], a.get("flipX"), a.get("flipY")) == ("text", 330, True, None)
    button(page, FLIPS[1]).click()
    assert drawn(page, "a") == (-1, -1)
    a = saved(page, client)[0]
    assert (a["angle"], a["flipX"], a["flipY"]) == (30, True, True)
    # With a plain text beside it the flip is for the bubble alone.
    pick(page, "a", "b")
    button(page, FLIPS[0]).click()
    a, b = saved(page, client)
    assert (a["angle"], a["flipX"]) == (330, False)
    assert (b.get("angle"), b.get("flipX")) == (None, None)
    unpick(page)
    pick(page, "b")
    for label in FLIPS:
        expect(button(page, label)).to_be_disabled()


@pytest.mark.parametrize("size", [(1024, 768), (768, 1024)])
def test_a_finger_inserts_a_shape_and_moves_the_slider(editor, size):
    client = user()
    page = editor(box("a", "shape", RED, **ROOM), client=client, touch=True)
    page.set_viewport_size({"width": size[0], "height": size[1]})
    upright = size[0] < size[1]
    if upright:
        # Held upright the shapes stand in the bar at the lower edge, which lies inside the window
        # and scrolls sideways.
        expect(page.locator(".dock .shapes .ib")).to_have_count(9)
        bar = page.locator(".dock").bounding_box()
        assert bar["x"] >= 0
        assert bar["x"] + bar["width"] <= size[0]
        assert bar["y"] + bar["height"] <= size[1]
        page.locator(".dock").get_by_label("Stern", exact=True).tap()
    else:
        # Every shape's button lies inside the bar, and nothing in the bar runs out of it sideways.
        bar = page.locator(".insert").bounding_box()
        buttons = page.locator(".insert .shapes .ib")
        expect(buttons).to_have_count(9)
        for each in buttons.all():
            place = each.bounding_box()
            assert place["x"] >= bar["x"]
            assert place["x"] + place["width"] <= bar["x"] + bar["width"]
            assert place["y"] + place["height"] <= bar["y"] + bar["height"]
        for css in (".insert .shapes", ".insert", ".left"):
            assert page.locator(css).evaluate("el => el.scrollWidth <= el.clientWidth")
        insert(page, "Stern").tap()
    expect(page.locator(".block")).to_have_count(2)
    expect(page.locator(f".block.sel {OUTLINE}")).to_have_count(1)
    # Low on the block: on the narrow window the star lies right above it, and the finger's area of
    # the star's lower handle reaches to 2 px above the block's middle. WebKit gives a tap that
    # near to the handle.
    low = at(page, "a").bounding_box()
    at(page, "a").tap(position={"x": low["width"] / 2, "y": low["height"] - 6})
    expect_picked(page, "a")
    if upright:
        drawer(page, "right")
    place = slider(page).bounding_box()
    slider(page).tap(position={"x": place["width"] / 2, "y": place["height"] / 2})
    expect(slider(page)).not_to_have_value("0")
    percent = int(slider(page).input_value())
    assert abs(percent - 50) <= 5
    assert saved(page, client)[0]["props"]["opacity"] == pytest.approx(1 - percent / 100)
    assert alpha(at(page, "a").locator(".frame")) == pytest.approx(1 - percent / 100, abs=0.01)


@pytest.mark.parametrize("label", ["Dreieck", "Stern", "Sprechblase"])
def test_a_new_shape_holds_text(editor, label):
    client = user()
    page = editor(client=client)
    insert(page, label).click()
    expect(page.locator(".block.sel")).to_have_count(1)
    page.keyboard.press("Enter")
    page.keyboard.type("Hallo")
    expect(page.locator(FIELD)).to_have_text("Hallo")
    expect(page.locator(f"{FIELD} p")).to_have_css("text-align", "center")
    page.keyboard.press("Escape")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect(page.locator(".block .frame")).to_have_text("Hallo")
    # The words stand inside the shape, about its middle.
    block, words = (page.locator(css).bounding_box() for css in (".block", ".block .frame p"))
    assert words["x"] + words["width"] / 2 == pytest.approx(block["x"] + block["width"] / 2, abs=2)
    assert words["y"] > block["y"] + block["height"] / 5
    assert words["y"] + words["height"] < block["y"] + block["height"] * 0.9
    (a,) = saved(page, client)
    assert a["props"]["text"] == "Hallo"


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


def test_undo_takes_back_a_whole_slide(editor):
    page = editor(box("a", "shape", RED, **ROOM), box("b", "shape", RECT, z=2, y=200))
    pick(page, "a")
    first = slide(page, 0.4)
    assert abs(first - 40) <= 5
    # The drag went through many values and is one step: one undo takes it all back.
    page.keyboard.press("Control+z")
    expect(slider(page)).to_have_value("0")
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    page.keyboard.press("Control+y")
    expect(slider(page)).to_have_value(str(first))
    # A second drag is a step of its own.
    second = slide(page, 0.8)
    assert second > first + 20
    page.keyboard.press("Control+z")
    expect(slider(page)).to_have_value(str(first))
    assert alpha(at(page, "a").locator(".frame")) == pytest.approx(1 - first / 100, abs=0.01)
    # With no fill there is nothing to see through.
    expect(slider(page)).to_be_enabled()
    page.get_by_role("button", name="Keine Füllung").click()
    expect(slider(page)).to_be_disabled()
    pick(page, "b")
    expect(slider(page)).to_be_disabled()


def test_the_slider_goes_to_all_selected(editor):
    client = user()
    page = editor(
        box("a", "shape", {**RED, "opacity": 0.25}, x=20, y=40, w=40, h=30),
        box("b", "text", {**TEXT, "fill": "#00ff00"}, z=2),
        box("c", "shape", {**RED, "kind": "triangle"}, z=3, x=20, y=200, w=40, h=40),
        box("d", "shape", RED, z=4, x=120, y=200, w=40, h=20),
        client=client,
    )
    pick(page, "a", "b", "c")
    # The first one's shows.
    expect(slider(page)).to_have_value("75")
    slider(page).fill("50")
    a, b, c, d = saved(page, client)
    assert [x["props"]["opacity"] for x in (a, b, c)] == [0.5, 0.5, 0.5]
    # What is not selected stays as it was.
    assert "opacity" not in d["props"]
    expect(at(page, "a").locator(".frame")).to_have_css("background-color", "rgba(255, 0, 0, 0.5)")
    expect(at(page, "b").locator(".frame")).to_have_css("background-color", "rgba(0, 255, 0, 0.5)")
    expect(at(page, "c").locator(OUTLINE)).to_have_attribute("fill-opacity", "0.5")
    # All of them at once are one step.
    page.keyboard.press("Control+z")
    expect(at(page, "c").locator(OUTLINE)).to_have_attribute("fill-opacity", "1")
    expect(slider(page)).to_have_value("75")


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
    # A line has no frame to change and no fill to see through.
    expect(frame(page, "Dreieck")).to_have_count(0)
    expect(slider(page)).to_be_disabled()


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
        assert a["props"] == {**props, "kind": name}
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
