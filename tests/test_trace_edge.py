"""Issue #494, a regression of #488: no ink of a dotted or outlined first letter is cut at the left.

A trace text of the look "dotted" or "outline" reaches past the left edge of its block, and the
block cuts it there. The tests lift every cut and compare the picture: a cut that hid ink shows as
a change.
"""

import io
import math
import re
from contextlib import contextmanager

import pytest
from PIL import Image, ImageChops
from pixels import HIDE
from playwright.sync_api import expect
from ui import RECT, RULING, TABLE, TEXT, at, box, sheet, user

from blattwerk import pdf

FONTS = ["andika", "nord", "sued", "grund", "urff", "va", "sas", "la"]
START = "Übung jagt Öl"
# Lifts every cut that hides ink: of the Lineatur, the frame, the paragraph and the table cell.
LIFT = (
    ".block .written, .frame, .frame p, .frame .rich, .table > div "
    "{ overflow: visible !important; clip-path: none !important; }"
)


def clip_of(block, width_mm):
    """The picture of a block's left edge: 3 mm before it, 15 mm after, and 3 mm above and below."""
    b = block.bounding_box()
    mm = b["width"] / width_mm
    return {
        "x": b["x"] - 3 * mm,
        "y": b["y"] - 3 * mm,
        "width": 18 * mm,
        "height": b["height"] + 6 * mm,
    }


def whole_clip(block, width_mm):
    """The picture of a whole block: 3 mm around it on every side."""
    b = block.bounding_box()
    mm = b["width"] / width_mm
    return {
        "x": b["x"] - 3 * mm,
        "y": b["y"] - 3 * mm,
        "width": b["width"] + 6 * mm,
        "height": b["height"] + 6 * mm,
    }


def changed_whole(before, after):
    """The pixels that differ by more than 40 in red, green or blue, anywhere in the picture."""
    one = Image.open(io.BytesIO(before)).convert("RGB")
    two = Image.open(io.BytesIO(after)).convert("RGB")
    red, green, blue = ImageChops.difference(one, two).split()
    most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return most.point(lambda v: 255 if v > 40 else 0).histogram()[255]


def changed(before, after):
    """The pixels that differ by more than 40 in red, green or blue, in the clip's band at the left.

    The band runs from 3 mm before a block's edge to 5 mm past it. The clip is 18 mm wide and the
    edge lies 3 mm in. Past 5 mm a cut has no first letter to hide: a fringe at the top of a shape's
    text differs there, and it is no cut at the left (#487).
    """
    one = Image.open(io.BytesIO(before)).convert("RGB")
    two = Image.open(io.BytesIO(after)).convert("RGB")
    band = round(one.width * 8 / 18)
    one, two = one.crop((0, 0, band, one.height)), two.crop((0, 0, band, two.height))
    red, green, blue = ImageChops.difference(one, two).split()
    most = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return most.point(lambda v: 255 if v > 40 else 0).histogram()[255]


# The editor draws a Lineatur's text in a field, and a field cuts at its own edge whatever its
# overflow says. So its cut is lifted by moving the edge: 40 px to the left, with a padding that
# keeps the letters where they are. Only for a Lineatur with no house, whose padding is its indent.
FIELD = (
    ".block textarea.written { left: -40px !important; width: calc(100% + 40px) !important; "
    "padding-left: 40px !important; box-sizing: border-box !important; }"
)


def lifted(page, items, field=False):
    """How many pixels each block's left edge gains once every cut is lifted: {name: count}.

    `items` maps a name to its block's locator and its width in mm. `field` lifts the cut of the
    editor's field too.
    """
    before = {name: page.screenshot(clip=clip_of(el, w)) for name, (el, w) in items.items()}
    page.add_style_tag(content=LIFT + (FIELD if field else ""))
    return {
        name: changed(before[name], page.screenshot(clip=clip_of(el, w)))
        for name, (el, w) in items.items()
    }


