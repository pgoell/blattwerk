"""Issue #76: trace text (Nachspurtext) looks, grey, outline and dotted, and a fading of each.

A text, a shape, a table, a Lineatur and a Karo take `trace` ("grey", "outline", "dotted") and
`fade` ("row", "rows") on their props. Which element owns the look, and how each look is drawn,
is the contract in the feature's notes; the tests read it off the page and off the PDF.
"""

import io
import re

import httpx
import pytest
from PIL import Image
from pixels import over, screen_and_print
from playwright.sync_api import expect
from ui import RECT, RULING, TABLE, TEXT, at, block, box, pick, saved, sheet, unpick, user

FONTS = ["andika", "nord", "sued", "grund", "urff", "va", "sas", "la"]
GREY = "rgb(170, 170, 170)"
WHITE = "rgb(255, 255, 255)"
INK = "#222222"

# The computed styles of a text element, read at once.
STYLE = """(el) => {
    const s = getComputedStyle(el);
    return {
        color: s.color,
        fill: s.webkitTextFillColor,
        stroke: s.webkitTextStrokeWidth,
        strokeColor: s.webkitTextStrokeColor,
        paint: s.paintOrder,
        blend: s.mixBlendMode,
        family: s.fontFamily,
        weight: s.fontWeight,
        style: s.fontStyle,
        mask: s.maskImage || s.webkitMaskImage || "none",
    };
}"""


def place(name, kind, props, **more):
    """A block with a name and a place of its own, for a sheet that holds many."""
    return {**block(kind, 0, 20, props), "id": name, **more}


def build(kind, props):
    """The blocks of one kind with the look, and the owner and letters elements in block "a"."""
    if kind == "text":
        blocks = [box("a", "text", {**TEXT, "text": "Hallo", **props}, w=120, h=40)]
        return blocks, ".frame", ".frame > p, .frame .rich"
    if kind == "shape":
        blocks = [box("a", "shape", {**RECT, "text": "Hallo", **props}, w=120, h=40)]
        return blocks, ".frame", ".frame > p, .frame .rich"
    if kind == "table":
        blocks = [box("a", "table", {**TABLE, **props}, w=120, h=60)]
        return blocks, ".table", ".table p"
    if kind == "ruling":
        blocks = [
            box("a", "ruling", {**RULING, "kind": "l1", "text": "Hallo", **props}, w=120, h=40)
        ]
        return blocks, "p.written", "p.written"
    if kind == "karo":
        blocks = [
            box("a", "ruling", {"kind": "k5", "color": INK, "text": "Hallo", **props}, w=120, h=40)
        ]
        return blocks, "svg.ruling", "svg.ruling text"
    # A group: the text "a" with the look, and a plain text "b" beside it.
    blocks = [
        box("a", "text", {**TEXT, "text": "Hallo", **props}, w=60, h=40, group=["g"]),
        box("b", "text", TEXT, z=2, x=90, y=50, w=60, h=40, group=["g"]),
    ]
    return blocks, ".frame", ".frame > p, .frame .rich"


def ink_pixels(shot, dark=100):
    """How many pixels are dark in a shot."""
    img = Image.open(io.BytesIO(shot)).convert("L")
    return sum(1 for v in img.tobytes() if v < dark)


def pdf_font_names(server, client, sheet_id):
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return res.content, set(re.findall(rb"/FontName /\w+\+([\w-]+)", res.content))


@pytest.mark.parametrize("look", ["grey", "outline", "dotted"])
@pytest.mark.parametrize("kind", ["text", "shape", "table", "ruling", "karo", "group"])
def test_each_look_draws_in_every_block_with_text(editor, kind, look):
    """B2: each kind with each look: the owner's attribute and the letters' computed styles."""
    props = {"trace": True} if look == "grey" else {"trace": look}
    if look == "dotted":
        props["font"] = "urff"
    blocks, owner_sel, letters_sel = build(kind, props)
    page = editor(*blocks)
    unpick(page)
    owner = at(page, "a").locator(owner_sel).first
    # Dotted without a cut draws grey: only Karo and the fonts other than urff are that case.
    shown = "grey" if (look == "dotted" and kind == "karo") else look
    expect(owner).to_have_attribute("data-trace", shown)
    letters = at(page, "a").locator(letters_sel).first
    if kind == "karo" and look == "outline":
        assert letters.evaluate(
            "el => el.getAttribute('fill') === 'none' && !!el.getAttribute('stroke')"
        )
        return
    style = letters.evaluate(STYLE)
    if shown == "grey" and kind == "karo":
        assert letters.get_attribute("fill") == "#aaaaaa", style
    elif shown == "grey":
        assert style["color"] == GREY, style
    if shown == "outline":
        assert style["fill"] == WHITE, style
        assert float(style["stroke"].rstrip("px")) > 0, style
        assert style["paint"].startswith("stroke"), style
        assert style["blend"] == "multiply", style
        assert style["strokeColor"] == style["color"], style
        assert style["color"] != GREY, style
    if look == "dotted" and shown == "dotted":
        assert "Grundschrift Urff Punkt" in style["family"], style
        assert style["weight"] == "400", style
        assert style["style"] == "normal", style
        assert style["color"] != GREY, style
    if look == "dotted" and shown == "grey":
        assert "Punkt" not in style["family"], style


