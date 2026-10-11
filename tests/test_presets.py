"""The ready-made sheets' boxes: a score box and a name line open for writing, as a text does.

The checklist of issue #377 names each test: a score box takes a typed number, the panel's Punkte
takes one too, every preset box opens on a double click, and the name line's words can change.
"""

import copy
from typing import cast

import pytest
from playwright.sync_api import expect
from ui import TEXT, at, box, doc, pick, saved, user

from blattwerk.templates import BUILT_IN

SCORE = '.block.sel input[aria-label="Punkte"]'
PANEL_SCORE = '.panel input[aria-label="Punkte"]'
WORD = '.block.sel input[aria-label^="Feld"]'
FIELD = ".block.sel .ProseMirror"
SHEETS = [cast(dict, template)["name"] for template in BUILT_IN]


def preset(name):
    """The pages of a ready-made sheet, as the templates hold them. A copy: a test may change it."""
    template = cast(dict, next(t for t in BUILT_IN if t["name"] == name))
    return copy.deepcopy(template["doc"]["pages"])


def opened(name):
    """The first page of a sheet as the editor's blocks, and its other pages."""
    pages = preset(name)
    return pages[0]["blocks"], pages[1:]


def score_ids(name):
    """The ids of the score boxes of a sheet, in order: the total of the header comes first."""
    return [b["id"] for page in preset(name) for b in page["blocks"] if b["type"] == "points"]


def max_of(blocks, name):
    return next(b for b in blocks if b["id"] == name)["props"]["max"]


def test_a_double_click_on_a_score_box_opens_its_field(editor):
    first, rest = opened("Klassenarbeit")
    page = editor(*first, pages=rest)
    at(page, score_ids("Klassenarbeit")[0]).dblclick()
    expect(page.locator(SCORE)).to_be_focused()


def test_a_typed_score_box_number_is_the_max(editor):
    client = user()
    first, rest = opened("Klassenarbeit")
    page = editor(*first, client=client, pages=rest)
    total = score_ids("Klassenarbeit")[0]
    at(page, total).dblclick()
    page.keyboard.type("25")
    page.keyboard.press("Enter")
    expect(page.locator(SCORE)).to_have_count(0)
    assert max_of(saved(page, client), total) == 25
    assert doc(page, client)["pages"][0]["blocks"] == saved(page, client)


def test_the_panel_takes_a_typed_score(editor):
    client = user()
    first, rest = opened("Klassenarbeit")
    page = editor(*first, client=client, pages=rest)
    task = score_ids("Klassenarbeit")[1]
    pick(page, task)
    page.locator(PANEL_SCORE).fill("7")
    page.locator(PANEL_SCORE).press("Enter")
    expect(page.locator(PANEL_SCORE)).to_have_value("7")
    assert max_of(saved(page, client), task) == 7


def test_the_panel_score_goes_to_every_picked_score_box(editor):
    client = user()
    first, rest = opened("Klassenarbeit")
    page = editor(*first, client=client, pages=rest)
    total, task = score_ids("Klassenarbeit")[:2]
    pick(page, total, task)
    page.locator(PANEL_SCORE).fill("7")
    page.locator(PANEL_SCORE).press("Enter")
    blocks = saved(page, client)
    assert (max_of(blocks, total), max_of(blocks, task)) == (7, 7)


def test_a_typed_score_is_one_undo_step(editor):
    client = user()
    first, rest = opened("Klassenarbeit")
    page = editor(*first, client=client, pages=rest)
    task = score_ids("Klassenarbeit")[1]
    at(page, task).dblclick()
    page.keyboard.type("25")
    page.keyboard.press("Enter")
    expect(at(page, task).locator(".points")).to_have_text("/ 25 Punkte")
    page.keyboard.press("Control+z")
    expect(at(page, task).locator(".points")).to_have_text("/ 10 Punkte")
    assert max_of(saved(page, client), task) == 10
    page.keyboard.press("Control+y")
    expect(at(page, task).locator(".points")).to_have_text("/ 25 Punkte")
    assert max_of(saved(page, client), task) == 25