@contextmanager
def print_page(browser, server, client, blocks):
    """The print page of a sheet of these blocks, drawn and ready, in a window of its own."""
    mine = sheet(client, blocks)["id"]
    context = browser.new_context(viewport={"width": 1400, "height": 1400}, device_scale_factor=2)
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page = context.new_page()
    page.set_extra_http_headers({"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    page.add_style_tag(content=HIDE)
    try:
        yield page
    finally:
        context.close()


def dotted(kind):
    """A dotted text of Urff, 30 pt, or a Lineatur 1 of it, 30 mm from the page's left edge."""
    if kind == "text":
        props = {
            **TEXT,
            "text": START,
            "size": 30,
            "font": "urff",
            "trace": "dotted",
            "align": "left",
        }
        return box("a", "text", props, x=30, y=20, w=150, h=30)
    props = {**RULING, "kind": "l1", "font": "urff", "text": START, "trace": "dotted"}
    return box("a", "ruling", props, x=30, y=20, w=150, h=40)


def four(font, look):
    """A text, a shape, a table and a Lineatur 1 of one font and look, one below another."""
    text = "jÄgf Übung"
    return [
        box(
            "text",
            "text",
            {**TEXT, "text": text, "size": 30, "font": font, "trace": look, "align": "left"},
            x=30,
            y=20,
            w=150,
            h=30,
        ),
        box(
            "shape",
            "shape",
            {**RECT, "text": text, "size": 30, "font": font, "trace": look, "align": "left"},
            x=30,
            y=60,
            w=150,
            h=30,
        ),
        box(
            "table",
            "table",
            {
                **TABLE,
                "cells": [[text, "Ü"]],
                "cols": [1, 1],
                "size": 20,
                "font": font,
                "trace": look,
                "align": "left",
            },
            x=30,
            y=100,
            w=150,
            h=20,
        ),
        box(
            "ruling",
            "ruling",
            {**RULING, "kind": "l1", "font": font, "text": text, "trace": look},
            x=30,
            y=130,
            w=150,
            h=40,
        ),
    ]


NAMES = ["text", "shape", "table", "ruling"]


@pytest.mark.parametrize("kind", ["text", "ruling"])
def test_the_start_dot_of_a_dotted_first_letter_is_whole(editor, kind):
    page = editor(dotted(kind))
    page.add_style_tag(content=HIDE)
    assert lifted(page, {"a": (at(page, "a"), 150)}, field=True) == {"a": 0}


@pytest.mark.parametrize("kind", ["text", "ruling"])
def test_the_start_dot_of_a_dotted_first_letter_is_whole_in_print(browser, server, kind):
    client = user()
    with print_page(browser, server, client, [dotted(kind)]) as page:
        assert lifted(page, {"a": (page.locator(".block"), 150)}) == {"a": 0}


@pytest.mark.parametrize("font", FONTS)
def test_no_ink_of_an_outlined_first_letter_is_cut_at_the_left(browser, server, font):
    client = user()
    with print_page(browser, server, client, four(font, "outline")) as page:
        items = {name: (page.locator(".block").nth(i), 150) for i, name in enumerate(NAMES)}
        gained = lifted(page, items)
    cut = {name: count for name, count in gained.items() if count}
    assert not cut, (font, cut)


@pytest.mark.parametrize("font", ["la", "urff"])
def test_no_ink_of_an_outlined_first_letter_is_cut_at_the_left_on_screen(editor, font):
    page = editor(*four(font, "outline"))
    page.add_style_tag(content=HIDE)
    items = {name: (at(page, name), 150) for name in NAMES}
    gained = lifted(page, items, field=True)
    cut = {name: count for name, count in gained.items() if count}
    assert not cut, (font, cut)


# The first character's left edge, relative to its block: a DOM range over the first letter.
FIRST_LEFT = """(blocks) => blocks.map((block) => {
    const node = block.querySelector(".written").firstChild;
    const range = document.createRange();
    range.setStart(node, 0);
    range.setEnd(node, 1);
    return range.getBoundingClientRect().left - block.getBoundingClientRect().left;
})"""
# The same on the editor's field: the text starts at the field's left edge plus its padding. The
# sheet may be zoomed: the rect is scaled, the padding is not, so the padding takes the zoom.
FIELD_LEFT = """(fields) => fields.map((el) => {
    const zoom = el.getBoundingClientRect().width / el.offsetWidth;
    return el.getBoundingClientRect().left + zoom * parseFloat(getComputedStyle(el).paddingLeft);
})"""


def three_rulings():
    """Three Lineaturen of Urff with one text: grey, outline and dotted, one below another."""
    looks = {"grey": True, "outline": "outline", "dotted": "dotted"}
    return [
        box(
            name,
            "ruling",
            {**RULING, "kind": "l1", "font": "urff", "text": START, "trace": look},
            x=30,
            y=20 + 50 * i,
            w=150,
            h=40,
        )
        for i, (name, look) in enumerate(looks.items())
    ]


def test_a_dotted_or_outlined_text_on_a_lineatur_starts_where_the_grey_one_does(
    browser, server, editor
):
    client = user()
    with print_page(browser, server, client, three_rulings()) as page:
        starts = page.locator(".block").evaluate_all(FIRST_LEFT)
    assert max(starts) - min(starts) <= 0.01, starts

    page = editor(*three_rulings())
    lefts = page.locator(".block textarea.written").evaluate_all(FIELD_LEFT)
    assert max(lefts) - min(lefts) <= 0.01, lefts


def test_the_open_field_shows_a_dotted_first_letter_whole(editor):
    page = editor(dotted("ruling"))
    page.add_style_tag(content=HIDE)
    at(page, "a").dblclick()
    expect(at(page, "a").locator("textarea.written")).to_be_focused()
    assert lifted(page, {"a": (at(page, "a"), 150)}, field=True) == {"a": 0}


# The ink of the first letter and the house's right edge, in px. An outline's stroke takes half its
# width, .035 em, from the ink. The house's stroke is half its width too.
INK_OF_FIRST = """async (block, outline) => {
    const el = block.querySelector(".written");
    const style = getComputedStyle(el);
    const font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    await document.fonts.load(font);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = font;
    const m = ctx.measureText(el.textContent[0]);
    const shade = outline ? 0.035 * parseFloat(style.fontSize) : 0;
    const start = el.getBoundingClientRect().left + parseFloat(style.paddingLeft);
    const ink = start - m.actualBoundingBoxLeft - shade;
    const svg = block.querySelector("svg.ruling");
    const roof = block.querySelector("g.house polygon.roof");
    const scale = svg.getScreenCTM().a;
    const half = (parseFloat(getComputedStyle(roof).strokeWidth) * scale) / 2;
    const house = block.querySelector("g.house").getBoundingClientRect().right + half;
    return [ink, house];
}"""


@pytest.mark.parametrize("look,font", [("dotted", "urff"), ("outline", "urff"), ("outline", "la")])
def test_with_a_house_a_dotted_or_outlined_first_letter_is_whole_and_clear_of_the_house(
    browser, server, editor, look, font
):
    block = box(
        "a",
        "ruling",
        {**RULING, "kind": "l1", "house": True, "font": font, "text": "Übung jagt", "trace": look},
        x=30,
        y=20,
        w=150,
        h=40,
    )
    page = editor(block)
    page.add_style_tag(content=HIDE)
    assert lifted(page, {"a": (at(page, "a"), 150)}) == {"a": 0}

    with print_page(browser, server, user(), [block]) as printed:
        ink, house = printed.locator(".block").evaluate(INK_OF_FIRST, look == "outline")
    assert math.floor(ink) >= math.ceil(house), (look, font, ink, house)


# The fonts with a dotted cut: the dotted look is drawn grey in the others.
DOTTED_FONTS = ["urff"]


def lifted_whole(page, items, field=False):
    """How many pixels differ in each whole block once every cut is lifted: {name: count}."""
    before = {name: page.screenshot(clip=whole_clip(el, w)) for name, (el, w) in items.items()}
    page.add_style_tag(content=LIFT + (FIELD if field else ""))
    return {
        name: changed_whole(before[name], page.screenshot(clip=whole_clip(el, w)))
        for name, (el, w) in items.items()
    }


@pytest.mark.parametrize("font", FONTS)
def test_no_ink_of_an_outlined_text_is_cut_above_or_below(browser, server, font):
    client = user()
    with print_page(browser, server, client, four(font, "outline")) as page:
        items = {name: (page.locator(".block").nth(i), 150) for i, name in enumerate(NAMES)}
        gained = lifted_whole(page, items)
    cut = {name: count for name, count in gained.items() if count}
    assert not cut, (font, cut)


@pytest.mark.parametrize("font", DOTTED_FONTS)
def test_no_ink_of_a_dotted_text_is_cut_above_or_below(browser, server, font):
    client = user()
    with print_page(browser, server, client, four(font, "dotted")) as page:
        items = {name: (page.locator(".block").nth(i), 150) for i, name in enumerate(NAMES)}
        gained = lifted_whole(page, items)
    cut = {name: count for name, count in gained.items() if count}
    assert not cut, (font, cut)


@pytest.mark.parametrize("font", ["va", "urff"])
def test_no_ink_of_an_outlined_text_is_cut_above_or_below_on_screen(editor, font):
    look = "outline" if font == "va" else "dotted"
    page = editor(*four(font, look))
    page.add_style_tag(content=HIDE)
    items = {name: (at(page, name), 150) for name in NAMES}
    gained = lifted_whole(page, items, field=True)
    cut = {name: count for name, count in gained.items() if count}
    assert not cut, (font, cut)


def test_an_outlined_va_text_in_a_shape_loses_no_ink_above(browser, server):
    client = user()
    with print_page(browser, server, client, [four("va", "outline")[1]]) as page:
        gained = lifted_whole(page, {"shape": (page.locator(".block"), 150)})
    assert gained == {"shape": 0}, gained


CUT = """(frames) => frames.map((f) => ({
    clip: getComputedStyle(f).clipPath,
    up: f.style.getPropertyValue("--ink-up"),
}))"""


def test_a_plain_and_a_grey_text_keep_their_cut(browser, server):
    """The fringe is for the outline and the dotted look: other texts keep the pixel they had."""
    text = {**TEXT, "text": "jÄgf Übung", "size": 30, "font": "va", "align": "left"}
    blocks = [
        box("plain", "text", text, x=30, y=20, w=150, h=30),
        box("grey", "text", {**text, "trace": True}, x=30, y=60, w=150, h=30),
        box("shape", "shape", {**RECT, **text}, x=30, y=100, w=150, h=30),
    ]
    with print_page(browser, server, user(), blocks) as page:
        cuts = page.locator(".block .frame").evaluate_all(CUT)
    for cut in cuts:
        assert cut["clip"].startswith("inset("), cut
        assert re.fullmatch(r"calc\([\d.]+em \+ 1px\)", cut["up"]), cut


def test_a_grey_and_a_plain_lineatur_keep_their_style(editor):
    """The mend touches the outline and the dotted look only: other Lineaturen draw as they did."""
    page = editor(
        box(
            "plain",
            "ruling",
            {**RULING, "kind": "l1", "font": "urff", "text": START},
            x=30,
            y=20,
            w=150,
            h=40,
        ),
        box(
            "grey",
            "ruling",
            {**RULING, "kind": "l1", "font": "urff", "text": START, "trace": True},
            x=30,
            y=80,
            w=150,
            h=40,
        ),
    )
    for name in ("plain", "grey"):
        field = at(page, name).locator("textarea.written")
        inline = field.evaluate(
            "el => ({ left: el.style.left, width: el.style.width, padding: el.style.paddingLeft })"
        )
        assert inline == {"left": "", "width": "", "padding": ""}, name
