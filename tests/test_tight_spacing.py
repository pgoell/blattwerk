"""Issue #487: no ink of a text is cut at any line spacing: on screen, open or in the PDF.

Checklist ids are in each docstring.
"""

import re
from io import BytesIO

import httpx
import pypdfium2
import pytest
from PIL import Image, ImageChops
from playwright.sync_api import expect
from ui import RECT, TEXT, at, box, pick, sheet, unpick, user

FONTS = ["andika", "nord", "sued", "grund", "urff", "va", "sas", "la"]
# The lever: what would clip the ink if the paragraph did not.
LEVER = (
    ".frame, .frame p, .frame .rich { overflow: visible !important; clip-path: none !important; }"
)
OPEN_LEVER = (
    ".block, .block *, .frame * { overflow: visible !important; clip-path: none !important; }"
)
CARET = "* { caret-color: transparent !important }"
# The rules before #487: no padding, no margin, the clip of the paragraph.
OLD_RULES = (
    ".frame p, .frame .rich { overflow: hidden !important; padding-block: 0 !important; "
    "margin-block: 0 !important; }"
)
RICH = [{"runs": [{"text": "ÄÖÜ"}]}, {"runs": [{"text": "gjpß"}]}]
ONE_LINE = "ÄgjpßÖÜ"
MM = 0.3528
# A shape has a padding of 1.3 mm and its border of 0.5 mm, top and bottom.
SHAPE_EDGE = 2 * 1.3 + 2 * 0.5


def dark(shot):
    """How many pixels are dark in the shot, and its first and last row that holds one."""
    img = Image.open(BytesIO(shot)).convert("L").point(lambda v: 255 if v < 100 else 0)
    box_ = img.getbbox()
    return img.histogram()[255], (box_[1] if box_ else None), (box_[3] - 1 if box_ else None)


def dark_in(img, top, bottom):
    """How many dark pixels lie in the rows from `top` to `bottom` of an image."""
    return sum(img.crop((0, top, img.width, bottom)).histogram()[:100])


def clip_of(block, margin=30):
    b = block.bounding_box()
    return {
        "x": b["x"] - margin,
        "y": b["y"] - margin,
        "width": b["width"] + 2 * margin,
        "height": b["height"] + 2 * margin,
    }


def text_props(key, kind, form, spacing):
    props = {**(TEXT if kind == "text" else RECT), "font": key, "size": 28, "valign": "middle"}
    if form == "rich":
        props |= {"text": "ÄÖÜ\ngjpß", "rich": RICH}
    else:
        props["text"] = ONE_LINE
    props["spacing"] = spacing
    return props


def cases():
    """Every font, kind and form at four spacings, and the issue's one-line block at 1.0."""
    out = [
        ("middle", key, kind, form, spacing)
        for key in FONTS
        for kind in ("text", "shape")
        for form in ("plain", "rich")
        for spacing in (1.0, 1.1, 1.3, 2.0)
    ]
    out += [("one_line", key, kind, "plain", 1.0) for key in FONTS for kind in ("text", "shape")]
    return out


@pytest.mark.parametrize("layout,key,kind,form,spacing", cases())
def test_no_ink_is_cut_on_the_screen(editor, layout, key, kind, form, spacing):
    """A1: a text or a shape draws its ink as it does with the cut lifted, at every spacing.

    `middle` is a block larger than its text. `one_line` is the issue's block: one line high
    (plus the padding of a shape), valign top.
    """
    props = text_props(key, kind, form, spacing)
    if layout == "one_line":
        props |= {"valign": "top"}
        height = 28 * MM + (SHAPE_EDGE if kind == "shape" else 0)
        block = box("a", kind, props, x=10, y=40, w=90, h=height)
    else:
        # Two lines at 2.0 are 40 mm and more: a block taller than them.
        block = box("a", kind, props, x=10, y=40, w=90, h=60 if spacing == 2.0 else 40)
    page = editor(block)
    unpick(page)
    clip = clip_of(at(page, "a"))
    before = page.screenshot(clip=clip)
    page.add_style_tag(content=LEVER)
    after = page.screenshot(clip=clip)
    count, top, bottom = dark(before)
    count2, top2, bottom2 = dark(after)
    assert count2 > 0
    assert abs(count - count2) <= 0.02 * count2, (count, count2)
    assert abs(top - top2) <= 1, (top, top2)
    assert abs(bottom - bottom2) <= 1, (bottom, bottom2)


