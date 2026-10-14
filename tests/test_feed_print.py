"""The Lernwörter in a text block, drawing and printing: Schüttelwörter over the list, the gaps of
Lückenwörter and their seed, the answer key, and what the PDF shows of what the editor shows.

The docstrings name the lines of the checklist that each test proves. The words of the list are
WORDS, which the sheet starts with; the shown letters are never pinned, only their properties.
"""

import io
import re

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from test_gaps import panel, step
from test_lock import FRAMES
from test_painter import held
from ui import RECT, TEXT, at, box, pick, user

from blattwerk import pdf

WORDS = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule"]
LISTED = {**TEXT, "list": True}
MIXED = {**LISTED, "mix": 7}
HOLES = {**LISTED, "holes": "one", "holeSeed": 7}
VOWELS = "aeiouäöü"


def sheet_id(page):
    """The id of the sheet the editor page has open."""
    return page.url.rsplit("/", 1)[1]


def gaps_of(locator):
    """Each paragraph of a block's text: the word whole, its hidden letters, and whether the first
    letter of the word is shown as plain text, not in a gap."""
    return locator.evaluate_all(
        """els => els.map((p) => ({
            word: p.textContent,
            hidden: [...p.querySelectorAll(".gap > span")].map((s) => s.textContent),
            first: !p.firstElementChild?.classList.contains("gap"),
        }))"""
    )


def hidden_letters(locator):
    """The letters hidden in each word of a block, in order."""
    return [para["hidden"] for para in gaps_of(locator)]


def printed(browser, server, mine):
    """The print page of a sheet, opened with a render token. The caller closes its context."""
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    return paper


def pdf_text(server, client, mine, solved=False):
    """The text of a sheet's PDF, every page in one string; `solved` is the answer key."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(
        f"{server}/api/sheets/{mine}/pdf", params={"solved": solved}, headers=cookie, timeout=60
    )
    assert res.status_code == 200
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages)


def test_a_linked_block_with_mix_shows_each_word_scrambled_with_a_line(editor):
    """A3: a linked block with Schüttelwörter shows each word scrambled, with a line to write on."""
    page = editor(box("a", "text", MIXED), words=WORDS)
    pick(page, "a")
    pairs = (
        at(page, "a")
        .locator(".mix")
        .evaluate_all(
            "els => els.map((el) => [el.dataset.mix, el.querySelector('.mixed').textContent])"
        )
    )
    assert [source for source, _ in pairs] == WORDS
    for source, shown in pairs:
        assert sorted(shown) == sorted(source)
        if len(source) >= 5:
            assert shown != source
    expect(at(page, "a").locator(".mix .gap.line")).to_have_count(len(WORDS))
    expect(panel(page, "Keine Linie")).to_have_count(0)
    expect(panel(page, "Linie dahinter")).to_have_attribute("aria-pressed", "true")


@pytest.mark.parametrize("mode", ["one", "second", "vowels"])
def test_each_mode_hides_its_letters(editor, mode):
    """A4: "one" hides one letter of each word, never the first; "second" every second letter;
    "vowels" every vowel."""
    page = editor(box("a", "text", {**LISTED, "holes": mode, "holeSeed": 7}), words=WORDS)
    paras = gaps_of(at(page, "a").locator(".rich p"))
    assert [para["word"] for para in paras] == WORDS
    for source, para in zip(WORDS, paras, strict=True):
        hidden = para["hidden"]
        if mode == "one":
            assert len(hidden) == 1
            assert para["first"]
        elif mode == "second":
            assert len(hidden) == len(source) // 2
            assert para["first"]
        else:
            assert hidden == [c for c in source if c.lower() in VOWELS]


JEDER = ["Zebra", "Kuh", "Blume", "Birne", "Fahrrad", "Schmetterling", "Wolke"]


def test_jeder_zweite_keeps_the_first_letter_of_every_word(editor):
    """A4: "Jeder zweite" keeps each first letter and hides the 2nd, 4th... (Kuh: K, _, h)."""
    page = editor(box("a", "text", {**LISTED, "holes": "second", "holeSeed": 7}), words=JEDER)
    paras = gaps_of(at(page, "a").locator(".rich p"))
    assert [para["word"] for para in paras] == JEDER
    assert all(para["first"] for para in paras)
    assert [para["hidden"] for para in paras] == [
        ["e", "r"],
        ["u"],
        ["l", "m"],
        ["i", "n"],
        ["a", "r", "a"],
        ["c", "m", "t", "e", "l", "n"],
        ["o", "k"],
    ]


def test_jeder_zweite_hides_nothing_of_a_one_letter_word_and_the_second_of_two(editor):
    """A4: a word of one letter stays whole; a word of two loses its second letter only."""
    page = editor(box("a", "text", {**LISTED, "holes": "second", "holeSeed": 7}), words=["a", "Ei"])
    paras = gaps_of(at(page, "a").locator(".rich p"))
    assert [para["hidden"] for para in paras] == [[], ["i"]]
    assert all(para["first"] for para in paras)


def test_jeder_zweite_prints_the_first_letter_of_every_word(editor, browser, server):
    """A4: the print of "Jeder zweite" keeps every first letter and hides what the editor hides."""
    page = editor(box("a", "text", {**LISTED, "holes": "second", "holeSeed": 7}), words=JEDER)
    paper = printed(browser, server, sheet_id(page))
    printed_paras = gaps_of(paper.locator(".rich p"))
    assert all(para["first"] for para in printed_paras)
    assert printed_paras == gaps_of(at(page, "a").locator(".rich p"))
    paper.context.close()


@pytest.mark.parametrize("mode, shown", [("one", 1), ("second", 0), ("vowels", 0)])
def test_neu_waehlen_is_shown_only_in_ein_buchstabe(editor, mode, shown):
    """A5: "Neu wählen" is shown for "Ein Buchstabe" only; the other modes ignore the seed."""
    page = editor(box("a", "text", {**LISTED, "holes": mode, "holeSeed": 7}), words=JEDER)
    pick(page, "a")
    expect(panel(page, "Neu wählen")).to_have_count(shown)


def test_a_hidden_letter_is_a_gap_of_its_own(editor, browser, server):
    """A4: each hidden letter is a gap of its own, and the print page hides its letter."""
    client = user()
    page = editor(box("a", "text", HOLES), client=client, words=WORDS)
    gaps = at(page, "a").locator('.rich.holes .gap[data-gap="true"]')
    expect(gaps).to_have_count(len(WORDS))
    assert gaps.evaluate_all("els => els.map((el) => el.textContent.length)") == [1] * len(WORDS)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator('.rich.holes .gap[data-gap="true"] > span').first).to_have_css(
        "visibility", "hidden"
    )
    paper.context.close()


def test_the_hidden_letters_are_the_same_after_a_reload(editor):
    """A5: a reload shows the same letters hidden in the same words."""
    page = editor(box("a", "text", HOLES), words=WORDS)
    before = hidden_letters(at(page, "a").locator(".rich p"))
    page.reload()
    expect(at(page, "a").locator(".rich.holes .gap")).to_have_count(len(WORDS))
    assert hidden_letters(at(page, "a").locator(".rich p")) == before


def test_neu_waehlen_picks_other_letters(editor):
    """A5: Neu wählen stores another seed, and at least one word hides other letters."""
    client = user()
    page = editor(box("a", "text", HOLES), client=client, words=WORDS)
    pick(page, "a")
    seed = held(page, client)["a"]["holeSeed"]
    before = hidden_letters(at(page, "a").locator(".rich p"))
    step(page, lambda: panel(page, "Neu wählen").click())
    assert held(page, client)["a"]["holeSeed"] != seed
    assert hidden_letters(at(page, "a").locator(".rich p")) != before


def test_neu_waehlen_with_all_vowels_makes_no_step(editor):
    """A5: with "Alle Vokale" there is no Neu wählen, so nothing is stored and no undo step."""
    client = user()
    page = editor(
        box("a", "text", {**LISTED, "holes": "vowels", "holeSeed": 7}), client=client, words=WORDS
    )
    pick(page, "a")
    undo = page.get_by_label("Rückgängig", exact=True)
    before = held(page, client)["a"]
    was = undo.is_enabled()
    expect(panel(page, "Neu wählen")).to_have_count(0)
    page.evaluate(FRAMES)
    assert held(page, client)["a"] == before
    assert undo.is_enabled() == was


@pytest.mark.parametrize(
    "more",
    [pytest.param({"mix": 7}, id="mix"), pytest.param({"holes": "one", "holeSeed": 7}, id="holes")],
)
def test_the_key_prints_the_full_words(editor, server, more):
    """A7: the answer key prints every full word; the pupils' print leaves out "Schule"."""
    client = user()
    page = editor(box("a", "text", {**LISTED, **more}), client=client, words=WORDS)
    mine = sheet_id(page)
    # A gap word's letters come out apart in the PDF's text, so the spaces go before the search.
    key = re.sub(r"\s", "", pdf_text(server, client, mine, solved=True))
    pupils = re.sub(r"\s", "", pdf_text(server, client, mine))
    for word in WORDS:
        assert word in key
    assert "Schule" not in pupils


