"""#433 and #434: a speech bubble with its own text keeps its lines in its body; a word wider than a
text of one's own breaks and keeps its line.

The checklist lines are named in each docstring.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed import CHOICE
from test_feed_print import printed, sheet_id
from test_fix_bubble import BODY, WORDS, in_body
from test_fix_mix import LINES, RECTS, holds, key
from ui import FIELD, RECT, TEXT, at, box, pick, saved, sheet, user

LONG = "Donaudampfschifffahrtsgesellschaftskapitän"

# Each paragraph of the field: its bottom above the body's foot, flipped its top below the tail.
FIELD_GAPS = """(root, flip) => {
    const frame = root.querySelector('.frame').getBoundingClientRect();
    return [...root.querySelectorAll('.ProseMirror p')].map((p) => {
        const r = p.getBoundingClientRect();
        const body = flip ? frame.top + 0.25 * frame.height : frame.top + 0.75 * frame.height;
        return flip ? r.top - body : body - r.bottom;
    });
}"""

# No paragraph clips: a word too wide for its block breaks, it is not cut off.
UNCLIPPED = """(root) => [...root.querySelectorAll('.frame p')].map(
    (p) => p.scrollWidth <= p.clientWidth + 1,
)"""

# Each word's line and its word, in the row of the line: whichever way the line stands.
SAME_ROW = """(root) => [...root.querySelectorAll('.mix')].map((mix) => {
    const line = mix.querySelector('.gap.line').getBoundingClientRect();
    const word = mix.querySelector('.mixed').getBoundingClientRect();
    return Math.abs(line.top - word.top) < word.height / 2;
})"""


def breaks(root):
    """A word too wide for its block: every letter and its line lie in the paragraph, which does not
    clip, and the line is drawn in the lower half of its box."""
    assert all(root.evaluate(RECTS))
    assert holds(root.evaluate(LINES))
    assert all(root.evaluate(UNCLIPPED))
    line = root.locator(".mix .gap.line")
    box_line = line.bounding_box()
    assert box_line["width"] >= 40
    drawn = line.locator("svg").bounding_box()
    assert drawn["y"] >= box_line["y"] + box_line["height"] / 2


def test_a_bubble_with_its_own_text_grows_until_its_lines_stand_in_its_body(editor):
    """#433 A speech bubble with its own text grows until all its lines stand in its body, above
    its tail, in the editor."""
    client = user()
    page = editor(
        box("a", "shape", {**RECT, **TEXT, "kind": "bubble", "text": ""}, h=30, w=60), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    for word in WORDS:
        page.keyboard.type(word)
        page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    saved(page, client)
    assert in_body(at(page, "a").evaluate(BODY))
    block = at(page, "a").bounding_box()["height"]
    frame = at(page, "a").locator(".frame").bounding_box()["height"]
    assert abs(block - frame) < 1


def test_a_bubble_with_its_own_text_prints_its_lines_in_its_body(editor, browser, server):
    """#433 A speech bubble with its own text grows until all its lines stand in its body, and in
    the PDF."""
    client = user()
    page = editor(
        box("a", "shape", {**RECT, **TEXT, "kind": "bubble", "text": ""}, h=30, w=60), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    for word in WORDS:
        page.keyboard.type(word)
        page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert in_body(paper.locator(".block").first.evaluate(BODY))
    paper.context.close()


def test_a_bubble_cut_loose_keeps_its_words_in_its_body(editor, browser, server):
    """#433 A linked speech bubble cut loose to Eigener Text keeps its words in its body, in the
    editor and in the PDF."""
    client = user()
    bubble = {**RECT, **TEXT, "kind": "bubble", "list": True}
    page = editor(box("a", "shape", bubble, h=30, w=60), client=client, words=WORDS)
    pick(page, "a")
    page.get_by_label(CHOICE).select_option(label="Eigener Text")
    expect(at(page, "a").locator(".frame")).not_to_have_class(re.compile(r"\blisted\b"))
    saved(page, client)
    assert in_body(at(page, "a").evaluate(BODY))
    paper = printed(browser, server, sheet_id(page))
    assert in_body(paper.locator(".block").first.evaluate(BODY))
    paper.context.close()


def test_a_flipped_bubble_with_its_own_text_keeps_its_lines_under_its_tail(browser, server):
    """#433 A flipped speech bubble with its own text keeps its lines under its tail: the tail is
    the top quarter of the frame and the lines lie in the rest."""
    client = user()
    bubble = {**RECT, **TEXT, "kind": "bubble", "text": "Hund\nKatze\nMaus"}
    stored = sheet(client, [box("a", "shape", bubble, h=60, w=60, flipY=True)])
    paper = printed(browser, server, stored["id"])
    tops = paper.locator(".block").first.evaluate(
        """(root) => {
            const frame = root.querySelector('.frame').getBoundingClientRect();
            const body = frame.top + 0.25 * frame.height;
            const paras = [...root.querySelectorAll('.frame p')];
            const rects = paras.map((p) => p.getBoundingClientRect());
            return rects.map((p) => [p.top - body, frame.bottom - p.bottom]);
        }"""
    )
    assert tops
    assert all(top >= -0.5 and foot >= -0.5 for top, foot in tops), tops
    paper.context.close()


@pytest.mark.parametrize("flip", [False, True], ids=["upright", "flipped"])
def test_a_bubble_being_typed_in_shows_its_text_in_its_body(editor, flip):
    """#433 A speech bubble being typed in keeps its text in its body: the field's lines lie in the
    body, and flipped top to bottom, below the tail."""
    client = user()
    bubble = {**RECT, **TEXT, "kind": "bubble", "text": "Hund\nKatze\nMaus"}
    page = editor(box("a", "shape", bubble, h=60, w=60, flipY=flip), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_visible()
    gaps = at(page, "a").evaluate(FIELD_GAPS, flip)
    assert gaps
    assert in_body(gaps), gaps


@pytest.mark.parametrize("kind", ["text", "shape"])
@pytest.mark.parametrize("line", ["after", "under"])
def test_a_lone_word_wider_than_its_block_breaks_and_keeps_its_line(
    editor, browser, server, kind, line
):
    """#434 A word wider than its block, alone in a text of one's own, breaks and keeps its line in
    the editor and in the PDF, on a text and on a shape, with the line after and under the word."""
    client = user()
    props = {**TEXT, "size": 16, "text": LONG, "mix": 7, "mixLine": line}
    if kind == "shape":
        props = {**RECT, **props}
    page = editor(box("a", kind, props, h=20, w=60), client=client)
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(1)
    breaks(at(page, "a"))
    paper = printed(browser, server, sheet_id(page))
    breaks(paper.locator("body"))
    paper.context.close()


def test_the_key_shows_a_lone_long_word_whole(editor, browser, server):
    """#434 The answer key shows a lone long word whole, inside its block, on its line."""
    client = user()
    props = {**TEXT, "size": 16, "text": LONG, "mix": 7, "mixLine": "after"}
    page = editor(box("a", "text", props, h=20, w=60), client=client)
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(1)
    paper = key(browser, server, sheet_id(page))
    assert all(paper.locator("body").evaluate(RECTS))
    assert paper.locator(".mix .gap.line > span").all_text_contents() == [LONG]
    paper.context.close()


