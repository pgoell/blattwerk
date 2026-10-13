"""The Knickblatt: a Lineatur that takes the list in its first column, with empty columns to write
in and a dashed fold line marked "knicken". The button and the Lineatur's choice make it, and it
draws and prints as the editor shows it.

The docstrings name the lines of the checklist that each test proves. The sheet starts with WORDS.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, printed, sheet_id
from test_gaps import panel
from test_words import list_tab, rulings, undo
from ui import RULING, TEXT, at, box, doc, pick, thumb, user

WORDS = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule"]
KNICK = {**RULING, "kind": "l3", "list": "fold", "folds": 2}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def across(locator):
    """The middle of a line across the screen, from its bounding box."""
    found = locator.bounding_box()
    return found["x"] + found["width"] / 2


def test_the_button_adds_a_knickblatt(editor):
    """A6: the button "Knickblatt" on the Lernwörter tab adds a fold Lineatur, six rows high."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, words=WORDS)
    list_tab(page)
    page.get_by_role("button", name="Knickblatt", exact=True).click()
    [blatt] = rulings(doc(page, client))
    assert blatt["props"]["list"] == "fold"
    assert blatt["props"]["folds"] == 2
    assert blatt["h"] == pytest.approx(6 * 11.5)


def test_the_button_is_off_without_words(editor):
    """A6: with no words in the sheet the button "Knickblatt" is off."""
    page = editor(box("a", "text", TEXT))
    list_tab(page)
    expect(page.get_by_role("button", name="Knickblatt", exact=True)).to_be_disabled()


def test_the_lineatur_choice_makes_a_knickblatt(editor):
    """A6: the Lineatur's text "Lernwörter als Knickblatt" makes the Lineatur a Knickblatt."""
    client = user()
    page = editor(box("r", "ruling", RULING), client=client, words=WORDS)
    pick(page, "r")
    choice = page.get_by_label("Text der Lineatur")
    choice.select_option(label="Lernwörter als Knickblatt")
    expect(choice).to_have_value("fold")
    assert rulings(doc(page, client))[0]["props"]["list"] == "fold"


def test_the_knickblatt_draws_the_words_the_columns_and_the_fold_line(editor):
    """A6: the words stand in the first column, the fold line is dashed and marked "knicken"."""
    page = editor(box("k", "ruling", KNICK, w=180, h=69), words=WORDS)
    block = at(page, "k")
    rows = block.locator(".listed .row")
    expect(rows).to_have_count(len(WORDS))
    assert (
        rows.evaluate_all("els => els.map((el) => el.querySelector('span').textContent)") == WORDS
    )
    fold = block.locator("svg.ruling line.fold")
    expect(fold).to_have_count(1)
    assert fold.evaluate("el => getComputedStyle(el).strokeDasharray") != "none"
    expect(block.locator("line.col")).to_have_count(1)
    expect(block.locator("text.knick")).to_have_text("knicken")
    frame = block.bounding_box()
    line = across(fold)
    assert line - frame["x"] == pytest.approx(frame["width"] / 3, abs=1)
    for word in block.locator(".listed .row span").all():
        assert word.bounding_box()["x"] + word.bounding_box()["width"] <= line + 1


def test_two_or_three_columns(editor):
    """A6: "3 Spalten zum Schreiben" makes three columns to write in, and one undo brings two."""
    client = user()
    page = editor(box("k", "ruling", KNICK, w=180, h=69), client=client, words=WORDS)
    pick(page, "k")
    panel(page, "3 Spalten zum Schreiben").click()
    assert rulings(doc(page, client))[0]["props"]["folds"] == 3
    expect(at(page, "k").locator("line.col")).to_have_count(2)
    undo(page)
    assert rulings(doc(page, client))[0]["props"]["folds"] == 2
    expect(at(page, "k").locator("line.col")).to_have_count(1)


def test_on_karo_the_column_lines_fall_on_whole_squares(editor):
    """A6: on Karo the fold line falls on a whole number of squares from the block's left edge."""
    page = editor(box("k", "ruling", {**KNICK, "kind": "k5"}, w=60, h=40), words=WORDS)
    block = at(page, "k")
    # On Karo the words are drawn letter by letter in squares: no rows, so wait for the fold line.
    expect(block.locator("svg.ruling line.fold")).to_have_count(1)
    frame = block.bounding_box()
    millimetres = (across(block.locator("svg.ruling line.fold")) - frame["x"]) * 60 / frame["width"]
    assert abs(millimetres - round(millimetres / 5) * 5) <= 0.2


def test_the_knickblatt_prints_as_the_editor_shows_it(editor, browser, server):
    """A10: the print page and the PDF hold the fold line, the word "knicken" and every word."""
    client = user()
    page = editor(box("k", "ruling", KNICK, w=180, h=69), client=client, words=WORDS)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator("line.fold")).to_have_count(1)
    expect(paper.locator("text.knick")).to_have_text("knicken")
    for word in WORDS:
        expect(paper.get_by_text(word, exact=True).first).to_be_visible()
    paper.context.close()
    text = pdf_text(server, client, sheet_id(page))
    assert "knicken" in text
    for word in WORDS:
        assert word in text


