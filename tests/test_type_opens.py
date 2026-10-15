"""A picked text, shape or table opens for writing by a typed letter or a second click."""

import re

import pytest
from playwright.sync_api import expect
from ui import (
    BROWSER,
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    upload,
    user,
)

SHAPE = {**RECT, **TEXT}
CELL = '[data-id="t"] textarea:not([readonly])'


def test_typing_opens_a_picked_text_and_writes_after_its_text(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.type("Welt")
    expect(page.locator(FIELD)).to_have_text("HalloWelt")
    expect(page.locator(FIELD)).to_be_focused()


def test_typing_opens_a_picked_shape(editor):
    page = editor(box("s", "shape", SHAPE))
    pick(page, "s")
    page.keyboard.type("Welt")
    expect(page.locator(FIELD)).to_have_text("HalloWelt")


def test_typing_opens_the_first_cell_of_a_picked_table(editor):
    page = editor(box("t", "table", TABLE))
    pick(page, "t")
    page.keyboard.type("x")
    expect(page.locator(CELL)).to_have_value("Hx")
    expect(page.locator(CELL)).to_be_focused()


def test_a_drag_of_a_picked_text_still_moves_it(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    before = at(page, "a").bounding_box()
    x, y = before["x"] + before["width"] / 2, before["y"] + before["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y, steps=10)
    page.mouse.up()
    expect(page.locator(FIELD)).to_have_count(0)
    assert at(page, "a").bounding_box()["x"] > before["x"] + 20


@pytest.mark.parametrize("kind", ["line", "picture", "maths", "group"])
def test_typing_changes_no_line_picture_maths_block_or_group(editor, kind):
    client = user()
    if kind == "line":
        made = [box("x", "shape", LINE)]
    elif kind == "picture":
        made = [{**picture(upload(client)), "id": "x"}]
    elif kind == "maths":
        made = [box("x", "maths", maths(client))]
    else:
        made = [
            box("x", "text", TEXT, group=["x", "y"]),
            box("y", "text", TEXT, z=2, group=["x", "y"]),
        ]
    page = editor(*made, client=client)
    if kind == "group":
        # A click on one member picks the whole group.
        at(page, "x").click()
        expect(page.locator(".block.sel")).to_have_count(2)
    else:
        pick(page, "x")
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    page.keyboard.type("x")
    page.wait_for_timeout(1500)
    expect(page.locator(FIELD)).to_have_count(0)
    expect(page.locator("textarea:focus")).to_have_count(0)
    assert client.get(f"/api/sheets/{sheet_id}").json()["doc"] == before


def test_typing_opens_nothing_with_two_blocks_picked_or_a_locked_block(editor):
    page = editor(box("a", "text", TEXT), box("b", "shape", SHAPE, z=2))
    pick(page, "a", "b")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_count(0)
    locked = editor(box("fest", "text", TEXT, locked=True))
    pick(locked, "fest")
    locked.keyboard.type("x")
    expect(locked.locator(FIELD)).to_have_count(0)


def test_a_command_key_does_not_open_a_picked_text(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    before = at(page, "a").bounding_box()["x"]
    page.keyboard.press("ArrowRight")
    page.wait_for_function(
        "x => document.querySelector('.block[data-id=\"a\"]').getBoundingClientRect().x > x",
        arg=before,
    )
    expect(page.locator(FIELD)).to_have_count(0)
    page.keyboard.press("Delete")
    expect(at(page, "a")).to_have_count(0)


def test_undo_takes_the_typed_letters_back(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.type("Welt")
    expect(page.locator(FIELD)).to_have_text("HalloWelt")
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    page.keyboard.press("Control+z")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(at(page, "a")).to_contain_text("Hallo")
    expect(at(page, "a")).not_to_contain_text("Welt")


def test_typing_on_a_turned_text_opens_it(editor):
    page = editor(box("a", "text", TEXT, angle=30))
    pick(page, "a")
    page.keyboard.type("Welt")
    expect(page.locator(FIELD)).to_have_text("HalloWelt")


def test_an_altgr_character_opens_a_picked_text(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("AltGraph+e")
    expect(page.locator(FIELD)).to_be_focused()


@pytest.mark.parametrize(
    "name, made, field, expected",
    [
        pytest.param("a", box("a", "text", TEXT), FIELD, "Hallo Welt", id="text"),
        pytest.param(
            "s",
            box("s", "shape", {**SHAPE, "text": "Rose"}),
            FIELD,
            "Rose rot",
            id="shape",
        ),
        pytest.param(
            "t",
            box("t", "table", {**TABLE, "cells": [["Zahl", "Z"], ["3", "7"]]}),
            CELL,
            "Zahl Eins",
            id="table",
        ),
        pytest.param(
            "r",
            box("r", "ruling", {**RULING, "text": "Oma"}),
            ".block.sel textarea",
            "Oma malt",
            id="ruling",
        ),
    ],
)
def test_a_space_opens_a_picked_block_and_types_into_it(editor, name, made, field, expected):
    page = editor(made)
    pick(page, name)
    page.keyboard.press("Space")
    expect(page.locator(field)).to_be_focused()
    page.keyboard.type(expected.split(" ")[-1])
    if field == FIELD:
        expect(page.locator(field)).to_have_text(expected)
    else:
        expect(page.locator(field)).to_have_value(expected)


def test_a_space_after_escape_on_a_typed_text_types_the_space(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.type("Birne")
    expect(page.locator(FIELD)).to_have_text("HalloBirne")
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    page.keyboard.press("Space")
    page.keyboard.type("Ei")
    expect(page.locator(FIELD)).to_have_text("HalloBirne Ei")


def test_undo_after_escape_gives_back_the_word_before_the_space(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.type("Birne")
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    page.keyboard.press("Space")
    page.keyboard.type("Ei")
    expect(page.locator(FIELD)).to_have_text("HalloBirne Ei")
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_contain_text("HalloBirne")
    expect(at(page, "a")).not_to_contain_text("Ei")


def test_a_space_with_nothing_picked_types_nothing(editor):
    page = editor(box("a", "text", TEXT))
    page.keyboard.press("Space")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(page.locator("textarea:focus")).to_have_count(0)
    expect(at(page, "a")).to_have_text("Hallo")


@pytest.mark.parametrize("key", ["Enter", "F2"])
def test_a_held_space_then_enter_keeps_the_text(editor, key):
    """Review of #561: Space held, Enter or F2, Space let go opens the text with all of it picked
    and types no space over it."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.down("Space")
    page.keyboard.press(key)
    page.keyboard.up("Space")
    expect(page.locator(FIELD)).to_be_focused()
    expect(page.locator(FIELD)).to_have_text("Hallo")


def test_a_held_space_then_a_click_in_the_panel_types_nothing(editor):
    """Review of #561: Space held, a click into the panel's first field, Space let go: the field
    keeps the focus and the text stays as it was."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.down("Space")
    first = page.locator(".panel input").first
    first.click()
    page.keyboard.up("Space")
    expect(first).to_be_focused()
    expect(at(page, "a")).to_have_text("Hallo")


def test_a_held_space_with_a_picked_text_pans_and_types_nothing(editor):
    """The orchestrator's check on #561: Space held and a drag move the desk with a picked text,
    as before this fix, and no space lands in the text."""
    from test_zoom import pan, roomy

    page = editor(box("a", "text", TEXT))
    roomy(page)
    pick(page, "a")
    corner = page.locator(".desk").bounding_box()
    pan(page, (corner["x"] + 40, corner["y"] + 40), 60, 40)
    expect(page.locator(FIELD)).to_have_count(0)
    expect_picked(page, "a")
    expect(at(page, "a")).to_have_text("Hallo")


def click_at(page, name, x_share=0.02, y_share=0.5):
    """A second click on the block at those shares of its width and height, on whatever
    lies on top there."""
    box = at(page, name).bounding_box()
    page.mouse.click(box["x"] + box["width"] * x_share, box["y"] + box["height"] * y_share)


def click_after(page, name, n, below=False):
    """A second click just left of the gap after the n-th letter of the block's drawn text,
    or under it near the block's bottom edge."""
    x, y, bottom = page.evaluate(
        """([name, n]) => {
            const block = document.querySelector(`.block[data-id="${name}"]`);
            const walk = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walk.nextNode()) && node.data.length < n);
            const range = document.createRange();
            range.setStart(node, n - 1);
            range.setEnd(node, n);
            const r = range.getBoundingClientRect();
            return [r.right - 1, r.top + r.height / 2, block.getBoundingClientRect().bottom - 3];
        }""",
        [name, n],
    )
    if below:
        assert bottom > y + 10, "the block has no room under its text"
        y = bottom
    page.mouse.click(x, y)


def test_a_second_click_opens_a_picked_text_with_the_caret_where_it_was(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    click_after(page, "a", 2)
    page.keyboard.type("X")
    expect(page.locator(FIELD)).to_have_text("HaXllo")


def test_a_second_click_below_the_text_puts_the_caret_on_its_last_line(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    click_after(page, "a", 2, below=True)
    page.keyboard.type("X")
    expect(page.locator(FIELD)).to_have_text("HaXllo")


def test_a_second_click_opens_a_picked_shape_with_words(editor):
    page = editor(box("s", "shape", SHAPE))
    pick(page, "s")
    click_after(page, "s", 3)
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("X")
    expect(page.locator(FIELD)).to_have_text("HalXlo")


def test_a_second_click_opens_the_cell_clicked_in_a_picked_table(editor):
    page = editor(box("t", "table", TABLE))
    pick(page, "t")
    # The cell at the bottom right, "7": the caret goes to its end.
    click_at(page, "t", 0.9, 0.8)
    expect(page.locator(CELL)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(CELL)).to_have_value("7x")


def test_escape_during_a_press_makes_its_release_no_click(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    where = at(page, "a").bounding_box()
    page.mouse.move(where["x"] + 5, where["y"] + 5)
    page.mouse.down()
    page.keyboard.press("Escape")
    page.mouse.up()
    expect_picked(page, "a")
    expect(page.locator(FIELD)).to_have_count(0)


def test_shift_or_ctrl_click_on_a_picked_text_opens_nothing(editor):
    for key in ("Shift", "Control"):
        page = editor(box("a", "text", TEXT))
        pick(page, "a")
        at(page, "a").click(modifiers=[key])
        expect(page.locator(FIELD)).to_have_count(0)


def test_a_click_on_one_of_several_picked_blocks_opens_nothing(editor):
    page = editor(box("a", "text", TEXT), {**box("b", "shape", SHAPE, z=2), "y": 120})
    pick(page, "a", "b")
    click_at(page, "a", 0.1)
    expect(page.locator(FIELD)).to_have_count(0)


def test_a_double_click_on_an_unpicked_text_opens_it_and_picks_no_word(editor):
    page = editor(box("a", "text", TEXT))
    at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_contain_text("Hallo")


@pytest.mark.parametrize("kind", ["line", "picture", "maths", "group", "locked"])
def test_a_second_click_opens_no_line_picture_maths_block_group_or_locked(editor, kind):
    client = user()
    if kind == "line":
        made = [box("x", "shape", LINE)]
    elif kind == "picture":
        made = [{**picture(upload(client)), "id": "x"}]
    elif kind == "maths":
        made = [box("x", "maths", maths(client))]
    elif kind == "group":
        made = [
            box("x", "text", TEXT, group=["x", "y"]),
            {**box("y", "text", TEXT, z=2, group=["x", "y"]), "y": 120},
        ]
    else:
        made = [box("x", "text", TEXT, locked=True)]
    page = editor(*made, client=client)
    if kind == "group":
        at(page, "x").click()
        expect(page.locator(".block.sel")).to_have_count(2)
    else:
        pick(page, "x")
    click_at(page, "x")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(page.locator("textarea:focus")).to_have_count(0)


WRITABLE = [
    pytest.param("a", box("a", "text", TEXT), FIELD, "Halloäb", id="text"),
    pytest.param("s", box("s", "shape", SHAPE), FIELD, "Halloäb", id="shape"),
    pytest.param("t", box("t", "table", TABLE), CELL, "Häb", id="table"),
    pytest.param(
        "r",
        box("r", "ruling", {**RULING, "text": "Oma"}),
        ".block.sel textarea",
        "Omaäb",
        id="ruling",
    ),
]


def expect_written(page, field, expected):
    if field == FIELD:
        expect(page.locator(field)).to_have_text(expected)
    else:
        expect(page.locator(field)).to_have_value(expected)


def german_key(page, key, text):
    """A key Playwright's keyboard does not know, as ä or a dead key: its keydown where the
    focus is, and then, as the browser does after the keydown, its text where the focus is now."""
    page.evaluate(
        """key => document.activeElement.dispatchEvent(
            new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }))""",
        key,
    )
    page.keyboard.insert_text(text)


@pytest.mark.parametrize("name, made, field, expected", WRITABLE)
def test_an_umlaut_as_the_first_key_opens_a_picked_block_and_lands(
    editor, name, made, field, expected
):
    page = editor(made)
    pick(page, name)
    german_key(page, "ä", "ä")
    page.keyboard.press("b")
    expect_written(page, field, expected)


@pytest.mark.parametrize("name, made, field, expected", WRITABLE)
def test_a_dead_key_as_the_first_key_opens_a_picked_block(editor, name, made, field, expected):
    """^ then e on a German keyboard: the ^ is a dead key whose keydown says "Dead", and ê
    follows."""
    page = editor(made)
    pick(page, name)
    german_key(page, "Dead", "ê")
    expect_written(page, field, expected.replace("äb", "ê"))


@pytest.mark.skipif(
    BROWSER == "webkit", reason="a dead key is sent through Chromium's DevTools protocol"
)
@pytest.mark.parametrize("name, made, field, expected", WRITABLE)
def test_a_dead_key_then_a_letter_opens_a_picked_block_and_lands_the_accent(
    editor, name, made, field, expected
):
    """^ then e on a German keyboard: the ^ is a dead key, and ê lands in the block."""
    page = editor(made)
    pick(page, name)
    cdp = page.context.new_cdp_session(page)
    cdp.send(
        "Input.dispatchKeyEvent",
        {"type": "keyDown", "key": "Dead", "code": "Backquote", "windowsVirtualKeyCode": 220},
    )
    cdp.send("Input.imeSetComposition", {"text": "^", "selectionStart": 1, "selectionEnd": 1})
    cdp.send(
        "Input.dispatchKeyEvent",
        {"type": "keyUp", "key": "Dead", "code": "Backquote", "windowsVirtualKeyCode": 220},
    )
    cdp.send("Input.insertText", {"text": "ê"})
    expect_written(page, field, expected.replace("äb", "ê"))


@pytest.mark.parametrize("name, made, field, expected", WRITABLE)
def test_a_second_click_opens_a_picked_block_and_the_first_letter_lands(
    editor, name, made, field, expected
):
    page = editor(made)
    pick(page, name)
    click_at(page, name, 0.9)
    german_key(page, "ä", "ä")
    page.keyboard.press("b")
    if name == "a" or name == "s":
        # The click lands right of the text: the caret at its end.
        expect_written(page, field, expected)
    else:
        expect(page.locator(field)).to_be_focused()
        expect(page.locator(field)).to_have_value(re.compile("äb$"))


def test_undo_takes_back_what_a_second_click_let_type(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    click_after(page, "a", 2)
    page.keyboard.type("XY")
    expect(page.locator(FIELD)).to_have_text("HaXYllo")
    page.keyboard.press("Escape")
    expect_picked(page, "a")
    page.keyboard.press("Control+z")
    expect(page.locator(FIELD)).to_have_count(0)
    expect(at(page, "a")).to_have_text("Hallo")
