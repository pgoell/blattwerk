"""A Karo's text wraps by word, as the field does: a word that does not fit moves whole."""

import math
import re

import pytest
from playwright.sync_api import expect
from ui import at, box, saved, sheet, user

from blattwerk import pdf

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


def marks(page, name):
    """Each letter drawn, as (x, y, character), in the order the svg has them."""
    return [(float(x), float(y), ch) for x, y, ch in at(page, name).evaluate(MARKS)]


def drawn_rows(page, name, row, cols, block=None):
    """The rows as drawn: each letter in the square its position lies in, spaces between."""
    rows = {}
    found = block.evaluate(MARKS) if block else marks(page, name)
    for x, y, ch in [(float(x), float(y), ch) for x, y, ch in found]:
        col, line = math.floor(x / row + 1e-6), math.floor(y / row + 1e-6)
        rows.setdefault(line, [" "] * cols)[col] = ch
    return ["".join(rows[r]).rstrip() for r in sorted(rows)]


@pytest.mark.parametrize("kind,row", [("k5", 5), ("k7", 7)])
def test_a_word_moves_whole_to_the_next_row(editor, kind, row):
    page = editor(
        box("a", "ruling", {"kind": kind, "color": "#222222", "text": SENTENCE}, w=20 * row, h=80)
    )
    assert drawn_rows(page, "a", row, 20) == ROWS_20


@pytest.mark.parametrize("kind,row", [("k5", 5), ("k7", 7)])
def test_the_print_moves_the_word_too(browser, server, kind, row):
    props = {"kind": kind, "color": "#222222", "text": SENTENCE, "syllables": True}
    mine = sheet(user(), [box("a", "ruling", props, w=20 * row, h=80)])["id"]
    # The page the PDF is printed from.
    printed = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    printed.goto(f"{server}/druck/{mine}")
    printed.wait_for_selector("body.ready", state="attached")
    assert drawn_rows(printed, "a", row, 20, printed.locator(".block").first) == ROWS_20
    printed.close()


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
    assert drawn_rows(page, "a", 7, 20) == ROWS_20
    paths = (
        at(page, "a").locator(".syl").evaluate_all("els => els.map((el) => el.getAttribute('d'))")
    )
    assert paths
    for d in paths:
        numbers = [float(v) for v in re.findall(r"-?[\d.]+", d)]
        rows = {math.floor(y / 7 - 0.8 + 1e-6) for y in numbers[1::2]}
        assert len(rows) == 1, d


@pytest.mark.parametrize("kind,row", [("k5", 5), ("k7", 7)])
def test_the_caret_stands_at_the_drawn_square(editor, kind, row):
    page = editor(
        box("a", "ruling", {"kind": kind, "color": "#222222", "text": SENTENCE}, w=20 * row, h=80)
    )
    block = at(page, "a")
    block.dblclick()
    field = block.locator("textarea")
    expect(field).to_be_focused()
    box_ = block.bounding_box()
    scale = box_["width"] / (20 * row)
    for word in ["Wald", "sammeln", "Kastanien", "Herbstbild", "Klasse"]:
        index = SENTENCE.index(word)
        # The word's square, from the rows as drawn: the word must lie whole in one drawn row.
        drawn = drawn_rows(page, "a", row, 20)
        assert any(word in text for text in drawn), word
        line = next(r for r, text in enumerate(drawn) if word in text)
        col = drawn[line].index(word)
        # The left quarter of the letter's square.
        px = box_["x"] + (col * row + row / 4) * scale
        py = box_["y"] + (line * row + row / 2) * scale
        page.mouse.click(px, py)
        assert field.evaluate("el => el.selectionStart") == index, word


@pytest.mark.parametrize(
    "text,word",
    [
        ("b " + "a" * 25 + " cd", "cd"),
        ("Wir lesen Mathe-Heft und mehr", "und"),
        ("Am Montag Kinder-Garten-Fest", "Garten"),
        ("Am Montag ueberall 3-4 und 5", "3-4"),
    ],
)
def test_the_caret_follows_a_break_at_a_hyphen_as_drawn(editor, text, word):
    page = editor(box("a", "ruling", {"kind": "k7", "color": "#222222", "text": text}, w=140, h=80))
    block = at(page, "a")
    block.dblclick()
    field = block.locator("textarea")
    expect(field).to_be_focused()
    box_ = block.bounding_box()
    scale = box_["width"] / (20 * 7)
    drawn = drawn_rows(page, "a", 7, 20)
    assert any(word in line for line in drawn), drawn
    line = next(r for r, t in enumerate(drawn) if word in t)
    col = drawn[line].index(word)
    page.mouse.click(box_["x"] + (col * 7 + 7 / 4) * scale, box_["y"] + (line * 7 + 7 / 2) * scale)
    assert field.evaluate("el => el.selectionStart") == text.index(word)


def test_the_rows_needed_count_moved_words(editor):
    # Char by char the text needs six rows, with the words moved seven: typing grows the Karo.
    client = user()
    page = editor(
        box("a", "ruling", {"kind": "k7", "color": "#222222", "text": ""}, w=140, h=42),
        client=client,
    )
    at(page, "a").dblclick()
    page.keyboard.type(SENTENCE)
    expect(at(page, "a").locator("svg.ruling text")).to_have_count(len(SENTENCE))
    assert drawn_rows(page, "a", 7, 20) == ROWS_20
    assert [b["h"] for b in saved(page, client) if b["id"] == "a"] == [pytest.approx(49)]
