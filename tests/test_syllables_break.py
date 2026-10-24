"""A syllable break set by hand: it stays through typing, a copy, the brush, and undo.

The helpers live in test_syllables.py.
"""

import pytest
from playwright.sync_api import expect
from test_lock import undo
from test_painter import held, paint
from test_syllables import (
    CELLS,
    WORDS,
    bows,
    expect_switch,
    gap,
    redo,
    reset,
    switch,
    word,
)
from ui import (
    TABLE,
    TEXT,
    at,
    box,
    caret,
    expect_picked,
    pick,
    saved,
    user,
)

# A text with its bows on and "Maus" split by hand.
MENDED = {**TEXT, "text": "Maus", "syllables": True, "breaks": {"maus": [2]}}


def test_a_click_between_two_letters_sets_a_break_and_one_more_takes_it_away(editor):
    """A4: click a word, set or remove a break; the bows follow at once."""
    client = user()
    page = editor(box("a", "text", {**WORDS, "text": "Fenster Maus maus"}), client=client)
    pick(page, "a")
    # Nothing to mend while the bows are off.
    expect(page.locator(".panel .words")).to_have_count(0)
    switch(page).click()
    expect(page.locator(".panel .hint", has_text="Silbe falsch?")).to_be_visible()
    # Each word once, as it is split now; "maus" is "Maus".
    expect(page.locator(".panel .words button")).to_have_text(["Fens·ter", "Maus"])
    expect(page.locator(".panel .gaps")).to_have_count(0)
    word(page, "Maus").click()
    expect(word(page, "Maus")).to_have_attribute("aria-pressed", "true")
    expect(word(page, "Fens·ter")).to_have_attribute("aria-pressed", "false")
    expect(page.locator(".panel .gaps button")).to_have_count(3)
    for name in ("M|aus", "Ma|us", "Mau|s"):
        expect(gap(page, name)).to_have_attribute("aria-pressed", "false")
    expect(reset(page)).to_have_count(0)
    gap(page, "Ma|us").click()
    # The fix holds for the word wherever it stands in the block, in capitals or not.
    bows(page, "a").to_have_text(["Fens", "ter", "Ma", "us", "ma", "us"])
    expect(gap(page, "Ma|us")).to_have_attribute("aria-pressed", "true")
    # The word says that it is split by hand.
    expect(word(page, "Ma·us")).to_have_attribute("title", "von Hand getrennt")
    expect(word(page, "Ma·us")).to_have_class("on own")
    expect(word(page, "Fens·ter")).not_to_have_attribute("title", "von Hand getrennt")
    expect(reset(page)).to_be_visible()
    assert held(page, client)["a"]["breaks"] == {"maus": [2]}
    # The same click takes the break away: the word is split as the module does, and no fix stays.
    gap(page, "Ma|us").click()
    bows(page, "a").to_have_text(["Fens", "ter", "Maus", "maus"])
    expect(word(page, "Maus")).to_have_class("on")
    expect(reset(page)).to_have_count(0)
    assert "breaks" not in held(page, client)["a"]
    # A break of the module's own goes the same way, and "Zurücksetzen" brings it back.
    word(page, "Fens·ter").click()
    expect(gap(page, "Fens|ter")).to_have_attribute("aria-pressed", "true")
    gap(page, "Fens|ter").click()
    bows(page, "a").to_have_text(["Fenster", "Maus", "maus"])
    assert held(page, client)["a"]["breaks"] == {"fenster": []}
    reset(page).click()
    bows(page, "a").to_have_text(["Fens", "ter", "Maus", "maus"])
    expect(reset(page)).to_have_count(0)
    assert "breaks" not in held(page, client)["a"]


