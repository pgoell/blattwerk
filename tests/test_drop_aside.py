"""A drag the sheet does not take: a dialog, the bar, or an open text field.

The drop helpers live in test_drop.py."""

import pytest
from playwright.sync_api import expect
from test_drop import (
    DRAG_START,
    EFFECT,
    HTTP,
    KEPT,
    LINK_EFFECT,
    PNG,
    REACHES,
    behind,
    landed,
    new,
    picture,
    spot,
)
from ui import (
    FIELD,
    TEXT,
    box,
    centre,
    drop,
    pick,
    saved,
    user,
)


def test_a_drop_while_a_dialog_is_open_adds_nothing(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    point = behind(page)
    drop(page, *point, PNG)
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    # A picture of the first drop would be there by the time the second one's is.
    drop(page, *point, PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]


def test_a_dialog_shows_that_it_takes_no_drop_and_the_browser_keeps_none(editor):
    page = editor(box("a", "text", TEXT))
    url = page.url
    point = behind(page)
    assert page.evaluate(EFFECT, point) == "none"
    assert drop(page, *point, PNG) == KEPT
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    assert page.evaluate(EFFECT, point) == "copy"
    assert drop(page, *point, PNG) == KEPT
    landed(page, 2)
    assert page.url == url


def test_a_file_dragged_over_the_top_bar_or_the_panel_is_refused(editor):
    page = editor(box("a", "text", TEXT))
    assert page.evaluate(EFFECT, centre(page.locator("header button").first)) == "none"
    assert page.evaluate(EFFECT, centre(page.locator("aside.panel"))) == "none"
    assert page.evaluate(EFFECT, spot(page, 105, 150)) == "copy"


def test_words_dragged_over_a_text_field_get_no_answer_from_the_editor(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    field = page.locator(FIELD)
    expect(field).to_be_visible()
    assert page.evaluate(LINK_EFFECT, [*centre(field), [("text/plain", "Wort")]]) == "unset"


@pytest.mark.parametrize(
    "items",
    [
        [("text/plain", "Wort"), ("text/html", "<b>Wort</b>")],
        [("text/uri-list", HTTP)],
    ],
    ids=["selected words", "link"],
)
def test_a_drag_into_an_open_text_field_is_left_to_the_field(editor, items):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    field = page.locator(FIELD)
    expect(field).to_be_visible()
    assert page.evaluate(LINK_EFFECT, [*centre(field), items]) == "unset"
    # The field's own handler may prevent the drop, so ask whether the drop reached the field.
    assert page.evaluate(REACHES, [*centre(field), items]) == ["dragover", "drop"]


def test_a_drag_started_in_the_page_is_left_to_the_page(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    field = page.locator(FIELD)
    expect(field).to_be_visible()
    page.evaluate(DRAG_START, centre(field))
    assert page.evaluate(LINK_EFFECT, [*spot(page, 105, 150), picture(HTTP)]) == "unset"
