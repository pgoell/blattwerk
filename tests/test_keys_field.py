"""Tab and Enter in the field a text is typed in, pressed in Chromium on the built frontend."""

from playwright.sync_api import expect
from ui import FIELD, ITEM, TEXT, box, pick, picked, saved, stopped, user


def opened(editor, props, client=None):
    """The editor with the text "a" open: all of it is picked."""
    page = editor(box("a", "text", props), box("b", "text", TEXT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    return page


def test_tab_in_a_plain_paragraph_types_a_tab_stop(editor):
    client = user()
    page = opened(editor, TEXT, client)
    page.keyboard.press("End")
    assert stopped(page, "Tab")
    # `to_have_text` would fold the tab away.
    expect(page.locator(FIELD)).to_have_js_property("textContent", "Hallo\t")
    expect(page.locator(FIELD)).to_be_focused()
    assert picked(page) == ["a"]
    assert saved(page, client)[0]["props"]["text"] == "Hallo\t"


def test_shift_tab_in_a_plain_paragraph_does_nothing(editor):
    page = opened(editor, TEXT)
    page.keyboard.press("End")
    assert stopped(page, "Shift+Tab")
    expect(page.locator(FIELD)).to_be_focused()
    assert picked(page) == ["a"]
    # The caret is where it was.
    page.keyboard.type("!")
    expect(page.locator(FIELD)).to_have_js_property("textContent", "Hallo!")


def test_tab_replaces_the_picked_words_and_undo_brings_them_back(editor):
    page = opened(editor, TEXT)
    page.keyboard.press("Tab")
    expect(page.locator(FIELD)).to_have_js_property("textContent", "\t")
    page.keyboard.press("Control+z")
    expect(page.locator(FIELD)).to_have_js_property("textContent", "Hallo")
    expect(page.locator(FIELD)).to_be_focused()


def test_ctrl_a_and_enter_in_a_field_leave_an_empty_paragraph(editor):
    client = user()
    page = opened(editor, TEXT, client)
    # A caret first: the field opens with all picked, and that is not what Ctrl+A is tested on.
    page.keyboard.press("End")
    page.keyboard.press("Control+a")
    page.keyboard.press("Enter")
    page.keyboard.type("zwei")
    expect(page.locator(f"{FIELD} p")).to_have_text(["", "zwei"])
    expect(page.locator(FIELD)).to_be_focused()
    assert saved(page, client)[0]["props"] == {**TEXT, "text": "\nzwei"}


def test_ctrl_a_and_enter_in_a_list_give_two_items_and_undo_brings_the_text_back(editor):
    page = opened(editor, ITEM)
    page.keyboard.press("End")
    page.keyboard.press("Control+a")
    page.keyboard.press("Enter")
    items = page.locator(f'{FIELD} p[data-list="bullet"]')
    expect(items).to_have_text(["", ""])
    expect(page.locator(f"{FIELD} p")).to_have_count(2)
    page.keyboard.press("Control+z")
    expect(items).to_have_text(["eins"])
    expect(page.locator(f"{FIELD} p")).to_have_count(1)
    expect(page.locator(FIELD)).to_be_focused()
