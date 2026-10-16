"""A text cut at the page's foot shows whole lines only, and the editor marks it."""

import httpx
import pypdfium2
from playwright.sync_api import expect
from test_foot_stop import LONG, SENTENCE, type_into
from ui import RECT, TEXT, at, box, unpick, user

# Each line of the frame's text, as the hit test finds it at three heights: True where drawn.
# A line cut through its letters is drawn at some heights and not at others.
LINES = """(frame) => {
  frame.scrollIntoView({ block: "center" });
  const out = [];
  for (const p of frame.querySelectorAll('p')) {
    const r = document.createRange();
    r.selectNodeContents(p);
    for (const q of r.getClientRects()) {
      if (q.width < 1 || q.height < 1) continue;
      out.push([0.25, 0.5, 0.75].map((f) => {
        const hit = document.elementFromPoint(q.left + q.width / 2, q.top + q.height * f);
        return !!hit && hit.closest('.frame') === frame;
      }));
    }
  }
  return out;
}"""


def assert_whole_lines(lines):
    """Every line is drawn at all its heights or at none, and the text has both kinds."""
    assert lines, "no line of text found"
    assert all(all(h) or not any(h) for h in lines), f"a line is cut through: {lines}"
    assert any(all(h) for h in lines), "no line is drawn"
    assert any(not any(h) for h in lines), "no line is hidden: the text does not reach the foot"


def test_a_text_cut_at_the_foot_shows_only_whole_lines(editor):
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=280, w=180, h=17))
    unpick(page)
    assert_whole_lines(at(page, "a").locator(".frame").evaluate(LINES))


def test_a_rectangle_cut_at_the_foot_shows_only_whole_lines(editor):
    rect = {"kind": "rect", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5, "text": LONG}
    page = editor(box("a", "shape", {**rect, "inside": False}, x=15, y=280, w=180, h=17))
    unpick(page)
    assert_whole_lines(at(page, "a").locator(".frame").evaluate(LINES))


def test_a_cut_text_marks_itself_while_nothing_is_picked(editor):
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=280, w=180, h=17))
    unpick(page)
    expect(at(page, "a").locator(".frame")).to_have_attribute("data-cut", "true")
    mark = at(page, "a").evaluate("el => getComputedStyle(el, '::after').content")
    assert mark != "none"


def test_the_mark_goes_when_the_text_fits_again(editor):
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=280, w=180, h=17))
    unpick(page)
    expect(at(page, "a").locator(".frame")).to_have_attribute("data-cut", "true")
    type_into(page, "Hallo")
    unpick(page)
    expect(at(page, "a").locator(".frame")).not_to_have_attribute("data-cut", "true")


# The clip of a frame at its level, from its clip-path, against its lines.
# `straddles` counts the lines the clip runs through. The block is level for the measure.
LEVEL = r"""(name) => {
  const block = document.querySelector(`.block[data-id="${name}"]`);
  const frame = block.querySelector('.frame');
  const was = block.style.transform;
  block.style.transform = 'none';
  const box = frame.getBoundingClientRect();
  const zoom = box.width / frame.offsetWidth || 1;
  const cut = parseFloat(/calc\(100% - ([\d.]+)px\)/.exec(getComputedStyle(frame).clipPath)[1]);
  const line = box.top + cut * zoom;
  const rects = [];
  for (const p of frame.querySelectorAll('p')) {
    const r = document.createRange();
    r.selectNodeContents(p);
    rects.push(...r.getClientRects());
  }
  const cutting = (q) => q.width >= 1 && q.top + q.height / 4 < line - 0.5 && q.bottom > line + 0.5;
  const straddles = rects.filter(cutting).length;
  block.style.transform = was;
  return { lines: rects.length, straddles };
}"""


def test_a_turned_text_cut_at_the_foot_marks_and_keeps_whole_lines(editor):
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=280, w=60, h=17, angle=10))
    unpick(page)
    expect(at(page, "a").locator(".frame")).to_have_attribute("data-cut", "true")
    level = page.evaluate(LEVEL, "a")
    assert level["lines"] > 0
    assert level["straddles"] == 0


def test_a_text_cut_at_the_foot_prints_only_whole_lines(editor, server):
    client = user()
    seven = " ".join([SENTENCE] * 12)
    page = editor(
        box("a", "text", {**TEXT, "text": seven}, x=15, y=255, w=180, h=42), client=client
    )
    unpick(page)
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    picture = pypdfium2.PdfDocument(res.content)[0].render(scale=4).to_pil().convert("L")
    per_mm = picture.height / 297
    lowest = 0
    for y in range(int(255 * per_mm), picture.height):
        strip = picture.crop((int(15 * per_mm), y, int(150 * per_mm), y + 1))
        if strip.getextrema()[0] < 128:
            lowest = y
    # On master the cut line touches the foot; with whole lines the ink stops above it.
    assert lowest / per_mm < 296, f"ink reaches {lowest / per_mm:.2f} mm"


STAR = {**RECT, "kind": "star", "inside": True, "size": 14, "align": "center"}


def test_a_saved_star_with_too_many_words_prints_only_whole_lines(editor):
    # Saved, not picked: the text stops at the star's inner box, and no line runs through its foot.
    star = {**STAR, "text": "Wir lesen heute eine schöne Geschichte.", "floor": True}
    page = editor(box("a", "shape", star, x=20, y=30, w=40, h=40))
    expect(at(page, "a").locator(".frame")).to_have_attribute("data-cut", "true")
    level = page.evaluate(LEVEL, "a")
    assert level["lines"] > 0
    assert level["straddles"] == 0


def test_a_short_text_in_a_star_gets_no_mark(editor):
    page = editor(box("a", "shape", {**STAR, "text": "Hallo"}, x=20, y=30, w=40, h=40))
    expect(at(page, "a").locator(".frame")).not_to_have_attribute("data-cut", "true")


def test_a_text_that_fits_gets_no_mark_and_no_clip(editor):
    # Extra: a text in the middle of the page is drawn as before, with no cut and no mark.
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=40, w=180, h=12))
    unpick(page)
    expect(at(page, "a").locator(".frame")).not_to_have_attribute("data-cut", "true")
    assert_whole_lines(at(page, "a").locator(".frame").evaluate(LINES))