def test_a_word_in_a_sentence_keeps_its_line_beside_it(editor, browser, server):
    """#434 A word in a sentence keeps its line beside it, on the same row, in the editor and in the
    PDF: the words of a sentence are not a lone word."""
    client = user()
    props = {**TEXT, "size": 16, "text": "Der Hund bellt", "mix": 7, "mixLine": "after"}
    page = editor(box("a", "text", props, h=20, w=180), client=client)
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(3)
    assert all(at(page, "a").evaluate(SAME_ROW))
    assert at(page, "a").locator("p.lone").count() == 0
    paper = printed(browser, server, sheet_id(page))
    assert all(paper.locator(".block").first.evaluate(SAME_ROW))
    assert paper.locator("p.lone").count() == 0
    paper.context.close()


def test_a_text_cut_loose_still_breaks_a_long_word(editor, browser, server):
    """#434 A text cut loose from Lernwörter to Eigener Text still breaks a long word, with its
    line, in the editor, in the PDF and in the answer key."""
    client = user()
    linked = {**TEXT, "size": 16, "list": True, "mix": 7}
    page = editor(box("a", "text", linked, h=20, w=80), client=client, words=["Hase", LONG])
    pick(page, "a")
    page.get_by_label(CHOICE).select_option(label="Eigener Text")
    expect(at(page, "a").locator(".frame")).not_to_have_class(re.compile(r"\blisted\b"))
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(2)
    assert all(at(page, "a").evaluate(RECTS))
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert all(paper.locator("body").evaluate(RECTS))
    paper.context.close()
    solved = key(browser, server, sheet_id(page))
    assert all(solved.locator("body").evaluate(RECTS))
    assert solved.locator(".mix .gap.line > span").last.text_content() == LONG
    solved.context.close()


def test_a_bubbles_solution_words_stand_under_its_text(browser, server):
    """Review of #433: a bubble with a gap and Lösungswörter prints the box of the words under its
    text, not over it, and both in its body."""
    client = user()
    runs = [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt laut im Garten"}]
    gapped = {**RECT, **TEXT, "kind": "bubble", "rich": [{"runs": runs}], "bank": 7}
    stored = sheet(client, [box("a", "shape", gapped, h=80, w=60)])
    paper = printed(browser, server, stored["id"])
    frame = paper.locator(".frame").bounding_box()
    rich = paper.locator(".frame .rich").bounding_box()
    bank = paper.locator(".frame .bank").bounding_box()
    assert bank["y"] >= rich["y"] + rich["height"]
    assert bank["y"] + bank["height"] <= frame["y"] + 0.75 * frame["height"] + 0.5
    paper.context.close()


def test_a_bubble_stored_too_low_for_its_text_keeps_its_first_line(browser, server):
    """Review of #433: a bubble too low for its own text, set to the middle as a shape is, starts
    its text at the top of its body, as any other shape does: the first lines are not cut off."""
    client = user()
    rich = [{"runs": [{"text": word}]} for word in [*WORDS, "Baum", "Haus", "Auto"]]
    low = {**RECT, **TEXT, "kind": "bubble", "valign": "middle", "rich": rich}
    stored = sheet(client, [box("a", "shape", low, h=30, w=60)])
    paper = printed(browser, server, stored["id"])
    frame = paper.locator(".frame").bounding_box()
    first = paper.locator(".frame p").first.bounding_box()
    assert first["y"] >= frame["y"]
    paper.context.close()
