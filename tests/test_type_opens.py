"""A picked text, shape or table opens for writing by a typed letter or a second click."""

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
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


def test_a_second_click_opens_a_picked_text(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    at(page, "a").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("Welt")
    expect(page.locator(FIELD)).to_contain_text("Welt")


def test_a_second_click_opens_a_picked_shape(editor):
    page = editor(box("s", "shape", SHAPE))
    pick(page, "s")
    at(page, "s").click()
    expect(page.locator(FIELD)).to_be_focused()


def test_a_second_click_opens_the_clicked_cell_of_a_picked_table(editor):
    page = editor(box("t", "table", TABLE))
    pick(page, "t")
    # Bottom right is the cell "7".
    box_ = at(page, "t").bounding_box()
    page.mouse.click(box_["x"] + box_["width"] * 0.75, box_["y"] + box_["height"] * 0.75)
    page.keyboard.type("y")
    expect(page.locator(CELL)).to_have_value("7y")


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
