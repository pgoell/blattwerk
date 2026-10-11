"""Schüttelwörter: the words of a text show their letters in a new order, from a seed the block
holds. The same order in the editor, after a reload and in the PDF; a line after or under each
word lets the pupil write the word; the answer key shows the word as typed.

The docstrings name the lines of the checklist for the feature: A is the drawing, I the editor's
own ways of changing a text. The shown words are pinned as literal strings: a probe read them from
the app once, and the tests do not shuffle a word themselves.
"""

import io
import unicodedata

import httpx
import pytest
from PIL import Image
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import FIELD, RECT, TEXT, at, box, saved, sheet, syls, tints, tool, user

from blattwerk import pdf

MIX = {**TEXT, "text": "Der Hund bellt laut", "mix": 7}
# The shown words of MIX at seed 7, in reading order, each as its letters stand in the mix.
SHOWN = ["Dre", "uHnd", "tlbel", "taul"]
GAP = {
    **MIX,
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt laut"}]}],
}
LONG = (
    "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter und baut sich aus Laub ein "
    "warmes Nest. Die Eichhörnchen sammeln Nüsse und verstecken sie überall im Garten, damit "
    "sie im Winter genug zu fressen haben."
)
TINT = ["#1a56db", "#e02424"]
# Long enough to wrap onto several rows in a box 60 mm wide, with a line after each word.
LONG_MIXED = "Der Hund bellt laut und die Katze schläft in der Straße vor dem Haus"

# What each `.mix` of a block holds: its word as typed, and its letters as shown.
SHOWN_PAIRS = """els => els.map((el) => [el.dataset.mix, el.querySelector(".mixed").textContent])"""


def shown_pairs(page, name):
    return at(page, name).locator(".mix").evaluate_all(SHOWN_PAIRS)


def shown_words(page, name):
    return [shown for _, shown in shown_pairs(page, name)]


@pytest.mark.parametrize(
    "kind,props",
    [("text", MIX), ("shape", {**RECT, **MIX})],
    ids=["text", "shape"],
)
def test_a_stored_mix_shows_each_word_with_its_letters_in_a_new_order(editor, kind, props):
    """A1: each word shows its letters in another order: the same letters, not the word as typed."""
    page = editor(box("a", kind, props))
    pairs = shown_pairs(page, "a")
    assert [source for source, _ in pairs] == ["Der", "Hund", "bellt", "laut"]
    assert [shown for _, shown in pairs] == SHOWN
    for source, shown in pairs:
        assert sorted(shown) == sorted(source)
        if len(source) >= 3:
            assert shown != source


def test_the_first_letter_stays_with_mix_first(editor):
    """A2: with mixFirst each word keeps its first letter in place, and the rest shuffles."""
    page = editor(box("a", "text", {**MIX, "mixFirst": True}))
    pairs = shown_pairs(page, "a")
    assert [shown for _, shown in pairs] == ["Dre", "Hndu", "btell", "ltua"]
    for source, shown in pairs:
        assert shown[0] == source[0]
        assert sorted(shown) == sorted(source)


def test_capitals_with_mix_caps(editor):
    """A3: with mixCaps the letters show in capitals; "ß" shows as SS and no letter is lost."""
    page = editor(box("a", "text", {**TEXT, "text": "Straße", "mix": 7, "mixCaps": True}))
    [(source, shown)] = shown_pairs(page, "a")
    assert source == "Straße"
    assert shown == "RTSSESA"
    assert shown == shown.upper()
    assert sorted(shown) == sorted("STRASSE")


def test_short_words_punctuation_and_digits_stay(editor):
    """A4: words of two letters, digits and punctuation keep their place and their look."""
    page = editor(box("a", "text", {**TEXT, "text": "Ei, im Jahr 2024: geht's!", "mix": 7}))
    assert [source for source, _ in shown_pairs(page, "a")] == ["Ei", "im", "Jahr", "geht's"]
    assert at(page, "a").locator(".rich p").text_content() == "Ei, im arhJ 2024: hste'g!"


