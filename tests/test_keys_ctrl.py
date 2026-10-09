"""What Ctrl or Alt with a key does as the first key after a list or a colour picker of the format
panel that shut with no pick."""

import pytest
from playwright.sync_api import expect
from test_keys_first import FROM, begun, expect_kept
from test_keys_focus import KINDS
from test_keys_panel import SELECTS, expect_words, write
from test_keys_shut import COLOURS, WRITTEN, opened, shut
from ui import TEXT, at, box, expect_picked, pick, stopped

# Every control with every way to shut what it opened.
WAYS = [(*c, way) for c in WRITTEN for way in ("beside", "ground", "escape")] + [
    (*s, way) for s in SELECTS for way in ("same", "beside", "ground")
]
# One control of each kind of field: a text's, a Lineatur's and a cell's.
FIELDS = [
    ("text", "Farbe", "beside"),
    ("ruling", "Art der Lineatur", "same"),
    ("table", "Linien", "beside"),
]
# What one undo leaves of "Wort". A text and a cell are the sheet's to undo, which takes the typing
# as one step. A Lineatur is the browser's, which takes back the last letter typed.
UNDONE = {"text": "Hallo", "shape": "", "ruling": "Wot", "table": "H"}
CLIPBOARD = "async (words) => (await navigator.clipboard.readText()) === words"


def left(page, label, way):
    """Opens the control and shuts it with no pick. Gives it and the value it has."""
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    return control, was


# Asked 1


@pytest.mark.parametrize("name, label, way", WAYS)
def test_ctrl_z_as_the_first_key_undoes_the_typing_once(editor, name, label, way):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    # A step before the typing, which a second undo would take back.
    pick(page, "b")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")
    moved = at(page, "b").bounding_box()
    area = write(page, name)
    control, was = left(page, label, way)
    page.keyboard.press("Control+z")
    expect_words(area, UNDONE[name])
    expect_kept(page, area, control, was, name)
    assert at(page, "b").bounding_box() == moved


# Asked 2


@pytest.mark.parametrize("name, label, way", FROM)
def test_ctrl_y_as_the_first_key_redoes(editor, name, label, way):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    page.keyboard.press("Control+z")
    expect_words(area, UNDONE[name])
    control, was = left(page, label, way)
    page.keyboard.press("Control+y")
    expect_words(area, "Wort")
    expect_kept(page, area, control, was, name)


# Asked 3


@pytest.mark.parametrize("key, words", [("x", "Wt"), ("c", "Wort")])
@pytest.mark.parametrize("name, label, way", FROM)
def test_ctrl_x_and_ctrl_c_as_the_first_key_take_the_letters_picked(
    editor, name, label, way, key, words
):
    page, area, control, was = begun(editor, name, label, way, letters=2)
    page.keyboard.press(f"Control+{key}")
    page.wait_for_function(CLIPBOARD, arg="or")
    expect_words(area, words)
    expect_kept(page, area, control, was, name)
    # The block is not copied.
    assert page.evaluate("localStorage.getItem('clip')") is None
    # A copy leaves the letters picked.
    page.keyboard.type("x")
    expect_words(area, "Wxt")


# Asked 4


@pytest.mark.parametrize("name, label, way", WAYS)
def test_ctrl_backspace_as_the_first_key_deletes_the_word_before_the_caret(
    editor, name, label, way
):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press("Control+Backspace")
    expect_words(area, "t")
    expect_kept(page, area, control, was, name)
    page.keyboard.type("x")
    expect_words(area, "xt")


