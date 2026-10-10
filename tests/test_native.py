"""The controls the browser draws itself, in a real window: a list, a colour picker, the file
dialog, and Tab through the panel. `mise run test:native` runs these, and nothing else runs them.

Headless Chromium opens no list and no picker, so the other tests fake the press. Here the mouse
and the keyboard do everything: a locator only finds the place to press and what to check. The
one way around is the file dialog, which is the system's: the file goes in through the chooser.

An open list and an open picker are windows of their own, and the mouse of the test reaches the
page only. So a pick is made with the keys: the arrows, then Enter.
"""

import pytest
from playwright.sync_api import expect
from ui import FIELD, RECT, RULING, TABLE, TEXT, at, box, centre, expect_picked, png

pytestmark = pytest.mark.native

POPUP = ".panel select:open, .panel input[type=color]:open"
BLACK = {**TEXT, "color": "#000000"}
# A select of the panel, the block that shows it and the value it starts with.
LISTS = [
    ("Schriftart", "text", TEXT, "andika"),
    ("Art der Lineatur", "ruling", RULING, "l4"),
    ("Schriftart der Tabelle", "table", TABLE, "andika"),
]
# What Tab stops at from the panel's first field on, down to the kinds of border.
START = ["X", "Y", "Breite", "Höhe", "Drehung", "Seitenverhältnis sperren"]
FONT = ["Schriftart", "Schrift kleiner", "Schrift größer", "Fett", "Kursiv", "Unterstrichen"]
PLACE = ["Aufzählung", "Nummerierung", "Links", "Mitte", "Rechts", "Oben", "Mitte", "Unten"]
TURN = ["Farbe", "Zeilenabstand", "Rechtsdrehung 90°", "Linksdrehung 90°"]
FLIP = ["Horizontal spiegeln", "Vertikal spiegeln"]
OUTLINE = ["Keine", "1 2 3", "a b c", "Symbol", "Eckig", "Abgerundet", "Rund", "Dreieck"]
FILL = ["Stern", "Sprechblase", "Füllung", "Rand"]
DASH = ["Randstärke", "Durchgezogen", "Gestrichelt", "Gepunktet"]
ORDER = {
    "text": (TEXT, [*START, *FONT, *PLACE, *TURN, *OUTLINE, *FILL, *DASH]),
    # A shape can be mirrored, and its border, which it has, can be taken away.
    "shape": (RECT, [*START, *FONT, *PLACE, *TURN, *FLIP, *OUTLINE, *FILL, "Kein Rand", *DASH]),
}


def press(page, found):
    """Clicks the middle of what the locator finds, with the mouse."""
    page.mouse.click(*centre(found))


