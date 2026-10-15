"""A letter that comes as text input with no usable keydown, as from an IME or an on-screen
keyboard, opens the picked block for writing, and the text goes into it."""

import re

import pytest
from playwright.sync_api import expect
from ui import BROWSER, FIELD, RECT, RULING, TABLE, TEXT, at, box, pick, picked

KINDS = [("text", TEXT), ("shape", RECT), ("table", TABLE), ("ruling", RULING)]


def field(page, kind):
    """What the words go into: a table's first cell, a Lineatur's text, else the block's text."""
    if kind == "table":
        return at(page, "a").locator("textarea")
    if kind == "ruling":
        return at(page, "a").locator("textarea.written")
    return page.locator(FIELD)


def expect_ends(page, kind, words):
    """The field shows the words at its end, as a text typed in at the caret reads."""
    where = field(page, kind)
    if kind in ("table", "ruling"):
        expect(where).to_have_value(re.compile(f"{words}$"))
    else:
        expect(where).to_have_text(re.compile(f"{words}$"))


def ime_keydown(page, key, code=229):
    """A keydown as an IME or an on-screen keyboard sends it: no usable key, the code 229."""
    page.evaluate(
        """([key, code]) => {
            const e = new KeyboardEvent("keydown", {key, bubbles: true, cancelable: true});
            Object.defineProperty(e, "keyCode", {get: () => code});
            document.activeElement.dispatchEvent(e);
        }""",
        [key, code],
    )


@pytest.mark.parametrize("key", ["Process", "Unidentified"])
@pytest.mark.parametrize("kind, props", KINDS)
def test_an_ime_key_with_nothing_usable_opens_the_picked_block_and_keeps_the_letter(
    editor, key, kind, props
):
    page = editor(box("a", kind, props))
    pick(page, "a")
    ime_keydown(page, key)
    page.keyboard.insert_text("Ü")
    page.keyboard.type("bung")
    expect_ends(page, kind, "Übung")


def test_text_input_with_no_keydown_reaches_no_field(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    focus = page.evaluate(
        "() => ({ editable: document.activeElement.isContentEditable, "
        "tag: document.activeElement.tagName })"
    )
    assert not focus["editable"] and focus["tag"] not in ("INPUT", "TEXTAREA")
    page.keyboard.insert_text("Ü")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(at(page, "a")).not_to_contain_text("Ü")
    assert picked(page) == ["a"]


def test_an_ime_key_with_nothing_picked_opens_nothing(editor):
    page = editor(box("a", "text", TEXT))
    ime_keydown(page, "Process")
    page.keyboard.insert_text("Ü")
    expect(page.locator(FIELD)).to_have_count(0)
    assert picked(page) == []


def test_an_ime_key_in_an_open_text_types_the_letter_once(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("ArrowRight")
    ime_keydown(page, "Process")
    page.keyboard.insert_text("Ü")
    page.keyboard.type("bung")
    expect(page.locator(FIELD)).to_have_text("HalloÜbung")


@pytest.mark.skipif(BROWSER != "chromium", reason="WebKit has no CDP to drive a composition")
@pytest.mark.parametrize("kind, props", KINDS)
def test_an_ime_composition_on_a_picked_block_keeps_its_letter(editor, kind, props):
    page = editor(box("a", kind, props))
    pick(page, "a")
    ime_keydown(page, "Process")
    cdp = page.context.new_cdp_session(page)
    cdp.send("Input.imeSetComposition", {"text": "U", "selectionStart": 1, "selectionEnd": 1})
    cdp.send("Input.imeSetComposition", {"text": "Ü", "selectionStart": 1, "selectionEnd": 1})
    cdp.send("Input.insertText", {"text": "Ü"})
    page.keyboard.type("bung")
    expect_ends(page, kind, "Übung")