@pytest.mark.parametrize("font", FONTS)
def test_outline_in_every_font(editor, server, font):
    """B3: a 40 pt text and a Lineatur l1 in each font: the outline is drawn, its stroke hollow."""
    text = {**TEXT, "text": "Hallo", "size": 40, "font": font}
    plain = editor(box("a", "text", text, w=180, h=40, x=15, y=40))
    plain_dark = ink_pixels(at(plain, "a").screenshot())
    outlined = editor(box("a", "text", {**text, "trace": "outline"}, w=180, h=40, x=15, y=40))
    shot = at(outlined, "a").screenshot()
    assert ink_pixels(shot) > 0
    assert ink_pixels(shot) < 0.8 * plain_dark
    # The middle of a thick stroke is white: a white pixel with dark on all four sides nearby.
    img = Image.open(io.BytesIO(shot)).convert("L")
    width, height = img.size
    px = img.tobytes()
    hollow = 0
    for y in range(4, height - 4, 2):
        for x in range(4, width - 4, 2):
            if px[y * width + x] < 240:
                continue
            left = any(px[y * width + xx] < 100 for xx in range(x - 4, x))
            right = any(px[y * width + xx] < 100 for xx in range(x + 1, x + 5))
            up = any(px[yy * width + x] < 100 for yy in range(y - 4, y))
            down = any(px[yy * width + x] < 100 for yy in range(y + 1, y + 5))
            if left and right and up and down:
                hollow += 1
    assert hollow > 0, font

    ruling = box("r", "ruling", {**RULING, "kind": "l1", "font": font}, w=180, h=40, x=15, y=40)
    blank = editor(ruling)
    with_text = editor(
        box(
            "r",
            "ruling",
            {**RULING, "kind": "l1", "font": font, "text": "Hallo", "trace": "outline"},
            w=180,
            h=40,
            x=15,
            y=40,
        )
    )
    if font == "va":
        blank_shot = Image.open(io.BytesIO(at(blank, "r").screenshot())).convert("RGB")
        text_shot = Image.open(io.BytesIO(at(with_text, "r").screenshot())).convert("RGB")

        def line_pixels(img, row):
            return sum(
                1
                for x in range(img.width)
                if all(
                    abs(c - v) <= 40
                    for c, v in zip(img.getpixel((x, row)), (34, 34, 34), strict=True)
                )
            )

        # The row of a ruling line: where the blank ruling is darkest.
        row = max(range(blank_shot.height), key=lambda y: line_pixels(blank_shot, y))
        plain_count = line_pixels(blank_shot, row)
        text_count = line_pixels(text_shot, row)
        assert plain_count > 0
        assert abs(text_count - plain_count) <= 0.15 * plain_count, (plain_count, text_count)


def test_dotted_uses_the_punkt_cut(editor, server):
    """B4: dotted text takes the Punkt cut of urff, far fewer dark pixels, and the PDF embeds it."""
    client = user()
    plain = editor(
        box(
            "a",
            "text",
            {**TEXT, "text": "Hallo", "size": 40, "font": "urff"},
            w=180,
            h=40,
            x=15,
            y=40,
        ),
        client=client,
    )
    plain_dark = ink_pixels(at(plain, "a").screenshot())
    dotted = editor(
        box(
            "a",
            "text",
            {**TEXT, "text": "Hallo", "size": 40, "font": "urff", "trace": "dotted"},
            w=180,
            h=40,
            x=15,
            y=40,
        ),
        client=client,
    )
    letters = at(dotted, "a").locator(".frame > p, .frame .rich").first
    assert "Grundschrift Urff Punkt" in letters.evaluate(STYLE)["family"]
    assert dotted.evaluate("async () => document.fonts.check('20px \"Grundschrift Urff Punkt\"')")
    assert ink_pixels(at(dotted, "a").screenshot()) < 0.5 * plain_dark
    sheet_id = dotted.url.rsplit("/", 1)[1]
    _, names = pdf_font_names(server, client, sheet_id)
    assert any(b"Grundschrift-Punkt" in name for name in names), names


