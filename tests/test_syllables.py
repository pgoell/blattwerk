"""Silbenbögen: the switch in the format panel, the bows in the open field, a word mended by hand.

The docstrings name the lines of the frozen checklist of PR #356. The words whose own split the
tests name are ones the patterns split as a child speaks them: Fens-ter, Was-ser, Ta-sche.
"""

from contextlib import suppress

import pytest
from playwright.sync_api import TimeoutError, expect
from test_lock import fest, undo
from test_painter import held
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    expect_picked,
    pick,
    syls,
    user,
)

WORDS = {**TEXT, "text": "Fenster Maus"}
BOWS = ["Fens", "ter", "Maus"]
# The kinds that hold words, each with "Fenster" and "Wasser" in it.
CELLS = {**TABLE, "cells": [["Fenster", "Wasser"], ["3", "7"]]}
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


def switch(page):
    return page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True)


def expect_switch(page, on):
    """Waits until the switch says its state, to the eye and to a screen reader."""
    expect(switch(page)).to_have_attribute("aria-pressed", "true" if on else "false")
    expect(switch(page)).to_have_class("on" if on else "")


class bows:
    """The syllables with a bow in the blocks, one block after the other: waits as `expect` does.

    The bows are drawn a frame after the text changes, in the open field and the open cell too.
    """

    SHOWN = """([names, want]) => {
        const of = (name) => [...document.querySelectorAll(`.block[data-id="${name}"] .syl`)];
        const shown = names.flatMap(of).map((el) => el.dataset.syl ?? el.textContent);
        return JSON.stringify(shown) === JSON.stringify(want);
    }"""

    def __init__(self, page, *names):
        self.page, self.names = page, names

    def to_have_text(self, want):
        # A wait that runs out leaves the telling to the comparison below.
        with suppress(TimeoutError):
            self.page.wait_for_function(self.SHOWN, arg=[self.names, want], timeout=5000)
        assert [syl for name in self.names for syl in syls(self.page, name)] == want

    def to_have_count(self, count):
        assert not count
        self.to_have_text([])


def word(page, name):
    """The button of a word in the panel's list, by the word as it is split."""
    return page.locator(".panel .words").get_by_role("button", name=name, exact=True)


def gap(page, name):
    """The button between two letters of the open word: "Ma|us"."""
    return page.locator(".panel .gaps").get_by_role("button", name=name, exact=True)


def reset(page):
    return page.locator(".panel").get_by_role("button", name="Zurücksetzen", exact=True)


def redo(page):
    return page.get_by_label("Wiederholen", exact=True)


def test_one_click_draws_a_bow_under_each_syllable_and_one_more_takes_them_away(editor):
    """A1: the switch stands with the text settings; one click on, one off; its state shows."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    expect_switch(page, False)
    # It follows the last text setting: the hint of the trace choice (Andika has no dotted cut).
    assert (
        switch(page).evaluate("(el) => el.previousElementSibling.textContent")
        == "Gepunktet gibt es nur in der Grundschrift (Urff)."
    )
    bows(page, "a").to_have_count(0)
    switch(page).click()
    expect_switch(page, True)
    bows(page, "a").to_have_text(BOWS)
    assert held(page, client)["a"]["syllables"] is True
    switch(page).click()
    expect_switch(page, False)
    bows(page, "a").to_have_count(0)
    # Off is the sheet as it was before.
    assert held(page, client)["a"] == WORDS


@pytest.mark.parametrize("kind", list(WORDY))
def test_every_kind_that_holds_words_takes_the_bows(editor, kind):
    """A10: a text, a shape with text, a table's cells, and each member of a group with words."""
    client = user()
    page = editor(*WORDY[kind], client=client)
    at(page, "a").click()
    wordy = ["a", "b"] if kind == "group" else ["a"]
    expect_picked(page, *(b["id"] for b in WORDY[kind]))
    expect(switch(page)).to_have_count(1)
    switch(page).click()
    expect_switch(page, True)
    # The digits of a table get none.
    bows(page, *wordy).to_have_text(["Fens", "ter", "Was", "ser"])
    now = held(page, client)
    assert [now[name].get("syllables") for name in wordy] == [True] * len(wordy)
    # A group's line holds no words and stays as it is.
    assert kind != "group" or now["c"] == LINE


