"""The yellow handle that adjusts a bubble's tail, a star's inner points and a triangle's tip."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import re

import pytest
from ui import (
    RECT,
    at,
    box,
    centre,
)

SENTENCE = "Wir lesen heute eine schöne Geschichte."
BUBBLE = {**RECT, "kind": "bubble"}
STAR = {**RECT, "kind": "star"}
TRI = {**RECT, "kind": "triangle"}
# The one element that draws a triangle, a star or a bubble.
OUTLINE = "svg.outline > *"
TEN = box("ten", "text", {"text": "zehn", "size": 10, "align": "left"}, x=150)
NUMBER = re.compile(r"[A-Za-z]|-?\d+(?:\.\d+)?(?:e-?\d+)?")


def mm(page):
    """Sheet pixels per mm."""
    return page.locator(".sheet").bounding_box()["width"] / 210


def handle(page, name):
    return page.locator(f'.sheet .adjust[data-id="{name}"]')


def font_px(block):
    return float(block.locator(".frame").evaluate("el => getComputedStyle(el).fontSize")[:-2])


def overlap(a, b):
    return (
        a["x"] < b["x"] + b["width"]
        and b["x"] < a["x"] + a["width"]
        and a["y"] < b["y"] + b["height"]
        and b["y"] < a["y"] + a["height"]
    )


def same_path(found, want):
    """Two outlines with the same commands, and numbers equal to a millionth."""
    got, expected = NUMBER.findall(found), NUMBER.findall(want)
    assert len(got) == len(expected), (found, want)
    for g, w in zip(got, expected, strict=True):
        if w.isalpha():
            assert g == w, (found, want)
        else:
            assert float(g) == pytest.approx(float(w), abs=1e-6), (found, want)


DEEP = {**STAR, "inside": True, "floor": True, "text": "Super", "size": 18, "align": "center"}


# The word's line lies within its paragraph's box, whose padding holds the ink: it prints whole.
WHOLE = """p => {
  const r = document.createRange();
  r.selectNodeContents(p);
  const s = p.getBoundingClientRect();
  return [...r.getClientRects()].every((q) => q.right <= s.right + 1 && q.left >= s.left - 1);
}"""


def type_at_end(page, name, text):
    page.mouse.dblclick(*centre(at(page, name)))
    page.keyboard.press("End")
    page.keyboard.type(text)
    page.keyboard.press("Escape")