@pytest.mark.parametrize("name, label, way", FROM)
def test_ctrl_delete_as_the_first_key_deletes_the_word_after_the_caret(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press("Control+Delete")
    expect_words(area, "Wor")
    expect_kept(page, area, control, was, name)
    page.keyboard.type("x")
    expect_words(area, "Worx")


@pytest.mark.parametrize("key", ["Backspace", "Delete"])
@pytest.mark.parametrize("name, label, way", FIELDS)
def test_ctrl_backspace_as_the_first_key_deletes_only_the_letters_picked(
    editor, name, label, way, key
):
    page, area, control, was = begun(editor, name, label, way, letters=2)
    page.keyboard.press(f"Control+{key}")
    expect_words(area, "Wt")
    expect_kept(page, area, control, was, name)


# Asked 5


@pytest.mark.parametrize("key, words", [("ArrowLeft", "xWort"), ("ArrowRight", "Wortx")])
@pytest.mark.parametrize("name, label, way", FROM)
def test_ctrl_and_an_arrow_as_the_first_key_move_the_caret_by_a_word(
    editor, name, label, way, key, words
):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press(f"Control+{key}")
    expect_kept(page, area, control, was, name)
    expect(page.get_by_label("X", exact=True)).to_have_value("15")
    page.keyboard.type("x")
    expect_words(area, words)


@pytest.mark.parametrize("name, label, way", FIELDS)
def test_ctrl_shift_and_an_arrow_as_the_first_key_pick_to_the_words_start(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press("Control+Shift+ArrowLeft")
    expect_kept(page, area, control, was, name)
    page.wait_for_function("String(getSelection()) === 'Wor'")
    page.keyboard.type("x")
    expect_words(area, "xt")


# Asked 6


@pytest.mark.parametrize("key", ["Alt+Backspace", "Alt+e"])
@pytest.mark.parametrize("name, label, way", FROM)
def test_alt_and_a_key_as_the_first_key_only_give_the_caret_back(editor, name, label, way, key):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press(key)
    expect_kept(page, area, control, was, name)
    expect_words(area, "Wort")
    # The next key acts as ever.
    page.keyboard.press("Backspace")
    expect_words(area, "Wot")
    page.keyboard.type("x")
    expect_words(area, "Woxt")


# AltGr comes as Ctrl with Alt on Windows. It types "@" on a German Q, and a letter of its own on
# a Polish Z, X, C and A. No browser types a sign for it here: the key must stay the browser's,
# which types the sign where the caret is.
@pytest.mark.parametrize("key", ["q", "z", "y", "x", "c", "a"])
@pytest.mark.parametrize("name, label, way", FIELDS)
def test_a_sign_typed_with_altgr_as_the_first_key_stays_the_browsers(editor, name, label, way, key):
    page, area, control, was = begun(editor, name, label, way, letters=1)
    assert not stopped(page, f"Control+Alt+{key}")
    expect_kept(page, area, control, was, name)
    expect_words(area, "Wort")
    page.wait_for_function("String(getSelection()) === 'r'")
    assert page.evaluate("localStorage.getItem('clip')") is None
    page.keyboard.type("@")
    expect_words(area, "Wo@t")


# Asked 7


@pytest.mark.parametrize("name, label, way", FROM)
def test_ctrl_a_as_the_first_key_picks_all_the_words(editor, name, label, way):
    page, area, control, was = begun(editor, name, label, way)
    page.keyboard.press("Control+a")
    page.wait_for_function("String(getSelection()) === 'Wort'")
    # Not all the blocks.
    expect_kept(page, area, control, was, name)
    page.keyboard.type("x")
    expect_words(area, "x")


# Implied 2


@pytest.mark.parametrize(
    "name, label, way", [(*c, "beside") for c in COLOURS] + [(*s, "same") for s in SELECTS]
)
def test_ctrl_z_and_ctrl_a_as_the_first_key_are_the_sheets_with_nothing_written_in(
    editor, name, label, way
):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    page.keyboard.press("ArrowRight")
    place = page.get_by_label("X", exact=True)
    expect(place).to_have_value("16")
    control, was = left(page, label, way)
    page.keyboard.press("Control+z")
    expect(place).to_have_value("15")
    expect(control).not_to_be_focused()
    expect(control).to_have_value(was)
    left(page, label, way)
    page.keyboard.press("Control+a")
    expect_picked(page, "z", name)
