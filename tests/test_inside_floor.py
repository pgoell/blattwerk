"""A circle, triangle or star with inside text: type stays at 10 pt, a wide word grows the shape."""

import math

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from ui import RECT, TEXT, at, box, pick, saved, user

SENTENCE = "Wir lesen heute eine schöne Geschichte."
SHAPE = {**RECT, "inside": True, "text": "", "size": 14, "align": "center"}
TEN = box("ten", "text", {"text": "zehn", "size": 10, "align": "left"}, x=150)


def make(page, label, text):
    """Makes a shape from the insert bar, types the text, and presses Escape. It stays picked."""
    page.locator(".insert").get_by_label(label, exact=True).click()
    page.keyboard.press("Enter")
    page.keyboard.type(text)
    page.keyboard.press("Escape")


def font_px(block):
    return float(block.locator(".frame").evaluate("el => getComputedStyle(el).fontSize")[:-2])


def at_least_ten_pt(page, block):
    """The type is no smaller than the 10 pt text beside it."""
    assert font_px(block) >= font_px(at(page, "ten")) - 0.05, (
        font_px(block),
        font_px(at(page, "ten")),
    )


@pytest.mark.parametrize("kind, side", [("circle", 20), ("triangle", 40), ("star", 40)])
def test_a_sentence_in_a_small_shape_keeps_10_pt_and_grows_the_shape(editor, kind, side):
    client = user()
    page = editor(
        TEN, box("a", "shape", {**SHAPE, "kind": kind}, x=20, y=30, w=side, h=side), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE)
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert a["w"] > side and a["h"] > side, a
    if kind == "circle":
        assert a["w"] == a["h"], a
    at_least_ten_pt(page, at(page, "a"))


def test_the_grow_joins_the_typing_in_one_undo(editor):
    client = user()
    page = editor(
        TEN, box("a", "shape", {**SHAPE, "kind": "star"}, x=20, y=30, w=40, h=40), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE)
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert a["w"] > 40, a
    page.keyboard.press("Control+z")
    expect(at(page, "a").locator(".frame")).to_have_text("")
    b = next(s for s in saved(page, client) if s["id"] == "a")
    assert (b["w"], b["h"]) == (40, 40), b


def test_a_star_at_the_foot_stops_and_keeps_10_pt(editor):
    client = user()
    page = editor(
        TEN, box("a", "shape", {**SHAPE, "kind": "star"}, x=100, y=250, w=40, h=40), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE)
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert a["y"] + a["h"] <= 297.05, a
    at_least_ten_pt(page, at(page, "a"))


SAVED = {**RECT, "kind": "star", "inside": True, "text": SENTENCE, "size": 14, "align": "center"}


@pytest.mark.parametrize("kind, side", [("star", 40), ("circle", 20)])
def test_a_saved_small_star_and_circle_print_as_before(editor, server, kind, side):
    client = user()
    page = editor(
        TEN,
        box("a", "shape", {**SAVED, "kind": kind}, x=20, y=30, w=side, h=side),
        client=client,
    )
    # Saved and not picked: the size stays, and the type shrinks past 10 pt as before.
    sheet_id = page.url.rsplit("/", 1)[1]
    a = next(
        b
        for b in client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]
        if b["id"] == "a"
    )
    assert (a["w"], a["h"]) == (side, side), a
    assert font_px(at(page, "a")) < font_px(at(page, "ten")) - 0.05
    # Every line lies inside the frame's box: nothing is drawn past the outline's inner box.
    outside = (
        at(page, "a")
        .locator(".frame")
        .evaluate(
            """el => {
            const f = el.getBoundingClientRect();
            return [...el.querySelectorAll('p')].flatMap((p) => {
                const r = document.createRange();
                r.selectNodeContents(p);
                const out = (q) => q.left < f.left - 1 || q.right > f.right + 1
                  || q.top < f.top - 1 || q.bottom > f.bottom + 1;
                return [...r.getClientRects()].filter((q) => q.width >= 1 && out(q));
            }).length;
        }"""
        )
    )
    assert outside == 0
    # The PDF shows the text only inside the shape's box, one mm of margin for the outline.
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    picture = pypdfium2.PdfDocument(res.content)[0].render(scale=4).to_pil().convert("L")
    per_mm = picture.height / 297
    # The reference text beside it lies at 150 mm: the ink of the shape alone is left of 140 mm.
    left = picture.crop((0, 0, int(140 * per_mm), picture.height))
    x0, y0, x1, y1 = left.point(lambda v: 255 if v < 128 else 0).getbbox()
    assert (
        x0 / per_mm >= 19
        and y0 / per_mm >= 29
        and x1 / per_mm <= 21 + side
        and y1 / per_mm <= 31 + side
    ), (
        x0 / per_mm,
        y0 / per_mm,
        x1 / per_mm,
        y1 / per_mm,
    )


