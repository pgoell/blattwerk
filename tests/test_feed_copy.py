"""Copying, duplicating and cutting a linked text loose from the word list.

The helpers live in test_feed.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_feed import (
    CHOICE,
    LISTED,
    WORDS,
    editor,  # noqa: F401
)
from test_gaps import step
from test_painter import held
from test_words import go, undo
from ui import (
    TEXT,
    at,
    box,
    doc,
    pick,
    saved,
    sheet,
    user,
)


def test_eigener_text_cuts_the_block_loose_with_its_words(editor):
    """I2: "Eigener Text" makes the words the block's own text, and one undo links it again."""
    client = user()
    linked = {**LISTED, "listCols": 2, "holes": "one", "holeSeed": 7}
    page = editor(box("a", "text", linked), client=client, words=WORDS)
    pick(page, "a")
    choice = page.get_by_label(CHOICE)
    step(page, lambda: choice.select_option(label="Eigener Text"))
    stored = held(page, client)["a"]
    assert stored["text"] == "\n".join(WORDS)
    assert not {"list", "listCols", "holes", "holeSeed"} & set(stored)
    step(page, lambda: undo(page))
    back = held(page, client)["a"]
    assert back["list"] is True
    assert back["holes"] == "one"
    assert back["text"] == "Hallo"


def test_a_copied_linked_text_with_no_list_keeps_its_own_text(editor):
    """I4: a linked text copied from a sheet with no list keeps its own text when pasted on a sheet
    with another list."""
    client = user()
    page = editor(box("t", "text", {**TEXT, "list": True}), client=client)
    other = sheet(client, [box("t", "text", TEXT, z=3)], words=WORDS)
    pick(page, "t")
    page.keyboard.press("Control+c")
    go(page, other)
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    # The sheet's own block is "t"; the pasted one is the other.
    [landed] = [b["props"] for b in doc(page, client)["pages"][0]["blocks"] if b["id"] != "t"]
    assert landed["text"] == "Hallo"
    assert "list" not in landed


def test_cut_loose_keeps_the_line_of_the_mixed_words(editor):
    """I2: a mixed linked text cut loose keeps the line after each word."""
    client = user()
    page = editor(box("a", "text", {**LISTED, "mix": 7}), client=client, words=WORDS)
    pick(page, "a")
    choice = page.get_by_label(CHOICE)
    step(page, lambda: choice.select_option(label="Eigener Text"))
    assert held(page, client)["a"]["mixLine"] == "after"
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(len(WORDS))


def test_a_copied_linked_text_takes_the_list_to_a_sheet_without_one(editor):
    """I4: a linked text pasted on a sheet with no list takes the list, and one undo takes it."""
    client = user()
    page = editor(box("t", "text", LISTED), client=client, words=WORDS)
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "t")
    page.keyboard.press("Control+c")
    go(page, other)
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == WORDS
    listed = [b for b in stored["pages"][0]["blocks"] if b["props"].get("list") is True]
    assert len(listed) == 1
    undo(page)
    stored = doc(page, client)
    assert "words" not in stored
    assert len(stored["pages"][0]["blocks"]) == 1


def test_a_copied_linked_text_lands_cut_loose_on_a_sheet_with_another_list(editor):
    """I4: a linked text pasted on a sheet with another list lands with its words as own text."""
    client = user()
    page = editor(box("t", "text", LISTED), client=client, words=WORDS)
    other = sheet(client, [box("t", "text", TEXT, z=3)], words=["Reh"])
    pick(page, "t")
    page.keyboard.press("Control+c")
    go(page, other)
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Reh"]
    own = "\n".join(WORDS)
    pasted = [b["props"] for b in stored["pages"][0]["blocks"] if b["props"].get("text") == own]
    assert len(pasted) == 1
    assert "list" not in pasted[0]


def test_a_duplicated_linked_text_stays_linked(editor):
    """I4: a duplicated linked text is linked too, and the sheet keeps its list."""
    client = user()
    page = editor(box("t", "text", LISTED), client=client, words=WORDS)
    pick(page, "t")
    page.keyboard.press("Control+d")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == WORDS
    assert [b["props"].get("list") for b in stored["pages"][0]["blocks"]] == [True, True]


def test_several_texts_link_in_one_step(editor):
    """I5: two picked texts take the list in one step, and one undo unlinks both."""
    client = user()
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2), client=client, words=WORDS)
    pick(page, "a", "b")
    choice = page.get_by_label(CHOICE)
    step(page, lambda: choice.select_option(label="Text aus Lernwörtern"))
    assert [b["props"].get("list") for b in saved(page, client)] == [True, True]
    step(page, lambda: undo(page))
    assert [b["props"].get("list") for b in saved(page, client)] == [None, None]
