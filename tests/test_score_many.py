"""Several score boxes picked at once: the panel's Punkte field keeps each box's own number when
the selection is let go, and a number typed there goes to every picked box in one step (issue #398).
"""

import pytest
from playwright.sync_api import expect
from ui import TEXT, at, box, pick, saved, unpick, user

PANEL_SCORE = '.panel input[aria-label="Punkte"]'


def maxes(page, client):
    """The max of each score box on the first page, by the box's name, as the server holds them."""
    return {b["id"]: b["props"]["max"] for b in saved(page, client) if b["type"] == "points"}


def three(editor, client):
    """Three score boxes that hold different numbers, and a text to click."""
    return editor(
        box("a", "points", {"max": 60}),
        box("b", "points", {"max": 15}, z=2),
        box("c", "points", {"max": 10}, z=3),
        box("t", "text", TEXT, z=4),
        client=client,
    )


def undo_is_off(page):
    expect(page.get_by_label("Rückgängig", exact=True).first).to_be_disabled()


@pytest.mark.parametrize("way", ["escape", "click", "select_all"])
def test_several_score_boxes_let_go_keep_their_numbers(editor, way):
    client = user()
    page = three(editor, client)
    if way == "select_all":
        unpick(page)
        page.keyboard.press("Control+a")
    else:
        pick(page, "a", "b")
    if way == "click":
        unpick(page)
    else:
        page.keyboard.press("Escape")
    expect(at(page, "a").locator(".points")).to_have_text("/ 60 Punkte")
    expect(at(page, "b").locator(".points")).to_have_text("/ 15 Punkte")
    expect(at(page, "c").locator(".points")).to_have_text("/ 10 Punkte")
    assert maxes(page, client) == {"a": 60, "b": 15, "c": 10}
    undo_is_off(page)


def test_a_number_typed_in_the_panel_lands_on_every_picked_box_in_one_step(editor):
    client = user()
    page = three(editor, client)
    pick(page, "a", "b", "c")
    # Typed key by key: a fill of the 60 that is there already would send no change.
    page.locator(PANEL_SCORE).fill("")
    page.locator(PANEL_SCORE).press_sequentially("60")
    page.locator(PANEL_SCORE).press("Enter")
    assert maxes(page, client) == {"a": 60, "b": 60, "c": 60}
    unpick(page)
    page.keyboard.press("Control+z")
    expect(at(page, "b").locator(".points")).to_have_text("/ 15 Punkte")
    assert maxes(page, client) == {"a": 60, "b": 15, "c": 10}


def test_a_number_typed_in_the_panel_is_kept_when_the_selection_is_let_go(editor):
    client = user()
    page = three(editor, client)
    pick(page, "a", "b")
    page.locator(PANEL_SCORE).fill("7")
    unpick(page)
    expect(at(page, "a").locator(".points")).to_have_text("/ 7 Punkte")
    expect(at(page, "b").locator(".points")).to_have_text("/ 7 Punkte")
    assert maxes(page, client) == {"a": 7, "b": 7, "c": 10}
