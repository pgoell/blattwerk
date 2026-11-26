"""A word added to the Lernwörter list grows the ruling linked to it, as far as the page allows."""

from itertools import pairwise

from playwright.sync_api import expect
from test_words import blatt, doc, field, rulings, undo
from ui import TEXT, at, box, user
from ui_new import from_template

SIX = ["Hund", "Katze", "Maus", "Reh", "Igel", "Fuchs"]
FOURTEEN = [f"Wort{i}" for i in range(14)]
# Six rows of Lineatur 1, 20 mm each, from 55 mm down.
ONE = {"kind": "l1", "color": "#555555", "list": "copy"}


def linked(stored, n=0):
    return [b for b in rulings(stored, n) if b["props"].get("list")]


def add_word(page, word):
    """Types a word more into the list, in the panel of the page's first block that shows it."""
    if not field(page).count():
        page.locator(".sheet .block:has(.listed)").first.click()
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Enter")
    page.keyboard.type(word)


def test_a_word_added_later_adds_a_row_to_the_ruling(editor):
    client = user()
    page = editor(box("r", "ruling", ONE, y=55, h=120), client=client, words=SIX)
    add_word(page, "Garten")
    assert linked(doc(page, client))[0]["h"] == 140
    expect(page.locator(".panel [role=status]")).to_have_count(0)


def test_the_ruling_stops_at_the_margin_and_warns(editor):
    client = user()
    page = editor(box("r", "ruling", ONE, y=55, h=120), client=client, words=SIX)
    at(page, "r").click()
    field(page).fill("\n".join(FOURTEEN))
    grown = linked(doc(page, client))[0]
    # Eleven rows reach 275 mm; the margin lies at 282 mm.
    assert grown["h"] == 220
    assert grown["y"] + grown["h"] <= 282
    expect(page.locator(".panel [role=status]")).to_have_text(
        "3 Wörter passen nicht in die Zeilen."
    )


def write_list(page, words):
    """Writes the list in the panel of the page's first block that shows it."""
    page.locator(".sheet .block:has(.listed)").first.click()
    field(page).fill("\n".join(words))


def test_a_sheet_from_the_template_shows_every_word_of_a_longer_list(editor):
    """The template's page holds six words; the two more go on a second page, for each exercise."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    from_template(page, "Lernwörter")
    write_list(page, [f"Wort{i}" for i in range(8)])
    stored = doc(page, client)
    assert len(stored["pages"]) == 2
    assert [rows_of(b) for b in linked(stored)] == [6, 6, 6]
    assert [(b["props"]["from"], rows_of(b)) for b in linked(stored, 1)] == [(6, 2)] * 3


def test_undo_takes_back_the_word_and_its_row_in_one_step(editor):
    client = user()
    page = editor(box("r", "ruling", ONE, y=55, h=120), client=client, words=SIX)
    add_word(page, "Garten")
    assert linked(doc(page, client))[0]["h"] == 140
    undo(page)
    stored = doc(page, client)
    assert linked(stored)[0]["h"] == 120
    assert len(stored["words"]) == 6


FIVE = ["Hund", "Katze", "Maus", "Reh", "Igel"]


def rows_of(block):
    """Rows of a Lineatur 3 ruling, whose row is 11.5 mm."""
    return round(block["h"] / 11.5)


def test_a_word_added_to_the_three_exercises_reaches_copy_trace_and_row(editor):
    """#739: five words leave room once the lower rulings move down, so the sixth reaches every ruling."""
    client = user()
    page = editor(*blatt(5), client=client, words=FIVE)
    before = sorted(linked(doc(page, client)), key=lambda b: b["y"])
    assert [rows_of(b) for b in before] == [5, 5, 5]
    add_word(page, "Garten")
    stored = doc(page, client)
    lines = sorted(linked(stored), key=lambda b: b["y"])
    assert [rows_of(b) for b in lines] == [6, 6, 6]
    assert lines[0]["y"] == before[0]["y"]
    assert lines[1]["y"] > before[1]["y"]
    assert lines[2]["y"] > before[2]["y"]
    assert lines[2]["y"] + lines[2]["h"] <= 282
    for upper, lower in pairwise(lines):
        assert upper["y"] + upper["h"] <= lower["y"]
    assert len(stored["pages"]) == 1
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    undo(page)
    back = doc(page, client)
    assert len(back["pages"]) == 1
    assert [rows_of(b) for b in sorted(linked(back), key=lambda b: b["y"])] == [5, 5, 5]
    assert len(back["words"]) == 5


def test_a_word_past_the_page_runs_on_for_every_ruling(editor):
    """#739: six words already fill the page. The seventh is a new page of copy, trace and row."""
    client = user()
    page = editor(*blatt(6), client=client, words=SIX)
    add_word(page, "Garten")
    stored = doc(page, client)
    first = sorted(linked(stored), key=lambda b: b["y"])
    assert [rows_of(b) for b in first] == [6, 6, 6]
    assert len(stored["pages"]) == 2
    second = sorted(linked(stored, 1), key=lambda b: b["y"])
    assert [b["props"]["list"] for b in second] == ["copy", "trace", "row"]
    assert [b["props"].get("from") for b in second] == [6, 6, 6]
    assert [rows_of(b) for b in second] == [1, 1, 1]
    assert second[-1]["y"] + second[-1]["h"] <= 282
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    undo(page)
    back = doc(page, client)
    assert len(back["pages"]) == 1
    assert len(back["words"]) == 6


def test_the_three_exercises_do_not_overlap_when_a_word_comes(editor):
    client = user()
    page = editor(*blatt(5), client=client, words=FIVE)
    add_word(page, "Garten")
    lines = sorted(linked(doc(page, client)), key=lambda b: b["y"])
    assert len(lines) == 3
    for upper, lower in pairwise(lines):
        assert upper["y"] + upper["h"] <= lower["y"]


def test_a_locked_ruling_keeps_its_rows_when_a_word_comes(editor):
    client = user()
    locked = {"kind": "l1", "color": "#222222", "list": "copy"}
    page = editor(box("r", "ruling", locked, y=55, h=120, locked=True), client=client, words=SIX)
    add_word(page, "Garten")
    expect(field(page)).to_have_value("Hund\nKatze\nMaus\nReh\nIgel\nFuchs\nGarten")
    assert linked(doc(page, client))[0]["h"] == 120


def test_a_sheet_from_the_template_keeps_its_six_rows_over_two_words(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    from_template(page, "Lernwörter")
    write_list(page, ["Hund", "Katze"])
    assert [b["h"] for b in linked(doc(page, client))] == [69, 69, 69]