def test_the_pdf_shows_what_the_editor_shows(editor, browser, server):
    """A10: the PDF holds the mixed words the editor shows, a gap text prints as the editor shows
    it, and three columns print in three columns."""
    client = user()
    mixed = editor(box("a", "text", MIXED), client=client, words=WORDS)
    shown = at(mixed, "a").locator(".mix .mixed").all_text_contents()
    assert len(shown) == len(WORDS)
    text = pdf_text(server, client, sheet_id(mixed))
    for word in shown:
        assert word in text

    gaps = editor(box("b", "text", HOLES), client=client, words=WORDS)
    paper = printed(browser, server, sheet_id(gaps))
    assert gaps_of(paper.locator(".rich p")) == gaps_of(at(gaps, "b").locator(".rich p"))
    paper.context.close()

    columns = editor(box("c", "text", {**LISTED, "listCols": 3}), client=client, words=WORDS)
    paper = printed(browser, server, sheet_id(columns))
    lefts = paper.locator(".rich p").evaluate_all(
        "els => new Set(els.map((p) => Math.round(p.getBoundingClientRect().left))).size"
    )
    assert lefts == 3
    paper.context.close()


def test_a_linked_shapes_outline_goes_with_its_words(editor, browser, server):
    """A10/A11: a linked triangle's outline reaches its words, on the editor and the print."""
    client = user()
    shape = {**RECT, **TEXT, "kind": "triangle", "fill": "#ffee88", "list": True}
    page = editor(box("s", "shape", shape, h=8), client=client, words=WORDS)
    paper = printed(browser, server, sheet_id(page))
    for scope in (at(page, "s"), paper.locator(".block").first):
        expect(scope.locator("svg.outline")).to_have_attribute("preserveAspectRatio", "none")
        drawn = scope.locator("svg.outline polygon").bounding_box()
        last = scope.locator(".frame.listed .rich p").last.bounding_box()
        assert drawn["y"] + drawn["height"] >= last["y"] + last["height"] - 1
    paper.context.close()
