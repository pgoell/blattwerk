"""A Karo's text wraps by word, as the field does: a word that does not fit moves whole."""

import math
import re

import pytest
from ui import at, box

SENTENCE = (
    "Am Montag gehen wir in den Wald und sammeln bunte Blaetter, Eicheln und Kastanien fuer unser "
    "Herbstbild in der Klasse."
)
# The rows the field wraps the sentence to on 20 squares, as both browsers show it.
ROWS_20 = [
    "Am Montag gehen wir",
    "in den Wald und",
    "sammeln bunte",
    "Blaetter, Eicheln",
    "und Kastanien fuer",
    "unser Herbstbild in",
    "der Klasse.",
]
# Each letter's svg text, with its position in mm.
MARKS = """(block) => [...block.querySelectorAll('svg.ruling text')].map(
  (t) => [t.getAttribute('x'), t.getAttribute('y'), t.textContent])"""


def drawn_rows(page, name, row, cols):
    """The rows as drawn: each letter in the square its position lies in, spaces between."""
    rows = {}
    for x, y, ch in at(page, name).evaluate(MARKS):
        col, line = math.floor(float(x) / row + 1e-6), math.floor(float(y) / row + 1e-6)
        rows.setdefault(line, [" "] * cols)[col] = ch
    return ["".join(rows[r]).rstrip() for r in sorted(rows)]


@pytest.mark.parametrize("kind,row", [("k5", 5), ("k7", 7)])
def test_a_word_moves_whole_to_the_next_row(editor, kind, row):
    page = editor(
        box("a", "ruling", {"kind": kind, "color": "#222222", "text": SENTENCE}, w=20 * row, h=80)
    )
    assert drawn_rows(page, "a", row, 20) == ROWS_20


@pytest.mark.parametrize("kind,row", [("k5", 5), ("k7", 7)])
def test_a_word_longer_than_a_row_still_breaks(editor, kind, row):
    text = "a" * 40 + " b"
    page = editor(
        box("a", "ruling", {"kind": kind, "color": "#222222", "text": text}, w=20 * row, h=80)
    )
    assert drawn_rows(page, "a", row, 20) == ["a" * 20, "a" * 20, " b"]


def test_the_bows_stay_in_one_row(editor):
    props = {"kind": "k7", "color": "#222222", "text": SENTENCE, "syllables": True}
    page = editor(box("a", "ruling", props, w=140, h=80))
    paths = (
        at(page, "a").locator(".syl").evaluate_all("els => els.map((el) => el.getAttribute('d'))")
    )
    assert paths
    for d in paths:
        numbers = [float(v) for v in re.findall(r"-?[\d.]+", d)]
        ys = numbers[1::2]
        rows = {math.floor(y / 7 - 0.8 + 1e-6) for y in ys}
        assert len(rows) == 1, d
