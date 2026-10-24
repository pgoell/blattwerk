"""The Lernwörter list is stored with the sheet, and a linked Lineatur grows to hold it."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_words import (
    LINKED,
    MODES,
    editor,  # noqa: F401
    field,
    list_tab,
    ready,
    rulings,
    store_words,
    undo,
)
from ui import (
    RULING,
    TEXT,
    at,
    box,
    copy_text,
    doc,
    pick,
    user,
)


def test_the_list_typed_in_the_tab_is_stored_with_the_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    page.keyboard.press("Enter")
    page.keyboard.type("Katze")
    assert doc(page, client)["words"] == ["Hund", "Katze"]
    page.reload()
    ready(page)
    list_tab(page)
    expect(field(page)).to_have_value("Hund\nKatze")


def test_a_pasted_list_lands_one_word_to_a_line(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Igel")
    page.keyboard.press("Enter")
    copy_text(page, "Hund, Katze;Maus\r\nReh")
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Igel\nHund\nKatze\nMaus\nReh")
    assert doc(page, client)["words"] == ["Igel", "Hund", "Katze", "Maus", "Reh"]


@pytest.mark.parametrize("mode", MODES)
def test_the_choice_links_a_lineatur(editor, mode):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option(mode)
    expect(page.get_by_label("Text der Lineatur")).to_have_value(mode)
    assert rulings(doc(page, client))[0]["props"]["list"] == mode
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_count(0)
    expect(page.get_by_text("Lineatur anklicken und lostippen")).to_have_count(0)
    expect(page.get_by_label("Schriftart auf den Zeilen")).to_be_visible()


def test_a_linked_block_grows_to_hold_every_word(editor):
    client = user()
    page = editor(box("r", "ruling", RULING, h=20), client=client)
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("copy")
    grown = rulings(doc(page, client))[0]
    assert grown["h"] == 50
    assert grown["props"]["list"] == "copy"
    undo(page)
    back = rulings(doc(page, client))[0]
    assert back["h"] == 20
    assert "list" not in back["props"]


@pytest.mark.parametrize("case", ["margin", "locked"])
def test_a_block_that_cannot_grow_says_how_many_words_do_not_fit(editor, case):
    client = user()
    if case == "margin":
        # The bottom margin lies at 282 mm: the ruling has room for two rows only.
        page = editor(box("r", "ruling", RULING, y=262), client=client)
        words = ["Hund", "Katze", "Maus", "Reh", "Igel"]
        warning = "3 Wörter passen nicht in die Zeilen."
    else:
        page = editor(box("r", "ruling", RULING, locked=True), client=client)
        words, warning = ["Hund", "Katze", "Maus"], "1 Wort passt nicht in die Zeilen."
    store_words(page, client, words)
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("copy")
    expect(page.locator(".panel [role=status]")).to_have_text(warning)
    assert rulings(doc(page, client))[0]["h"] == 20


def test_a_list_that_grows_later_warns_and_moves_no_block(editor):
    """A linked ruling grows by a row for a new word only into free room (#600): with a block right
    under it, it keeps its rows, warns, and the block stays."""
    client = user()
    # The linked ruling lies at y 50 to 70; this one right under it.
    under = box("u", "ruling", RULING, z=2, y=70, h=20)
    page = editor(box("r", "ruling", LINKED, h=20), under, client=client)
    store_words(page, client, ["Hund", "Katze"])
    list_tab(page)
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Enter")
    page.keyboard.type("Maus")
    expect(field(page)).to_have_value("Hund\nKatze\nMaus")
    assert rulings(doc(page, client))[0]["h"] == 20
    assert rulings(doc(page, client))[1]["y"] == 70
    page.get_by_role("tab", name="Format").click()
    pick(page, "r")
    expect(page.locator(".panel [role=status]")).to_have_text("1 Wort passt nicht in die Zeilen.")


@pytest.mark.parametrize("mode", MODES)
def test_cut_loose_keeps_the_words_as_plain_text(editor, mode):
    client = user()
    page = editor(box("r", "ruling", {**RULING, "list": mode}), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("own")
    props = rulings(doc(page, client))[0]["props"]
    assert "list" not in props
    assert props["text"] == "Hund\nKatze"
    # Trace and row keep their grey text over the words, as they did on the list; copy has none.
    if mode == "copy":
        assert "trace" not in props
    else:
        assert props["trace"] is True
    expect(at(page, "r").locator("textarea.written")).to_have_value("Hund\nKatze")