# A Lineatur with lines takes the bows since #357; Karo has none (tests/test_ruling_bows.py).
@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths"])
def test_a_block_that_holds_no_words_shows_no_switch(editor, kind):
    """A10: a line, a picture, a symbol and maths have no bows to switch on."""
    client = user()
    page = editor(*({**b, "locked": False} for b in fest(client, kind)), client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(switch(page)).to_have_count(0)


def test_a_block_with_no_words_picked_along_stays_as_it_is(editor):
    """A10: the switch of a text leaves a line picked with it; a Karo takes it (#676)."""
    client = user()
    karo = {**RULING, "kind": "k5"}
    blocks = [
        box("a", "text", WORDS),
        box("r", "ruling", karo, z=2),
        box("l", "shape", LINE, z=3),
    ]
    page = editor(*blocks, client=client)
    pick(page, "a", "r", "l")
    switch(page).click()
    bows(page, "a").to_have_text(BOWS)
    now = held(page, client)
    assert (now["r"], now["l"]) == ({**karo, "syllables": True}, LINE)


def test_the_format_of_the_words_passes_a_line_picked_along_and_the_stroke_reaches_it(editor):
    """Issue #359: a line holds no words, so it takes no script and no size. Its dashes it takes."""
    client = user()
    page = editor(box("a", "text", TEXT), box("l", "shape", LINE, z=2), client=client)
    pick(page, "a", "l")
    panel = page.locator(".panel")
    panel.get_by_label("Schriftart").select_option("grund")
    panel.get_by_label("Schrift größer").click()
    # The words' own "Rechts": the one beside it moves the blocks.
    panel.locator('button[aria-pressed][aria-label="Rechts"]').click()
    now = held(page, client)
    assert now["a"] == {**TEXT, "font": "grund", "size": 16, "align": "right"}
    assert now["l"] == LINE
    panel.get_by_label("Gestrichelt").click()
    now = held(page, client)
    assert now["l"] == {**LINE, "dash": "dashed"}
    assert now["a"]["dash"] == "dashed"


def test_the_switch_goes_on_unless_all_picked_have_the_bows_in_one_undo_step(editor):
    """I1: as bold, for a text, a shape and a table picked together; one step for all of them."""
    client = user()
    blocks = [
        box("a", "text", {**WORDS, "syllables": True}),
        box("b", "shape", {**RECT, "text": "Wasser"}, z=2),
        box("t", "table", CELLS, z=3),
    ]
    page = editor(*blocks, client=client)

    def have():
        now = held(page, client)
        return [name for name in "abt" if now[name].get("syllables")]

    pick(page, "a", "b", "t")
    # One of them has the bows, not all: the switch shows off, and a click sets them on all.
    expect_switch(page, False)
    expect(switch(page)).to_have_count(1)
    switch(page).click()
    expect_switch(page, True)
    bows(page, "a", "b", "t").to_have_text([*BOWS, "Was", "ser", "Fens", "ter", "Was", "ser"])
    assert have() == ["a", "b", "t"]
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    bows(page, "b", "t").to_have_count(0)
    assert have() == ["a"]
    redo(page).click()
    expect(redo(page)).to_be_disabled()
    expect_switch(page, True)
    assert have() == ["a", "b", "t"]
    # All have them now: the next click takes them from all, in one step again.
    switch(page).click()
    expect_switch(page, False)
    bows(page, "a", "b", "t").to_have_count(0)
    assert have() == []
    undo(page).click()
    bows(page, "t").to_have_text(["Fens", "ter", "Was", "ser"])
    assert have() == ["a", "b", "t"]


def test_tab_reaches_the_switch_and_space_and_enter_press_it(editor):
    """I7: by keyboard alone, and the switch says its state."""
    page = editor(box("a", "text", WORDS))
    pick(page, "a")
    page.get_by_label("Zeilenabstand").focus()
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    expect(switch(page)).to_be_focused()
    expect_switch(page, False)
    page.keyboard.press("Space")
    expect_switch(page, True)
    bows(page, "a").to_have_text(BOWS)
    expect(switch(page)).to_be_focused()
    page.keyboard.press("Enter")
    expect_switch(page, False)
    bows(page, "a").to_have_count(0)


def test_the_words_of_a_long_text_stand_in_a_box_that_scrolls(editor):
    """A4: a text of 150 words leaves the panel usable: its words scroll in a box of their own."""
    many = [a + b + c for a in "bdfgklmnpr" for b in "aeiou" for c in ("l", "m", "n")]
    page = editor(box("a", "text", {**TEXT, "text": " ".join(many), "syllables": True}))
    pick(page, "a")
    words = page.locator(".panel .words")
    expect(words.locator("button")).to_have_count(150)
    high, full = words.evaluate("(el) => [el.clientHeight, el.scrollHeight]")
    assert high <= 132 < full
    # The last word is a scroll away, and opens as the first does.
    words.locator("button").last.click()
    expect(page.locator(".panel .gaps")).to_be_visible()
    assert words.evaluate("(el) => el.clientHeight") == high
    expect(switch(page)).to_be_in_viewport()


def test_a_tables_cell_shows_its_bows_again_when_its_field_closes(editor):
    """A10: a cell written in has its bows once the writing ends, the new word's too."""
    page = editor(box("a", "table", {**CELLS, "syllables": True}))
    bows(page, "a").to_have_text(["Fens", "ter", "Was", "ser"])
    at(page, "a").locator("[data-cell='0']").dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.type(" Tasche")
    page.keyboard.press("Escape")
    expect(at(page, "a").locator("textarea")).to_have_count(0)
    bows(page, "a").to_have_text(["Fens", "ter", "Ta", "sche", "Was", "ser"])


def test_a_tables_open_cell_shows_its_bows_and_they_follow_each_letter_typed(editor):
    """I2: the bows show in the cell being written in, as in a text's open field."""
    page = editor(box("a", "table", {**CELLS, "syllables": True}))
    at(page, "a").locator("[data-cell='0']").dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    bows(page, "a").to_have_text(["Fens", "ter", "Was", "ser"])
    page.keyboard.press("End")
    page.keyboard.type(" Ta")
    bows(page, "a").to_have_text(["Fens", "ter", "Ta", "Was", "ser"])
    page.keyboard.type("sche")
    bows(page, "a").to_have_text(["Fens", "ter", "Ta", "sche", "Was", "ser"])


@pytest.mark.parametrize("kind", ["text", "shape"])
def test_the_bows_follow_each_letter_typed_and_the_switch_leaves_the_caret(editor, kind):
    """I2: bows in the open field; the switch works with the field open and the caret stays."""
    client = user()
    props = {**TEXT, "text": "Fenster"} if kind == "text" else {**RECT, "text": "Fenster"}
    page = editor(box("a", kind, props), client=client)
    caret(page, "Fenster", 4)
    bows(page, "a").to_have_count(0)
    switch(page).click()
    expect_switch(page, True)
    bows(page, "a").to_have_text(["Fens", "ter"])
    # The field is still written in, at the place the caret had.
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Fensxter")
    page.keyboard.press("Backspace")
    page.keyboard.press("End")
    for typed, shown in (
        (" ", ["Fens", "ter"]),
        ("Was", ["Fens", "ter", "Was"]),
        ("ser", ["Fens", "ter", "Was", "ser"]),
    ):
        page.keyboard.type(typed)
        bows(page, "a").to_have_text(shown)
    # The word the caret stands at is open with no click; a break set there shows in the field.
    expect(word(page, "Was·ser")).to_have_attribute("aria-pressed", "true")
    gap(page, "Wa|sser").click()
    bows(page, "a").to_have_text(["Fens", "ter", "Wa", "s", "ser"])
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("n")
    expect(page.locator(FIELD)).to_have_text("Fenster Wassern")
    page.keyboard.press("Backspace")
    # The caret in another word opens that one.
    page.keyboard.press("Home")
    expect(word(page, "Fens·ter")).to_have_attribute("aria-pressed", "true")
    expect(gap(page, "Fens|ter")).to_have_attribute("aria-pressed", "true")
    switch(page).click()
    expect_switch(page, False)
    bows(page, "a").to_have_count(0)
    expect(page.locator(FIELD)).to_be_focused()
    assert held(page, client)["a"]["breaks"] == {"wasser": [2, 3]}
