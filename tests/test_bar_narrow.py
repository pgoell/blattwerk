"""The bar when the window is tight: an open text, no Mehr, a turn, a long title.

The bar helpers live in test_bar.py."""

import pytest
from conftest import IPAD, TURNED
from playwright.sync_api import expect
from test_bar import (
    BAR,
    EDITS,
    LAST,
    THEMES,
    ZOOM,
    expect_fitted,
    listed,
    menu,
    more,
    resize,
    sized,
    text,
)
from ui import (
    FIELD,
    at,
    centre,
    expect_picked,
    swipe,
    tool,
)


@pytest.mark.parametrize("touch", [True, False], ids=["fingers", "mouse"])
def test_a_text_stays_open_with_its_caret_while_mehr_opens_and_shuts(editor, touch):
    """I3"""
    page = sized(editor, text("a"), width=834, height=1194, touch=touch, theme="")
    expect_fitted(page)
    if touch:
        at(page, "a").tap()
        expect_picked(page, "a")
        # A second tap on the selected text opens it; see test_ipad for the swipe.
        swipe(page, centre(at(page, "a")))
    else:
        at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.type("x")
    if touch:
        more(page).tap()
    else:
        more(page).click()
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("y")
    expect(page.locator(FIELD)).to_have_text("Halloxy")
    # A command picked there ends the writing, as its button in the bar does.
    tool(page, "Lösungen zeigen").click()
    expect(page.locator(FIELD)).to_have_count(0)
    expect(at(page, "a")).to_contain_text("Halloxy")


@THEMES
def test_where_all_fits_there_is_no_mehr(editor, theme):
    """I4"""
    page = editor(text("a"), theme=theme)
    expect_fitted(page)
    expect(more(page)).to_have_count(0)
    expect(page.get_by_label("Feedback", exact=True)).to_be_visible()


@THEMES
def test_a_turn_of_the_ipad_shuts_mehr_and_fits_the_bar_anew(editor, theme):
    """I4"""
    page = editor(text("a"), theme=theme, touch=True)
    expect_fitted(page)
    upright = page.evaluate(BAR)["names"]
    for size in (TURNED, IPAD):
        more(page).tap()
        expect(menu(page)).to_be_visible()
        resize(page, **size)
        expect(menu(page)).to_have_count(0)
        expect_fitted(page)
        expect(more(page)).to_have_attribute("aria-expanded", "false")
    assert page.evaluate(BAR)["names"] == upright
    assert listed(page) == [*EDITS, *ZOOM, *LAST][len(upright) :]


@pytest.mark.parametrize("size", [(834, 1194), (768, 1024)], ids=["ipad", "small-ipad"])
def test_a_long_title_pushes_neither_pdf_nor_undo_out_of_the_window(editor, size):
    """I5"""
    page = sized(editor, text("a"), width=size[0], height=size[1], touch=True, theme="")
    expect_fitted(page)
    before = page.evaluate(BAR)["names"]
    title = page.get_by_label("Titel")
    title.fill("W" * 80)
    expect(title).to_have_value("W" * 80)
    expect_fitted(page)
    # The title takes the room of what may fold (#318): those go under "Mehr", the last first, and
    # the four that never fold stay where `expect_fitted` finds them.
    names = page.evaluate(BAR)["names"]
    assert names == before[: len(names)]
    page.keyboard.press("Enter")
    expect(title).not_to_be_focused()
    expect_fitted(page)
