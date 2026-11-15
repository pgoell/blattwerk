"""Font, size, bold, italic and underline for single cells of a table, a whole row or column (#1154)."""

import re

from playwright.sync_api import expect
from test_cells import GRID, cell, open_cell, print_page, props
from ui import at, box, pick, unpick, user

# Chromium quotes a font's name in `font-family`, WebKit does not.
NORD = re.compile(r'^"?Fibel Nord"?$')
SUED = re.compile(r'^"?Fibel Sued"?$')


def button(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def weight(page, n):
    return cell(page, "t", n).evaluate("el => getComputedStyle(el).fontWeight")


def test_bold_goes_on_the_picked_cells_only(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    button(page, "Fett").click()
    expect(button(page, "Fett")).to_have_attribute("aria-pressed", "true")
    for n in range(9):
        assert weight(page, n) == ("700" if n in (0, 1, 3, 4) else "400"), n
    looks = props(page, client)["looks"]
    assert looks == [
        [{"bold": True}, {"bold": True}, None],
        [{"bold": True}, {"bold": True}, None],
        [None, None, None],
    ]
    # The cells stay picked.
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(4)


def test_one_undo_takes_the_format_back(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 4)
    button(page, "Kursiv").click()
    expect(cell(page, "t", 4)).to_have_css("font-style", "italic")
    page.get_by_label("Rückgängig", exact=True).click()
    expect(cell(page, "t", 4)).to_have_css("font-style", "normal")
    assert "looks" not in props(page, client)


def test_a_whole_row_and_a_whole_column(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 4)
    page.get_by_role("button", name="Ganze Zeile", exact=True).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(3)
    button(page, "Unterstrichen").click()
    open_cell(page, "t", 1)
    page.get_by_role("button", name="Ganze Spalte", exact=True).click()
    expect(at(page, "t").locator(".table > div.picked")).to_have_count(3)
    button(page, "Schrift größer").click()
    expect(page.locator(".panel output").filter(has_text="pt").first).to_have_text("16 pt")
    looks = props(page, client)["looks"]
    assert [[bool(x and x.get("underline")) for x in row] for row in looks] == [
        [False] * 3,
        [True] * 3,
        [False] * 3,
    ]
    assert [[(x or {}).get("size") for x in row] for row in looks] == [[None, 16, None]] * 3


def test_a_cell_font_shows_and_the_table_font_clears_it(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 2)
    # The keys of the closed list step through the fonts: andika, nord, sued.
    page.locator(".panel").get_by_label("Schriftart der Zellen").press("ArrowDown")
    expect(cell(page, "t", 2)).to_have_css("font-family", NORD)
    expect(cell(page, "t", 1)).not_to_have_css("font-family", NORD)
    assert props(page, client)["looks"][0][2] == {"font": "nord"}
    # With no cell open the font is the table's, for every cell.
    unpick(page)
    pick(page, "t")
    page.locator(".panel").get_by_label("Schriftart der Tabelle").press("ArrowDown")
    page.locator(".panel").get_by_label("Schriftart der Tabelle").press("ArrowDown")
    expect(cell(page, "t", 2)).to_have_css("font-family", SUED)
    assert "looks" not in props(page, client)


def test_a_cell_bold_wins_over_the_kopfzeile_and_a_new_row_keeps_the_looks_in_place(editor):
    client = user()
    page = editor(box("t", "table", {**GRID, "head": True}), client=client)
    open_cell(page, "t", 0)
    button(page, "Fett").click()
    expect(cell(page, "t", 0)).to_have_css("font-weight", "400")
    expect(cell(page, "t", 1)).to_have_css("font-weight", "700")
    page.get_by_role("button", name="Zeile darüber", exact=True).click()
    expect(at(page, "t").locator(".table > div[data-cell]")).to_have_count(12)
    looks = props(page, client)["looks"]
    assert looks[0] == [None, None, None]
    assert looks[1][0] == {"bold": False}


def test_the_print_draws_the_looks(editor, browser, server):
    client = user()
    looks = [
        [{"bold": True, "size": 20}, None, None],
        [None, {"italic": True}, None],
        [None, None, None],
    ]
    page = editor(box("t", "table", {**GRID, "looks": looks}), client=client)
    expect(cell(page, "t", 0)).to_have_css("font-weight", "700")
    sheet_id = page.url.rsplit("/", 1)[1]
    context, printed = print_page(browser, server, client, sheet_id)
    try:
        first = printed.locator('.table > div[data-cell="0"]')
        expect(first).to_have_css("font-weight", "700")
        assert first.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") > printed.locator(
            '.table > div[data-cell="2"]'
        ).evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
        expect(printed.locator('.table > div[data-cell="4"]')).to_have_css("font-style", "italic")
    finally:
        context.close()