@pytest.mark.parametrize("spacing", [1.0, 1.3])
def test_no_ink_is_cut_in_the_open_text(editor, spacing):
    """A1: the open field of a text keeps its ink, as its closed block does."""
    props = text_props("urff", "text", "plain", spacing) | {"valign": "middle"}
    page = editor(box("a", "text", props, x=10, y=40, w=90, h=40))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    page.add_style_tag(content=CARET)
    clip = clip_of(at(page, "a"))
    before = page.screenshot(clip=clip)
    page.add_style_tag(content=OPEN_LEVER)
    after = page.screenshot(clip=clip)
    count, top, bottom = dark(before)
    count2, top2, bottom2 = dark(after)
    assert count2 > 0
    assert abs(count - count2) <= 0.02 * count2, (count, count2)
    assert abs(top - top2) <= 1, (top, top2)
    assert abs(bottom - bottom2) <= 1, (bottom, bottom2)


def pdf_ink(doc, index, x, y, w, h):
    """The ink of a PDF page in a block's region, the block plus 3 mm around it.

    Summed darkness, not a count of dark pixels: a thin stem that falls between two pixels is pale
    on both and would count as none.
    """
    paper = doc[index]
    img = paper.render(scale=4).to_pil().convert("L")
    per_mm = img.width / (paper.get_width() * 25.4 / 72)
    left, top = round((x - 3) * per_mm), round((y - 3) * per_mm)
    right, bottom = round((x + w + 3) * per_mm), round((y + h + 3) * per_mm)
    shades = img.crop((left, top, right, bottom)).histogram()
    return sum((255 - value) * n for value, n in enumerate(shades))


def fetch_pdf(server, client, sheet_id):
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return pypdfium2.PdfDocument(res.content)


def test_no_ink_is_cut_in_the_pdf(server):
    """A2: the same letters print the same ink at 1.0 and at 2.0, where nothing can be cut.

    Texts, shapes and rich texts of every font; each at 1.0 against the same at 2.0.
    """
    client = user()
    first, second, pairs = [], [], []
    for i, key in enumerate(FONTS):
        y = 10 + 30 * i
        # 90 mm wide: a joined script's line of 28 pt breaks in 50 mm, and its second line is cut.
        for x, spacing in ((5, 1.0), (105, 2.0)):
            props = text_props(key, "text", "plain", spacing)
            first.append(box(f"t{i}-{spacing}", "text", props, x=x, y=y, w=90, h=20))
        pairs.append(((0, 5, y, 90, 20), (0, 105, y, 90, 20)))
    for i, key in enumerate(FONTS):
        y = 10 + 30 * i
        for x, kind, form, spacing, w, h in (
            (5, "shape", "plain", 1.0, 50, 24),
            (65, "shape", "plain", 2.0, 50, 24),
            (125, "text", "rich", 1.0, 35, 20),
            (170, "text", "rich", 2.0, 35, 20),
        ):
            props = text_props(key, kind, form, spacing)
            # Small enough for one line in the block's width, in a joined script too.
            props["size"] = 14
            second.append(box(f"s{i}-{x}", kind, props, x=x, y=y, w=w, h=h))
        pairs.append(((1, 5, y, 50, 24), (1, 65, y, 50, 24)))
        pairs.append(((1, 125, y, 35, 20), (1, 170, y, 35, 20)))
    mine = sheet(client, first, second)
    doc = fetch_pdf(server, client, mine["id"])
    for one, two in pairs:
        count = pdf_ink(doc, *one)
        count2 = pdf_ink(doc, *two)
        assert count > 0
        assert abs(count - count2) <= 0.02 * max(count, count2), (one, count, count2)


