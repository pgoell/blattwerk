"""Silbenbögen and Silbenfarbe on a Lineatur's written line: below the text, clear of its lines."""

import pytest
from playwright.sync_api import expect
from test_bows import bows, expect_under
from test_tints import tint_switch
from ui import RULING, at, box, pick

ABEND = {**RULING, "kind": "l1", "text": "Abend"}
# The drawn lines of a ruling: each `<line>` of its svg, by its height in the window's pixels.
LINES = """(block) => [...block.querySelectorAll('svg.ruling line')].map(
  (l) => l.getBoundingClientRect().top)"""


def bows_switch(page):
    return page.get_by_role("button", name="Silbenbögen", exact=True)


@pytest.mark.parametrize("kind", ["l1", "l2", "l3", "l4", "lines"])
def test_c1_the_panel_shows_the_bows_switch_for_each_lineatur_with_lines(editor, kind):
    page = editor(box("a", "ruling", {**ABEND, "kind": kind}))
    pick(page, "a")
    expect(bows_switch(page)).to_be_visible()


def test_c1_switching_the_bows_on_draws_two_bows_for_abend(editor):
    page = editor(box("a", "ruling", ABEND))
    pick(page, "a")
    bows_switch(page).click()
    expect(at(page, "a").locator(".syl")).to_have_count(2)
    expect_under(bows(page, "a"))


@pytest.mark.parametrize("kind", ["l1", "l2", "l3", "l4", "lines"])
def test_c2_each_bow_lies_below_its_baseline_and_clear_of_the_drawn_lines(editor, kind):
    page = editor(box("a", "ruling", {**ABEND, "kind": kind, "syllables": True}))
    found = bows(page, "a")
    expect_under(found)
    lines = at(page, "a").evaluate(LINES)
    for one in found:
        top, bottom = one["bow"][1], one["bow"][3]
        assert not [y for y in lines if top < y < bottom], (kind, one, lines)


def test_c3_a_karo_ruling_shows_no_bows_switch(editor):
    page = editor(box("a", "ruling", {**ABEND, "kind": "k5"}))
    pick(page, "a")
    expect(page.get_by_role("button", name="Silbenbögen", exact=True)).to_have_count(0)


def test_c4_the_bows_switch_on_then_one_undo_takes_it_off(editor):
    page = editor(box("a", "ruling", ABEND))
    pick(page, "a")
    bows_switch(page).click()
    expect(at(page, "a").locator(".syl")).to_have_count(2)
    page.keyboard.press("Control+z")
    expect(at(page, "a").locator(".syl")).to_have_count(0)


def test_c5_silbenfarbe_colours_the_syllables_of_the_ruling(editor):
    page = editor(box("a", "ruling", ABEND))
    pick(page, "a")
    tint_switch(page).click()
    expect(tint_switch(page)).to_have_attribute("aria-pressed", "true")
    expect(page.get_by_label("Erste Silbe")).to_be_visible()
