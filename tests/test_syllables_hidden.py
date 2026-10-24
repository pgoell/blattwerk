"""Syllable bows when a word hides a character: a soft hyphen, an emoji, or the colouring.

The helpers live in test_syllables.py.
"""

import pytest
from playwright.sync_api import expect
from test_painter import held
from test_syllables import (
    bows,
    expect_switch,
    gap,
    reset,
    switch,
    word,
)
from ui import (
    FIELD,
    LINE,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    expect_picked,
    pick,
    syls,
    tints,
    user,
)

# A soft hyphen wherever it lies in a word, and an emoji alone, with a selector, or with a joiner.
SOFT = ["Fens­ter", "Fe­nster", "Fenster­"]
EMOJI = ["Fen😀ster", "Fen😀️ster", "Fen👨‍👩ster"]
PAIR = ["#1a56db", "#e02424"]
# The kinds that hold words, each with a soft hyphen and an emoji in a word.
HIDDEN = {
    "text": [box("a", "text", {**TEXT, "text": "Fens­ter Wa😀sser"})],
    "shape": [box("a", "shape", {**RECT, "text": "Fens­ter Wa😀sser"})],
    "table": [box("a", "table", {**TABLE, "cells": [["Fens­ter", "Wa😀sser"], ["3", "7"]]})],
    "group": [
        box("a", "text", {**TEXT, "text": "Fens­ter"}, group=["g"]),
        box("b", "shape", {**RECT, "text": "Wa😀sser"}, z=2, group=["g"]),
        box("c", "shape", LINE, z=3, group=["g"]),
    ],
}


def test_a_word_that_every_object_knows_is_a_word_like_any_other(editor):
    """ "constructor" names a member of every object: it has no fix until the teacher sets one."""
    client = user()
    text = {**TEXT, "text": "Maus constructor", "syllables": True}
    page = editor(box("a", "text", text), client=client)
    faults = []
    page.on("pageerror", lambda fault: faults.append(fault))
    pick(page, "a")
    # The page still stands, and the word shows no fix and no way back from one.
    name = "".join(syls(page, "a")[1:])
    assert name == "constructor"
    shown = page.locator(".panel .words button").nth(1)
    expect(shown).not_to_have_class("own")
    shown.click()
    expect(reset(page)).to_have_count(0)
    gap(page, "con|structor").click()
    expect(reset(page)).to_be_visible()
    assert list(held(page, client)["a"]["breaks"]) == ["constructor"]
    # A sheet that holds the fix opens again.
    page.reload()
    expect(at(page, "a")).to_be_visible()
    assert "".join(syls(page, "a")) == "Mausconstructor"
    assert not faults


@pytest.mark.parametrize("word", SOFT, ids=["inside", "early", "at-end"])
def test_a_soft_hyphen_in_a_word_gives_the_bows_of_the_word_without_it(editor, word):
    """Line 1: the bows are those of the word without the hyphen, wherever the hyphen lies."""
    page = editor(box("a", "text", {**TEXT, "text": f"{word} Maus", "syllables": True}))
    bows(page, "a").to_have_text(["Fens", "ter", "Maus"])


@pytest.mark.parametrize("word", EMOJI, ids=["emoji", "selector", "joiner"])
def test_an_emoji_in_a_word_gives_the_bows_of_the_word_without_it(editor, word):
    """Line 2: an emoji, with its variation selector or a joiner, parts no word."""
    page = editor(box("a", "text", {**TEXT, "text": f"{word} Maus", "syllables": True}))
    bows(page, "a").to_have_text(["Fens", "ter", "Maus"])


def test_the_panel_lists_a_word_with_hidden_characters_once_as_the_reader_sees_it(editor):
    """Line 3: the words to mend list "Fenster" once, not as two halves."""
    text = " ".join([*SOFT, *EMOJI, "Fenster"])
    page = editor(box("a", "text", {**TEXT, "text": text, "syllables": True}))
    pick(page, "a")
    expect(page.locator(".panel .words button")).to_have_text(["Fens·ter"])


def test_a_break_set_by_hand_holds_for_the_word_with_a_soft_hyphen_and_for_the_plain_one(editor):
    """Line 4: a break for "Fenster" holds with a soft hyphen, and one set in the list for both."""
    client = user()
    text = {**TEXT, "text": "Fens­ter Fenster", "syllables": True, "breaks": {"fenster": [2]}}
    page = editor(box("a", "text", text), client=client)
    bows(page, "a").to_have_text(["Fe", "nster", "Fe", "nster"])
    pick(page, "a")
    word(page, "Fe·nster").click()
    expect(gap(page, "Fe|nster")).to_have_attribute("aria-pressed", "true")
    gap(page, "Fens|ter").click()
    bows(page, "a").to_have_text(["Fe", "ns", "ter", "Fe", "ns", "ter"])
    assert held(page, client)["a"]["breaks"] == {"fenster": [2, 4]}
    reset(page).click()
    bows(page, "a").to_have_text(["Fens", "ter", "Fens", "ter"])
    assert "breaks" not in held(page, client)["a"]


@pytest.mark.parametrize(
    ("word", "first"), [("Fens­ter", "Fens"), ("Fen😀ster", "Fen😀s")], ids=["soft", "emoji"]
)
def test_the_colours_take_their_turn_by_the_same_syllables_as_the_bows(editor, word, first):
    """Line 5: each word starts with the first colour, and the colours go by the bows' syllables."""
    text = f"{word} Wasser"
    page = editor(box("a", "text", {**TEXT, "text": text, "syllables": True, "tints": PAIR}))
    bows(page, "a").to_have_text(["Fens", "ter", "Was", "ser"])
    blue, red = PAIR
    assert tints(page, "a") == [(first, blue), ("ter", red), ("Was", blue), ("ser", red)]


@pytest.mark.parametrize("kind", list(HIDDEN))
def test_every_kind_that_holds_words_takes_the_bows_over_hidden_characters(editor, kind):
    """Line 6: every kind that holds words, with a soft hyphen and an emoji in its words."""
    page = editor(*HIDDEN[kind])
    at(page, "a").click()
    wordy = ["a", "b"] if kind == "group" else ["a"]
    expect_picked(page, *(b["id"] for b in HIDDEN[kind]))
    expect(switch(page)).to_have_count(1)
    switch(page).click()
    expect_switch(page, True)
    bows(page, *wordy).to_have_text(["Fens", "ter", "Was", "ser"])


def test_a_soft_hyphen_in_a_text_open_for_writing_gives_the_bows_of_the_closed_one(editor):
    """Line I7: the bows in the open field are those the text has once closed."""
    page = editor(box("a", "text", {**TEXT, "text": "Fens­ter Maus", "syllables": True}))
    bows(page, "a").to_have_text(["Fens", "ter", "Maus"])
    caret(page, "Maus", 0)
    expect(page.locator(FIELD)).to_be_focused()
    bows(page, "a").to_have_text(["Fens", "ter", "Maus"])
    page.keyboard.press("Escape")
    bows(page, "a").to_have_text(["Fens", "ter", "Maus"])
