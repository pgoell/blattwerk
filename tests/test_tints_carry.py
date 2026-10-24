"""Typing, the brush, a copy and a locked block keep the syllable colours."""

from contextlib import suppress

import pytest
import ui
from playwright.sync_api import (
    TimeoutError,
    expect,
)
from test_painter import (
    held,
    paint,
)
from test_tints import (
    BLUE,
    CELLS,
    COUNT,
    GREEN,
    GREYS,
    IN_PAPER,
    MENDED,
    PAIR,
    RED,
    RULES,
    WORDS,
    across,
    expect_tint_switch,
    gap,
    greys,
    tint_switch,
    tinted,
    word,
)
from ui import (
    FIELD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    expect_picked,
    pick,
    saved,
    tints,
    user,
)


def test_tab_reaches_the_colour_switch_and_its_settings_and_space_and_enter_press_them(editor):
    """I7: by keyboard alone, the switch and its settings, which the switch shows when on."""
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    pick(page, "a")
    page.get_by_label("Zeilenabstand").focus()
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    expect(
        page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True)
    ).to_be_focused()
    page.keyboard.press("Tab")
    expect(tint_switch(page)).to_be_focused()
    expect_tint_switch(page, False)
    page.keyboard.press("Space")
    expect_tint_switch(page, True)
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Maus", BLUE)])
    # WebKit's Tab passes a colour field, the block's own "Farbe" too.
    if ui.BROWSER != "webkit":
        page.keyboard.press("Tab")
        expect(page.locator(".panel").get_by_label("Erste Silbe", exact=True)).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.locator(".panel").get_by_label("Zweite Silbe", exact=True)).to_be_focused()
    page.keyboard.press("Tab")
    expect(greys(page)).to_be_focused()
    page.keyboard.press("Space")
    expect(greys(page)).to_have_attribute("aria-pressed", "true")
    tinted(page, "a").to_have_text([("Fens", GREYS[0]), ("ter", GREYS[1]), ("Maus", GREYS[0])])
    page.keyboard.press("Tab")
    expect(across(page)).to_be_focused()
    page.keyboard.press("Enter")
    expect(across(page)).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["tintsAcross"] is True
    tint_switch(page).focus()
    page.keyboard.press("Enter")
    expect_tint_switch(page, False)
    tinted(page, "a").to_have_count(0)


def test_a_tables_open_cell_shows_its_colours_and_they_follow_each_letter_typed(editor):
    """I2: the colours show in the cell being written in, as in a text's open field."""
    page = editor(box("a", "table", {**CELLS, "tints": PAIR}))
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    at(page, "a").locator("[data-cell='0']").dblclick()
    expect(at(page, "a").locator("textarea")).to_be_focused()
    # A browser colours nothing inside a field: the cell's own text shows, the field's does not.
    expect(at(page, "a").locator("p.open")).to_have_css("visibility", "visible")
    expect(at(page, "a").locator("textarea")).to_have_css("color", "rgba(0, 0, 0, 0)")
    page.keyboard.press("End")
    page.keyboard.type(" Ta")
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Ta", BLUE), ("Was", BLUE), ("ser", RED)]
    )
    page.keyboard.type("sche")
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Ta", BLUE), ("sche", RED), ("Was", BLUE), ("ser", RED)]
    )
    # The field still takes the mouse: a click in its middle is a click in the field.
    area = at(page, "a").locator("textarea")
    area.click()
    expect(area).to_be_focused()
    page.keyboard.press("Home")
    page.keyboard.type("O ")
    expect(area).to_have_value("O Fenster Tasche")


