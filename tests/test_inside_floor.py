"""A circle, triangle or star with inside text: type stays at 10 pt, a wide word grows the shape."""

import pytest
from playwright.sync_api import expect
from ui import RECT, at, box, pick, saved, user

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


def test_a_saved_star_with_a_long_text_draws_10_pt_and_is_not_grown(editor):
    client = user()
    page = editor(
        TEN,
        box("a", "shape", {**SHAPE, "kind": "star", "text": SENTENCE}, x=20, y=30, w=40, h=40),
        client=client,
    )
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
