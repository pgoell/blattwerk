"""Who has the keys after a control of the format panel while something is written in, or after a
list that shut with no pick, and what Tab does in a Lineatur."""

import re

import pytest
from playwright.sync_api import expect
from test_keys_focus import CONTROLS, KINDS, OPEN, choose
from ui import FIELD, RECT, RULING, TEXT, at, box, caret, expect_picked, pick, saved, unpick, user

# Every select of the panel for a block that holds words.
SELECTS = [
    ("text", "Schriftart"),
    ("shape", "Schriftart"),
    ("ruling", "Art der Lineatur"),
    ("ruling", "Schriftart auf den Zeilen"),
    ("table", "Schriftart der Tabelle"),
]
# The words of a text or a shape, of its own blue: all but the last letter are red.
LAST = {
    **TEXT,
    "text": "Hallo du",
    "color": "#0000ff",
    "rich": [{"runs": [{"text": "Hallo d", "color": "#ff0000"}, {"text": "u"}]}],
}
WRITTEN = [
    (name, label) for name in ("text", "shape", "ruling", "table") for label in CONTROLS[name]
]


def write(page, name):
    """Opens the block, types "Wort" over what it held and puts the caret before the last letter."""
    pick(page, name)
    page.keyboard.press("Enter")
    # A text's field hears of a caret the browser moved only a moment later, but of a letter at
    # once: the "r" is typed last, so the field knows where the caret is.
    page.keyboard.type("Wot")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("r")
    area = page.locator(OPEN)
    expect(area).to_be_focused()
    return area


def expect_words(area, words):
    """Waits until the text's field, the Lineatur or the cell holds just these words."""
    if area.evaluate("el => el.tagName") == "TEXTAREA":
        expect(area).to_have_value(words)
    else:
        expect(area).to_have_text(words)


def expect_caret(page, area):
    """The caret is back before the last letter, and the next key types there."""
    expect(area).to_be_focused()
    if area.evaluate("el => el.tagName") == "TEXTAREA":
        expect(area).to_have_js_property("selectionStart", 3)
        expect(area).to_have_js_property("selectionEnd", 3)
    page.keyboard.type("x")
    expect_words(area, "Worxt")
    page.keyboard.press("Backspace")
    expect_words(area, "Wort")


def press(page, label):
    """Presses a select of the panel as the mouse does, and leaves its list shut.

    The press is a pointerdown made by hand and the focus is given, as a real press gives it: so
    the select is as a list opened and shut with no pick leaves it. `opened` in test_keys_shut.py
    opens the list itself.
    """
    control = page.locator(".panel").get_by_label(label, exact=True)
    control.dispatch_event("pointerdown")
    control.focus()
    return control


def shut(page, control, way):
    """Shuts the list `press` opened, with no pick of the mouse."""
    if way == "escape":
        page.keyboard.press("Escape")
    elif way == "walk":
        # The arrows pick and Enter shuts the list.
        was = control.input_value()
        page.keyboard.press("ArrowDown")
        expect(control).not_to_have_value(was)
        page.keyboard.press("Enter")
    # A click on the value the select already has tells the page nothing: no key and no event
    # comes between the press and what follows. `select_option` would send a `change` here that
    # no browser sends.


# Asked #192, Implied 5


@pytest.mark.parametrize("key", ["Tab", "Shift+Tab"])
def test_tab_in_a_ruling_keeps_the_writing_open_and_types_nothing(editor, key):
    page = editor(box("lines", "ruling", RULING), box("b", "text", TEXT, z=2))
    written = at(page, "lines").locator("textarea.written")
    pick(page, "lines")
    page.keyboard.press("Enter")
    page.keyboard.type("abc")
    page.keyboard.press(key)
    expect(written).to_be_focused()
    expect(written).to_have_value("abc")
    expect_picked(page, "lines")
    page.keyboard.type("d")
    expect(written).to_have_value("abcd")


# Asked #193


@pytest.mark.parametrize("label", CONTROLS["ruling"])
def test_a_pick_with_the_mouse_gives_the_keys_back_to_a_ruling(editor, label):
    page = editor(box("ruling", "ruling", RULING), box("b", "text", TEXT, z=2))
    area = write(page, "ruling")
    choose(page, label)
    expect_caret(page, area)
    # The key right after a pick is the Lineatur's too.
    choose(page, label)
    page.keyboard.press("Backspace")
    expect(area).to_have_value("Wot")
    expect_picked(page, "ruling")


@pytest.mark.parametrize("label", CONTROLS["table"])
def test_a_pick_with_the_mouse_gives_the_keys_back_to_a_cell(editor, label):
    page = editor(box("table", "table", KINDS["table"][1]), box("b", "text", TEXT, z=2))
    area = write(page, "table")
    choose(page, label)
    expect_caret(page, area)
    choose(page, label)
    page.keyboard.press("Backspace")
    expect(area).to_have_value("Wot")
    # It is still the first cell.
    expect(at(page, "table").locator('[data-cell="0"] textarea')).to_be_focused()
    expect_picked(page, "table")


@pytest.mark.parametrize(
    "name, label", [("ruling", "Farbe"), ("table", "Farbe"), ("table", "Linien")]
)
def test_a_press_on_the_word_beside_a_colour_keeps_the_writing_open(editor, name, label):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    # The word takes no focus: the press on it names nothing the focus goes to. The colour gets
    # the focus only with the click.
    word = page.locator(".panel label").filter(has_text=re.compile(rf"^{label}$"))
    word.click(position={"x": 2, "y": 2})
    expect(word.locator("input")).to_be_focused()
    expect(area).to_be_editable()
    expect(area).to_have_value("Wort")
    expect_picked(page, name)