@pytest.mark.parametrize("key", ["Enter", "F2"])
def test_enter_and_f2_open_a_picked_score_with_all_of_it_picked(editor, key):
    client = user()
    page = editor(box("a", "points", {"max": 10}), box("b", "text", TEXT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press(key)
    expect(page.locator(SCORE)).to_be_focused()
    page.keyboard.type("8")
    page.keyboard.press("Enter")
    assert max_of(saved(page, client), "a") == 8


@pytest.mark.parametrize("key", ["Enter", "F2"])
def test_enter_and_f2_open_a_picked_name_line_with_its_first_word_picked(editor, key):
    page = editor(box("a", "name", {}), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.keyboard.press(key)
    expect(page.locator(WORD).first).to_be_focused()
    page.keyboard.type("Vorname")
    expect(page.locator(WORD).first).to_have_value("Vorname")
    expect(page.locator(WORD)).to_have_count(3)


@pytest.mark.parametrize("key", ["Backspace", "Delete"])
def test_backspace_and_delete_in_a_score_field_delete_no_box(editor, key):
    client = user()
    page = editor(box("a", "points", {"max": 10}), box("b", "text", TEXT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(SCORE)).to_be_focused()
    page.keyboard.press(key)
    expect(page.locator(SCORE)).to_have_value("")
    page.keyboard.type("x")
    expect(page.locator(SCORE)).to_have_value("x")
    expect(page.locator(".block")).to_have_count(2)
    page.keyboard.press("Escape")
    expect(page.locator(SCORE)).to_have_count(0)
    assert max_of(saved(page, client), "a") == 10


@pytest.mark.parametrize("typed", ["", "0", "1000", "x", "5a"])
def test_a_score_that_is_no_whole_number_leaves_the_old_one(editor, typed):
    client = user()
    page = editor(box("a", "points", {"max": 10}), client=client)
    at(page, "a").dblclick()
    expect(page.locator(SCORE)).to_be_focused()
    if typed:
        page.keyboard.type(typed)
    else:
        page.keyboard.press("Backspace")
    page.keyboard.press("Enter")
    expect(page.locator(SCORE)).to_have_count(0)
    expect(at(page, "a").locator(".points")).to_have_text("/ 10 Punkte")
    assert max_of(doc(page, client)["pages"][0]["blocks"], "a") == 10


@pytest.mark.parametrize("kind", ["points", "name"])
def test_a_locked_score_or_name_line_does_not_open(editor, kind):
    page = editor(box("a", kind, {"max": 10}, locked=True))
    at(page, "a").dblclick()
    page.keyboard.press("Enter")
    expect(page.locator(SCORE)).to_have_count(0)
    expect(page.locator(WORD)).to_have_count(0)


@pytest.mark.parametrize("sheet_name", SHEETS)
def test_every_preset_box_is_unlocked_and_ungrouped(sheet_name):
    for page in preset(sheet_name):
        for b in page["blocks"]:
            assert b["locked"] is False and "group" not in b, b["id"]


PRESET_BOXES = [
    (sheet_name, b["id"], b["type"], b.get("props", {}).get("kind"))
    for sheet_name in SHEETS
    for page in preset(sheet_name)
    for b in page["blocks"]
]


@pytest.mark.parametrize(("sheet_name", "name", "kind", "shape"), PRESET_BOXES)
def test_every_preset_box_that_shows_words_or_a_number_opens_on_a_double_click(
    editor, sheet_name, name, kind, shape
):
    # A line shows no words, so it has no field. The test above checks that it is free.
    if kind == "shape" and shape in ("line", "arrow", "double"):
        return
    first, rest = opened(sheet_name)
    page = editor(*first, pages=rest)
    at(page, name).dblclick()
    if kind == "points":
        expect(page.locator(SCORE)).to_be_focused()
    elif kind == "name":
        expect(page.locator(WORD).first).to_be_focused()
    else:
        expect(page.locator(FIELD)).to_be_focused()