def test_the_order_is_the_same_after_a_reload(editor):
    """A5: a reload shows the same letters in the same order."""
    page = editor(box("a", "text", MIX))
    expect(at(page, "a").locator(".mixed").first).to_have_text(SHOWN[0])
    page.reload()
    expect(at(page, "a").locator(".mixed").first).to_have_text(SHOWN[0])
    assert shown_words(page, "a") == SHOWN


def test_another_seed_gives_another_order(editor):
    """A5: the same text with another seed shows its letters in another order."""
    page = editor(box("a", "text", MIX), box("b", "text", {**MIX, "mix": 8}, z=2))
    assert shown_words(page, "a") == SHOWN
    assert shown_words(page, "b") == ["erD", "nuHd", "bltle", "talu"]


def test_a_line_stands_after_each_word(editor):
    """A6: with mixLine "after" each word's line lies to the right of the word, on its row, and is
    wider than the word the line holds."""
    page = editor(box("a", "text", {**MIX, "mixLine": "after"}))
    for mixed in at(page, "a").locator(".mix").all():
        word = mixed.locator(".mixed").bounding_box()
        line = mixed.locator(".gap.line").bounding_box()
        held = mixed.locator(".gap.line > span").bounding_box()
        assert line["x"] >= word["x"] + word["width"] - 1
        assert abs(line["y"] - word["y"]) < word["height"] / 2
        assert line["width"] > held["width"] + 1


def test_a_line_stands_under_each_word(editor):
    """A6: with mixLine "under" each word's line lies below the word, and is at least as wide."""
    page = editor(box("a", "text", {**MIX, "mixLine": "under"}))
    for mixed in at(page, "a").locator(".mix").all():
        word = mixed.locator(".mixed").bounding_box()
        line = mixed.locator(".gap.line").bounding_box()
        assert line["y"] >= word["y"] + word["height"] - 1
        assert line["width"] >= word["width"] - 1


def test_the_editor_hides_the_word_on_the_line_until_the_key_is_shown(editor):
    """A8: the editor shows an empty line after each word, as the print does; the key shows the
    word as typed on it, in red."""
    page = editor(box("a", "text", {**MIX, "mixLine": "after"}))
    expect(at(page, "a").locator(".mix .gap.line > span").first).to_have_css("visibility", "hidden")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "a").locator(".mix .gap.line > span").first).to_have_css(
        "visibility", "visible"
    )
    expect(at(page, "a").locator(".mix .gap.line > span").first).to_have_css(
        "color", "rgb(192, 57, 43)"
    )


def test_a_line_on_the_second_row_is_drawn_on_the_print(editor, browser, server):
    """A line on a row below the first is drawn on the print: its screenshot has ink in it."""
    client = user()
    props = {**TEXT, "text": LONG_MIXED, "mix": 7, "mixLine": "after"}
    page = editor(box("a", "text", props, w=60, h=90), client=client)
    mine = page.url.rstrip("/").split("/")[-1]
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    tops = paper.locator(".mix .gap.line").evaluate_all(
        "els => els.map((el) => Math.round(el.getBoundingClientRect().top))"
    )
    assert len(set(tops)) >= 2
    for gap in paper.locator(".mix .gap.line").all():
        shot = Image.open(io.BytesIO(gap.screenshot())).convert("L")
        assert sum(shot.histogram()[:128]) > 0
    paper.context.close()


def test_a_double_click_shows_the_source_words_to_edit(editor):
    """A7: a double click opens the words as typed; Escape shows them mixed again, and the stored
    text is unchanged."""
    client = user()
    page = editor(box("a", "text", MIX), client=client)
    at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_have_text("Der Hund bellt laut")
    page.keyboard.press("Escape")
    expect(at(page, "a").locator(".mixed").first).to_have_text(SHOWN[0])
    assert saved(page, client)[0]["props"]["text"] == "Der Hund bellt laut"


