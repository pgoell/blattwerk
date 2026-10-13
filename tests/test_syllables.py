"""Silbenbögen: the switch in the format panel, the bows in the open field, a word mended by hand.

The docstrings name the lines of the frozen checklist of PR #356. The words whose own split the
tests name are ones the patterns split as a child speaks them: Fens-ter, Was-ser, Ta-sche.
"""

from contextlib import suppress

import pytest
from playwright.sync_api import TimeoutError, expect
from test_lock import fest, undo
from test_painter import held, paint
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
    saved,
    syls,
    tints,
    user,
)

WORDS = {**TEXT, "text": "Fenster Maus"}
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
BOWS = ["Fens", "ter", "Maus"]
# A text with its bows on and "Maus" split by hand.
MENDED = {**TEXT, "text": "Maus", "syllables": True, "breaks": {"maus": [2]}}
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


@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths", "ruling"])
def test_a_block_that_holds_no_words_shows_no_switch(editor, kind):
    """A10: a line, a picture, a symbol, maths and a Lineatur have no bows to switch on."""
    client = user()
    page = editor(*({**b, "locked": False} for b in fest(client, kind)), client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(switch(page)).to_have_count(0)


def test_a_block_with_no_words_picked_along_stays_as_it_is(editor):
    """A10: the switch of a text changes neither a Lineatur nor a line picked with it."""
    client = user()
    blocks = [
        box("a", "text", WORDS),
        box("r", "ruling", RULING, z=2),
        box("l", "shape", LINE, z=3),
    ]
    page = editor(*blocks, client=client)
    pick(page, "a", "r", "l")
    switch(page).click()
    bows(page, "a").to_have_text(BOWS)
    now = held(page, client)
    assert (now["r"], now["l"]) == (RULING, LINE)


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
