"""The list's field in the panel of a block that shows it, and a picked block's own settings."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_keys_focus import choose
from test_words import (
    LINKED,
    WORDS,
    editor,  # noqa: F401
    field,
    lernen,
    link,
    redo,
    rulings,
    sollen,
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
    blatt,
    box,
    doc,
    expect_picked,
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
        if lernen(page).evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(lernen(page)).to_be_focused()
    page.keyboard.press("Space")
    assert rulings(doc(page, client))[0]["props"]["list"] == "copy"
    page.keyboard.press("Tab")
    expect(field(page)).to_be_focused()
    page.keyboard.type("Hund")
    assert doc(page, client)["words"] == ["Hund"]
    page.keyboard.press("Tab")
    expect(sollen(page)).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(sollen(page)).to_have_value("trace")
    assert rulings(doc(page, client))[0]["props"]["list"] == "trace"


@pytest.mark.parametrize(
    "kind", ["text", "shape", "line", "picture", "table", "lineatur", "maths", "group"]
)
def test_a_picked_block_of_any_kind_shows_its_settings_without_the_list(editor, kind):
    """The list's field stands in the panel of a block that shows the list, and of no other."""
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
    page = editor(*blocks, box("r", "ruling", LINKED, y=200, z=5), words=WORDS, client=client)
    pick(page, "r")
    expect(field(page)).to_be_visible()
    # A click on a block of a group picks the whole group, so no count of one is waited for here.
    at(page, "k").click()
    expect(field(page)).to_have_count(0)
    expect(page.locator(".what")).to_be_visible()


def test_a_lineatur_added_from_the_panel_shows_its_settings(editor):
    page = editor(box("r", "ruling", LINKED), words=WORDS)
    pick(page, "r")
    expect(field(page)).to_be_visible()
    page.locator(".insert, .dock").get_by_label("Lineatur", exact=True).click()
    expect(page.get_by_label("Art der Lineatur")).to_be_visible()
    expect(field(page)).to_have_count(0)


def test_typing_in_the_list_keeps_the_block_picked(editor):
    page = editor(box("r", "ruling", LINKED), words=WORDS)
    pick(page, "r")
    field(page).click()
    page.keyboard.press("Control+End")
    page.keyboard.type("\nApfel")
    expect(field(page)).to_contain_text("Apfel")
    expect_picked(page, "r")


def test_an_undo_in_the_list_stays_on_the_list(editor):
    page = editor(box("r", "ruling", LINKED), words=WORDS)
    pick(page, "r")
    field(page).click()
    page.keyboard.press("Control+End")
    page.keyboard.type("\nApfel")
    expect(field(page)).to_contain_text("Apfel")
    undo(page)
    expect(field(page)).to_be_visible()
    expect(field(page)).not_to_contain_text("Apfel")
    expect_picked(page, "r")


def test_a_pick_turns_the_panel_from_blatt_to_auswahl(editor):
    page = editor(box("a", "text", TEXT), words=WORDS)
    blatt(page)
    expect(page.locator(".what")).to_have_count(0)
    pick(page, "a")
    expect(page.get_by_role("tab", name="Auswahl")).to_have_attribute("aria-selected", "true")
    expect(page.locator(".what")).to_be_visible()


def test_a_change_to_the_list_reaches_every_linked_block_in_one_undo_step(editor):
    """A6: the blocks draw from the list, on the page in use and on the others."""
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "list": "copy"}, h=40),
        box("o", "ruling", {**RULING, "list": "row"}, y=120, h=40, z=2),
        more=[box("b", "ruling", {**RULING, "list": "trace"}, h=40)],
        client=client,
        words=["Hund"],
        seiten=True,
    )
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(1)
    pick(page, "a")
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
    lernen(page).click()
    expect(lernen(page)).not_to_be_focused()
    expect(at(page, "a").locator("textarea")).to_have_count(0)
    expect(at(page, "a").locator(".listed .row span")).to_have_text("Hund")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")
    control = choose(page, "Die Kinder sollen")
    expect(control).not_to_be_focused()
    # Cut loose again, the block is not being written in.
    link(page, "own")
    expect(at(page, "a").locator("textarea.written")).to_have_attribute("readonly", "")
    assert rulings(doc(page, client))[0]["props"]["text"] == "Hund"


def test_a_short_lineatur_is_said_though_another_shows_every_word(editor):
    """Review of #571: only a run-on Lineatur covers the words another cannot show."""
    page = editor(
        box("a", "ruling", LINKED, h=40),
        box("b", "ruling", LINKED, y=120, h=10, z=2),
        words=["Hund", "Katze", "Igel"],
    )
    pick(page, "a")
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
    link(page, "copy")
    stored = rulings(doc(page, client))[0]
    assert (stored["props"]["list"], stored["h"]) == ("copy", 20)
    said = "3 Wörter passen nicht in die Zeilen."
    expect(page.locator(".panel [role=status]")).to_have_text(said)
