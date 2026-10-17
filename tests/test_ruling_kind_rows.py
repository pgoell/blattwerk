"""A Lineatur's rows grow with its kind when its text needs them: all letters stay drawn."""

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
    page.get_by_label("Rückgängig", exact=True).click()
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


def test_i2_a_kind_change_to_a_finer_karo_keeps_rows_when_the_text_fits(editor):
    """I2: k7 to k5 with a short text that fits keeps its rows."""
    page = editor(box("l", "ruling", {**RULING, "kind": "k7", "text": "Hallo"}, h=35))
    pick(page, "l")
    kind_to(page, "k5")
    expect(page.get_by_text("5 Zeilen")).to_be_visible()
