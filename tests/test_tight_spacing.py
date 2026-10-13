"""Issue #487: a line spacing under 1.3 cuts no ink, on screen, in the open field or in the PDF.

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
OLD_RULES = (
    ".frame p, .frame .rich { overflow: hidden !important; padding-block: 0 !important; "
    "margin-block: 0 !important; }"
)
RICH = [{"runs": [{"text": "ÄÖÜ"}]}, {"runs": [{"text": "gjpß"}]}]
ONE_LINE = "ÄgjpßÖÜ"
MM = 0.3528


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


@pytest.mark.parametrize(
    "layout,key,kind,form,spacing",
    [
        ("middle", key, kind, form, spacing)
        for key in FONTS
        for kind in ("text", "shape")
        for form in ("plain", "rich")
        for spacing in (1.0, 1.1)
    ]
    + [("one_line", key, kind, "plain", 1.0) for key in FONTS for kind in ("text", "shape")],
)
def test_no_ink_is_cut_on_the_screen(editor, layout, key, kind, form, spacing):
    """A1: a text or a shape at a spacing under 1.3 draws its ink as it does with the cut lifted.

    `middle` is a block larger than its text. `one_line` is the issue's block: one line
    high, valign top.
    """
    props = text_props(key, kind, form, spacing)
    if layout == "one_line":
        props |= {"valign": "top"}
        block = box("a", kind, props, x=10, y=40, w=90, h=28 * MM)
    else:
        block = box("a", kind, props, x=10, y=40, w=90, h=40)
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


def test_no_ink_is_cut_in_the_open_text(editor):
    """A1: the open field of a text at a spacing of 1.0 keeps its ink, as its closed block does."""
    props = text_props("urff", "text", "plain", 1.0) | {"valign": "middle"}
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
    """The dark pixels of a PDF page in a block's region, the block plus 3 mm around it."""
    paper = doc[index]
    img = paper.render(scale=4).to_pil().convert("L")
    per_mm = img.width / (paper.get_width() * 25.4 / 72)
    left, top = round((x - 3) * per_mm), round((y - 3) * per_mm)
    right, bottom = round((x + w + 3) * per_mm), round((y + h + 3) * per_mm)
    return sum(img.crop((left, top, right, bottom)).histogram()[:100])


def fetch_pdf(server, client, sheet_id):
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return pypdfium2.PdfDocument(res.content)


def test_no_ink_is_cut_in_the_pdf(server):
    """A2: the same letters print the same ink at 1.0 and 1.3, for texts, shapes and rich texts."""
    client = user()
    first, second, regions = [], [], []
    for i, key in enumerate(FONTS):
        y = 10 + 30 * i
        for x, spacing in ((5, 1.0), (65, 1.3)):
            props = text_props(key, "text", "plain", spacing)
            first.append(box(f"t{i}-{spacing}", "text", props, x=x, y=y, w=50, h=20))
            regions.append((0, x, y, 50, 20))
    for i, key in enumerate(FONTS):
        y = 10 + 30 * i
        for x, kind, form, spacing, w in (
            (5, "shape", "plain", 1.0, 50),
            (65, "shape", "plain", 1.3, 50),
            (125, "text", "rich", 1.0, 35),
            (170, "text", "rich", 1.3, 35),
        ):
            props = text_props(key, kind, form, spacing)
            second.append(box(f"s{i}-{x}", kind, props, x=x, y=y, w=w, h=20))
            regions.append((1, x, y, w, 20))
    mine = sheet(client, first, second)
    doc = fetch_pdf(server, client, mine["id"])
    counts = [pdf_ink(doc, index, x, y, w, h) for index, x, y, w, h in regions]
    for i in range(0, len(counts), 2):
        assert counts[i] > 0
        assert abs(counts[i] - counts[i + 1]) <= 0.02 * max(counts[i], counts[i + 1]), (
            i,
            counts[i : i + 2],
        )


@pytest.mark.parametrize("spacing", [1.0, 1.3])
def test_a_text_too_long_ends_at_the_foot(editor, server, spacing):
    """A3: a text too long for its block is cut at its foot plus the spill, and not before it."""
    text = "\n".join(["gjpß ÄÖÜ"] * 12)
    props = {
        **TEXT,
        "text": text,
        "font": "andika",
        "size": 14,
        "spacing": spacing,
        "valign": "top",
    }
    page = editor(box("a", "text", props, x=10, y=40, w=90, h=20))
    unpick(page)
    block = at(page, "a")
    b = block.bounding_box()
    size_px = block.locator("p").first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    mm = b["height"] / 20
    spill = (1.3 - spacing) / 2 * size_px
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
        # In the PDF: the last 2 mm above the foot hold ink, and nothing lies 0.5 mm past the spill.
        client = user()
        mine = sheet(client, [box("a", "text", props, x=10, y=40, w=90, h=20)])
        paper = fetch_pdf(server, client, mine["id"])[0]
        img = paper.render(scale=4).to_pil().convert("L")
        per_mm = img.width / (paper.get_width() * 25.4 / 72)
        foot_mm = 40 + 20
        spill_mm = (1.3 - spacing) / 2 * 14 * 25.4 / 72
        assert dark_in(img, round((foot_mm - 2) * per_mm), round(foot_mm * per_mm)) > 0
        assert dark_in(img, round((foot_mm + spill_mm + 0.5) * per_mm), img.height) == 0


@pytest.mark.parametrize("spacing", [None, 1.3, 2.0])
@pytest.mark.parametrize("kind", ["text", "shape", "rich", "long"])
@pytest.mark.parametrize("key", FONTS)
def test_the_default_spacing_draws_as_before(editor, key, kind, spacing):
    """A4: at no spacing or at 1.3 and above, the frame has no `tight` class and draws as it did."""
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
    expect(frame).not_to_have_class(re.compile(r"\btight\b"))
    styles = frame.locator("p").first.evaluate(
        """el => {
            const s = getComputedStyle(el);
            return [s.paddingTop, s.paddingBottom, s.marginTop, s.marginBottom, s.overflow];
        }"""
    )
    assert styles == ["0px", "0px", "0px", "0px", "hidden"]
    assert frame.evaluate("el => el.style.clipPath").startswith("inset(-1px")
    clip = clip_of(at(page, "a"))
    before = page.screenshot(clip=clip)
    page.add_style_tag(content=OLD_RULES)
    after = page.screenshot(clip=clip)
    a, b = Image.open(BytesIO(before)).convert("RGB"), Image.open(BytesIO(after)).convert("RGB")
    assert ImageChops.difference(a, b).getbbox() is None
