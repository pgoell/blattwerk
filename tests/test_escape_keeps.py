"""Escape keeps what was typed, as in PowerPoint: on a name line and in a score box on the sheet
(issue #631). The panel's score field still drops what was typed on Escape."""

import pytest
from playwright.sync_api import expect
from test_menu import item, menu
from ui import RECT, RULING, TABLE, TEXT, at, box, doc, pick, user

WORD = '.block.sel input[aria-label^="Feld"]'
PANEL_SCORE = '.panel input[aria-label="Punkte"]'


def fields_of(page, client, name):
    """The fields the server holds for a name line, once the editor has saved."""
    blocks = doc(page, client)["pages"][0]["blocks"]
    return next(b for b in blocks if b["id"] == name)["props"].get("fields")


def test_escape_keeps_the_word_typed_after_f2_on_a_name_line(editor):
    """A4, issue #631: Escape ends the writing and keeps the word; Ctrl+Z gives Name back."""
    client = user()
    page = editor(box("n", "name", {}), client=client)
    pick(page, "n")
    page.keyboard.press("F2")
    expect(page.locator(WORD).first).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.type("Lena")
    page.keyboard.press("Escape")
    expect(page.locator(WORD)).to_have_count(0)
    expect(at(page, "n")).to_contain_text("Lena")
    assert fields_of(page, client, "n") == ["Lena", "Datum", "Klasse"]
    page.keyboard.press("Control+z")
    expect(at(page, "n")).to_contain_text("Name")
    expect(at(page, "n")).not_to_contain_text("Lena")


def test_escape_keeps_the_word_typed_in_text_bearbeiten_on_a_name_line(editor):
    """A4, issue #631: Text bearbeiten opens the line as F2 does; Escape keeps the word."""
    client = user()
    page = editor(box("n", "name", {}), client=client)
    pick(page, "n")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    item(page, "Text bearbeiten").click()
    expect(page.locator(WORD).first).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.type("Lena")
    page.keyboard.press("Escape")
    expect(page.locator(WORD)).to_have_count(0)
    expect(at(page, "n")).to_contain_text("Lena")
    assert fields_of(page, client, "n") == ["Lena", "Datum", "Klasse"]


def test_escape_keeps_a_word_typed_in_the_second_field_and_drops_an_emptied_one(editor):
    """A4, issue #631: Escape keeps every field as Enter does; an emptied word is dropped."""
    client = user()
    page = editor(box("n", "name", {}), client=client)
    pick(page, "n")
    page.keyboard.press("F2")
    expect(page.locator(WORD).first).to_be_focused()
    page.locator(WORD).nth(1).click()
    page.keyboard.press("Control+a")
    page.keyboard.type("Oma")
    page.keyboard.press("Escape")
    expect(page.locator(WORD)).to_have_count(0)
    assert fields_of(page, client, "n") == ["Name", "Oma", "Klasse"]
    pick(page, "n")
    page.keyboard.press("F2")
    expect(page.locator(WORD).first).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Backspace")
    page.keyboard.press("Escape")
    expect(page.locator(WORD)).to_have_count(0)
    assert fields_of(page, client, "n") == ["Oma", "Klasse"]


def test_escape_keeps_a_score_typed_on_the_sheet(editor):
    """A3, issue #631: a score box on the sheet keeps the typed score on Escape, as Enter does."""
    client = user()
    page = editor(box("p", "points", {"max": 10}), client=client)
    at(page, "p").dblclick()
    field = at(page, "p").locator("input")
    expect(field).to_be_focused()
    page.keyboard.type("7")
    page.keyboard.press("Escape")
    expect(at(page, "p").locator(".points")).to_have_text("/ 7 Punkte")
    assert doc(page, client)["pages"][0]["blocks"][0]["props"]["max"] == 7


def test_escape_in_the_panel_score_field_still_drops_the_typed_score(editor):
    """A3, issue #631 guard: the panel's score field keeps the old score on Escape."""
    page = editor(box("a", "points", {"max": 10}))
    pick(page, "a")
    page.locator(PANEL_SCORE).fill("")
    page.locator(PANEL_SCORE).press_sequentially("7")
    page.locator(PANEL_SCORE).press("Escape")
    expect(at(page, "a").locator(".points")).to_have_text("/ 10 Punkte")
    expect(page.locator(PANEL_SCORE)).to_have_value("10")


@pytest.mark.parametrize(
    "kind,props",
    [("text", TEXT), ("shape", RECT), ("ruling", RULING), ("table", TABLE)],
)
def test_escape_after_f2_keeps_the_typing_on_every_block_that_takes_text(editor, kind, props):
    """Rule 13, issue #631: as on the name line, Escape keeps what F2 and typing put into a text, a
    shape, a Lineatur and a table cell, and one Ctrl+Z takes it back."""
    page = editor(box("a", kind, props))
    pick(page, "a")
    page.keyboard.press("F2")
    page.keyboard.press("Control+a")
    page.keyboard.type("Oma")
    page.keyboard.press("Escape")
    expect(at(page, "a")).to_contain_text("Oma")
    open_fields = ".block.sel [contenteditable=true], .block.sel textarea:not([readonly])"
    expect(page.locator(f"{open_fields}, .block.sel input")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "a")).not_to_contain_text("Oma")
