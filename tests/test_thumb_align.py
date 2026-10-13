"""The thumbnail of a page in Seiten starts a block's text where the page does."""

from playwright.sync_api import expect
from ui import RULING, TEXT, at, box, thumb

# The share of the paragraph's width that lies left of its text: 0 where the text starts at the
# left edge. Measured on the text node, so only a paragraph with text in it can be measured.
SHARE = """(p) => {
  const range = document.createRange();
  range.selectNodeContents(p.firstChild);
  const text = range.getBoundingClientRect();
  const box = p.getBoundingClientRect();
  return (text.left - box.left) / box.width;
}"""

RULING_TEXT = {**RULING, "kind": "l1", "color": "#222222", "text": "Igel"}


def test_the_thumbnail_starts_a_lineaturs_text_at_the_left(editor):
    page = editor(box("a", "ruling", RULING_TEXT, w=120, h=20), theme="")
    expect(thumb(page, 0)).to_be_visible()
    paragraph = thumb(page, 0).locator("p.written")
    align = paragraph.evaluate("p => getComputedStyle(p).textAlign")
    assert align in ("left", "start"), align
    thumb_share = paragraph.evaluate(SHARE)
    assert thumb_share < 0.02, thumb_share
    # On the page the text is a field, so only its alignment is checked there.
    page_align = at(page, "a").locator(".written").evaluate("p => getComputedStyle(p).textAlign")
    assert page_align in ("left", "start"), page_align


def test_the_thumbnail_keeps_a_centred_text_centred(editor):
    page = editor(
        box("t", "text", {**TEXT, "text": "Igel", "align": "center"}, w=120, h=20), theme=""
    )
    expect(thumb(page, 0)).to_be_visible()
    expect(thumb(page, 0).locator("p")).to_have_css("text-align", "center")
