"""A text cut at the page's foot shows whole lines only, and the editor marks it."""

from playwright.sync_api import expect
from test_foot_stop import LONG, type_into
from ui import TEXT, at, box, unpick

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


def test_a_text_that_fits_gets_no_mark_and_no_clip(editor):
    # Extra: a text in the middle of the page is drawn as before, with no cut and no mark.
    page = editor(box("a", "text", {**TEXT, "text": LONG}, x=15, y=40, w=180, h=12))
    unpick(page)
    expect(at(page, "a").locator(".frame")).not_to_have_attribute("data-cut", "true")
    assert_whole_lines(at(page, "a").locator(".frame").evaluate(LINES))