def control(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def until(page, key, check):
    """Presses the key until the check holds.

    A list and a picker are `:open` before they listen for keys, and a key that comes in between
    is lost. The key is pressed again only when the one before changed nothing.
    """
    for _ in range(4):
        page.keyboard.press(key)
        try:
            return check()
        except AssertionError:
            pass
    page.keyboard.press(key)
    check()


def opened(page, label):
    """Opens a list or a colour picker of the panel with the mouse."""
    found = control(page, label)
    press(page, found)
    expect(found).to_be_focused()
    expect(page.locator(POPUP)).to_have_count(1)
    return found


def shut(page, found, way):
    """Shuts what `opened` opened, with no pick."""
    if way == "escape":
        until(page, "Escape", lambda: expect(page.locator(POPUP)).to_have_count(0))
        return
    if way == "same":
        press(page, found)
    elif way == "ground":
        # The panel's bare ground, at its upper left corner.
        place = page.locator(".panel").bounding_box()
        page.mouse.click(place["x"] + 3, place["y"] + 3)
    elif way == "beside":
        page.mouse.click(5, 300)
    expect(page.locator(POPUP)).to_have_count(0)


def write(page, name):
    """Opens the text, types "Wort" over what it held and puts the caret before the last letter."""
    press(page, at(page, name))
    expect_picked(page, name)
    page.keyboard.press("Enter")
    # The field hears of a caret the browser moved only a moment later, but of a letter at once.
    page.keyboard.type("Wot")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("r")
    area = page.locator(FIELD)
    expect(area).to_be_focused()
    return area


# Asked #217: a real select opens and a pick lands


@pytest.mark.parametrize("label, kind, props, was", LISTS)
def test_the_arrows_and_enter_pick_in_a_real_list(editor, label, kind, props, was):
    page = editor(box("a", kind, props), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, label)
    expect(found).to_have_value(was)
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value(was)
    # The pick gives the keys back to the sheet (#99): Tab picks the next block.
    expect(found).not_to_be_focused()
    page.keyboard.press("Tab")
    expect_picked(page, "b")


def test_a_pick_in_a_real_list_is_one_undo_step(editor):
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    expect(undo(page)).to_be_disabled()
    # The list walks two down and tells the page nothing until Enter.
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()
    page.keyboard.press("Enter")
    expect(found).not_to_have_value("l4")
    press(page, undo(page))
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_escape_in_a_real_list_with_no_arrow_adds_no_undo_step(editor):
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    shut(page, found, "escape")
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_escape_after_an_arrow_in_a_real_list_picks_as_chromium_does_in_one_step(editor):
    # Chromium takes the option the arrows went to when the list shuts, by Escape or by a click
    # anywhere, and sends `change`. So the page cannot tell it from a pick: it is one step.
    page = editor(box("a", "ruling", RULING))
    press(page, at(page, "a"))
    found = opened(page, "Art der Lineatur")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Escape")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value("l4")
    press(page, undo(page))
    expect(found).to_have_value("l4")
    expect(undo(page)).to_be_disabled()


def test_ctrl_z_right_after_a_pick_in_a_real_list_takes_it_back(editor):
    page = editor(box("a", "text", TEXT))
    press(page, at(page, "a"))
    found = opened(page, "Schriftart")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(found).not_to_have_value("andika")
    # No press in between: the key goes where the pick left the focus.
    page.keyboard.press("Control+z")
    expect(found).to_have_value("andika")
    expect(undo(page)).to_be_disabled()
    expect_picked(page, "a")


# Asked #212


@pytest.mark.parametrize("way", ["escape", "same", "ground"])
def test_a_letter_after_a_real_list_shut_with_no_pick_is_typed_in_the_text(editor, way):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    area = write(page, "a")
    found = opened(page, "Schriftart")
    shut(page, found, way)
    # The select would take an "l" as its own: another font starts with it.
    page.keyboard.type("l")
    expect(area).to_have_text("Worlt")
    expect(area).to_be_focused()
    expect(found).to_have_value("andika")
    expect_picked(page, "a")


def test_a_letter_after_a_click_beside_a_real_list_changes_no_font(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, "Schriftart")
    # In a real window the press beside the list shuts it and goes on to the page.
    shut(page, found, "beside")
    page.keyboard.type("l")
    expect(found).to_have_value("andika")
    expect(found).not_to_be_focused()
    expect(undo(page)).to_be_disabled()
    # The sheet has the keys.
    page.keyboard.press("Delete")
    expect(at(page, "a")).to_have_count(0)


# Asked #217: a real colour picker opens and a pick lands


def test_an_arrow_and_enter_pick_in_a_real_colour_picker(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    words = at(page, "a").get_by_text("Hallo")
    press(page, at(page, "a"))
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    found = opened(page, "Farbe")
    until(page, "ArrowRight", lambda: expect(found).not_to_have_value("#222222"))
    expect(words).not_to_have_css("color", "rgb(34, 34, 34)")
    page.keyboard.press("Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(found).not_to_have_value("#222222")
    expect(found).not_to_be_focused()
    # The whole visit to the picker is one step.
    press(page, undo(page))
    expect(found).to_have_value("#222222")
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    expect(undo(page)).to_be_disabled()


# Asked #210


@pytest.mark.parametrize("way", ["escape", "ground", "beside"])
def test_tab_after_a_real_colour_picker_shut_with_no_pick_picks_the_next_block(editor, way):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    found = opened(page, "Farbe")
    shut(page, found, way)
    expect(found).to_have_value("#222222")
    page.keyboard.press("Tab")
    expect_picked(page, "b")
    expect(found).not_to_be_focused()
    expect(undo(page)).to_be_disabled()


def test_delete_after_a_real_colour_picker_put_back_and_shut_deletes_the_block(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    press(page, at(page, "a"))
    found = opened(page, "Farbe")
    until(page, "ArrowRight", lambda: expect(found).not_to_have_value("#222222"))
    # The first Escape puts the colour back and leaves the picker open: Delete would be its own.
    page.keyboard.press("Escape")
    expect(found).to_have_value("#222222")
    expect(page.locator(POPUP)).to_have_count(1)
    # The second shuts it, and the next key is the sheet's.
    shut(page, found, "escape")
    page.keyboard.press("Delete")
    expect(at(page, "a")).to_have_count(0)
    expect(at(page, "b")).to_have_count(1)


def test_a_letter_after_a_real_colour_picker_shut_with_no_pick_is_typed_in_the_text(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    area = write(page, "a")
    found = opened(page, "Farbe")
    shut(page, found, "escape")
    page.keyboard.type("l")
    expect(area).to_have_text("Worlt")
    expect(area).to_be_focused()
    expect(found).to_have_value("#222222")
    expect_picked(page, "a")


# Asked #258


def test_a_real_colour_picker_moved_away_and_back_adds_no_undo_step(editor):
    # Black lies at the lower edge of the picker's field: one up and one down ends where it began.
    page = editor(box("a", "text", BLACK))
    press(page, at(page, "a"))
    found = opened(page, "Farbe")
    until(page, "ArrowUp", lambda: expect(found).not_to_have_value("#000000"))
    page.keyboard.press("ArrowDown")
    expect(found).to_have_value("#000000")
    shut(page, found, "escape")
    expect(found).to_have_value("#000000")
    expect(undo(page)).to_be_disabled()


# Asked #217: the file dialog of a picture upload


def test_a_picture_given_to_the_file_dialog_lands_on_the_sheet(editor):
    page = editor(box("a", "text", TEXT))
    with page.expect_file_chooser() as dialog:
        press(page, page.get_by_label("Bild", exact=True))
    # The dialog is the system's and no key of the test reaches it: the chooser takes the file.
    dialog.value.set_files({"name": "bild.png", "mimeType": "image/png", "buffer": png()})
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(page.locator(".block.sel img")).to_be_visible()
    expect(at(page, "a")).not_to_have_class("block sel")
    press(page, undo(page))
    expect(page.locator(".block[data-id]")).to_have_count(1)


# Asked #217: Tab order through the panel


@pytest.mark.parametrize("kind", ORDER)
def test_tab_walks_the_panel_in_its_order(editor, kind):
    props, order = ORDER[kind]
    page = editor(box("a", kind, props))
    press(page, at(page, "a"))
    expect_picked(page, "a")
    # F6 goes from the sheet to the bar Einfügen, the header and the panel.
    for _ in range(3):
        page.keyboard.press("F6")
    for i, label in enumerate(order):
        if i:
            page.keyboard.press("Tab")
        expect(page.locator(":focus")).to_have_accessible_name(label)
    expect_picked(page, "a")
