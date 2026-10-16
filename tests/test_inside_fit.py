"""A circle, triangle or star with its text inside never grows for it: its type shrinks to fit."""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from ui import RECT, at, box, pick, reload, saved, user

SENTENCE = "Male den Hasen in den Kreis und schreibe seinen Namen darunter."
# A star with its text inside, as #655 makes one.
STAR = {
    **RECT,
    "kind": "star",
    "inside": True,
    "text": "Super gemacht!",
    "size": 14,
    "align": "center",
}


def make(page, label, text):
    """Makes a shape from the insert bar, types the text, and presses Escape. It stays picked."""
    page.locator(".insert").get_by_label(label, exact=True).click()
    page.keyboard.press("Enter")
    page.keyboard.type(text)
    page.keyboard.press("Escape")


def enter(page, label, value):
    """Writes the value into a field of the right panel and commits it with Enter."""
    field = page.locator(".geo").get_by_label(label, exact=True)
    field.fill(value)
    field.press("Enter")


def words_on_lines(block):
    """Each word of the block's text with the number of lines its letters stand on."""
    return block.locator(".frame").evaluate(
        """el => {
            const out = [];
            const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
            for (let n = walker.nextNode(); n; n = walker.nextNode()) {
                for (const m of n.data.matchAll(/\\S+/g)) {
                    const r = document.createRange();
                    r.setStart(n, m.index);
                    r.setEnd(n, m.index + m[0].length);
                    const tops = new Set([...r.getClientRects()].map((q) => Math.round(q.top)));
                    out.push({ word: m[0], lines: tops.size });
                }
            }
            return out;
        }"""
    )


def whole(block):
    """Every word stands on one line."""
    words = words_on_lines(block)
    assert words, "no text is drawn"
    assert all(w["lines"] == 1 for w in words), words


def cut(block):
    """Whether the text runs past the bottom of the frame's inner box."""
    return block.locator(".frame").evaluate("el => el.scrollHeight > el.clientHeight + 1")


def font_px(block):
    return block.locator(".frame").evaluate("el => getComputedStyle(el).fontSize")


def test_star_keeps_its_height_and_no_word_splits(editor):
    client = user()
    page = editor(client=client)
    make(page, "Stern", "Super gemacht!")
    (a,) = saved(page, client)
    assert a["h"] == 40, a
    whole(page.locator(".block.sel"))
    assert not cut(page.locator(".block.sel"))


def test_star_stays_whole_at_60_and_30_mm_wide(editor):
    client = user()
    page = editor(client=client)
    make(page, "Stern", "Super gemacht!")
    enter(page, "Breite", "60")
    whole(page.locator(".block.sel"))
    enter(page, "Breite", "30")
    whole(page.locator(".block.sel"))
    assert not cut(page.locator(".block.sel"))


def test_circle_stays_round_and_every_word_is_whole(editor):
    client = user()
    page = editor(client=client)
    make(page, "Kreis", SENTENCE)
    (a,) = saved(page, client)
    assert a["w"] == a["h"], a
    whole(page.locator(".block.sel"))


def past_foot(block):
    """How many px the text's lowest line reaches past the frame's foot, where the clip cuts it."""
    return block.locator(".frame").evaluate(
        """el => {
            const r = document.createRange();
            r.selectNodeContents(el);
            const low = Math.max(...[...r.getClientRects()].map((q) => q.bottom));
            return low - el.getBoundingClientRect().bottom;
        }"""
    )


def uncut_on_paper(page, client, browser, server):
    """The triangle's text reaches no further than its frame on the print page either."""
    saved(page, client)
    paper = printed(browser, server, sheet_id(page))
    try:
        assert past_foot(paper.locator(".block").filter(has_text="Dach")) <= 1
    finally:
        paper.context.close()


def roof(page):
    """The triangle of #660: Das Dach vom Haus, 60 mm wide."""
    make(page, "Dreieck", "Das Dach vom Haus")
    enter(page, "Breite", "60")


@pytest.mark.parametrize("percent", ["50", "30"])
def test_a_triangle_squashed_by_hoehe_percent_cuts_no_line(editor, browser, server, percent):
    client = user()
    page = editor(client=client)
    roof(page)
    enter(page, "Höhe %", percent)
    (a,) = saved(page, client)
    assert past_foot(at(page, a["id"])) <= 1
    whole(at(page, a["id"]))
    uncut_on_paper(page, client, browser, server)


def test_a_triangle_in_a_group_squashed_by_hoehe_percent_cuts_no_line(editor, browser, server):
    client = user()
    page = editor(client=client)
    roof(page)
    page.locator(".insert").get_by_label("Rechteck", exact=True).click()
    page.keyboard.type("x")
    page.keyboard.press("Escape")
    a, b = saved(page, client)
    expect(at(page, b["id"])).to_have_class("block sel")
    at(page, a["id"]).click(modifiers=["Shift"])
    page.keyboard.press("Control+g")
    expect(page.locator(".block.sel")).to_have_count(2)
    enter(page, "Höhe %", "30")
    assert past_foot(at(page, a["id"])) <= 1
    uncut_on_paper(page, client, browser, server)


def test_typing_into_a_new_star_shrinks_as_it_goes_and_breaks_no_word(editor):
    client = user()
    page = editor(client=client)
    page.locator(".insert").get_by_label("Stern", exact=True).click()
    page.keyboard.type("Super gemacht!")
    whole(page.locator(".block.sel"))
    page.keyboard.press("Escape")
    (a,) = saved(page, client)
    assert a["h"] == 40, a


def test_shrunk_star_grows_back_to_full_size(editor):
    page = editor(box("a", "shape", STAR, x=20, y=30, w=40, h=40))
    pick(page, "a")
    enter(page, "Breite", "100")
    full = font_px(at(page, "a"))
    enter(page, "Breite", "30")
    assert font_px(at(page, "a")) != full
    enter(page, "Breite", "100")
    assert font_px(at(page, "a")) == full


def test_a_star_and_a_circle_print_their_words_whole_and_keep_their_shape_after_a_reload(
    editor, browser, server
):
    client = user()
    page = editor(client=client)
    make(page, "Stern", "Super gemacht!")
    make(page, "Kreis", SENTENCE)
    star, circle = saved(page, client)
    reload(page, page.url)
    assert [(b["w"], b["h"]) for b in saved(page, client)] == [(40, 40), (40, 40)]
    whole(at(page, star["id"]))
    whole(at(page, circle["id"]))
    paper = printed(browser, server, sheet_id(page))
    try:
        for words in ("Super", "Hasen"):
            block = paper.locator(".block").filter(has_text=words)
            whole(block)
            assert past_foot(block) <= 1
    finally:
        paper.context.close()