@pytest.mark.parametrize("key", FONTS)
@pytest.mark.parametrize("spacing", [1.0, 1.3])
def test_a_text_too_long_ends_at_the_foot(editor, server, key, spacing):
    """A3: a text too long for its block is cut at its foot plus the font's own reach below it."""
    text = "\n".join(["gjpß ÄÖÜ"] * 12)
    props = {**TEXT, "text": text, "font": key, "size": 14, "spacing": spacing, "valign": "top"}
    page = editor(box("a", "text", props, x=10, y=40, w=90, h=20))
    unpick(page)
    block = at(page, "a")
    b = block.bounding_box()
    size_px = block.locator("p").first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    mm = b["height"] / 20
    # The paragraph's padding is the font's reach below its line, in px: none where it holds it.
    spill = block.locator("p").first.evaluate(
        "el => parseFloat(getComputedStyle(el).paddingBottom)"
    )
    down_em = spill / size_px
    clip = {
        "x": b["x"] - 10,
        "y": b["y"] - 10,
        "width": b["width"] + 20,
        "height": b["height"] + spill + 40,
    }
    foot = 10 + b["height"]
    shot = page.screenshot(clip=clip)
    count, _, bottom = dark(shot)
    assert count > 0
    assert dark_in(Image.open(BytesIO(shot)).convert("L"), round(foot - 2 * mm), round(foot)) > 0
    assert bottom <= foot + spill + 2, (bottom, foot, spill)
    if spacing == 1.0:
        # In the PDF: the last 2 mm above the foot hold ink, and nothing lies 0.5 mm past the reach.
        client = user()
        mine = sheet(client, [box("a", "text", props, x=10, y=40, w=90, h=20)])
        paper = fetch_pdf(server, client, mine["id"])[0]
        img = paper.render(scale=4).to_pil().convert("L")
        per_mm = img.width / (paper.get_width() * 25.4 / 72)
        foot_mm = 40 + 20
        spill_mm = down_em * 14 * 25.4 / 72
        assert dark_in(img, round((foot_mm - 2) * per_mm), round(foot_mm * per_mm)) > 0
        assert dark_in(img, round((foot_mm + spill_mm + 0.5) * per_mm), img.height) == 0


# Fonts whose ink reaches past the line box at 1.3 too: their paragraphs carry the padding at 1.3.
# Andika's lowest sign reaches 0.015 em under its line of 1.3, under the fiftieth that counts.
REACHES_AT_13 = ["grund", "va", "sas", "la"]


@pytest.mark.parametrize("spacing", [None, 1.3, 2.0])
@pytest.mark.parametrize("kind", ["text", "shape", "rich", "long"])
@pytest.mark.parametrize("key", FONTS)
def test_the_default_spacing_draws_as_before(editor, key, kind, spacing):
    """A4: a font whose ink its line holds draws as before; a font whose ink reaches out keeps every
    letter in its paragraph and only lets the ink outside it show.
    """
    props = {**(RECT if kind == "shape" else TEXT), "font": key, "size": 20, "valign": "middle"}
    if kind == "rich":
        props |= {"text": "ÄÖÜ\ngjpß", "rich": RICH}
    elif kind == "long":
        props |= {"text": "\n".join(["gjpß ÄÖÜ"] * 12), "size": 14, "valign": "top"}
    else:
        props["text"] = ONE_LINE
    if spacing is not None:
        props["spacing"] = spacing
    block_kind = "shape" if kind == "shape" else "text"
    page = editor(box("a", block_kind, props, x=10, y=40, w=90, h=40))
    unpick(page)
    frame = at(page, "a").locator(".frame")
    # The joined scripts reach past their place at the sides, so they are tight at every spacing.
    reaches = key in REACHES_AT_13
    clip = clip_of(at(page, "a"))
    before = page.screenshot(clip=clip)
    if not reaches:
        expect(frame).not_to_have_class(re.compile(r"\btight\b"))
        styles = frame.locator("p").first.evaluate(
            """el => {
                const s = getComputedStyle(el);
                return [s.paddingTop, s.paddingBottom, s.marginTop, s.marginBottom, s.overflow];
            }"""
        )
        assert styles == ["0px", "0px", "0px", "0px", "hidden"]
        assert frame.evaluate("el => el.style.clipPath").startswith("inset(-1px")
        page.add_style_tag(content=OLD_RULES)
        after = page.screenshot(clip=clip)
        a, b = Image.open(BytesIO(before)).convert("RGB"), Image.open(BytesIO(after)).convert("RGB")
        assert ImageChops.difference(a, b).getbbox() is None
        return
    # The paragraph's own box, without its new padding: the letters inside it may not move.
    expect(frame).to_have_class(re.compile(r"\btight\b"))
    box_ = frame.locator("p").first.evaluate(
        """el => {
            const r = el.getBoundingClientRect(), s = getComputedStyle(el);
            return [r.left + parseFloat(s.paddingLeft), r.top + parseFloat(s.paddingTop),
                    r.right - parseFloat(s.paddingRight), r.bottom - parseFloat(s.paddingBottom)];
        }"""
    )
    left, top = round(box_[0] - clip["x"]), round(box_[1] - clip["y"])
    right, bottom = round(box_[2] - clip["x"]), round(box_[3] - clip["y"])
    page.add_style_tag(content=OLD_RULES)
    after = page.screenshot(clip=clip)
    a, b = Image.open(BytesIO(before)).convert("RGB"), Image.open(BytesIO(after)).convert("RGB")
    diff = ImageChops.difference(a, b)
    assert diff.crop((left + 1, top + 1, right - 1, bottom - 1)).getbbox() is None
    # With the new rules the dark count is the count of the unclipped letters, within 2 %.
    if kind != "long":
        page.add_style_tag(content=LEVER)
        full = dark(page.screenshot(clip=clip))[0]
        count = dark(before)[0]
        assert abs(count - full) <= 0.02 * full, (count, full)


