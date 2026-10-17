"""Silbenbögen and Silbenfarbe on a Karo Lineatur: bows under the squares, colours on letters."""

import re

import pytest
from playwright.sync_api import expect
from test_tints import BLUE, RED
from ui import RULING, at, box, sheet, syls, unpick, user

from blattwerk import pdf

KARO = {**RULING, "kind": "k5", "text": "Abend", "syllables": True}
# The squares' column and row lines, each bow's box and each letter's box, in the window's pixels.
GEOMETRY = """(block) => {
  const box = (el) => el.getBoundingClientRect();
  const quad = (el) => { const r = box(el); return [r.left, r.right, r.top, r.bottom]; };
  const lines = [...block.querySelectorAll('svg.ruling line')].map(box);
  const vertical = lines.filter((r) => r.width < 1 && r.height > 1).map((r) => r.left);
  return {
    vertical: vertical.sort((a, b) => a - b),
    horizontal: lines.filter((r) => r.height < 1 && r.width > 1).map((r) => r.top),
    bows: [...block.querySelectorAll('.syl')].map(quad),
    letters: [...block.querySelectorAll('svg.ruling text')].map(quad),
  };
}"""


@pytest.mark.parametrize("kind", ["k5", "k7"])
def test_k1_each_bow_lies_under_its_squares_and_below_the_letters(editor, kind):
    page = editor(box("a", "ruling", {**KARO, "kind": kind}))
    assert syls(page, "a") == ["A", "bend"]
    geo = at(page, "a").evaluate(GEOMETRY)
    first, second = geo["bows"]
    # The first bow lies in square 0, the second spans squares 1 to 4.
    assert first[0] >= geo["vertical"][0] - 0.5 and first[1] <= geo["vertical"][1] + 0.5, geo
    assert second[0] >= geo["vertical"][1] - 0.5 and second[1] <= geo["vertical"][5] + 0.5, geo
    for bow in geo["bows"]:
        assert not [y for y in geo["horizontal"] if bow[2] < y < bow[3]], geo
    _, _, letter_top, letter_bottom = geo["letters"][0]
    assert first[2] > (letter_top + letter_bottom) / 2, geo


def test_k2_the_letters_take_the_colour_of_their_syllable(editor):
    page = editor(box("a", "ruling", {**KARO, "tints": [BLUE, RED]}))
    unpick(page)
    letters = at(page, "a").locator("svg.ruling text")
    expect(letters).to_have_count(5)
    expect(letters.nth(0)).to_have_attribute("fill", BLUE)
    for i in range(1, 5):
        expect(letters.nth(i)).to_have_attribute("fill", RED)


def test_k3_with_trace_the_colours_win_over_grey(editor):
    page = editor(box("a", "ruling", {**KARO, "tints": [BLUE, RED], "trace": True}))
    unpick(page)
    letters = at(page, "a").locator("svg.ruling text")
    expect(letters.nth(0)).to_have_attribute("fill", BLUE)
    expect(letters.nth(1)).to_have_attribute("fill", RED)


def test_k4_on_the_outline_look_the_colours_go_on_the_stroke(editor):
    page = editor(box("a", "ruling", {**KARO, "tints": [BLUE, RED], "trace": "outline"}))
    unpick(page)
    letters = at(page, "a").locator("svg.ruling text")
    expect(letters.nth(0)).to_have_attribute("stroke", BLUE)
    expect(letters.nth(0)).to_have_attribute("fill", "none")
    expect(letters.nth(1)).to_have_attribute("stroke", RED)


def test_k5_a_syllable_that_wraps_gets_a_bow_on_each_row(editor):
    page = editor(box("a", "ruling", {**KARO, "text": "Fenster", "tints": [BLUE, RED]}, w=25))
    assert syls(page, "a") == ["Fens", "ter", "ter"]
    expect(at(page, "a").locator('.syl[data-syl="ter"]')).to_have_count(2)


def test_k6_breaks_set_by_hand_cut_the_syllables(editor):
    page = editor(box("a", "ruling", {**KARO, "text": "Maus", "breaks": {"maus": [2]}}))
    assert syls(page, "a") == ["Ma", "us"]


def test_k7_tints_across_carry_the_colour_turn_on_from_word_to_word(editor):
    text = "Tomate Tomate"
    page = editor(
        box("a", "ruling", {**KARO, "text": text, "tints": [BLUE, RED], "tintsAcross": True})
    )
    unpick(page)
    letters = at(page, "a").locator("svg.ruling text")
    expect(letters.nth(7)).to_have_attribute("fill", RED)


def test_k8_a_decomposed_umlaut_does_not_shift_the_colours(editor):
    # The "a" and its dots are two code points, so two squares.
    text = "Bäume"
    page = editor(box("a", "ruling", {**KARO, "text": text, "tints": [BLUE, RED]}))
    assert syls(page, "a") == ["Bäu", "me"]
    unpick(page)
    letters = at(page, "a").locator("svg.ruling text")
    expect(letters.nth(0)).to_have_attribute("fill", BLUE)
    expect(letters.nth(5)).to_have_attribute("fill", RED)


def printed(browser, server, sheet_id, route=None):
    client = user()
    context = browser.new_context(viewport={"width": 1400, "height": 1000})
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page = context.new_page()
    if route:
        page.route(re.compile(route), lambda r: r.abort())
    context.set_extra_http_headers({"X-Render-Token": pdf.new_token(sheet_id)})
    page.goto(f"{server}/druck/{sheet_id}")
    page.wait_for_selector("body.ready", state="attached")
    return page


def test_k9_the_print_page_draws_the_karo_bows_and_colours(browser, server):
    mine = sheet(user(), [box("a", "ruling", {**KARO, "tints": [BLUE, RED]})])["id"]
    page = printed(browser, server, mine)
    expect(page.locator(".syl")).to_have_count(2)
    expect(page.locator(".unsplit")).to_have_count(0)
    expect(page.locator("svg.ruling text").first).to_have_attribute("fill", BLUE)


def test_k10_a_splitter_that_does_not_load_lets_the_karo_print_go_on(browser, server):
    mine = sheet(user(), [box("a", "ruling", {**KARO, "tints": [BLUE, RED]})])["id"]
    page = printed(browser, server, mine, route=r"syllables.*\.js")
    expect(page.locator(".unsplit")).to_have_count(0)
