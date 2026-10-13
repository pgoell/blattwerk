"""A picked Lineatur opens for writing by a key that types a letter, or by a second click."""

import pytest
from playwright.sync_api import expect
from ui import RULING, TEXT, at, box, expect_picked, pick

KINDS = ["l1", "l2", "l3", "l4", "lines", "k5", "k7"]
WRITTEN = "textarea.written"
HINT = "Lineatur anklicken und lostippen"


def ruling(name="l", kind="l1", text=None, props=None, **more):
    made = {**RULING, "kind": kind, **({"text": text} if text is not None else {}), **(props or {})}
    return box(name, "ruling", made, h=40, **more)


def writing(page, name="l"):
    return at(page, name).locator(WRITTEN)


@pytest.mark.parametrize("kind", KINDS)
def test_a_key_on_a_picked_ruling_writes_on_its_rows(editor, kind):
    page = editor(ruling(kind=kind))
    pick(page, "l")
    page.keyboard.type("Mama")
    expect(writing(page)).to_have_value("Mama")
    expect(writing(page)).to_be_focused()
    if kind in ("k5", "k7"):
        expect(at(page, "l").locator("svg text")).to_have_count(4)


def test_a_key_appends_to_the_text_already_there(editor):
    page = editor(ruling(text="ab"))
    pick(page, "l")
    page.keyboard.type("c")
    expect(writing(page)).to_have_value("abc")


@pytest.mark.parametrize("kind", ["l1", "k5"])
def test_a_second_click_opens_a_picked_ruling(editor, kind):
    page = editor(ruling(kind=kind))
    pick(page, "l")
    at(page, "l").click()
    expect(writing(page)).to_be_focused()
    page.keyboard.type("Papa")
    expect(writing(page)).to_have_value("Papa")


def test_command_keys_stay_commands_on_a_picked_ruling(editor):
    page = editor(ruling())
    pick(page, "l")
    before = at(page, "l").bounding_box()["x"]
    page.keyboard.press("ArrowRight")
    # The block moves at once on the key; the wait is for that move, not a fixed time.
    page.wait_for_function(
        "x => document.querySelector('.block[data-id=\"l\"]').getBoundingClientRect().x > x",
        arg=before,
    )
    expect(writing(page)).not_to_be_focused()
    expect(writing(page)).to_have_value("")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(WRITTEN)).to_have_count(2)
    page.keyboard.press("Delete")
    expect(page.locator(WRITTEN)).to_have_count(1)


def test_typing_begun_by_a_key_undoes_and_escape_keeps_the_block_picked(editor):
    page = editor(ruling())
    pick(page, "l")
    page.keyboard.type("Oma")
    page.keyboard.press("Escape")
    expect(writing(page)).not_to_be_focused()
    expect_picked(page, "l")
    expect(writing(page)).to_have_value("Oma")
    page.keyboard.press("Control+z")
    expect(writing(page)).to_have_value("")


def test_a_locked_or_linked_ruling_opens_by_neither_key_nor_click(editor):
    locked = editor(ruling(locked=True))
    at(locked, "l").click()
    locked.keyboard.type("x")
    at(locked, "l").click()
    locked.keyboard.type("y")
    expect(writing(locked)).to_have_value("")
    expect(locked.locator("textarea:focus")).to_have_count(0)


def test_a_linked_ruling_opens_by_neither_key_nor_click(editor):
    page = editor(ruling(props={"list": "row"}), words=["Mama", "Papa"])
    pick(page, "l")
    page.keyboard.type("x")
    at(page, "l").click()
    page.keyboard.type("y")
    expect(page.locator("textarea:focus")).to_have_count(0)
    # A linked Lineatur draws its list, with no field of its own at all.
    expect(page.locator(WRITTEN)).to_have_count(0)


def test_a_drag_and_a_shift_click_do_not_open_the_ruling(editor):
    page = editor(ruling())
    pick(page, "l")
    box_ = at(page, "l").bounding_box()
    x, y = box_["x"] + box_["width"] / 2, box_["y"] + box_["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y, steps=10)
    page.mouse.up()
    expect(writing(page)).to_have_attribute("readonly", "")
    expect(writing(page)).not_to_be_focused()
    page.keyboard.down("Shift")
    at(page, "l").click()
    page.keyboard.up("Shift")
    expect(writing(page)).to_have_attribute("readonly", "")
    expect(writing(page)).not_to_be_focused()


def test_typing_with_several_blocks_picked_opens_none(editor):
    page = editor(ruling("a"), ruling("b", z=2))
    pick(page, "a", "b")
    page.keyboard.type("x")
    expect(writing(page, "a")).to_have_value("")
    expect(writing(page, "b")).to_have_value("")


def test_a_locked_block_picked_beside_the_ruling_keeps_it_shut(editor):
    page = editor(box("fest", "text", TEXT, locked=True), ruling(z=2))
    pick(page, "fest", "l")
    page.keyboard.type("x")
    expect(writing(page)).to_have_value("")
    # Moveable's area lies over the two picked blocks, so the click goes to the point.
    place = at(page, "l").bounding_box()
    page.mouse.click(place["x"] + place["width"] / 2, place["y"] + place["height"] / 2)
    page.keyboard.type("y")
    expect(writing(page)).to_have_value("")
    expect(writing(page)).not_to_be_focused()


def test_the_panel_names_the_way_in(editor):
    page = editor(ruling())
    pick(page, "l")
    expect(page.get_by_text(HINT)).to_be_visible()