@pytest.mark.parametrize("font", ["andika", "nord", "sued", "grund", "va", "sas", "la"])
@pytest.mark.parametrize("kind", ["text", "table", "ruling"])
def test_dotted_without_a_cut_draws_grey(editor, kind, font):
    """I4: dotted in a font with no dotted cut, and in a table or a Lineatur, draws grey."""
    props = {"trace": "dotted", "font": font}
    blocks, owner_sel, letters_sel = build(kind, props)
    page = editor(*blocks)
    unpick(page)
    expect(at(page, "a").locator(owner_sel).first).to_have_attribute("data-trace", "grey")
    style = at(page, "a").locator(letters_sel).first.evaluate(STYLE)
    assert style["color"] == GREY, style
    assert "Punkt" not in style["family"], style


@pytest.mark.parametrize(
    "kind, props",
    [
        ("text", {"bold": True, "italic": True}),
        ("text", {"rich": [{"runs": [{"text": "Mama", "bold": True}]}]}),
        ("table", {"head": True}),
    ],
    ids=["text-bold-italic", "rich-bold-run", "table-head"],
)
def test_dotted_is_never_bold(editor, kind, props):
    """I5: a dotted text stays in the Punkt cut at weight 400 and upright, bold or not."""
    look = {"trace": "dotted", "font": "urff", **props}
    blocks, _, letters_sel = build(kind, look)
    page = editor(*blocks)
    letters = at(page, "a").locator(letters_sel).first
    style = letters.evaluate(STYLE)
    assert "Grundschrift Urff Punkt" in style["family"], style
    assert style["weight"] == "400", style
    assert style["style"] == "normal", style


def fade_block(kind, fade):
    """A block that fills with the same words in rows, grey and faded, and its size."""
    props = {"trace": True, "fade": fade}
    if kind == "text":
        text = "\n".join(["Hallo Hallo Hallo Hallo"] * 4)
        return [box("a", "text", {**TEXT, "text": text, **props}, w=180, h=30, x=15, y=40)]
    if kind == "shape":
        text = "\n".join(["Hallo Hallo Hallo Hallo"] * 4)
        return [
            box(
                "a",
                "shape",
                {**RECT, "stroke": "none", "text": text, **props},
                w=180,
                h=30,
                x=15,
                y=40,
            )
        ]
    if kind == "table":
        cells = [["Hallo"] * 4 for _ in range(4)]
        return [
            box(
                "a",
                "table",
                {**TABLE, "cells": cells, "cols": [1, 1, 1, 1], **props},
                w=180,
                h=60,
                x=15,
                y=40,
            )
        ]
    if kind == "ruling":
        text = "\n".join(["Hallo Hallo Hallo"] * 4)
        return [
            box(
                "a",
                "ruling",
                {**RULING, "kind": "l1", "text": text, **props},
                w=180,
                h=40,
                x=15,
                y=40,
            )
        ]
    text = "\n".join(["HALLO HALLO HALLO"] * 8)
    return [
        box(
            "a",
            "ruling",
            {"kind": "k5", "color": INK, "text": text, **props},
            w=180,
            h=40,
            x=15,
            y=40,
        )
    ]


