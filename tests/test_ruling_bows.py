"""Silbenbögen and Silbenfarbe on a Lineatur's written line: below the text, clear of its lines."""

import pytest
from playwright.sync_api import expect
from test_bows import bows, expect_under
from test_syllables import gap, word
from test_tints import BLUE, PAIR, RED, tint_switch, tinted
from ui import RULING, at, box, pick, sheet, syls, user

from blattwerk import pdf

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


def test_c3_mending_a_word_on_a_lineatur_moves_its_bows(editor):
    page = editor(box("a", "ruling", {**ABEND, "text": "Fenster Maus", "syllables": True}))
    pick(page, "a")
    word(page, "Maus").click()
    gap(page, "Ma|us").click()
    assert syls(page, "a") == ["Fens", "ter", "Ma", "us"]


def test_c5_a_trace_lineatur_shows_its_bows(editor):
    page = editor(box("a", "ruling", {**ABEND, "trace": True, "syllables": True}))
    assert syls(page, "a") == ["A", "bend"]
    expect_under(bows(page, "a"))


def test_c4_silbenfarbe_colours_the_letters_of_the_ruling(editor):
    page = editor(box("a", "ruling", {**ABEND, "tints": PAIR}))
    tinted(page, "a").to_have_text([("A", BLUE), ("bend", RED)])


def test_the_colours_stay_while_typing_on_a_lineatur(editor):
    page = editor(box("a", "ruling", {**ABEND, "tints": PAIR}))
    at(page, "a").dblclick()
    page.keyboard.press("End")
    page.keyboard.type(" Abend")
    tinted(page, "a").to_have_text([("A", BLUE), ("bend", RED), ("A", BLUE), ("bend", RED)])
    # What the eye reads: the coloured copy, and no black letters of the field over it.
    copy = at(page, "a").locator("p.written.copy")
    expect(copy).to_be_visible()
    fill = "(t) => getComputedStyle(t).webkitTextFillColor"
    assert at(page, "a").locator("textarea.written").evaluate(fill) == "rgba(0, 0, 0, 0)"


def test_x1_two_rows_of_text_give_a_bow_per_syllable_in_each(editor):
    page = editor(box("a", "ruling", {**ABEND, "text": "Abend Abend", "syllables": True}, h=40))
    assert syls(page, "a") == ["A", "bend", "A", "bend"]
    expect_under(bows(page, "a"))


def test_x2_the_print_page_draws_the_bows_clear_of_the_lines(browser, server):
    client = user()
    mine = sheet(client, [box("a", "ruling", {**ABEND, "syllables": True})])["id"]
    token = {"X-Render-Token": pdf.new_token(mine)}
    context = browser.new_context(
        viewport={"width": 1400, "height": 1000}, extra_http_headers=token
    )
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page = context.new_page()
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator(".syl")).to_have_count(2)
    expect(page.locator(".unsplit")).to_have_count(0)
    lines = page.eval_on_selector_all(
        "svg.ruling line", "els => els.map((l) => l.getBoundingClientRect().top)"
    )
    bows = page.eval_on_selector_all(
        ".syl",
        "els => els.map((e) => [e.getBoundingClientRect().top, e.getBoundingClientRect().bottom])",
    )
    assert len(lines) == 4 and len(bows) == 2
    for top, bottom in bows:
        assert not [y for y in lines if top < y < bottom], (top, bottom, lines)
    context.close()