def test_the_key_shows_the_source_on_the_line_and_the_pupils_print_hides_it(
    editor, browser, server
):
    """A8: the key shows the typed word red on its line; the pupil's print hides it. The PDF of the
    key holds the word, the pupil's PDF does not, and both hold the mixed letters."""
    client = user()
    props = {**MIX, "mixLine": "after"}
    page = editor(box("a", "text", props), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "a").locator(".gap.line > span").first).to_have_css("color", "rgb(192, 57, 43)")
    mine = page.url.rstrip("/").split("/")[-1]
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    for query, state in (("", "hidden"), ("?loesungen", "visible")):
        paper.goto(f"{server}/druck/{mine}{query}")
        paper.wait_for_selector("body.ready", state="attached")
        expect(paper.locator(".gap.line > span").first).to_have_css("visibility", state)
    paper.context.close()
    mine_sheet = sheet(client, [box("a", "text", props)])["id"]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    texts = []
    for solved in (False, True):
        res = httpx.get(
            f"{server}/api/sheets/{mine_sheet}/pdf",
            params={"solved": solved},
            headers=cookie,
            timeout=60,
        )
        assert res.status_code == 200
        texts.append(" ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages))
    assert "Hund" not in texts[0]
    assert "Hund" in texts[1]
    for shown in SHOWN:
        assert shown in texts[0]
        assert shown in texts[1]


def test_with_no_line_the_key_shows_the_source_in_place_of_the_mixed_word(editor, server):
    """A8: with no line the key shows the typed word where the mixed one stands, and the pupils'
    print shows only the mixed letters."""
    client = user()
    page = editor(box("a", "text", MIX), client=client)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "a").locator(".mixkey")).to_have_count(4)
    assert at(page, "a").locator(".mixkey").all_text_contents() == ["Der", "Hund", "bellt", "laut"]
    assert at(page, "a").locator(".mixed").count() == 0
    mine = sheet(client, [box("a", "text", MIX)])["id"]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    texts = []
    for solved in (False, True):
        res = httpx.get(
            f"{server}/api/sheets/{mine}/pdf", params={"solved": solved}, headers=cookie, timeout=60
        )
        assert res.status_code == 200
        texts.append(" ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages))
    assert "Hund" not in texts[0]
    assert "uHnd" in texts[0]
    assert "Hund" in texts[1]
    assert "uHnd" not in texts[1]


def test_the_pdf_holds_the_same_letter_order_as_the_editor(editor, server):
    """A10: the mixed words the editor shows are in the PDF's text, in the same order."""
    client = user()
    page = editor(box("a", "text", MIX), client=client)
    shown = shown_words(page, "a")
    mine = page.url.rstrip("/").split("/")[-1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages)
    # Each word is found after the one before it, so the PDF has them in the editor's order.
    found, end = [], 0
    for word in shown:
        found.append(text.index(word, end))
        end = found[-1] + len(word)
    assert len(found) == len(shown) == 4
    assert found == sorted(found)


@pytest.mark.parametrize(
    "props,reference",
    [
        ({**TEXT, "text": "Der Hund bellt laut", "mix": "7"}, None),
        ({**TEXT, "text": "Der Hund bellt laut", "mix": None}, None),
        ({**TEXT, "text": "Der Hund bellt laut", "mix": "NaN"}, None),
        ({**MIX, "mixLine": "x"}, MIX),
        ({**MIX, "mixFirst": "yes"}, MIX),
    ],
    ids=["mix-text", "mix-null", "mix-nan", "mixLine", "mixFirst"],
)
def test_garbage_in_the_mix_props_draws_the_plain_text(editor, props, reference):
    """I6: a mix that is no number draws the plain text; a line or flag that is no valid value
    draws as if it were not there."""
    if reference is None:
        page = editor(box("a", "text", props))
        expect(at(page, "a")).to_contain_text("Der Hund bellt laut")
        expect(at(page, "a").locator(".mix")).to_have_count(0)
        return
    page = editor(box("a", "text", props), box("b", "text", reference, z=2))
    assert shown_words(page, "a") == shown_words(page, "b") == SHOWN
    expect(at(page, "a").locator(".gap")).to_have_count(0)
    expect(at(page, "a").locator(".mix.under")).to_have_count(0)


def test_a_composed_and_a_decomposed_umlaut_show_the_same_order(editor):
    """I7: "Bär" typed with ä as one mark or as a and a combining diaeresis shows the same order."""
    page = editor(
        box("a", "text", {**TEXT, "text": "Der Bär brummt", "mix": 7}),
        box("b", "text", {**TEXT, "text": "Der Bär brummt", "mix": 7}, z=2),
    )
    shown = [
        unicodedata.normalize("NFC", at(page, name).locator(".rich").text_content())
        for name in ("a", "b")
    ]
    assert shown[0] == shown[1]
    assert shown[0] == "Dre rBä bmutrm"


def test_a_gap_word_is_not_mixed(editor):
    """I8: a gap shows its word as before; the other words are mixed."""
    page = editor(box("a", "text", GAP))
    expect(at(page, "a").locator("[data-gap]")).to_have_count(1)
    expect(at(page, "a").locator(".gap > span")).to_have_text("Hund")
    assert [source for source, _ in shown_pairs(page, "a")] == ["Der", "bellt", "laut"]
    assert shown_words(page, "a") == ["Dre", "tlbel", "taul"]


def test_a_mixed_word_has_no_bow_and_no_colour(editor):
    """I8: a text that is all mixed draws no bow and no colour; the same words unmixed draw them."""
    paired = {"syllables": True, "tints": TINT}
    page = editor(
        box("a", "text", {**MIX, **paired}),
        box("b", "text", {**TEXT, "text": "Der Hund bellt laut", **paired}, z=2),
    )
    assert syls(page, "b")
    assert tints(page, "b")
    assert syls(page, "a") == []
    assert tints(page, "a") == []


def test_line_numbers_count_the_lines_of_a_mixed_text(editor):
    """I8: a mixed text with a line under each word has one number per line of its words."""
    page = editor(
        box(
            "a",
            "text",
            {**TEXT, "text": LONG, "mix": 7, "mixLine": "under", "lines": 1},
            w=70,
            h=160,
        )
    )
    expect(at(page, "a").locator(".unsplit")).to_have_count(0)
    tops = sorted(
        at(page, "a")
        .locator(".mixed")
        .evaluate_all("els => els.map((el) => el.getBoundingClientRect().top)")
    )
    rows = [tops[0]]
    for top in tops[1:]:
        if top - rows[-1] > 4:
            rows.append(top)
    numbers = at(page, "a").locator(".ln").all_text_contents()
    assert len(rows) > 3
    assert numbers == [str(n) for n in range(1, len(rows) + 1)]


def test_the_bank_never_stands_in_reading_order(editor):
    """I8: the box of solution words is out of reading order, for each of six seeds."""
    gaps = {
        **TEXT,
        "text": "Der Hund bellt. Die Katze miaut.",
        "rich": [
            {
                "runs": [
                    {"text": "Der "},
                    {"text": "Hund", "gap": True},
                    {"text": " bellt. Die "},
                    {"text": "Katze", "gap": True},
                    {"text": " miaut."},
                ]
            }
        ],
    }
    page = editor(
        *(box(f"s{seed}", "text", {**gaps, "bank": seed}, z=seed) for seed in range(1, 7))
    )
    for seed in range(1, 7):
        order = at(page, f"s{seed}").locator(".bank span").all_inner_texts()
        assert sorted(order) == ["Hund", "Katze"]
        assert order != ["Hund", "Katze"], seed
