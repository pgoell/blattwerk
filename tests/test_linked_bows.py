"""Silbenbögen on a Lineatur linked to the Lernwörter: a bow under each syllable of each word."""

import pytest
from playwright.sync_api import expect
from test_bows import bows, expect_under
from test_gaps import panel
from test_lernwoerter_follow import add_word
from test_tints import BLUE, PAIR, RED, tinted
from ui import RULING, at, box, pick, sheet, user

from blattwerk import pdf

WORDS = ["Hase", "Igel", "Maus", "Katze"]
# Ha-se, I-gel, Mau-s, Kat-ze.
SEVEN = 7


def linked(mode, **more):
    # Tall enough for the four words, one a row.
    props = {**RULING, "kind": "l2", "list": mode, "syllables": True, **more}
    return box("a", "ruling", props, h=120, w=180)


@pytest.mark.parametrize("mode", ["copy", "trace", "fold"])
def test_each_listed_word_gets_a_bow_under_each_syllable(editor, mode):
    page = editor(linked(mode), words=WORDS)
    found = bows(page, "a")
    assert len(found) == SEVEN
    expect_under(found)
    expect(at(page, "a").locator(".syl")).to_have_count(SEVEN)


SYLLABLES = {"Hase": 2, "Igel": 2, "Maus": 1, "Katze": 2}
# Per row: the repetitions of its word whose box lies inside the row, and the syllables each has.
# A bow whose middle lies in no row, below its row's bottom, shows as an orphan.
ROWS = """(block, syllables) => {
  const inside = (r, box) =>
    r.left >= box.left && r.right <= box.right && r.top >= box.top && r.bottom <= box.bottom;
  const rows = [...block.querySelectorAll('.written.listed .row')].map((row) => {
    const box = row.getBoundingClientRect();
    const word = row.querySelector('span').textContent;
    const spans = [...row.querySelectorAll('span')];
    const shown = spans.filter((s) => inside(s.getBoundingClientRect(), box)).length;
    return { word, box, shown };
  });
  const bows = [...block.querySelectorAll('svg.bows .syl')].map((p) =>
    p.getBoundingClientRect());
  const orphan = bows.filter((b) => {
    const mid = (b.top + b.bottom) / 2;
    return !rows.some((row) => mid >= row.box.top && mid <= row.box.bottom);
  }).length;
  return { expected: rows.reduce((sum, row) => sum + row.shown * syllables[row.word], 0), orphan };
}"""


def test_row_mode_gives_each_repetition_its_own_bows(editor):
    page = editor(linked("row"), words=WORDS)
    found = bows(page, "a")
    expect_under(found)
    counted = at(page, "a").evaluate(ROWS, SYLLABLES)
    assert counted["orphan"] == 0, counted
    assert len(found) == counted["expected"], (len(found), counted)


def test_syllable_colour_colours_the_listed_words(editor):
    page = editor(linked("copy", tints=PAIR), words=WORDS)
    # Each word is its own paragraph, so the colours turn anew with each: Ha-se, I-gel, Mau, Kat-ze.
    want = [("Ha", BLUE), ("se", RED), ("I", BLUE), ("gel", RED)]
    tinted(page, "a").to_have_text([*want, ("Maus", BLUE), ("Kat", BLUE), ("ze", RED)])


def test_a_row_cut_off_below_the_block_draws_no_bows(editor):
    props = {**RULING, "kind": "l2", "list": "copy", "syllables": True}
    page = editor(box("a", "ruling", props, h=40, w=180), words=WORDS)
    found = bows(page, "a")
    # Only the words whose rows fit the block have bows: Hase's, not the rows below.
    assert 0 < len(found) < SEVEN, len(found)
    expect_under(found)


def test_a_word_added_to_the_list_adds_its_bows(editor):
    page = editor(linked("copy"), words=WORDS)
    expect(at(page, "a").locator(".syl")).to_have_count(SEVEN)
    add_word(page, "Sonne")
    # Son-ne: two more bows.
    expect(at(page, "a").locator(".syl")).to_have_count(SEVEN + 2)


# Each word of a row, as the row's box cuts it: inside, outside or across its bottom.
CUT = """(block) => [...block.querySelectorAll('.written.listed .row')].flatMap((row) => {
  const box = row.getBoundingClientRect();
  return [...row.querySelectorAll('span')].map((span) => {
    const r = span.getBoundingClientRect();
    return r.bottom <= box.bottom + 0.5 ? 'in' : r.top >= box.bottom - 0.5 ? 'out' : 'cut';
  });
})"""


def test_the_print_page_lays_out_a_linked_row_as_the_editor_does(editor, browser, server):
    """A row is a paragraph for the bows; the print's paragraph style must not lay it out anew."""
    page = editor(linked("row"), words=WORDS)
    shown = at(page, "a").evaluate(CUT)
    client = user()
    mine = sheet(client, [linked("row")], words=WORDS)["id"]
    context = browser.new_context(
        viewport={"width": 1400, "height": 1400},
        extra_http_headers={"X-Render-Token": pdf.new_token(mine)},
    )
    try:
        printed = context.new_page()
        printed.emulate_media(media="print")
        printed.goto(f"{server}/druck/{mine}")
        printed.wait_for_selector("body.ready", state="attached")
        printed.wait_for_selector(".unsplit", state="detached")
        drawn = printed.locator(".print .block[data-block]").first.evaluate(CUT)
    finally:
        context.close()
    assert "cut" not in drawn, drawn
    assert drawn == shown


# The word of each row, pressed: its box as laid out and as drawn, and the bows of the block.
PRESSED = """(block) => {
  const word = block.querySelector('.written.listed .row > span > span');
  const r = word.getBoundingClientRect();
  const bows = [...block.querySelectorAll('svg.bows .syl')].map((p) => p.getBoundingClientRect());
  const spans = bows.map((b) => [b.left, b.right]);
  return { word: [r.left, r.right], scale: word.style.transform, bows: spans };
}"""


def test_a_pressed_fold_word_keeps_its_bows_inside_it(editor):
    """A long word in a narrow fold is scaled to fit; after the folds change, its bows follow it."""
    client = user()
    props = {**RULING, "kind": "l3", "list": "fold", "folds": 2, "syllables": True}
    page = editor(box("a", "ruling", props, w=60, h=120), client=client, words=["Schmetterling"])
    pick(page, "a")
    panel(page, "3 Spalten zum Schreiben").click()
    expect(at(page, "a").locator("line.col")).to_have_count(2)
    expect(at(page, "a").locator(".syl").first).to_be_visible()
    got = at(page, "a").evaluate(PRESSED)
    assert got["bows"], got
    for left, right in got["bows"]:
        assert left >= got["word"][0] - 1 and right <= got["word"][1] + 1, got
