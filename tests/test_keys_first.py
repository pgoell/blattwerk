"""What the first key does after a list or a colour picker of the format panel that shut with no
pick, while something is written in, and what Tab does after a letter typed from there."""

import pytest
from playwright.sync_api import expect
from test_keys_focus import KINDS
from test_keys_panel import SELECTS, expect_words, write
from test_keys_shut import COLOURS, WRITTEN, opened, shut
from ui import TEXT, at, box, expect_picked, pick

# Every control the first key may come from, with a way to shut what it opened.
FROM = [(*c, "beside") for c in WRITTEN] + [(*s, "same") for s in SELECTS]


def begun(editor, name, label, way, letters=0):
    """Writes "Wort" in the block, the caret before the last letter, then opens and shuts the
    control. With `letters` that many before the caret are picked first."""
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    for _ in range(letters):
        page.keyboard.press("Shift+ArrowLeft")
    page.wait_for_function("n => String(getSelection()).length === n", arg=letters)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    return page, area, control, was


def expect_kept(page, area, control, was, name):
    """The key went to what is written in alone: the block and the control are as they were."""
    expect(area).to_be_focused()
    expect(control).to_have_value(was)
    expect_picked(page, name)
    expect(page.locator(".block")).to_have_count(2)


# Asked #223


@pytest.mark.parametrize("key, words", [("Backspace", "Wot"), ("Delete", "Wor")])
@pytest.mark.parametrize("name, label, way", FROM)
def test_backspace_and_delete_as_the_first_key_delete_a_letter(
    editor, name, label, way, key, words
):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press(key)
    expect_words(area, words)
    expect_kept(page, area, control, was, name)
    # The caret is where the letter was.
    page.keyboard.type("x")
    expect_words(area, "Woxt" if key == "Backspace" else "Worx")


@pytest.mark.parametrize(
    "key, words",
    [
        ("ArrowLeft", "Woxrt"),
        ("ArrowRight", "Wortx"),
        ("ArrowUp", "xWort"),
        ("ArrowDown", "Wortx"),
    ],
)
@pytest.mark.parametrize("name, label", WRITTEN)
def test_an_arrow_as_the_first_key_after_a_colour_moves_the_caret(editor, name, label, key, words):
    page, area, control, was = begun(editor, name, label, "beside")
    page.keyboard.press(key)
    expect_kept(page, area, control, was, name)
    expect(page.get_by_label("X", exact=True)).to_have_value("15")
    page.keyboard.type("x")
    expect_words(area, words)


@pytest.mark.parametrize("name, label", SELECTS)
def test_an_arrow_after_a_shut_list_stays_the_lists(editor, name, label):
    page, area, control, was = begun(editor, name, label, "same")
    page.keyboard.press("ArrowDown")
    expect(control).to_be_focused()
    expect(control).not_to_have_value(was)
    expect_words(area, "Wort")
    expect_picked(page, name)


@pytest.mark.parametrize("key, words", [("Home", "xWort"), ("End", "Wortx")])
@pytest.mark.parametrize("name, label, way", FROM)
def test_home_and_end_as_the_first_key_move_the_caret(editor, name, label, way, key, words):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press(key)
    expect_kept(page, area, control, was, name)
    page.keyboard.type("x")
    expect_words(area, words)


@pytest.mark.parametrize("name", ["text", "shape"])
@pytest.mark.parametrize("label, way", [("Farbe", "beside"), ("Schriftart", "same")])
def test_ctrl_b_as_the_first_key_sets_the_word_the_caret_is_in(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    bold = area.locator("span[data-bold]")
    expect(bold).to_have_count(0)
    page.keyboard.press("Control+b")
    expect(bold).to_have_text("Wort")
    expect_kept(page, area, control, was, name)
    # The caret stayed where it was.
    page.keyboard.type("x")
    expect(bold).to_have_text("Worxt")


@pytest.mark.parametrize("key", ["NumLock", "ScrollLock", "ContextMenu"])
@pytest.mark.parametrize(
    "name, label, way", [("text", "Farbe", "beside"), ("ruling", "Art der Lineatur", "same")]
)
def test_a_key_that_only_switches_is_not_the_first_key(editor, name, label, way, key):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press(key)
    # The keys are not given back yet.
    expect(control).to_be_focused()
    page.keyboard.press("Backspace")
    expect_words(area, "Wot")
    expect_kept(page, area, control, was, name)


# Implied 1


@pytest.mark.parametrize("key", ["Backspace", "Delete"])
@pytest.mark.parametrize("name, label, way", FROM)
def test_the_first_backspace_or_delete_deletes_the_letters_picked(editor, name, label, way, key):
    page, area, control, was = begun(editor, name, label, way, letters=2)
    page.keyboard.press(key)
    expect_words(area, "Wt")
    expect_kept(page, area, control, was, name)


@pytest.mark.parametrize("name, label", WRITTEN)
def test_shift_and_an_arrow_as_the_first_key_pick_one_letter_more(editor, name, label):
    page, area, control, was = begun(editor, name, label, "beside", letters=1)
    page.keyboard.press("Shift+ArrowLeft")
    expect_kept(page, area, control, was, name)
    page.wait_for_function("String(getSelection()) === 'or'")
    page.keyboard.type("x")
    expect_words(area, "Wxt")


# Implied 2


@pytest.mark.parametrize("name, label, way", FROM)
def test_undo_after_a_first_backspace_brings_the_letter_back(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press("Backspace")
    expect_words(area, "Wot")
    page.keyboard.press("Control+z")
    expect_words(area, "Wort")
    expect_kept(page, area, control, was, name)


# Implied 3


@pytest.mark.parametrize(
    "name, label, way", [(*c, "beside") for c in COLOURS] + [(*s, "same") for s in SELECTS]
)
def test_delete_after_a_shut_list_or_picker_removes_the_block_with_nothing_written_in(
    editor, name, label, way
):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    shut(page, opened(page, label), way)
    page.keyboard.press("Delete")
    expect(at(page, name)).to_have_count(0)
    expect(at(page, "z")).to_have_count(1)


# Asked #224


@pytest.mark.parametrize("name, label, way", FROM)
def test_tab_after_a_letter_typed_from_the_panel_does_what_tab_does_there(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.type("l")
    expect_words(area, "Worlt")
    page.keyboard.press("Tab")
    if name == "table":
        # The next cell, and the first keeps its words.
        cells = at(page, name).locator("[data-cell]")
        expect(cells.nth(0)).to_have_text("Worlt")
        expect(cells.nth(1).locator("textarea")).to_be_focused()
    else:
        # A tab stop in a text and a shape, nothing in a Lineatur.
        expect_words(area, "Worlt" if name == "ruling" else "Worl\tt")
        expect(area).to_be_focused()
    expect(control).to_have_value(was)
    expect_picked(page, name)