@pytest.mark.parametrize("kind", ["text", "shape"])
def test_the_colours_follow_each_letter_typed_and_the_switch_leaves_the_caret(editor, kind):
    """I2: colours in the open field; the switch works with the field open and the caret stays."""
    client = user()
    props = {**TEXT, "text": "Fenster"} if kind == "text" else {**RECT, "text": "Fenster"}
    page = editor(box("a", kind, props), client=client)
    caret(page, "Fenster", 4)
    tinted(page, "a").to_have_count(0)
    tint_switch(page).click()
    expect_tint_switch(page, True)
    tinted(page, "a").to_have_text([("Fens", BLUE), ("ter", RED)])
    # The field is still written in, at the place the caret had.
    expect(page.locator(FIELD)).to_be_focused()
    # A letter typed makes no rule anew: the colours that stay keep theirs.
    page.evaluate(RULES)
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Fensxter")
    tinted(page, "a").to_have_text([("Fensx", BLUE), ("ter", RED)])
    assert page.evaluate("window.rules") == 0
    page.keyboard.press("Backspace")
    page.keyboard.press("End")
    for typed, shown in (
        (" ", [("Fens", BLUE), ("ter", RED)]),
        ("Was", [("Fens", BLUE), ("ter", RED), ("Was", BLUE)]),
        ("ser", [("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)]),
    ):
        page.keyboard.type(typed)
        tinted(page, "a").to_have_text(shown)
    # The word the caret stands at is open with no click; a break set there shows in the field.
    expect(word(page, "Was·ser")).to_have_attribute("aria-pressed", "true")
    gap(page, "Wa|sser").click()
    tinted(page, "a").to_have_text(
        [("Fens", BLUE), ("ter", RED), ("Wa", BLUE), ("s", RED), ("ser", BLUE)]
    )
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("n")
    expect(page.locator(FIELD)).to_have_text("Fenster Wassern")
    page.keyboard.press("Backspace")
    # The caret in another word opens that one.
    page.keyboard.press("Home")
    expect(word(page, "Fens·ter")).to_have_attribute("aria-pressed", "true")
    expect(gap(page, "Fens|ter")).to_have_attribute("aria-pressed", "true")
    tint_switch(page).click()
    expect_tint_switch(page, False)
    tinted(page, "a").to_have_count(0)
    expect(page.locator(FIELD)).to_be_focused()
    assert held(page, client)["a"]["breaks"] == {"wasser": [2, 3]}


def test_the_brush_carries_the_colours_and_their_setting_and_leaves_the_words_split_by_hand(
    editor,
):
    """I3: the format painter carries the colours and the setting, not the hand fixes."""
    client = user()
    coloured = {**MENDED, "tints": PAIR, "tintsAcross": True}
    blocks = [
        box("a", "text", coloured),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2),
        box("t", "table", CELLS, z=3),
        box("c", "text", TEXT, z=4),
    ]
    page = editor(*blocks, client=client)
    paint(page, "a", "b")
    tinted(page, "b").to_have_text([("Maus", BLUE)])
    now = held(page, client)
    assert (now["b"]["tints"], now["b"]["tintsAcross"]) == (PAIR, True)
    assert "breaks" not in now["b"]
    paint(page, "a", "t")
    tinted(page, "t").to_have_text([("Fens", BLUE), ("ter", RED), ("Was", BLUE), ("ser", RED)])
    now = held(page, client)
    assert (now["t"]["tints"], now["t"]["tintsAcross"]) == (PAIR, True)
    assert "breaks" not in now["t"]
    # A block without colours takes them away, as one not bold takes the bold; the fix stays.
    paint(page, "c", "a")
    tinted(page, "a").to_have_count(0)
    now = held(page, client)["a"]
    assert "tints" not in now and "tintsAcross" not in now
    assert "syllables" not in now and now["breaks"] == {"maus": [2]}


def test_a_copy_and_a_duplicate_keep_the_colours_and_the_words_split_by_hand(editor):
    """I4: copy and paste, and duplicate, of a block keep the colours and its hand fixes."""
    client = user()
    page = editor(box("a", "text", {**MENDED, "tints": PAIR}), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    made = page.eval_on_selector_all(".block[data-id]", "els => els.map((el) => el.dataset.id)")
    tinted(page, *made).to_have_text([("Ma", BLUE), ("us", RED)] * 3)
    assert list(held(page, client).values()) == [{**MENDED, "tints": PAIR}] * 3


@pytest.mark.parametrize("kind", ["text", "table"])
def test_a_locked_block_takes_the_colours_and_a_word_split_by_hand(editor, kind):
    """I5: as it takes any format; its place, size and text stay."""
    client = user()
    props = {"text": {**TEXT, "text": "Maus"}, "table": {**TABLE, "cells": [["Maus", "7"]]}}[kind]
    block = box("a", kind, props, locked=True)
    page = editor(block, client=client)
    at(page, "a").click()
    expect_picked(page, "a")
    tint_switch(page).click()
    tinted(page, "a").to_have_text([("Maus", BLUE)])
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    tinted(page, "a").to_have_text([("Ma", BLUE), ("us", RED)])
    assert saved(page, client) == [
        {**block, "props": {**props, "tints": PAIR, "breaks": {"maus": [2]}}}
    ]


def test_bold_italic_underline_colour_and_a_list_keep_their_look_in_a_coloured_text(editor):
    """I6: the runs keep their look, and so does the bullet, under the colours."""
    hand = "#e03131"
    runs = [
        {"text": "Rote ", "color": hand},
        {"text": "Ba", "bold": True},
        {"text": "nane ", "italic": True},
        {"text": "Esel", "underline": True},
    ]
    listed = [{"runs": runs, "list": "bullet"}, {"runs": [{"text": "Oma"}]}]
    text = "Rote Banane Esel\nOma"
    props = {**TEXT, "text": text, "rich": listed, "color": GREEN, "tints": PAIR}
    page = editor(box("a", "text", props))
    # The colours skip the letters of the hand colour; "Banane" is coloured whole.
    tinted(page, "a").to_have_text(
        [
            ("Ba", BLUE),
            ("na", RED),
            ("ne", BLUE),
            ("E", BLUE),
            ("sel", RED),
            ("O", BLUE),
            ("ma", RED),
        ]
    )
    spans = at(page, "a").locator(".rich p span")
    expect(spans.nth(0)).to_have_css("color", "rgb(224, 49, 49)")
    expect(spans.nth(1)).to_have_css("font-weight", "700")
    expect(spans.nth(2)).to_have_css("font-style", "italic")
    expect(spans.nth(3)).to_have_css("text-decoration-line", "underline")
    item = at(page, "a").locator(".rich p").first
    assert item.evaluate("el => getComputedStyle(el, '::before').content") == '"•"'
    assert item.evaluate("el => getComputedStyle(el, '::before').color") == "rgb(47, 158, 68)"


def test_the_sheet_lists_thumbnail_shows_the_colours(editor, server):
    """I8: the thumbnail on the list draws the colours too: one range per syllable."""
    page = editor(box("a", "text", {**WORDS, "size": 40, "tints": PAIR}, w=180, h=40))
    tints(page, "a")
    page.goto(server)
    expect(page.locator(".sheets li .paper")).to_be_visible()
    with suppress(TimeoutError):
        page.wait_for_function(f"() => ({IN_PAPER})() === 3", timeout=5000)
    assert page.evaluate(f"({IN_PAPER})()") == 3


def test_a_word_that_every_object_knows_takes_its_colours(editor):
    """ "constructor" names a member of every object: it takes its colours like any word."""
    text = {**TEXT, "text": "constructor toString Maus", "tints": PAIR}
    page = editor(box("a", "text", text))
    faults = []
    page.on("pageerror", lambda fault: faults.append(fault))
    expect(at(page, "a")).to_be_visible()
    assert "".join(text for text, _ in tints(page, "a")) == "constructortoStringMaus"
    assert not faults


def test_a_block_that_goes_takes_its_colours_along(editor):
    """Extra: a block deleted takes its colour ranges with it: none stay on the page."""
    page = editor(
        box("a", "text", {**WORDS, "tints": PAIR}),
        box("b", "text", {**TEXT, "text": "Wasser", "tints": PAIR}, z=2),
    )
    pick(page, "b")
    page.keyboard.press("Delete")
    expect(at(page, "b")).to_have_count(0)
    # The three of "Fenster Maus" and no more.
    with suppress(TimeoutError):
        page.wait_for_function(f"() => ({COUNT})() === 3", timeout=5000)
    assert page.evaluate(f"({COUNT})()") == 3