SIDE_LEVER = (
    ".frame, .frame p, .frame .rich { overflow: visible !important; clip-path: none !important; }"
)
# The side padding and margin off: the paragraph as it was before the sides were lifted.
NO_SIDES = (
    ".frame.tight p, .frame.tight .rich"
    " { padding-inline: 0 !important; margin-inline: 0 !important; }"
)
ALL_FONTS = ["andika", "nord", "sued", "grund", "urff", "va", "sas", "la"]


@pytest.mark.parametrize("italic", [False, True])
@pytest.mark.parametrize("align", ["left", "right"])
@pytest.mark.parametrize("key", REACHES_AT_13)
def test_no_ink_is_cut_at_the_sides(editor, key, align, italic):
    """A1: a joined script's letters reach past their place, and no ink is cut at either side.

    j reaches left of its place and f right of it. The print fonts' plain text keeps its sides as
    sheets saved before had them (#489).
    """
    props = {**TEXT, "font": key, "size": 40, "align": align, "text": "jgf Tgjf", "italic": italic}
    page = editor(box("a", "text", props, x=10, y=40, w=90, h=30))
    unpick(page)
    clip = clip_of(at(page, "a"))
    before = page.screenshot(clip=clip)
    page.add_style_tag(content=SIDE_LEVER)
    full = dark(page.screenshot(clip=clip))[0]
    count = dark(before)[0]
    assert full > 0
    assert abs(count - full) <= 0.005 * full, (count, full)


@pytest.mark.parametrize("key", REACHES_AT_13)
def test_the_sides_keep_the_line_breaks(editor, key):
    """A1: the side padding moves no letter and breaks no line of a wrapping text."""
    props = {**TEXT, "font": key, "size": 20, "align": "left", "text": "Hallo gjpß Tgjp " * 6}
    page = editor(box("a", "text", props, x=10, y=40, w=60, h=60))
    unpick(page)
    frame = at(page, "a").locator(".frame")
    expect(frame).to_have_class(re.compile(r"\btight\b"))
    measure = """el => {
        const p = el.querySelector(':scope > p'), r = document.createRange();
        r.setStart(p.firstChild, 0);
        r.setEnd(p.firstChild, 1);
        const lh = parseFloat(getComputedStyle(p).lineHeight);
        return [r.getBoundingClientRect().left, Math.round(p.getBoundingClientRect().height / lh)];
    }"""
    tight = frame.evaluate(measure)
    page.add_style_tag(content=NO_SIDES)
    loose = frame.evaluate(measure)
    assert abs(tight[0] - loose[0]) < 0.5, (tight, loose)
    assert tight[1] == loose[1] > 1, (tight, loose)


@pytest.mark.parametrize("key", REACHES_AT_13)
def test_a_bullet_keeps_its_indent_in_a_tight_text(editor, key):
    """A1: a bullet of a list in a tight text keeps its indent of 1.5 em."""
    props = {**TEXT, "font": key, "size": 20, "align": "left", "text": "Liste"}
    props["rich"] = [{"runs": [{"text": "Liste"}], "list": "bullet"}]
    page = editor(box("a", "text", props, x=10, y=40, w=60, h=40))
    unpick(page)
    item = at(page, "a").locator(".frame .rich p[data-list]").first
    expect(item).to_have_attribute("data-list", "bullet")
    expect(at(page, "a").locator(".frame")).to_have_class(re.compile(r"\btight\b"))
    em = item.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    indent = item.evaluate("el => parseFloat(getComputedStyle(el).paddingLeft)")
    assert abs(indent - 1.5 * em) < 0.5, (indent, em)