# Asked #194


@pytest.mark.parametrize("name, label", SELECTS)
def test_a_list_shut_with_escape_gives_the_keys_back_to_the_sheet(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = press(page, label)
    shut(page, control, "escape")
    expect(control).not_to_be_focused()
    # The Escape shut the list and no more.
    expect_picked(page, name)
    page.keyboard.press("Tab")
    expect_picked(page, "z")


@pytest.mark.parametrize("name, label", SELECTS)
def test_a_list_shut_by_a_click_on_its_value_gives_the_keys_back_to_the_sheet(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = press(page, label)
    shut(page, control, "same")
    page.keyboard.press("Tab")
    expect_picked(page, "z")
    assert page.evaluate("document.activeElement === document.body")
    # Shift+Tab goes the other way, as from the sheet.
    pick(page, name)
    press(page, label)
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "z")
    assert page.evaluate("document.activeElement === document.body")


@pytest.mark.parametrize("name, label", SELECTS)
def test_a_list_walked_with_the_arrows_gives_the_keys_back_to_the_sheet(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = press(page, label)
    shut(page, control, "walk")
    expect(control).not_to_be_focused()
    # The Enter shut the list and opened nothing.
    expect(page.locator(OPEN)).to_have_count(0)
    expect_picked(page, name)
    page.keyboard.press("Tab")
    expect_picked(page, "z")


# Asked #196, Implied 1


@pytest.mark.parametrize("kind, props", [("text", TEXT), ("shape", RECT)])
def test_a_colour_set_by_the_keys_is_for_what_is_typed_next(editor, kind, props):
    client = user()
    page = editor(box("a", kind, {**props, **LAST}), client=client)
    field, farbe = page.locator(FIELD), page.locator(".panel").get_by_label("Farbe", exact=True)
    caret(page, "du", 2)
    # A text's field hears of a caret the browser moved only a moment later. "Farbe" shows the
    # block's own blue once the field knows the caret at the end, behind the one letter not red.
    expect(farbe).to_have_value("#0000ff")
    # No press comes first: the control is reached and set by the keys.
    farbe.fill("#00ff00")
    expect(field).to_be_focused()
    page.keyboard.type(" da")
    expect(field).to_have_text("Hallo du da")
    (a,) = saved(page, client)
    # The block and its words keep their colours.
    assert a["props"]["color"] == "#0000ff"
    assert a["props"]["rich"] == [
        {
            "runs": [
                {"text": "Hallo d", "color": "#ff0000"},
                {"text": "u"},
                {"text": " da", "color": "#00ff00"},
            ]
        }
    ]
    # One undo takes the colour and what was typed in it away, and no more.
    page.keyboard.press("Control+z")
    expect(field).to_have_text("Hallo du")
    expect(field.locator("span[data-color]")).to_have_text(["Hallo d"])
    expect(field).to_be_focused()
    (a,) = saved(page, client)
    assert a["props"]["color"] == "#0000ff"
    assert a["props"]["rich"] == LAST["rich"]


# Implied 4


@pytest.mark.parametrize("way", ["escape", "same", "walk"])
@pytest.mark.parametrize("name, label", SELECTS)
def test_a_list_shut_with_no_pick_gives_the_keys_back_to_what_is_written_in(
    editor, name, label, way
):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    control = press(page, label)
    expect(area).not_to_be_focused()
    shut(page, control, way)
    if way == "same":
        # Tab is the first key since the press: it brings the caret back and types nothing.
        page.keyboard.press("Tab")
        expect_words(area, "Wort")
    expect_caret(page, area)
    expect_picked(page, name)


# Implied 6


@pytest.mark.parametrize("name, label", WRITTEN)
def test_a_control_reached_by_the_keys_keeps_the_writing_open(editor, name, label):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    control = page.locator(".panel").get_by_label(label, exact=True)
    # No press comes first.
    control.focus()
    expect(control).to_be_focused()
    expect(page.locator(OPEN)).to_have_count(1)
    if control.evaluate("el => el.tagName") == "SELECT":
        control.select_option(
            control.evaluate("el => [...el.options].find((o) => !o.selected && o.value).value")
        )
        # Who walks a select with the keys keeps the focus there, until Enter.
        expect(control).to_be_focused()
        expect(page.locator(OPEN)).to_have_count(1)
        page.keyboard.press("Enter")
    else:
        # A colour is set once its picker has closed.
        control.fill("#00ff00")
    expect_caret(page, area)
    expect_picked(page, name)


# Implied 7


@pytest.mark.parametrize("to", ["page", "block", "title"])
@pytest.mark.parametrize("name", ["text", "ruling", "table"])
def test_a_press_on_the_sheet_after_one_in_the_panel_still_ends_the_writing(editor, name, to):
    # Another kind of Lineatur is higher: the other block lies clear of it.
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2, y=200))

    def leave():
        if to == "page":
            unpick(page)
        elif to == "title":
            # The block stays picked: the press itself ends the writing.
            page.get_by_label("Titel").click()
        else:
            pick(page, "b")
        expect(page.locator(OPEN)).to_have_count(0)
        # A picked table's bars lie where the next click would pick it.
        unpick(page)

    # After a pick the caret is back in what is written in.
    write(page, name)
    choose(page, CONTROLS[name][0])
    leave()
    # A list that is still open has the focus.
    write(page, name)
    press(page, CONTROLS[name][0])
    leave()
    # So has a control reached by the keys.
    write(page, name)
    page.locator(".panel").get_by_label(CONTROLS[name][0], exact=True).focus()
    leave()
