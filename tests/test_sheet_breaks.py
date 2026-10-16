"""A syllable break mended once holds for the same word in every block of the sheet (issue #404).

The mend is set in the panel of one block. It is stored with the sheet, so a text added later, and
a block that stood before, split the word the same way.
"""

from playwright.sync_api import expect
from test_painter import held
from test_syllables import gap, word
from ui import TEXT, box, pick, reload, syls, user

SKATE = "Am Abend fahren Oma und Opa mit dem Skateboard."
ROLL = "Das Skateboard rollt."


def bows_on(page):
    page.locator(".panel").get_by_role("button", name="Silbenbögen", exact=True).click()


def mend_skateboard(page):
    """Takes two breaks out of Skateboard in the panel of the picked block: Skate|board."""
    pick(page, "a")
    word(page, "Ska·te·bo·ard").click()
    gap(page, "Ska|teboard").click()
    gap(page, "Skatebo|ard").click()
    expect(word(page, "Skate·board")).to_be_visible()


def test_a_mend_holds_in_a_text_added_later(editor):
    page = editor(box("a", "text", {**TEXT, "text": SKATE}))
    pick(page, "a")
    bows_on(page)
    mend_skateboard(page)
    page.get_by_label("Text", exact=True).click()
    page.keyboard.type(ROLL)
    expect(page.locator(".block.sel .ProseMirror")).to_have_text(ROLL)
    bows_on(page)
    new = page.locator(".block.sel").get_attribute("data-id")
    assert syls(page, new) == ["Das", "Skate", "board", "rollt"]


def test_a_mend_reaches_a_block_that_stood_before_it(editor):
    page = editor(
        box("a", "text", {**TEXT, "text": SKATE}), box("b", "text", {**TEXT, "text": ROLL}, z=2)
    )
    pick(page, "a")
    bows_on(page)
    pick(page, "b")
    bows_on(page)
    mend_skateboard(page)
    pick(page, "b")
    assert syls(page, "b") == ["Das", "Skate", "board", "rollt"]


def test_one_undo_takes_a_mend_back_in_every_block_and_redo_brings_it_back(editor):
    # One click takes the break out of Abend: one step, so one undo.
    page = editor(
        box("a", "text", {**TEXT, "text": SKATE, "syllables": True}),
        box("b", "text", {**TEXT, "text": "Das Abend rollt.", "syllables": True}, z=2),
    )
    pick(page, "a")
    word(page, "A·bend").click()
    gap(page, "A|bend").click()
    pick(page, "b")
    assert syls(page, "b") == ["Das", "Abend", "rollt"]
    pick(page, "a")
    page.keyboard.press("ControlOrMeta+z")
    pick(page, "b")
    assert syls(page, "b") == ["Das", "A", "bend", "rollt"]
    page.keyboard.press("ControlOrMeta+y")
    pick(page, "b")
    assert syls(page, "b") == ["Das", "Abend", "rollt"]


def test_a_mend_holds_after_a_reload(editor, server):
    page = editor(
        box("a", "text", {**TEXT, "text": SKATE}), box("b", "text", {**TEXT, "text": ROLL}, z=2)
    )
    pick(page, "a")
    bows_on(page)
    mend_skateboard(page)
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")
    address = f"{server}/api/sheets/{page.url.rsplit('/', 1)[1]}"
    reload(page, address)
    pick(page, "b")
    bows_on(page)
    assert syls(page, "b") == ["Das", "Skate", "board", "rollt"]


def test_a_block_split_before_the_sheet_mends_moves_its_mend_to_the_sheet(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": SKATE, "syllables": True, "breaks": {"skateboard": [5]}}),
        client=client,
    )
    assert syls(page, "a")[-2:] == ["Skate", "board"]
    pick(page, "a")
    gap(page, "Skate|board").click()
    expect(word(page, "Ska·te·bo·ard")).to_be_visible()
    assert "breaks" not in held(page, client)["a"]


def test_a_mend_on_a_table_and_a_text_both_hold(editor):
    cells = {
        "cells": [["Skateboard", "Oma"]],
        "cols": [1, 1],
        "size": 14,
        "align": "center",
        "line": "#222222",
        "syllables": True,
    }
    page = editor(
        box("a", "text", {**TEXT, "text": SKATE, "syllables": True}), box("t", "table", cells, z=2)
    )
    mend_skateboard(page)
    assert syls(page, "t") == ["Skate", "board", "O", "ma"]


def test_a_mend_holds_for_the_word_in_capitals(editor):
    page = editor(
        box("a", "text", {**TEXT, "text": "SKATEBOARD fahren.", "syllables": True}),
        box("b", "text", {**TEXT, "text": ROLL, "syllables": True}, z=2),
    )
    pick(page, "a")
    word(page, "SKA·TE·BO·ARD").click()
    gap(page, "SKA|TEBOARD").click()
    gap(page, "SKATEBO|ARD").click()
    pick(page, "b")
    assert syls(page, "b") == ["Das", "Skate", "board", "rollt"]
