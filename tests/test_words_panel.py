"""The list's tab, its buttons and a picked block's own settings."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import re

import pytest
from playwright.sync_api import expect
from test_keys_focus import choose
from test_words import (
    LINKED,
    WORDS,
    editor,  # noqa: F401
    field,
    list_tab,
    redo,
    rulings,
    store_words,
    undo,
)
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    doc,
    maths,
    pick,
    picture,
    thumb,
    upload,
    user,
)


def test_tab_reaches_the_list_controls_and_keys_press_them(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    pick(page, "r")
    page.get_by_label("Art der Lineatur").focus()
    for _ in range(12):
        if page.get_by_label("Text der Lineatur").evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(page.get_by_label("Text der Lineatur")).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(page.get_by_label("Text der Lineatur")).to_have_value("copy")
    assert rulings(doc(page, client))[0]["props"]["list"] == "copy"

    store_words(page, client, ["Hund"])
    list_tab(page)
    field(page).focus()
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_focused()
    page.keyboard.press("Enter")
    assert len(doc(page, client)["pages"]) == 2


@pytest.mark.parametrize(
    "kind", ["text", "shape", "line", "picture", "table", "lineatur", "maths", "group"]
)
def test_a_picked_block_of_any_kind_shows_its_settings_not_the_list(editor, kind):
    client = user()
    blocks = {
        "text": [box("k", "text", TEXT)],
        "shape": [box("k", "shape", RECT)],
        "line": [box("k", "shape", LINE)],
        "picture": [{**picture(upload(client)), "id": "k"}],
        "table": [box("k", "table", TABLE)],
        "lineatur": [box("k", "ruling", RULING)],
        "maths": [box("k", "maths", maths(client))],
        "group": [
            {**box("k", "shape", RECT), "group": ["g"]},
            {**box("j", "shape", RECT, z=2), "group": ["g"]},
        ],
    }[kind]
    page = editor(*blocks, words=WORDS, client=client)
    list_tab(page)
    expect(field(page)).to_be_visible()
    # A click on a block of a group picks the whole group, so no count of one is waited for here.
    at(page, "k").click()
    expect(page.get_by_role("tab", name="Format")).to_have_attribute("aria-selected", "true")
    expect(field(page)).to_have_count(0)
    expect(page.locator(".what")).to_be_visible()


def test_a_lineatur_added_from_the_panel_shows_its_settings(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    list_tab(page)
    page.locator(".dock").get_by_label("Lineatur", exact=True).click()
    expect(page.get_by_label("Art der Lineatur")).to_be_visible()
    expect(field(page)).to_have_count(0)


def test_blattform_a_picked_block_shows_its_settings_not_the_list(editor):
    client = user()
    page = editor(box("a", "text", TEXT), words=WORDS, client=client, theme=None)
    page.locator(".panel").get_by_role("button", name="Lernwörter", exact=True).click()
    expect(field(page)).to_be_visible()
    pick(page, "a")
    expect(field(page)).to_have_count(0)
    expect(page.locator(".what")).to_be_visible()


def test_the_knickblatt_shows_its_own_settings(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    list_tab(page)
    page.get_by_role("button", name="Knickblatt", exact=True).click()
    expect(page.get_by_label("Text der Lineatur")).to_have_value("fold")
    expect(field(page)).to_have_count(0)


def test_typing_in_the_list_with_nothing_picked_stays_on_the_list(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    list_tab(page)
    field(page).click()
    page.keyboard.press("End")
    page.keyboard.type("\nApfel")
    expect(field(page)).to_contain_text("Apfel")
    expect(page.get_by_role("tab", name="Lernwörter")).to_have_attribute("aria-selected", "true")


def test_lernwoerter_bearbeiten_brings_the_list_back(editor):
    page = editor(box("r", "ruling", LINKED), words=WORDS)
    list_tab(page)
    pick(page, "r")
    expect(page.get_by_role("tab", name="Format")).to_have_attribute("aria-selected", "true")
    page.get_by_role("button", name="Lernwörter bearbeiten").click()
    expect(field(page)).to_be_visible()
    # Review of #571: a click on the block that is picked still shows its settings.
    at(page, "r").click()
    expect(page.get_by_role("tab", name="Format")).to_have_attribute("aria-selected", "true")
    expect(field(page)).to_have_count(0)


def test_an_undo_in_the_list_stays_on_the_list(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    list_tab(page)
    field(page).click()
    page.keyboard.press("End")
    page.keyboard.type("\nApfel")
    expect(field(page)).to_contain_text("Apfel")
    undo(page)
    expect(field(page)).to_be_visible()
    expect(page.get_by_role("tab", name="Lernwörter")).to_have_attribute("aria-selected", "true")


def test_a_pick_on_the_ansicht_tab_stays_on_ansicht(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    page.get_by_role("tab", name="Ansicht").click()
    pick(page, "a")
    expect(page.get_by_role("tab", name="Ansicht")).to_have_attribute("aria-selected", "true")


def test_the_two_buttons_under_the_list_say_what_they_make(editor):
    """#429: a teacher could not tell what each button makes."""
    page = editor(words=WORDS)
    list_tab(page)
    blatt = page.get_by_role("button", name="Lernwörter-Blatt")
    knick = page.get_by_role("button", name="Knickblatt", exact=True)
    expect(blatt).to_have_attribute("title", re.compile("Überschrift"))
    expect(knick).to_have_attribute("title", re.compile("Falten"))
    expect(page.locator(".panel .hint", has_text="Überschrift")).to_be_visible()
    expect(page.locator(".panel .hint", has_text="Falten")).to_be_visible()


