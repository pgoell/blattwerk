"""Where Enter, Tab and a click leave the focus when a button has it.

Shared pieces live in test_keys.py."""

import re

from playwright.sync_api import expect
from ui import (
    FIELD,
    RULING,
    TEXT,
    at,
    box,
    expect_picked,
    pick,
    picked,
)


def test_a_button_with_the_focus_keeps_enter_and_tab(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    bold = page.locator(".panel button.bold")
    bold.focus()
    page.keyboard.press("Tab")
    # The focus went on to the next button, and the selection stayed.
    expect(page.locator(".panel button.italic")).to_be_focused()
    assert picked(page) == ["a"]
    # Enter presses the button and opens no field.
    page.keyboard.press("Enter")
    expect(at(page, "a").locator(".frame")).to_have_css("font-style", "italic")
    assert page.locator(".ProseMirror").count() == 0
    assert picked(page) == ["a"]


def test_a_press_on_the_sheet_takes_the_focus_from_an_input(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    title = page.get_by_label("Titel")
    for key in ("Tab", "Enter"):
        title.click()
        expect(title).to_be_focused()
        pick(page, "a")
        expect(title).not_to_be_focused()
        page.keyboard.press(key)
        # Tab goes on to the next block, and Enter opens the one pressed.
        expect_picked(page, "b" if key == "Tab" else "a")
    expect(page.locator(FIELD)).to_be_focused()
    # A field that is open keeps the focus when its own block is pressed.
    at(page, "a").locator(".ProseMirror").click()
    expect(page.locator(FIELD)).to_be_focused()


def test_a_button_pressed_with_the_mouse_takes_no_focus(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    for label in ("Sperren", "Entsperren", "Größer", "Schrift größer", "Rechteck", "Rückgängig"):
        page.get_by_label(label, exact=True).click()
        assert page.evaluate("document.activeElement === document.body")
    expect(page.locator(".block")).to_have_count(2)
    # 16 pt. WebKit writes one more digit of it than Chromium does.
    size = re.compile(r"^21\.3333\d*px$")
    expect(at(page, "a").locator(".frame")).to_have_css("font-size", size)
    pick(page, "a")
    page.keyboard.press("Tab")
    expect_picked(page, "b")
    # Enter opens the copy that Duplizieren made and makes no other.
    page.get_by_label("Duplizieren", exact=True).click()
    expect(page.locator(".block")).to_have_count(3)
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    expect(page.locator(".block")).to_have_count(3)
    assert picked(page) != ["b"]


def test_a_button_reached_by_the_keys_keeps_the_focus(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    copy = page.get_by_label("Duplizieren", exact=True)
    copy.focus()
    for count in (2, 3):
        page.keyboard.press("Enter")
        expect(page.locator(".block")).to_have_count(count)
        expect(copy).to_be_focused()
    assert page.locator(".ProseMirror").count() == 0


def test_a_button_ends_or_keeps_a_field_as_before(editor):
    page = editor(box("a", "text", TEXT), box("lines", "ruling", RULING, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    # The panel's buttons leave the focus in the field.
    page.locator(".panel button.bold").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.get_by_label("Schrift größer").click()
    expect(page.locator(FIELD)).to_be_focused()
    # A button of the bar ends it.
    at(page, "a").locator(".ProseMirror").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.get_by_label("Größer", exact=True).click()
    expect(page.locator(".ProseMirror")).to_have_count(0)
    assert picked(page) == ["a"]
    pick(page, "lines")
    page.keyboard.press("Enter")
    written = at(page, "lines").locator("textarea.written")
    expect(written).to_be_editable()
    page.get_by_label("Größer", exact=True).click()
    expect(written).not_to_be_editable()


def test_a_button_in_a_dialog_keeps_the_focus_in_it(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.get_by_label("Feedback").click()
    dialog = page.locator("dialog.feedback")
    # With nothing to send the form stays open and says so.
    dialog.get_by_text("Abschicken").click()
    expect(dialog.get_by_role("status")).not_to_be_empty()
    expect(dialog.get_by_text("Abschicken")).to_be_focused()
    # The keys are the dialog's, not the sheet's behind it, wherever in it the focus is.
    for _ in range(2):
        page.keyboard.press("Delete")
        page.keyboard.press("Tab")
        assert page.locator(".block").count() == 2
        assert picked(page) == ["a"]
        # A press on its heading leaves no control of it with the focus.
        dialog.locator("h1").click()
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)


def test_a_right_click_on_a_button_leaves_the_focus(editor):
    page = editor(box("a", "text", TEXT))
    title = page.get_by_label("Titel")
    title.click()
    page.get_by_label("Größer", exact=True).click(button="right")
    expect(title).to_be_focused()
