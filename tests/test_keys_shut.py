"""Who has the keys after a list or a colour picker of the format panel that the mouse opened
and shut with no pick."""

import pytest
from playwright.sync_api import expect
from test_keys_focus import CONTROLS, KINDS, OPEN
from test_keys_panel import SELECTS, expect_caret, expect_words, write
from ui import BROWSER, TEXT, box, expect_picked, pick

COLOURS = [
    (name, label)
    for name, labels in CONTROLS.items()
    for label in labels
    if (name, label) not in SELECTS
]
# The colours of a block that holds words.
WRITTEN = [(name, label) for name, label in COLOURS if name != "line"]
# The list and the picker take the press that shuts them and tell the page nothing of it, until
# it is called again.
SWALLOW = """() => {
    window.swallow ??= (e) => (e.preventDefault(), e.stopPropagation());
    window.swallowing = !window.swallowing;
    for (const type of ["pointerdown", "mousedown"])
        (window.swallowing ? addEventListener : removeEventListener)(type, window.swallow, true);
}"""


def opened(page, label):
    """Opens the list of a select or the picker of a colour of the panel with the mouse.

    Chromium opens them without a head too, and keeps the keys from the page while they are
    open. WebKit opens neither there: the press gives the focus and no more.
    """
    control = page.locator(".panel").get_by_label(label, exact=True)
    control.click()
    expect(control).to_be_focused()
    if BROWSER != "webkit":
        page.wait_for_function("el => el.matches(':open')", arg=control.element_handle())
    return control


def shut(page, control, way):
    """Shuts what `opened` opened, with no pick."""
    if way == "escape":
        # Chromium's picker keeps the key and the colour the focus. WebKit opened no picker: the
        # key is the first since the press and gives the keys back itself.
        page.keyboard.press("Escape")
    elif way == "same":
        # A press on the select shuts its list as a click on the value it has does: no event comes.
        control.click()
    elif way == "beside":
        # Without a head the press beside a list goes on to the page.
        page.evaluate(SWALLOW)
        page.mouse.click(5, 300)
        page.evaluate(SWALLOW)
    elif way == "ground":
        # The press beside may reach the panel's bare ground too.
        page.locator(".panel").click(position={"x": 3, "y": 3})
    if BROWSER != "webkit" or way != "escape":
        expect(control).to_be_focused()
    if BROWSER != "webkit":
        page.wait_for_function("el => !el.matches(':open')", arg=control.element_handle())


# Asked #210


@pytest.mark.parametrize("way", ["beside", "escape"])
@pytest.mark.parametrize("name, label", COLOURS)
def test_tab_after_a_colour_picker_shut_with_no_pick_picks_the_next_block(editor, name, label, way):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    page.keyboard.press("Tab")
    expect_picked(page, "z")
    assert page.evaluate("document.activeElement === document.body")
    pick(page, name)
    expect(control).to_have_value(was)


# Asked #212


@pytest.mark.parametrize("way", ["same", "beside", "ground"])
@pytest.mark.parametrize("name, label", SELECTS)
def test_a_letter_after_a_list_shut_with_no_pick_is_typed_in_what_is_written_in(
    editor, name, label, way
):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    # The select would take an "l" as its own: another font and another Lineatur start with it.
    page.keyboard.type("l")
    expect_words(area, "Worlt")
    expect(area).to_be_focused()
    expect(control).to_have_value(was)
    expect_picked(page, name)


# Implied 3


@pytest.mark.parametrize("way", ["beside", "ground", "escape"])
@pytest.mark.parametrize("name, label", WRITTEN)
def test_a_colour_picker_shut_with_no_pick_gives_the_caret_back(editor, name, label, way):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    page.keyboard.type("l")
    expect_words(area, "Worlt")
    page.keyboard.press("Backspace")
    expect_caret(page, area)
    expect(control).to_have_value(was)
    expect_picked(page, name)


# Implied 4


@pytest.mark.parametrize("way", ["same", "beside"])
@pytest.mark.parametrize("name, label", SELECTS)
def test_a_letter_after_a_shut_list_changes_no_font_with_nothing_written_in(
    editor, name, label, way
):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, way)
    page.keyboard.type("l")
    expect(control).not_to_be_focused()
    expect(control).to_have_value(was)
    expect(page.locator(OPEN)).to_have_count(0)
    # The keys are the sheet's again.
    page.keyboard.press("Tab")
    expect_picked(page, "z")


@pytest.mark.parametrize("name, label", COLOURS)
def test_a_letter_and_an_arrow_after_a_shut_colour_picker_are_the_sheets(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = opened(page, label)
    was = control.input_value()
    shut(page, control, "beside")
    page.keyboard.type("l")
    expect(control).not_to_be_focused()
    expect(page.locator(OPEN)).to_have_count(0)
    expect_picked(page, name)
    # The arrow, as the first key, moves the block.
    control = opened(page, label)
    shut(page, control, "beside")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")
    expect(control).not_to_be_focused()
    expect(control).to_have_value(was)


# Implied 5


@pytest.mark.parametrize("name, label", SELECTS)
def test_a_list_still_open_keeps_its_keys(editor, name, label):
    page = editor(box(name, *KINDS[name]), box("b", "text", TEXT, z=2))
    area = write(page, name)
    control = opened(page, label)
    was = control.input_value()
    # The arrow walks the list, the letter goes on in it, and Enter picks.
    page.keyboard.press("ArrowDown")
    if BROWSER != "webkit":
        # WebKit opens no list without a head: the letter would be the writing's.
        page.keyboard.type("l")
    page.keyboard.press("Enter")
    expect(control).not_to_have_value(was)
    expect_words(area, "Wort")
    expect_caret(page, area)


@pytest.mark.parametrize("name, label", [(n, c) for n, cs in CONTROLS.items() for c in cs])
def test_a_control_reached_by_the_keys_alone_keeps_them(editor, name, label):
    page = editor(box("z", "text", TEXT), box(name, *KINDS[name], z=2))
    pick(page, name)
    control = page.locator(".panel").get_by_label(label, exact=True)
    # No press comes first.
    control.focus()
    was = control.input_value()
    page.keyboard.type("l")
    expect(control).to_be_focused()
    if (name, label) in SELECTS:
        expect(control).not_to_have_value(was)
    page.keyboard.press("ArrowRight")
    expect(control).to_be_focused()
    expect(page.get_by_label("X", exact=True)).to_have_value("15")
    expect_picked(page, name)
