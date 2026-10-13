"""Removing one guide line: by dragging its number off the sheet, or by a right click on it.

The panel's hint says so too.
"""

import re

import pytest
from playwright.sync_api import expect
from ui import TEXT, at, box, expect_picked, pick

HINT = (
    "Eine einzelne Hilfslinie entfernen: an ihrer Zahl vom Blatt ziehen "
    "oder mit der rechten Maustaste auf die Zahl klicken."
)
# The sheet's guide lines, or a page's own. Each tab is the `b` in its line; `.x` is upright.
LINES = {"guide": ".sheet .rule:not(.own)", "own guide": ".sheet .rule.own"}


def sheet_with_guides(editor, thing, axes):
    """The block "a" picked, and a guide line for each letter of `axes`: `x` upright, `y` level."""
    page = editor(box("a", "text", TEXT, x=60, w=60))
    at(page, "a").click()
    page.get_by_role("tab", name="Ansicht").click()
    if thing == "own guide":
        page.get_by_role("button", name="Nur diese Seite").click()
    for axis in axes:
        page.get_by_role("button", name="Senkrecht" if axis == "x" else "Waagerecht").click()
    return page


def tabs(page, thing):
    return page.locator(f"{LINES[thing]} b")


def centre(locator):
    r = locator.bounding_box()
    return r["x"] + r["width"] / 2, r["y"] + r["height"] / 2


@pytest.mark.parametrize("thing", ["guide", "own guide"])
def test_a_guide_dragged_off_the_sheet_goes_alone_and_one_undo_brings_it_back(editor, thing):
    page = sheet_with_guides(editor, thing, "xxy")
    all_tabs = tabs(page, thing)
    expect(all_tabs).to_have_count(3)
    before = all_tabs.all_inner_texts()
    # The second upright guide's tab goes to the left, past the sheet's edge, and is let go there.
    x, y = centre(all_tabs.nth(1))
    left = page.locator(".sheet").first.bounding_box()["x"] - 20
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(left, y, steps=5)
    # The line is let go where the page last drew it: a hand lets go after it sees the line there.
    expect(all_tabs.nth(1)).to_have_text(re.compile("^-"))
    page.mouse.up()
    expect(all_tabs).to_have_text([before[0], before[2]])
    page.keyboard.press("Control+z")
    expect(all_tabs).to_have_text(before)


@pytest.mark.parametrize("thing", ["guide", "own guide"])
def test_a_right_click_removes_one_guide_in_one_undo_step(editor, thing):
    page = sheet_with_guides(editor, thing, "xxx")
    all_tabs = tabs(page, thing)
    expect(all_tabs).to_have_count(3)
    before = all_tabs.all_inner_texts()
    all_tabs.nth(1).click(button="right")
    page.locator("dialog.menu").get_by_role("menuitem", name="Hilfslinie entfernen").click()
    expect(all_tabs).to_have_text([before[0], before[2]])
    page.keyboard.press("Control+z")
    expect(all_tabs).to_have_text(before)
    page.keyboard.press("Control+y")
    expect(all_tabs).to_have_text([before[0], before[2]])


def test_a_right_click_on_a_guide_keeps_the_selection_and_escape_keeps_the_guide(editor):
    page = sheet_with_guides(editor, "guide", "xx")
    pick(page, "a")
    expect_picked(page, "a")
    all_tabs = tabs(page, "guide")
    expect(all_tabs).to_have_count(2)
    all_tabs.nth(0).click(button="right")
    expect(page.locator("dialog.menu")).to_be_visible()
    expect_picked(page, "a")
    page.keyboard.press("Escape")
    expect(page.locator("dialog.menu")).to_have_count(0)
    expect(all_tabs).to_have_count(2)
    expect_picked(page, "a")


def test_alle_entfernen_still_removes_every_guide(editor):
    page = sheet_with_guides(editor, "guide", "xy")
    expect(tabs(page, "guide")).to_have_count(2)
    page.get_by_role("button", name="Alle entfernen").click()
    expect(tabs(page, "guide")).to_have_count(0)


def test_the_panel_says_how_to_remove_one_guide(editor):
    page = editor(box("a", "text", TEXT, x=60, w=60))
    at(page, "a").click()
    page.get_by_role("tab", name="Ansicht").click()
    expect(page.get_by_text(HINT, exact=True)).to_be_visible()


def test_a_right_click_beside_the_menu_on_another_guide_opens_that_one(editor):
    # One upright and one level guide: their tabs lie apart, so the menu does not cover the second.
    page = sheet_with_guides(editor, "guide", "xy")
    all_tabs = tabs(page, "guide")
    expect(all_tabs).to_have_count(2)
    before = all_tabs.all_inner_texts()
    all_tabs.nth(0).click(button="right")
    expect(page.locator("dialog.menu")).to_be_visible()
    # The open menu is modal, so the second tab is reached by the mouse, not by a click on it.
    x, y = centre(all_tabs.nth(1))
    page.mouse.click(x, y, button="right")
    page.get_by_role("menuitem", name="Hilfslinie entfernen").click()
    expect(all_tabs).to_have_text([before[0]])
