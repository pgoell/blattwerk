"""#423: a long word's line and its solution stay in their column, in a linked text in columns.

The checklist lines are named in each docstring.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from ui import RECT, TEXT, at, box, pick, user

from blattwerk import pdf

WORDS = ["Hase", "Kuh", "Blume", "Birne", "Fahrrad", "Schmetterling"]
COLUMNS = {**TEXT, "size": 16, "list": True, "listCols": 3, "mix": 7}
LONG = ["Hase", "Donaudampfschifffahrtsgesellschaftskapitän"]

# Each word's line lies inside its paragraph, and is at least as wide as its word.
LINES = """(root) => [...root.querySelectorAll('.mix')].map((mix) => {
    const p = mix.closest('p').getBoundingClientRect();
    const line = mix.querySelector('.gap.line').getBoundingClientRect();
    const word = mix.querySelector('.mixed').getBoundingClientRect();
    return {
        inside: line.left >= p.left - 0.5 && line.right <= p.right + 0.5,
        wide: line.width >= word.width - 0.5,
    };
})"""

# Every client rect of a word, and of the key's word on its line, lies inside its paragraph.
RECTS = """(root) => [...root.querySelectorAll('.mix')].flatMap((mix) => {
    const p = mix.closest('p').getBoundingClientRect();
    const parts = [...mix.querySelectorAll('.mixed, .gap.line > span')];
    const boxes = parts.flatMap((el) => [...el.getClientRects()]);
    return boxes.map((r) => r.left >= p.left - 0.5 && r.right <= p.right + 0.5);
})"""


def holds(rows):
    return all(all(row.values()) for row in rows)


def key(browser, server, mine):
    """The answer key's print page, with a render token. The caller closes its context."""
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}?loesungen")
    paper.wait_for_selector("body.ready", state="attached")
    return paper


@pytest.mark.parametrize("kind", ["text", "shape"])
@pytest.mark.parametrize("line", [None, "under"], ids=["after", "under"])
def test_a_long_words_line_stays_in_its_column(editor, browser, server, kind, line):
    """#423 Schüttelwörter from Lernwörter in three columns: the line of a long word is at least
    as long as the word and lies inside the block, on a text and on a shape, with the line after
    and under the word."""
    client = user()
    props = {**COLUMNS, **({"mixLine": line} if line else {})}
    if kind == "shape":
        props = {**RECT, **props}
    page = editor(box("a", kind, props, h=20, w=180), client=client, words=WORDS)
    pick(page, "a")
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(len(WORDS))
    assert holds(at(page, "a").evaluate(LINES))
    paper = printed(browser, server, sheet_id(page))
    assert holds(paper.locator("body").evaluate(LINES))
    paper.context.close()


def test_the_key_shows_a_long_word_whole(editor, browser, server):
    """#423 The answer key shows the long word whole, inside the block."""
    client = user()
    page = editor(box("a", "text", COLUMNS, h=20, w=180), client=client, words=WORDS)
    paper = key(browser, server, sheet_id(page))
    assert all(paper.locator("body").evaluate(RECTS))
    assert paper.locator(".mix .gap.line > span").all_text_contents() == WORDS
    paper.context.close()


def test_a_word_wider_than_its_block_breaks_and_keeps_its_line(editor, browser, server):
    """#423 One column, block 80 mm wide, a word wider than the block: the word breaks, is whole in
    the key (every letter to be seen, over two lines if need be) and has a line."""
    client = user()
    props = {**TEXT, "size": 16, "list": True, "mix": 7}
    page = editor(box("a", "text", props, h=20, w=80), client=client, words=LONG)
    pick(page, "a")
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(len(LONG))
    pupils = printed(browser, server, sheet_id(page))
    solved = key(browser, server, sheet_id(page))
    for paper in (pupils, solved):
        assert all(paper.locator("body").evaluate(RECTS))
        line = paper.locator(".mix").last.locator(".gap.line")
        box_line = line.bounding_box()
        assert box_line["width"] >= 40 * 96 / 25.4
        drawn = line.locator("svg").bounding_box()
        assert drawn["y"] >= box_line["y"] + box_line["height"] / 2
    assert solved.locator(".mix .gap.line > span").last.text_content() == LONG[1]
    pupils.context.close()
    solved.context.close()