def test_a_knickblatt_cut_loose_keeps_the_words_untraced(editor):
    """I2: "Eigener Text" keeps the words as plain text, with no list, folds or trace."""
    client = user()
    page = editor(box("k", "ruling", KNICK, w=180, h=69), client=client, words=WORDS)
    pick(page, "k")
    page.get_by_label("Text der Lineatur").select_option(label="Eigener Text")
    props = rulings(doc(page, client))[0]["props"]
    assert props["text"] == "\n".join(WORDS)
    assert not {"list", "folds", "trace"} & set(props)


def test_garbage_folds_draw_two_columns(editor):
    """I7: a count of folds that is no 2 or 3 draws two columns."""
    page = editor(box("k", "ruling", {**KNICK, "folds": 9}, w=180, h=69), words=WORDS)
    expect(at(page, "k").locator("line.fold")).to_have_count(1)
    expect(at(page, "k").locator("line.col")).to_have_count(1)


LONG = ["jagen", "Übung", "Schmetterling"]
# Each row's word and where its ink ends, against the fold line and the clip.
# A word pressed narrower is whole; a cut word is not.
EDGES = """(scope) => {
  const line = scope.querySelector('svg.ruling line.fold').getBoundingClientRect().right;
  return [...scope.querySelectorAll('.listed .row > span')].map((span) => {
    const word = span.firstElementChild ?? span;
    const range = document.createRange();
    range.selectNodeContents(word);
    return {
      text: span.textContent,
      drawn: range.getBoundingClientRect().right,
      clip: span.getBoundingClientRect().right,
      line,
    };
  });
}"""


def whole(scope, words):
    """Each word is whole: its text is there, its ink is inside the clip and before the fold."""
    found = scope.evaluate(EDGES)
    assert [row["text"] for row in found] == words
    for row in found:
        assert row["drawn"] <= min(row["clip"], row["line"]) + 0.5, row


def test_a_long_word_shows_whole_on_a_knickblatt(editor):
    """A6: a word wider than its column is pressed narrower and shows whole, before the fold."""
    page = editor(box("k", "ruling", {**KNICK, "kind": "l1"}, w=180, h=60), words=LONG)
    whole(at(page, "k"), LONG)


@pytest.mark.parametrize("folds", [2, 3])
def test_a_long_word_shows_whole_with_the_house(editor, folds):
    """A6: with the house on, the first column is narrower, and the word still shows whole."""
    page = editor(
        box("k", "ruling", {**KNICK, "kind": "l1", "folds": folds, "house": True}, w=180, h=60),
        words=LONG,
    )
    whole(at(page, "k"), LONG)


@pytest.mark.parametrize(
    ("font", "kind", "house"),
    [
        ("andika", "l1", False),
        ("nord", "l1", False),
        ("sued", "l1", False),
        ("grund", "l1", False),
        ("urff", "l1", False),
        ("va", "l1", False),
        ("sas", "l1", False),
        ("la", "l2", True),
    ],
)
def test_a_long_word_shows_whole_in_each_school_script(editor, font, kind, house):
    """A6: in each school script the long word shows whole, in its lines and its house."""
    page = editor(
        box("k", "ruling", {**KNICK, "kind": kind, "font": font, "house": house}, w=180, h=60),
        words=LONG,
    )
    whole(at(page, "k"), LONG)


def test_a_long_word_prints_whole(editor, browser, server):
    """A10: the PDF holds the long word, and the print page shows it whole."""
    client = user()
    page = editor(
        box("k", "ruling", {**KNICK, "kind": "l1"}, w=180, h=60), client=client, words=LONG
    )
    paper = printed(browser, server, sheet_id(page))
    whole(paper.locator("body"), LONG)
    paper.context.close()
    assert "Schmetterling" in pdf_text(server, client, sheet_id(page))


def test_a_word_that_fits_keeps_its_size(editor):
    """A6: "jagen" fits its column, so it has no transform: it is not stretched or pressed."""
    page = editor(box("k", "ruling", {**KNICK, "kind": "l1"}, w=180, h=60), words=LONG)
    jagen = at(page, "k").locator(".listed .row span").first
    expect(jagen).to_have_text("jagen")
    assert jagen.evaluate("el => (el.firstElementChild ?? el).style.transform") == ""


@pytest.mark.parametrize("angle", [30, 90])
def test_a_turned_knickblatt_presses_the_long_word_as_a_level_one(editor, angle):
    """From the review: the word is measured as laid out, so a turned block presses it alike."""
    press = "el => el.firstElementChild.style.transform"
    props = {**KNICK, "kind": "l1"}
    level = box("k", "ruling", props, w=180, h=60)
    turned = box("t", "ruling", props, z=2, x=15, y=100, w=180, h=60, angle=angle)
    page = editor(level, turned, words=LONG)
    want = at(page, "k").locator(".listed .row > span").nth(2).evaluate(press)
    assert want.startswith("scaleX(0.")
    assert at(page, "t").locator(".listed .row > span").nth(2).evaluate(press) == want


def test_the_thumbnail_shows_the_long_word_whole(editor):
    """A6: the thumbnail of the page shows the long word whole, as the editor does."""
    page = editor(box("k", "ruling", {**KNICK, "kind": "l1"}, w=180, h=60), words=LONG)
    expect(thumb(page, 0)).to_be_visible()
    whole(thumb(page, 0), LONG)
