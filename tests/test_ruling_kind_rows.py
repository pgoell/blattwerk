"""A Lineatur's rows grow with its kind when its text needs them: all letters stay drawn."""

import pytest
from playwright.sync_api import expect
from test_karo_bows import printed
from ui import RULING, at, box, pick, saved, sheet, user

TEXT = "Schmetterlinge fliegen über die Blumenwiese. Der Fußball rollt, die Möhre wächst."
LETTERS = "svg text"


def karo(kind="k5", h=15, **more):
    return box("l", "ruling", {**RULING, "kind": kind, "text": TEXT}, h=h, **more)


def kind_to(page, kind):
    page.get_by_label("Art der Lineatur").select_option(kind)


def test_a5_the_letters_of_a_karo_text_all_stay_drawn_when_the_kind_grows(editor):
    """A5: k5 to k7, text needs more rows: all letters drawn, rows are whole 7 mm rows."""
    client = user()
    page = editor(karo(), client=client)
    pick(page, "l")
    kind_to(page, "k7")
    expect(at(page, "l").locator(LETTERS)).to_have_count(len(TEXT))
    stored = saved(page, client)[0]
    rows = stored["h"] / 7
    cols = int(stored["w"] / 7 + 0.05)
    assert abs(rows - round(rows)) < 0.01, stored["h"]
    assert round(rows) >= -(-len(TEXT) // cols), stored


def test_a6_the_print_page_draws_every_letter_after_the_kind_grew(editor, browser, server):
    """A6: after k5 to k7 the print page draws every letter of the text."""
    client = user()
    page = editor(karo(), client=client)
    pick(page, "l")
    kind_to(page, "k7")
    expect(at(page, "l").locator(LETTERS)).to_have_count(len(TEXT))
    saved(page, client)
    sheet_id = page.url.rsplit("/", 1)[1]
    printing = printed(browser, server, sheet_id)
    expect(printing.locator("svg.ruling text")).to_have_count(len(TEXT))


def test_a7_one_undo_takes_the_kind_and_the_rows_back(editor):
    """A7: one undo after k5 to k7 gives k5 and the 3 rows again."""
    page = editor(karo())
    pick(page, "l")
    kind_to(page, "k7")
    expect(page.get_by_label("Art der Lineatur")).to_have_value("k7")
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Art der Lineatur")).to_have_value("k5")
    expect(page.get_by_text("3 Zeilen")).to_be_visible()


def test_a8_a_stored_karo_too_short_draws_all_letters(editor, browser, server):
    """A8: a stored k7 block of 15 mm with the text draws all letters, editor and /druck alike."""
    client = user()
    page = editor(karo(kind="k7", h=15), client=client)
    expect(at(page, "l").locator(LETTERS)).to_have_count(len(TEXT))
    sheet_id = sheet(client, [karo(kind="k7", h=15)])["id"]
    printing = printed(browser, server, sheet_id)
    expect(printing.locator("svg.ruling text")).to_have_count(len(TEXT))


def test_a8_a_stored_lined_ruling_too_short_grows_on_load_and_in_print(editor, browser, server):
    """A8: a stored Lineatur 1 of one row with three lines opens and prints with three rows."""
    client = user()
    lined = box("l", "ruling", {**RULING, "kind": "l1", "text": "Mama\nPapa\nOma"}, h=20)
    page = editor(lined, client=client)
    # Three rows of 20 mm: the box is 60 mm high for its width in mm.
    page.wait_for_function(
        """w => {
            const b = document.querySelector('.block[data-id="l"]');
            return Math.abs(b.offsetHeight / b.offsetWidth - 60 / w) < 0.01;
        }""",
        arg=lined["w"],
    )
    printing = printed(browser, server, sheet(client, [lined])["id"])
    written = printing.locator(".written")
    assert written.evaluate("p => p.scrollHeight <= p.clientHeight + 1")
    assert printing.locator("svg.ruling line").count() >= 3 * 4


def test_i2_a_kind_change_to_a_finer_karo_keeps_rows_when_the_text_fits(editor):
    """I2: k7 to k5 with a short text that fits keeps its rows."""
    page = editor(box("l", "ruling", {**RULING, "kind": "k7", "text": "Hallo"}, h=35))
    pick(page, "l")
    kind_to(page, "k5")
    expect(page.get_by_text("5 Zeilen")).to_be_visible()


LONG = TEXT * 3


@pytest.mark.parametrize("start, end, h", [("l4", "l1", 20), ("k5", "l1", 15), ("l1", "k5", 40)])
def test_a9_a_kind_change_grows_the_rows_a_long_text_needs(editor, start, end, h):
    """A9: a kind change to or from a lined kind grows the rows when the text wraps over them."""
    client = user()
    page = editor(box("l", "ruling", {**RULING, "kind": start, "text": LONG}, h=h), client=client)
    pick(page, "l")
    kind_to(page, end)
    expect(page.get_by_label("Art der Lineatur")).to_have_value(end)
    row = {"l1": 20, "l4": 10, "k5": 5}
    stored = saved(page, client)[0]
    assert stored["h"] / row[end] > h / row[start], stored


def test_a9_a_lined_text_counts_its_line_breaks(editor):
    """A9: three lines on Lineatur 1 need three rows: three do not warn, two do."""
    page = editor(box("l", "ruling", {**RULING, "kind": "l1", "text": "Mama\nPapa\nOma"}, h=60))
    pick(page, "l")
    expect(page.get_by_text("3 Zeilen")).to_be_visible()
    expect(page.locator('[data-rows="short"]')).to_have_count(0)
    page.get_by_label("Eine Zeile weniger").click()
    expect(page.get_by_text("2 Zeilen")).to_be_visible()
    expect(page.locator('[data-rows="short"]')).to_be_visible()


def test_i1_each_karo_gets_its_own_rows_and_one_undo_takes_both_back(editor):
    """I1: two picked Karo rulings each grow to their own rows; one undo takes both back."""
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "kind": "k5", "text": "Hallo"}, h=15),
        box("b", "ruling", {**RULING, "kind": "k5", "text": TEXT}, h=15, z=2),
        client=client,
    )
    pick(page, "a", "b")
    kind_to(page, "k7")
    stored = {b["id"]: b for b in saved(page, client)}
    # The long text needs more than the 3 rows it had; the short one keeps them.
    assert stored["b"]["h"] > 21 and stored["b"]["h"] % 7 < 0.01, stored["b"]
    assert stored["a"]["h"] == 21, stored["a"]
    page.keyboard.press("Control+z")
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["a"]["h"] == 15 and stored["b"]["h"] == 15, stored
    assert stored["a"]["props"]["kind"] == stored["b"]["props"]["kind"] == "k5"