def test_an_edit_of_a_saved_star_brings_the_floor(editor):
    client = user()
    page = editor(TEN, box("a", "shape", SAVED, x=20, y=30, w=40, h=40), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE + " Ende.")
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert a["w"] > 40, a
    at_least_ten_pt(page, at(page, "a"))


def test_the_grown_star_keeps_its_top_left_corner_and_its_page_edge(editor):
    client = user()
    page = editor(
        TEN, box("a", "shape", {**SHAPE, "kind": "star"}, x=20, y=30, w=40, h=40), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE)
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert (a["x"], a["y"]) == (20, 30), a
    assert a["x"] + a["w"] <= 210, a


def test_a_grown_star_is_still_whole_in_its_outline_for_a_child(editor):
    client = user()
    page = editor(
        TEN, box("a", "shape", {**SHAPE, "kind": "star"}, x=20, y=30, w=40, h=40), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(SENTENCE)
    page.keyboard.press("Escape")
    saved(page, client)
    spill = (
        at(page, "a")
        .locator(".frame p")
        .evaluate_all("ps => ps.map((p) => p.scrollWidth - p.clientWidth)")
    )
    assert max(spill) <= 1, spill


HELD = '.panel [data-held="text"]'


def enter_field(page, label, value):
    """Writes the value into a field of the right panel and commits it with Enter."""
    field = page.locator(".geo").get_by_label(label, exact=True)
    field.fill(value)
    field.press("Enter")


def roof_at(page):
    """The triangle of #680: Das Dach vom Haus ist rot und spitz, 60 mm wide."""
    make(page, "Dreieck", "Das Dach vom Haus ist rot und spitz.")
    enter_field(page, "Breite", "60")


def test_the_panel_says_why_a_triangle_cannot_be_squashed_by_its_text(editor):
    client = user()
    page = editor(client=client)
    roof_at(page)
    enter_field(page, "Höhe %", "50")
    expect(page.locator(HELD)).to_contain_text("Der Text braucht diese Höhe")
    enter_field(page, "Höhe", "20")
    expect(page.locator(HELD)).to_be_visible()


def test_the_hint_goes_when_another_block_is_picked(editor):
    client = user()
    roof = {
        **RECT,
        "kind": "triangle",
        "inside": True,
        "text": "Das Dach vom Haus ist rot und spitz.",
        "size": 14,
        "align": "center",
    }
    page = editor(
        box("a", "shape", roof, x=20, y=30, w=60, h=63), box("b", "text", TEXT, z=2), client=client
    )
    pick(page, "a")
    enter_field(page, "Höhe %", "50")
    expect(page.locator(HELD)).to_be_visible()
    pick(page, "b")
    expect(page.locator(HELD)).to_have_count(0)


def test_a_circle_that_takes_its_smaller_height_shows_no_hint(editor):
    client = user()
    circle = {
        **RECT,
        "kind": "circle",
        "inside": True,
        "text": "Hallo",
        "size": 14,
        "align": "center",
    }
    page = editor(box("a", "shape", circle, x=20, y=30, w=40, h=40), client=client)
    pick(page, "a")
    enter_field(page, "Höhe %", "50")
    saved(page, client)
    expect(page.locator(HELD)).to_have_count(0)


def test_a_locked_saved_star_keeps_its_old_type_after_a_bold_click(editor):
    """A locked shape cannot grow, so a change to it must not bring the floor and hide words."""
    client = user()
    page = editor(TEN, box("a", "shape", SAVED, x=20, y=30, w=40, h=40, locked=True), client=client)
    pick(page, "a")
    page.keyboard.press("Control+b")
    expect(at(page, "a").locator(".frame")).to_have_css("font-weight", "700")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    assert (a["w"], a["h"], a["props"].get("floor")) == (40, 40, None), a
    # It still shrinks its words to fit, below the 10 pt text beside it, and hides none.
    assert font_px(at(page, "a")) < font_px(at(page, "ten"))
    expect(at(page, "a").locator(".frame")).not_to_have_attribute("data-cut", "true")


def test_a_turned_star_that_grows_for_a_wide_word_stays_above_the_foot(editor):
    client = user()
    star = {**SHAPE, "kind": "star", "floor": True}
    page = editor(TEN, box("a", "shape", star, x=100, y=235, w=40, h=40, angle=30), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Donaudampfschifffahrtsgesellschaft")
    page.keyboard.press("Escape")
    a = next(b for b in saved(page, client) if b["id"] == "a")
    turn = math.radians(a["angle"])
    low = a["y"] + a["h"] / 2 + a["w"] / 2 * abs(math.sin(turn)) + a["h"] / 2 * abs(math.cos(turn))
    assert low <= 297.01, a