def test_a_word_split_by_hand_outlasts_typing_a_save_and_a_reload(editor):
    """A5: the fix survives edits of the text around it, a save and a reload."""
    client = user()
    page = editor(box("a", "text", MENDED), client=client)
    bows(page, "a").to_have_text(["Ma", "us"])
    # Typed before the word, inside another word, and after it.
    caret(page, "Maus", 0)
    page.keyboard.type("Das ")
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("s")
    page.keyboard.press("End")
    page.keyboard.type(" lacht")
    page.keyboard.press("Escape")
    bows(page, "a").to_have_text(["Dass", "Ma", "us", "lacht"])
    assert held(page, client)["a"] == {**MENDED, "text": "Dass Maus lacht"}
    page.reload()
    bows(page, "a").to_have_text(["Dass", "Ma", "us", "lacht"])
    # The word deleted and typed again is split as the teacher split it.
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Control+a")
    page.keyboard.type("Haus")
    page.keyboard.press("Escape")
    bows(page, "a").to_have_text(["Haus"])
    assert held(page, client)["a"] == {**MENDED, "text": "Haus"}
    page.keyboard.press("Enter")
    page.keyboard.type("Maus")
    page.keyboard.press("Escape")
    bows(page, "a").to_have_text(["Ma", "us"])
    assert held(page, client)["a"] == MENDED


def test_the_switch_and_each_break_undo_and_redo_one_step_each(editor):
    """A6: Ctrl+Z takes one break back, and then the switch; Ctrl+Y sets each again."""
    page = editor(box("a", "text", {**TEXT, "text": "Maus"}))
    pick(page, "a")
    switch(page).click()
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    gap(page, "M|aus").click()
    steps = [[], ["Maus"], ["Ma", "us"], ["M", "a", "us"]]
    bows(page, "a").to_have_text(steps[3])
    for step in (2, 1, 0):
        page.keyboard.press("Control+z")
        bows(page, "a").to_have_text(steps[step])
    expect_switch(page, False)
    expect(undo(page)).to_be_disabled()
    for step in (1, 2, 3):
        page.keyboard.press("Control+y")
        bows(page, "a").to_have_text(steps[step])
        expect_switch(page, True)
    expect(redo(page)).to_be_disabled()
    expect(gap(page, "M|aus")).to_have_attribute("aria-pressed", "true")


def test_the_brush_carries_the_bows_and_leaves_the_words_split_by_hand(editor):
    """I3: the format painter carries the switch, not the hand fixes, which belong to the words."""
    client = user()
    blocks = [
        box("a", "text", MENDED),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2),
        box("t", "table", CELLS, z=3),
        box("c", "text", TEXT, z=4),
    ]
    page = editor(*blocks, client=client)
    paint(page, "a", "b")
    bows(page, "b").to_have_text(["Maus"])
    paint(page, "a", "t")
    bows(page, "t").to_have_text(["Fens", "ter", "Was", "ser"])
    now = held(page, client)
    assert (now["b"]["syllables"], now["t"]["syllables"]) == (True, True)
    assert "breaks" not in now["b"] and "breaks" not in now["t"]
    # A block without bows takes them away, as one not bold takes the bold; the fix stays.
    paint(page, "c", "a")
    bows(page, "a").to_have_count(0)
    now = held(page, client)["a"]
    assert "syllables" not in now and now["breaks"] == {"maus": [2]}


def test_a_copy_and_a_duplicate_keep_the_bows_and_the_words_split_by_hand(editor):
    """I4: copy and paste, and duplicate, of a block keep the switch and its hand fixes."""
    client = user()
    page = editor(box("a", "text", MENDED), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    made = page.eval_on_selector_all(".block[data-id]", "els => els.map((el) => el.dataset.id)")
    bows(page, *made).to_have_text(["Ma", "us"] * 3)
    assert list(held(page, client).values()) == [MENDED] * 3


@pytest.mark.parametrize("kind", ["text", "table"])
def test_a_locked_block_takes_the_bows_and_a_word_split_by_hand(editor, kind):
    """I5: as it takes any format; its place, size and text stay."""
    client = user()
    props = {"text": {**TEXT, "text": "Maus"}, "table": {**TABLE, "cells": [["Maus", "7"]]}}[kind]
    block = box("a", kind, props, locked=True)
    page = editor(block, client=client)
    at(page, "a").click()
    expect_picked(page, "a")
    switch(page).click()
    bows(page, "a").to_have_text(["Maus"])
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    bows(page, "a").to_have_text(["Ma", "us"])
    assert saved(page, client) == [
        {**block, "props": {**props, "syllables": True, "breaks": {"maus": [2]}}}
    ]