def test_i3_minus_takes_a_row_from_a_full_karo_and_plus_adds_one(editor):
    """I3: "Eine Zeile weniger" on a full Karo shows the short hint; "mehr" adds a row."""
    page = editor(karo())
    pick(page, "l")
    kind_to(page, "k7")
    expect(page.locator('[data-rows="short"]')).to_have_count(0)
    page.get_by_label("Eine Zeile weniger").click()
    expect(page.locator('[data-rows="short"]')).to_be_visible()
    page.get_by_label("Eine Zeile mehr").click()
    expect(page.get_by_text("4 Zeilen")).to_be_visible()


def test_i4_a_kind_change_near_the_foot_grows_at_most_to_the_foot(editor):
    """I4: a k5 Karo with 5 rows left above the foot grows to those 5 rows of 7 mm and warns."""
    client = user()
    text = TEXT * 2
    block = box("l", "ruling", {**RULING, "kind": "k5", "text": text}, h=25, y=258.5)
    page = editor(block, client=client)
    pick(page, "l")
    kind_to(page, "k7")
    assert saved(page, client)[0]["h"] == 35, saved(page, client)[0]
    expect(page.locator('[data-rows="short"]')).to_be_visible()


def test_i5_the_syllable_bows_match_a_tall_block_with_the_same_text(editor):
    """I5: after k5 to k7 the bows are those of a tall k7 block with the same text."""
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": TEXT, "syllables": True}, h=15),
        box("t", "ruling", {**RULING, "kind": "k7", "text": TEXT, "syllables": True}, h=140, z=2),
    )
    pick(page, "l")
    kind_to(page, "k7")
    expect(at(page, "l").locator(LETTERS)).to_have_count(len(TEXT))
    bows = at(page, "t").locator(".syl").count()
    assert bows > 0
    expect(at(page, "l").locator(".syl")).to_have_count(bows)
