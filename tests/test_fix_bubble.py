"""#424: a speech bubble filled from the Lernwörter keeps its words in its body, above its tail.

The body is the top three quarters of the frame. The checklist lines are named in each docstring.
"""

import pytest
from playwright.sync_api import expect
from test_feed import CHOICE
from test_feed_print import printed, sheet_id
from ui import RECT, TEXT, at, box, pick, saved, sheet, user

WORDS = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule", "Garten"]
BUBBLE = {**RECT, **TEXT, "kind": "bubble", "list": True}

# Each paragraph's bottom, and the frame's rect, as the body of the frame is measured.
BODY = """(root) => {
    const frame = root.querySelector('.frame').getBoundingClientRect();
    const body = frame.top + 0.75 * frame.height;
    return [...root.querySelectorAll('.frame p')].map(
        (p) => body - p.getBoundingClientRect().bottom,
    );
}"""

# The gap from the frame's top to the first paragraph, and from the last paragraph to the body edge.
EDGES = """(root) => {
    const frame = root.querySelector('.frame').getBoundingClientRect();
    const paras = [...root.querySelectorAll('.frame p')].map((p) => p.getBoundingClientRect());
    return {
        top: paras[0].top - frame.top,
        foot: frame.top + 0.75 * frame.height - paras.at(-1).bottom,
    };
}"""


def in_body(rows):
    """Every paragraph's bottom lies in the body, 0.5 px of tolerance."""
    return all(gap >= -0.5 for gap in rows)


def test_a_linked_bubble_grows_until_its_words_stand_in_its_body(editor):
    """#424 A speech bubble set to Text aus Lernwörtern grows until all words stand in its body,
    above the tail, in the editor."""
    client = user()
    page = editor(
        box("a", "shape", {**BUBBLE, "list": False}, h=30, w=60), client=client, words=WORDS
    )
    pick(page, "a")
    page.get_by_label(CHOICE).select_option(label="Text aus Lernwörtern")
    expect(at(page, "a").locator(".frame.listed .rich p")).to_have_count(len(WORDS))
    saved(page, client)
    assert in_body(at(page, "a").evaluate(BODY))
    block = at(page, "a").bounding_box()["height"]
    frame = at(page, "a").locator(".frame").bounding_box()["height"]
    assert abs(block - frame) < 1


def test_a_linked_bubble_prints_its_words_in_its_body(editor, browser, server):
    """#424 A speech bubble set to Text aus Lernwörtern grows until all words stand in its body,
    and in the PDF."""
    client = user()
    page = editor(
        box("a", "shape", {**BUBBLE, "list": False}, h=30, w=60), client=client, words=WORDS
    )
    pick(page, "a")
    page.get_by_label(CHOICE).select_option(label="Text aus Lernwörtern")
    expect(at(page, "a").locator(".frame.listed .rich p")).to_have_count(len(WORDS))
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    assert in_body(paper.locator(".block").first.evaluate(BODY))
    paper.context.close()


def test_a_bubble_stored_too_low_prints_its_words_in_its_body(browser, server):
    """Implied 8: a linked bubble that the editor has not grown (stored too low, as on a page out
    of view) still prints its words in its body."""
    client = user()
    stored = sheet(client, [box("a", "shape", BUBBLE, h=20, w=60)], words=WORDS)
    paper = printed(browser, server, stored["id"])
    assert in_body(paper.locator(".block").first.evaluate(BODY))
    paper.context.close()


def test_a_linked_rectangle_keeps_its_height(browser, server):
    """Implied 6: a linked rectangle keeps its height: only the bubble leaves room for its tail."""
    client = user()
    rect = {**BUBBLE, "kind": "rect"}
    stored = sheet(
        client,
        [box("r", "shape", rect, h=20, w=60), box("b", "shape", BUBBLE, h=20, w=60, z=2)],
        words=WORDS,
    )
    paper = printed(browser, server, stored["id"])
    # The print page names no block: the bubble is the one with an outline, the rectangle has none.
    rect = paper.locator(".block:not(:has(svg.outline))")
    rect_frame = rect.locator(".frame").bounding_box()
    bubble_frame = paper.locator(".block:has(svg.outline) .frame").bounding_box()
    assert rect_frame["height"] < bubble_frame["height"]
    last = rect.locator(".frame p").last.bounding_box()
    assert rect_frame["y"] + rect_frame["height"] - (last["y"] + last["height"]) < 3 * 96 / 25.4
    paper.context.close()


@pytest.mark.parametrize("valign", ["top", "bottom"])
def test_the_words_of_a_linked_bubble_keep_their_place_in_the_body(browser, server, valign):
    """Implied 6 and the valign of a text: a linked bubble stored 120 mm high keeps its words at
    the top or at the bottom of its body."""
    client = user()
    bubble = {**BUBBLE, "valign": valign}
    stored = sheet(client, [box("b", "shape", bubble, h=120, w=60)], words=WORDS[:3])
    paper = printed(browser, server, stored["id"])
    edges = paper.locator(".block").first.evaluate(EDGES)
    if valign == "top":
        assert edges["top"] < 4 * 96 / 25.4
    else:
        assert 0 <= edges["foot"] < 4 * 96 / 25.4
    paper.context.close()
