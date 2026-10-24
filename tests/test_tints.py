"""Silbenfarbe: the switch in the format panel, two colours turn by turn, the greys, the setting
that runs the turn on, and the colours with bows, hand fixes and a hand colour.

The docstrings name the lines of the checklist for the feature. The words whose own split the
tests name are ones the patterns split as a child speaks them: Fens-ter, Was-ser, A-bend.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

from contextlib import suppress

from playwright.sync_api import TimeoutError, expect
from ui import (
    LINE,
    RECT,
    TABLE,
    TEXT,
    TINTS,
    box,
    tints,
)

BLUE, RED = "#1a56db", "#e02424"
PAIR = [BLUE, RED]
GREYS = ["#000000", "#707070"]
FIRST, SECOND = "#2f9e44", "#f08c00"
GREEN, ORANGE = "#2f9e44", "#f08c00"
WORDS = {**TEXT, "text": "Fenster Maus"}
# A text with its bows on and "Maus" split by hand.
MENDED = {**TEXT, "text": "Maus", "syllables": True, "breaks": {"maus": [2]}}
CELLS = {**TABLE, "cells": [["Fenster", "Wasser"], ["3", "7"]]}
# The kinds that hold words, each with "Fenster" and "Wasser" in it.
WORDY = {
    "text": [box("a", "text", {**TEXT, "text": "Fenster Wasser"})],
    "shape": [box("a", "shape", {**RECT, "text": "Fenster Wasser"})],
    "table": [box("a", "table", CELLS)],
    "group": [
        box("a", "text", {**TEXT, "text": "Fenster"}, group=["g"]),
        box("b", "shape", {**RECT, "text": "Wasser"}, z=2, group=["g"]),
        box("c", "shape", LINE, z=3, group=["g"]),
    ],
}
GARBAGE = ["red", ["#1a56db"], ["#1a56db", "}*{display:none}"], [1, 2], {"0": "#000000"}, True]

# The stored colour of a stretch of text, and the colour a pixel shows, from the page's own text.
TINTED = f"""([names, want]) => {{
    const found = names.flatMap((name) => {{
        const block = document.querySelector(`.block[data-id="${{name}}"]`);
        return block ? ({TINTS})(block) : [];
    }});
    return JSON.stringify(found) === JSON.stringify(want);
}}"""
SPANS = """(block) => {
    const found = [];
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-"))
            for (const range of marked)
                if (block.contains(range.startContainer) && !range.collapsed) found.push(range);
    found.sort((a, b) => a.compareBoundaryPoints(Range.START_TO_START, b));
    return found.map((range) => {
        const box = range.getBoundingClientRect();
        return [box.left, box.right];
    });
}"""
NAMES = "[...CSS.highlights.keys()].filter((name) => name.startsWith('tint-')).sort()"
# Counts each rule for a colour that comes or goes from now on.
RULES = """() => {
    window.rules = 0;
    const own = [...document.head.querySelectorAll("style")].find((el) =>
        el.textContent.startsWith("::highlight(tint-"));
    new MutationObserver((all) => (window.rules += all.length)).observe(own, { childList: true });
}"""
COUNT = """() => {
    let n = 0;
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-")) n += marked.size;
    return n;
}"""
IN_PAPER = """() => {
    const paper = document.querySelector(".sheets li .paper");
    if (!paper) return -1;
    let n = 0;
    for (const [name, marked] of CSS.highlights)
        if (name.startsWith("tint-"))
            for (const range of marked) if (paper.contains(range.startContainer)) n++;
    return n;
}"""


def tint_switch(page):
    return page.locator(".panel").get_by_role("button", name="Silbenfarbe", exact=True)


def greys(page):
    return page.locator(".panel").get_by_role("button", name="Schwarz/Grau", exact=True)


def across(page):
    return page.locator(".panel").get_by_role("button", name="Über Wortgrenzen", exact=True)


def expect_tint_switch(page, on):
    """Waits until the switch says its state, to the eye and to a screen reader."""
    expect(tint_switch(page)).to_have_attribute("aria-pressed", "true" if on else "false")
    expect(tint_switch(page)).to_have_class("on" if on else "")


def set_colour(page, label, value):
    """Picks a colour in a field of the panel as the mouse does: a press, the focus, the pick.

    Headless Chromium opens no colour picker. The `input` comes while a picker is dragged and
    the `change` when it closes.
    """
    control = page.locator(".panel").get_by_label(label, exact=True)
    control.dispatch_event("pointerdown")
    control.focus()
    # React hears only of a value set as the browser sets it.
    control.evaluate(
        """(el, value) => {
            const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
            for (const step of ["#123456", value]) {
                own.set.call(el, step);
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        value,
    )


def luminance(colour):
    """The relative luminance of a colour, as WCAG 2 has it."""
    lit = []
    for i in (1, 3, 5):
        channel = int(colour[i : i + 2], 16) / 255
        lit.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lit[0] + 0.7152 * lit[1] + 0.0722 * lit[2]


def contrast(one, other):
    """The contrast ratio of two colours, from 1 to 21."""
    high, low = sorted([luminance(one), luminance(other)], reverse=True)
    return (high + 0.05) / (low + 0.05)


def near(pixels, colour):
    """The pixels whose every channel lies within 40 of the colour's."""
    target = [int(colour[i : i + 2], 16) for i in (1, 3, 5)]
    return sum(
        all(abs(p - t) <= 40 for p, t in zip(pixel, target, strict=True)) for pixel in pixels
    )


class tinted:
    """The colours of the stretches in the blocks, one block after the other: waits as `expect`.

    The colours are drawn a frame after the text changes, in the open field and the open cell too.
    """

    def __init__(self, page, *names):
        self.page, self.names = page, names

    def to_have_text(self, want):
        # A wait that runs out leaves the telling to the comparison below.
        with suppress(TimeoutError):
            self.page.wait_for_function(TINTED, arg=[self.names, want], timeout=5000)
        assert [tint for name in self.names for tint in tints(self.page, name)] == want

    def to_have_count(self, count):
        assert not count
        self.to_have_text([])


def word(page, name):
    """The button of a word in the panel's list, by the word as it is split."""
    return page.locator(".panel .words").get_by_role("button", name=name, exact=True)


def gap(page, name):
    """The button between two letters of the open word: "Ma|us"."""
    return page.locator(".panel .gaps").get_by_role("button", name=name, exact=True)


def redo(page):
    return page.get_by_label("Wiederholen", exact=True)