@pytest.mark.parametrize("fade", ["row", "rows"])
@pytest.mark.parametrize("kind", ["text", "shape", "ruling", "karo", "table"])
def test_fading_gets_lighter_and_ends_empty(editor, kind, fade):
    """B5: grey text fades along its rows: the ink falls part by part and the last part is empty."""
    page = editor(*fade_block(kind, fade))
    owner = at(page, "a")
    expect(owner.locator("[data-fade]").first).to_have_attribute("data-fade", fade)
    shown = Image.open(io.BytesIO(owner.screenshot())).convert("L")
    # The same block with its letters hidden: what differs is the grey ink alone, so the dark
    # lines of a table or a Lineatur and the border of a shape are no part of it.
    page.add_style_tag(
        content=(
            ".block[data-id='a'] .frame > p, .block[data-id='a'] .frame .rich,"
            " .block[data-id='a'] .table p, .block[data-id='a'] p.written,"
            " .block[data-id='a'] svg.ruling text { visibility: hidden !important }"
        )
    )
    blank = Image.open(io.BytesIO(owner.screenshot())).convert("L")
    ink = [max(0, b - s) for b, s in zip(blank.tobytes(), shown.tobytes(), strict=True)]
    width, height = blank.size
    rows = 8 if kind == "karo" else 4
    parts = []
    for i in range(rows if fade == "rows" else 4):
        if fade == "row":
            cols = range(i * width // 4, (i + 1) * width // 4)
            band = [ink[y * width + x] for y in range(height) for x in cols]
        else:
            band = ink[i * height // rows * width : (i + 1) * height // rows * width]
        parts.append(sum(band))
    assert all(parts[i] <= parts[i - 1] * 1.05 for i in range(1, len(parts))), parts
    assert parts[0] > 1.2 * parts[2], parts
    assert parts[-1] < 0.03 * parts[0], parts


def test_an_old_sheet_opens_unchanged(editor, server):
    """B7: a sheet saved before the looks keeps its Lineatur's grey, and no block gets a look."""
    client = user()
    blocks = [
        place(
            "r",
            "ruling",
            {**RULING, "kind": "l1", "text": "Alt", "trace": True},
            x=15,
            y=20,
            w=180,
            h=40,
        ),
        place("t", "text", {**TEXT, "text": "Alt"}, x=15, y=80, w=180, h=20),
        place("s", "shape", {**RECT, "text": "Alt"}, x=15, y=120, w=180, h=20),
        place("tb", "table", TABLE, x=15, y=160, w=120, h=40),
    ]
    page = editor(*blocks, client=client)
    expect(at(page, "r").locator("p.written").first).to_have_attribute("data-trace", "grey")
    pick(page, "t")
    page.keyboard.press("ArrowRight")
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["r"]["props"]["trace"] is True
    assert "fade" not in stored["r"]["props"]
    for name in ("t", "s", "tb"):
        assert "trace" not in stored[name]["props"], name
    assert page.locator(".sheet [data-trace], .sheet [data-fade]").count() == 1
    for name in ("t", "s", "tb"):
        letters = at(page, name).locator(".frame > p, .frame .rich, .table p").first
        style = letters.evaluate(STYLE)
        assert style["blend"] == "normal", (name, style)
        assert style["stroke"] in ("0px", "0"), (name, style)
        assert style["mask"] == "none", (name, style)


def look_sheet():
    """One sheet with every look and both fadings: a text, a shape with a fill, a table, two
    Lineaturen and a Karo."""
    return [
        place(
            "t1",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": True, "fade": "row"},
            x=15,
            y=20,
            w=180,
            h=25,
        ),
        place(
            "t2",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": "outline", "fade": "rows"},
            x=15,
            y=50,
            w=180,
            h=25,
        ),
        place(
            "t3",
            "text",
            {**TEXT, "text": "Hallo " * 20, "trace": "dotted", "font": "urff"},
            x=15,
            y=80,
            w=180,
            h=25,
        ),
        place(
            "s1",
            "shape",
            {**RECT, "fill": "#ffd43b", "text": "Hallo", "trace": "outline", "fade": "row"},
            x=15,
            y=110,
            w=180,
            h=25,
        ),
        place("tb", "table", {**TABLE, "trace": "grey", "fade": "rows"}, x=15, y=140, w=120, h=40),
        place(
            "r1",
            "ruling",
            {
                **RULING,
                "kind": "l1",
                "font": "va",
                "text": "Hallo Hallo\nHallo",
                "trace": "outline",
                "fade": "rows",
            },
            x=15,
            y=190,
            w=90,
            h=40,
        ),
        place(
            "r2",
            "ruling",
            {**RULING, "kind": "l1", "font": "urff", "text": "Hallo", "trace": "dotted"},
            x=15,
            y=235,
            w=90,
            h=40,
        ),
        place(
            "k",
            "ruling",
            {"kind": "k5", "color": INK, "text": "Hallo", "trace": "outline"},
            x=110,
            y=190,
            w=85,
            h=40,
        ),
    ]


def test_screen_and_pdf_agree(browser, server):
    """B9: the screen and the PDF of a sheet with every look and fading agree."""
    client = user()
    mine = sheet(client, look_sheet())
    screen, printed = screen_and_print(browser, server, client, mine["id"])
    assert not over(screen, printed)


def test_the_pdf_holds_no_picture(server):
    """B9: the PDF of that sheet has no image: letters, dots and outlines are vectors."""
    client = user()
    mine = sheet(client, look_sheet())
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    assert re.search(rb"/Subtype\s*/Image", res.content) is None
