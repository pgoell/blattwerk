"""A circle, triangle or star with its text inside never grows for it: its type shrinks to fit."""

from test_feed_print import pdf_text
from ui import RECT, at, box, pick, saved, user

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


def test_triangle_with_half_height_is_not_cut(editor, server):
    client = user()
    page = editor(client=client)
    make(page, "Dreieck", "Das Dach vom Haus")
    enter(page, "Breite", "60")
    enter(page, "Höhe %", "50")
    block = page.locator(".block.sel")
    assert not cut(block)
    # Every line of text lies above the bottom edge of the triangle.
    bottom = block.locator(".frame").evaluate("el => el.getBoundingClientRect().bottom")
    lowest = block.locator(".frame").evaluate(
        """el => {
            const r = document.createRange();
            r.selectNodeContents(el);
            return Math.max(...[...r.getClientRects()].map((q) => q.bottom));
        }"""
    )
    assert lowest <= bottom + 1, (lowest, bottom)
    saved(page, client)
    assert "vom Haus" in pdf_text(server, client, page.url.rsplit("/", 1)[1])


def test_shrunk_star_grows_back_to_full_size(editor):
    page = editor(box("a", "shape", STAR, x=20, y=30, w=40, h=40))
    pick(page, "a")
    enter(page, "Breite", "100")
    full = font_px(at(page, "a"))
    enter(page, "Breite", "30")
    assert font_px(at(page, "a")) != full
    enter(page, "Breite", "100")
    assert font_px(at(page, "a")) == full
