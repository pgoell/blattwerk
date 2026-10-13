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
        return blocks, ".written[data-trace]", ".written"
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
def test_outline_in_every_font(editor, font):
    """B3: a 40 pt text in each font: dark ink, fewer than plain, and the stem middles white."""
    text = {**TEXT, "text": "Hallo", "size": 40, "font": font}
    plain_page = editor(box("a", "text", text, w=180, h=40, x=15, y=40))
    plain = Image.open(io.BytesIO(at(plain_page, "a").screenshot())).convert("L")
    outlined_page = editor(box("a", "text", {**text, "trace": "outline"}, w=180, h=40, x=15, y=40))
    outlined = Image.open(io.BytesIO(at(outlined_page, "a").screenshot())).convert("L")
    assert plain.size == outlined.size
    width, height = plain.size
    p, o = plain.tobytes(), outlined.tobytes()
    dark_plain = sum(1 for v in p if v < 100)
    dark_outline = sum(1 for v in o if v < 100)
    assert dark_outline > 0
    # No count against the plain text: Urff and the two Fibeln have stems as thin as the two
    # lines an outline draws around them, so their outline holds about as much ink (98 %).
    assert dark_plain > 0
    # The middle of a stem: dark in the plain text, with dark 2 px away on all four sides.
    stems = [
        (x, y)
        for y in range(2, height - 2)
        for x in range(2, width - 2)
        if p[y * width + x] < 100
        and all(p[(y + dy) * width + x + dx] < 100 for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)))
    ]
    assert stems, font
    hollow = sum(1 for x, y in stems if o[y * width + x] >= 100)
    assert hollow / len(stems) > 0.9, (hollow, len(stems))

    if font == "va":

        def ruling(**more):
            props = {**RULING, "kind": "l1", "font": font, **more}
            page = editor(box("r", "ruling", props, w=180, h=40, x=15, y=40))
            return Image.open(io.BytesIO(at(page, "r").screenshot())).convert("RGB")

        blank = ruling()
        typed = ruling(text="Hallo", trace="outline")

        def line_pixels(img, row):
            # Right of the word: no letter there, only the ruling's line.
            return sum(
                1
                for x in range(int(img.width * 0.7), img.width)
                if sum(img.getpixel((x, row))) < 3 * 120
            )

        row = max(range(blank.height), key=lambda y: line_pixels(blank, y))
        plain_count = line_pixels(blank, row)
        text_count = line_pixels(typed, row)
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
    """Four rows of the same words, each row full across the block, grey and faded."""
    props = {"trace": True, "fade": fade}
    full = "Hallo " * 12
    if kind == "text":
        # Four rows of 14 pt, 6.4 mm each.
        text = "\n".join([full] * 4)
        return [box("a", "text", {**TEXT, "text": text, **props}, w=180, h=26, x=15, y=40)]
    if kind == "shape":
        text = "\n".join([full] * 4)
        shape = {**RECT, "stroke": "none", "valign": "top", "align": "left", "text": text, **props}
        return [box("a", "shape", shape, w=180, h=29, x=15, y=40)]
    if kind == "table":
        cells = [["Hallo"] * 4 for _ in range(4)]
        table = {**TABLE, "cells": cells, "cols": [1, 1, 1, 1], **props}
        return [box("a", "table", table, w=180, h=60, x=15, y=40)]
    if kind == "ruling":
        # Four rows of 20 mm, a word in each.
        text = "\n".join(["Hallo " * 4] * 4)
        return [
            box(
                "a",
                "ruling",
                {**RULING, "kind": "l1", "text": text, **props},
                w=180,
                h=80,
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
            " .block[data-id='a'] .table p, .block[data-id='a'] .written,"
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
    expect(at(page, "r").locator(".written").first).to_have_attribute("data-trace", "grey")
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
        place("tb", "table", {**TABLE, "trace": True, "fade": "rows"}, x=15, y=140, w=120, h=40),
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
    # The looks did reach the print: the dotted text brought its cut along.
    assert b"Grundschrift-Punkt" in res.content


SIDE_LEVER = (
    ".frame, .frame p, .frame .rich { overflow: visible !important; clip-path: none !important; }"
)
LEVER_ALL = (
    ".block, .block *, .frame * { overflow: visible !important; clip-path: none !important; }"
)


def dark_count(shot):
    img = Image.open(io.BytesIO(shot)).convert("L").point(lambda v: 255 if v < 100 else 0)
    return img.histogram()[255]


def clip_of(block, margin=30):
    b = block.bounding_box()
    return {
        "x": b["x"] - margin,
        "y": b["y"] - margin,
        "width": b["width"] + 2 * margin,
        "height": b["height"] + 2 * margin,
    }


@pytest.mark.parametrize(
    "props",
    [
        {"size": 0, "spacing": None},
        {"size": 14, "spacing": 0},
    ],
)
def test_a_fade_with_no_size_or_spacing_still_opens(editor, props):
    """B5: a fade whose row has no height draws the text and opens, with no mask."""
    spacing = props.pop("spacing")
    text = {**TEXT, "text": "Hallo\nHallo", "trace": True, "fade": "rows", **props}
    if spacing is not None:
        text["spacing"] = spacing
    page = editor(box("a", "text", text, x=15, y=40, w=80, h=60))
    expect(at(page, "a").locator(".frame")).to_be_attached()
    expect(at(page, "a")).to_be_visible()


def test_a_shape_with_no_size_still_opens(editor):
    """B5: a shape with no size key and a rows fade draws and opens."""
    shape = {"kind": "rect", "text": "Hallo\nHallo", "trace": True, "fade": "rows"}
    page = editor(box("a", "shape", shape, x=15, y=40, w=80, h=60))
    expect(at(page, "a").locator(".frame")).to_be_attached()
    expect(at(page, "a")).to_be_visible()


@pytest.mark.parametrize("valign", ["top", "middle"])
@pytest.mark.parametrize("kind", ["text", "shape"])
def test_rows_fade_by_the_texts_own_lines(editor, kind, valign):
    """B5: three rows in a 60 mm block: the first has ink, the second less, the third none."""
    text = "\n".join(["Hallo"] * 3)
    base = TEXT if kind == "text" else {"kind": "rect", "stroke": "none"}
    props = {**base, "text": text, "size": 20, "valign": valign, "trace": True, "fade": "rows"}
    page = editor(box("a", kind, props, x=15, y=40, w=80, h=60))
    owner = at(page, "a")
    frame = owner.locator(".frame")
    shown = Image.open(io.BytesIO(owner.screenshot())).convert("L")
    hide = ".block[data-id='a'] .frame > p, .block[data-id='a'] .frame .rich"
    page.add_style_tag(content=f"{hide} {{ visibility: hidden !important }}")
    blank = Image.open(io.BytesIO(owner.screenshot())).convert("L")
    ink = [max(0, b - s) for b, s in zip(blank.tobytes(), shown.tobytes(), strict=True)]
    width = blank.width
    # The rows are the paragraph's own lines: from its top, one line height each.
    top, line = frame.locator("p").first.evaluate(
        "el => { const o = el.parentElement.getBoundingClientRect();"
        " const r = el.getBoundingClientRect();"
        " return [r.top - o.top, parseFloat(getComputedStyle(el).lineHeight)]; }"
    )
    parts = []
    for i in range(3):
        y0, y1 = round(top + i * line), round(top + (i + 1) * line)
        parts.append(sum(ink[y * width + x] for y in range(y0, y1) for x in range(width)))
    assert parts[0] > 0, parts
    assert parts[1] < 0.9 * parts[0], parts
    assert parts[2] < 0.03 * parts[0], parts


@pytest.mark.parametrize("font", FONTS)
def test_the_outline_is_whole_at_every_edge(editor, font):
    """B5: an outline's stroke and joined letters are drawn whole at both sides, in each font."""
    for align in ["left", "right"]:
        props = {
            **TEXT,
            "font": font,
            "size": 40,
            "align": align,
            "text": "Tgjp",
            "trace": "outline",
        }
        page = editor(box("a", "text", props, x=10, y=40, w=90, h=20))
        unpick(page)
        clip = clip_of(at(page, "a"))
        before = page.screenshot(clip=clip)
        page.add_style_tag(content=SIDE_LEVER)
        full = dark_count(page.screenshot(clip=clip))
        count = dark_count(before)
        assert full > 0
        assert abs(count - full) <= 0.01 * full, (align, count, full)


@pytest.mark.parametrize("kind", ["text", "ruling"])
def test_the_open_text_does_not_fade(editor, kind):
    """B5: a text being typed in shows its look but not its fade; closed again, it fades."""
    if kind == "text":
        props = {**TEXT, "text": "Hallo\nHallo", "trace": True, "fade": "row", "size": 20}
        page = editor(box("a", "text", props, x=15, y=40, w=80, h=30))
        selector = ".block[data-id='a'] .frame .rich, .block[data-id='a'] .frame > p"
    else:
        props = {"kind": "l1", "color": "#222222", "text": "Hallo", "trace": True, "fade": "row"}
        page = editor(box("a", "ruling", props, x=15, y=40, w=180, h=40))
        selector = ".block[data-id='a'] .written"
    read = (
        f"() => {{ const el = document.querySelector({selector!r});"
        " const s = getComputedStyle(el);"
        " return s.maskImage || s.webkitMaskImage || 'none'; }"
    )
    assert page.evaluate(read).startswith("linear-gradient"), page.evaluate(read)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(
        page.locator(".block[data-id='a'] .ProseMirror, .block[data-id='a'] textarea.written").first
    ).to_be_attached()
    assert page.evaluate(read) == "none", page.evaluate(read)
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    assert page.evaluate(read).startswith("linear-gradient"), page.evaluate(read)
