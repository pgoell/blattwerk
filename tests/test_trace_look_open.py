"""A trace look still opens when the block has no size, and an open text does not fade."""

import io

import pytest
from PIL import Image
from playwright.sync_api import expect
from test_trace_look import FONTS
from ui import TEXT, at, box, pick, unpick

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
            # j reaches left of its place and f right of it.
            "text": "jgf Tgjf",
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
        assert abs(count - full) <= 0.005 * full, (align, count, full)


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
