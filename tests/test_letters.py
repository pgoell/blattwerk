"""Zeichen farbig markieren (#849).

Vowels, umlauts, consonants, the first and last letter of a word, and up to three letter groups.
Punctuation stays uncoloured. The same marks work on a text, a shape, a table and a Lineatur.
"""

import pytest
from playwright.sync_api import expect
from ui import RECT, RULING, TABLE, TEXT, at, box, pick, saved, user

RED = "#e02424"
GREEN = "#2f9e44"
ORANGE = "#f08c00"
PURPLE = "#7048e8"
WORDS = "Schule, Ei und die Maus!"
MARKS = {
    "vowels": RED,
    "groups": [
        {"letters": "sch", "where": "start", "color": GREEN},
        {"letters": "ei", "where": "any", "color": ORANGE},
        {"letters": "ie", "where": "end", "color": PURPLE},
    ],
}
# "au" in Maus is one stretch: both letters are vowels.
WANT = [
    ("Sch", GREEN),
    ("u", RED),
    ("e", RED),
    ("Ei", ORANGE),
    ("u", RED),
    ("ie", PURPLE),
    ("au", RED),
]
INKS = r"""(block) => {
    const found = [];
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("ink-"))
            for (const range of marked)
                if (block.contains(range.startContainer) && !range.collapsed)
                    found.push([range, "#" + name.slice(4)]);
    found.sort(([a], [b]) => a.compareBoundaryPoints(Range.START_TO_START, b));
    return found.map(([range, colour]) => [range.toString().replace(/\u00ad/g, ""), colour]);
}"""


def inks(page, name):
    """The stretches a block colours, in order, once the marks are drawn."""
    expect(at(page, name).locator(".unsplit")).to_have_count(0)
    return [tuple(found) for found in at(page, name).evaluate(INKS)]


def block_of(kind):
    """One block of `kind` holding the sentence and the marks."""
    if kind == "text":
        return box("a", "text", {**TEXT, "text": WORDS, "marks": MARKS})
    if kind == "shape":
        return box("a", "shape", {**RECT, "text": WORDS, "align": "left", "marks": MARKS})
    if kind == "table":
        return box(
            "a",
            "table",
            {**TABLE, "cells": [[WORDS]], "cols": [1], "align": "left", "marks": MARKS},
        )
    return box("a", "ruling", {**RULING, "text": WORDS, "marks": MARKS}, h=60)


@pytest.mark.parametrize("kind", ["text", "shape", "table", "ruling"])
def test_letter_marks_colour_text_shape_table_and_lineatur(editor, kind):
    """A group wins over a vowel, and a comma and an exclamation mark stay uncoloured."""
    page = editor(block_of(kind))
    assert inks(page, "a") == WANT
    coloured = "".join(text for text, _ in inks(page, "a"))
    assert "," not in coloured
    assert "!" not in coloured


def test_karo_colours_the_letter_in_its_square(editor):
    """Karo paints the colour on the square's letter. Punctuation keeps the text colour."""
    page = editor(
        box("a", "ruling", {**RULING, "kind": "k5", "text": "Schule!", "marks": {"vowels": RED}})
    )
    expect(at(page, "a").locator(".unsplit")).to_have_count(0)
    fills = (
        at(page, "a")
        .locator("svg.ruling text")
        .evaluate_all(
            "els => els.filter((el) => el.textContent).map((el) => [el.textContent, el.getAttribute('fill')])"
        )
    )
    assert fills == [
        ["S", "currentColor"],
        ["c", "currentColor"],
        ["h", "currentColor"],
        ["u", RED],
        ["l", "currentColor"],
        ["e", RED],
        ["!", "currentColor"],
    ]


def test_the_panel_marks_vowels_and_a_group_at_the_start_of_a_word(editor):
    """Vokale and a Buchstabengruppe write the marks, and Rückgängig takes the vowels back."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Schule!"}), client=client)
    pick(page, "a")
    panel = page.locator(".panel")
    vowels = panel.get_by_role("button", name="Vokale", exact=True)
    vowels.click()
    expect(vowels).to_have_attribute("aria-pressed", "true")
    assert inks(page, "a") == [("u", RED), ("e", RED)]
    assert saved(page, client)[0]["props"]["marks"] == {"vowels": RED}
    page.get_by_label("Rückgängig", exact=True).click()
    expect(vowels).to_have_attribute("aria-pressed", "false")
    assert inks(page, "a") == []
    vowels.click()
    expect(vowels).to_have_attribute("aria-pressed", "true")
    panel.get_by_role("button", name="Buchstabengruppe", exact=True).click()
    panel.get_by_label("Buchstaben 1").fill("sch")
    panel.get_by_label("Stelle 1").select_option("start")
    colour = panel.get_by_label("Farbe der Gruppe 1")
    colour.evaluate(
        """(el, value) => {
            const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
            own.set.call(el, value);
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        GREEN,
    )
    assert inks(page, "a") == [("Sch", GREEN), ("u", RED), ("e", RED)]
    stored = saved(page, client)[0]["props"]["marks"]
    assert stored["vowels"] == RED
    assert stored["groups"] == [{"letters": "sch", "where": "start", "color": GREEN}]