def test_a_change_to_the_list_reaches_every_linked_block_in_one_undo_step(editor):
    """A6: the blocks draw from the list, on the page in use and on the others."""
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "list": "copy"}, h=40),
        box("o", "ruling", {**RULING, "list": "row"}, y=120, h=40, z=2),
        more=[box("b", "ruling", {**RULING, "list": "trace"}, h=40)],
        client=client,
        words=["Hund"],
    )
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(1)
    list_tab(page)
    field(page).press("Control+End")
    field(page).press_sequentially("\nKatze\nMaus")
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(3)
        expect(block.locator(".listed .row").nth(2).locator("span").first).to_have_text("Maus")
    assert doc(page, client)["words"] == ["Hund", "Katze", "Maus"]
    undo(page)
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(1)
    assert doc(page, client)["words"] == ["Hund"]
    redo(page)
    expect(at(page, "a").locator(".listed .row")).to_have_count(3)


def test_the_choice_gives_the_keys_back_to_the_sheet_and_ends_the_writing(editor):
    """A pick in the list with the mouse leaves the keys with the sheet, as the panel's other
    lists do, and a Lineatur being written in is no longer: linked, it has no field."""
    client = user()
    page = editor(box("a", "ruling", {**RULING, "text": "eigen"}, h=40), client=client)
    store_words(page, client, ["Hund"])
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(at(page, "a").locator("textarea.written:not([readonly])")).to_be_focused()
    control = choose(page, "Text der Lineatur")
    expect(control).not_to_be_focused()
    expect(at(page, "a").locator("textarea")).to_have_count(0)
    expect(at(page, "a").locator(".listed .row span")).to_have_text("Hund")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")
    # Cut loose again, the block is not being written in.
    page.locator(".panel").get_by_label("Text der Lineatur").select_option("own")
    expect(at(page, "a").locator("textarea.written")).to_have_attribute("readonly", "")
    assert rulings(doc(page, client))[0]["props"]["text"] == "Hund"


def test_a_list_too_long_for_one_page_of_the_blatt_runs_on_with_no_warning(editor):
    """A list too long for one page's rows goes on to the next page, so the tab says nothing."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, [f"Wort{n}" for n in range(12)])
    list_tab(page)
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    stored = doc(page, client)
    assert len(stored["pages"]) == 3
    assert [b["h"] for b in rulings(stored, 1)] == [72, 72, 72]


def test_a_short_lineatur_is_said_though_another_shows_every_word(editor):
    """Review of #571: only a run-on Lineatur covers the words another cannot show."""
    page = editor(
        box("a", "ruling", LINKED, h=40),
        box("b", "ruling", LINKED, y=120, h=10, z=2),
        words=["Hund", "Katze", "Igel"],
    )
    list_tab(page)
    status = page.locator(".panel [role=status]")
    expect(status).to_have_text("In einer Lineatur passen 2 Wörter nicht in die Zeilen.")


def test_a_lineatur_in_a_group_with_a_locked_block_takes_the_list_and_does_not_grow(editor):
    """Review: such a block is as fixed as the locked one, as "Bis Seitenende" has it."""
    client = user()
    page = editor(
        box("r", "ruling", RULING, group=["g"]),
        box("t", "text", TEXT, y=150, z=2, locked=True, group=["g"]),
        client=client,
    )
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel"])
    at(page, "r").click()
    page.get_by_label("Text der Lineatur").select_option("copy")
    stored = rulings(doc(page, client))[0]
    assert (stored["props"]["list"], stored["h"]) == ("copy", 20)
    said = "3 Wörter passen nicht in die Zeilen."
    expect(page.locator(".panel [role=status]")).to_have_text(said)
