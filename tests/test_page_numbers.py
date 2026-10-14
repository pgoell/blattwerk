"""Automatic page numbers (#88): a sheet numbers its pages from the Ansicht tab or panel Seiten."""

import io

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from test_clipboard import button
from test_pages import copy as duplicate
from test_pages import pull, three, thumb
from ui import TEXT, at, box, centre, doc, reload, user

FOLIO = ".sheet[data-page] .scaled .folio"
MM = {"upright": 210, "landscape": 297}


def folio(page, n):
    return page.locator(f'.sheet[data-page="{n}"] .scaled .folio')


def switch(page, name):
    """The button Aus or An of the numbers: the Raster has an Aus of its own."""
    return page.get_by_role("group", name="Seitenzahlen").get_by_role("button", name=name)


def click_on(page, n):
    """Clicks the middle of page n's number, scrolled into the window first."""
    folio(page, n).scroll_into_view_if_needed()
    x, y = centre(folio(page, n))
    # The number lies under nothing of the editor's own: a click there reaches the page.
    assert page.evaluate(f"document.elementsFromPoint({x}, {y}).length") > 0
    page.mouse.click(x, y)


def numbers(page, at_=None, form=None):
    """Turns the numbers on in the Ansicht tab, then picks a place and a form if asked."""
    page.get_by_role("tab", name="Ansicht").click()
    page.get_by_role("button", name="An", exact=True).click()
    expect(page.get_by_role("button", name="An", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    if at_:
        page.get_by_role("button", name=at_, exact=True).click()
    if form:
        page.get_by_role("button", name=form, exact=True).click()


def test_a_sheet_without_page_numbers_shows_none_on_screen_or_in_the_pdf(editor, server):
    """Off by default: the Ansicht tab says Aus, and no page has a number."""
    client = user()
    page = three(editor, client=client)
    page.get_by_role("tab", name="Ansicht").click()
    expect(page.get_by_role("heading", name="Seitenzahlen", exact=True)).to_be_visible()
    expect(switch(page, "Aus")).to_have_attribute("aria-pressed", "true")
    expect(page.locator(FOLIO)).to_have_count(0)
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    text = " ".join(p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages)
    assert "Seite" not in text
    assert "/ 3" not in text


def test_turning_numbers_on_numbers_each_of_three_pages_and_a_reload_keeps_them(editor):
    """The three pages read 1, 2, 3, and they still do after a reload."""
    page = three(editor)
    numbers(page)
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])
    reload(page, page.url)
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])


def test_the_page_panel_checkbox_turns_the_numbers_on(editor, server):
    """The checkbox under the thumbnails does what the Ansicht tab does."""
    client = user()
    page = three(editor, client=client)
    page.locator("aside.left").get_by_label("Seitenzahlen", exact=True).check()
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])
    assert doc(page, client)["pageNumbers"]["on"] is True


@pytest.mark.parametrize(
    ("form", "texts"),
    [
        ("2", ["1", "2", "3"]),
        ("Seite 2", ["Seite 1", "Seite 2", "Seite 3"]),
        ("2 / 5", ["1 / 3", "2 / 3", "3 / 3"]),
        ("Seite 2 von 5", ["Seite 1 von 3", "Seite 2 von 3", "Seite 3 von 3"]),
    ],
)
def test_each_form_gives_its_text_on_page_two_of_three(editor, form, texts):
    """The four forms: page 2 of 3 reads as the form says."""
    page = three(editor)
    numbers(page, form=form)
    expect(folio(page, 1)).to_have_text(texts[1])
    expect(page.locator(FOLIO)).to_have_text(texts)


@pytest.mark.parametrize(
    ("change", "texts"),
    [
        (lambda page: button(page, "Neue Seite").click(), ["1 / 4", "2 / 4", "3 / 4", "4 / 4"]),
        (lambda page: button(page, "Seite löschen").click(), ["1 / 2", "2 / 2"]),
        (lambda page: pull(page, 0, 2, "right"), ["1 / 3", "2 / 3", "3 / 3"]),
        (lambda page: duplicate(page).click(), ["1 / 4", "2 / 4", "3 / 4", "4 / 4"]),
    ],
    ids=["added", "deleted", "moved", "copied"],
)
def test_the_numbers_run_one_to_m_after_a_page_is_added_deleted_moved_or_copied(
    editor, change, texts
):
    """The "of" form follows the sheet: each number is its page's place, and the total the count."""
    page = three(editor)
    numbers(page, form="2 / 5")
    expect(page.locator(FOLIO)).to_have_count(3)
    thumb(page, 1).click()
    change(page)
    expect(page.locator(FOLIO)).to_have_text(texts)


def test_undo_and_redo_take_turning_on_and_a_form_change_as_one_step_each(editor):
    """Each change is one undo step: the switch on, then the form."""
    page = three(editor)
    page.get_by_role("tab", name="Ansicht").click()
    page.get_by_role("button", name="An", exact=True).click()
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])
    page.keyboard.press("Control+z")
    expect(page.locator(FOLIO)).to_have_count(0)
    page.keyboard.press("Control+y")
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])
    page.get_by_role("button", name="2 / 5", exact=True).click()
    expect(page.locator(FOLIO)).to_have_text(["1 / 3", "2 / 3", "3 / 3"])
    page.keyboard.press("Control+z")
    expect(page.locator(FOLIO)).to_have_text(["1", "2", "3"])
    page.keyboard.press("Control+y")
    expect(page.locator(FOLIO)).to_have_text(["1 / 3", "2 / 3", "3 / 3"])


def test_nicht_auf_der_ersten_seite_leaves_page_one_bare_and_page_two_reads_2(editor):
    """With the box ticked, page 1 has no number and page 2 reads 2."""
    page = three(editor)
    numbers(page)
    page.get_by_label("Nicht auf der ersten Seite", exact=True).check()
    expect(folio(page, 0)).to_have_count(0)
    expect(page.locator(FOLIO)).to_have_text(["2", "3"])
    expect(folio(page, 1)).to_have_text("2")


def test_nicht_auf_der_ersten_seite_keeps_the_sheets_total_in_the_of_form(editor):
    """Page 1 is skipped, but the total still counts it: page 2 of 3 reads 2 / 3."""
    page = three(editor)
    numbers(page, form="2 / 5")
    page.get_by_label("Nicht auf der ersten Seite", exact=True).check()
    expect(page.locator(FOLIO)).to_have_text(["2 / 3", "3 / 3"])


def test_a_block_over_a_number_is_picked_by_a_click_on_the_number(editor):
    """The number lies under the text block; the block takes the click, not the number."""
    cover = {**box("cover", "text", TEXT), "x": 60, "y": 280, "w": 90, "h": 10}
    page = editor(cover)
    numbers(page)
    expect(folio(page, 0)).to_have_text("1")
    click_on(page, 0)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect(at(page, "cover")).to_have_class("block sel")


def test_a_click_on_a_bare_number_picks_no_block(editor):
    """With no block over it, a click on the number picks nothing."""
    page = editor()
    numbers(page)
    expect(folio(page, 0)).to_have_text("1")
    # Nothing takes hold of it: the click goes through to the page.
    expect(folio(page, 0)).to_have_css("pointer-events", "none")
    click_on(page, 0)
    expect(page.locator(".block.sel")).to_have_count(0)


def test_a_landscape_page_puts_its_number_centred_6_mm_above_its_own_bottom(editor):
    """Page 2 is landscape: its number centres on its 297 mm width, 6 mm above its 210 mm bottom."""
    page = editor(
        box("a", "text", TEXT),
        pages=[{"blocks": [], "landscape": True}, {"blocks": []}],
    )
    numbers(page)
    expect(folio(page, 1)).to_have_text("2")
    sheet = page.locator('.sheet[data-page="1"]').bounding_box()
    mark = folio(page, 1).bounding_box()
    px = sheet["width"] / MM["landscape"]
    assert abs(sheet["height"] / px - MM["upright"]) <= 1
    assert abs((mark["x"] + mark["width"] / 2 - sheet["x"]) / px - 148.5) <= 1
    assert abs((sheet["y"] + sheet["height"] - (mark["y"] + mark["height"])) / px - 6) <= 1


def test_unten_aussen_puts_odd_pages_right_and_even_pages_left(editor):
    """Page 1 has its number 15 mm from the right edge, page 2 15 mm from the left edge."""
    page = three(editor)
    numbers(page, at_="Unten außen")
    expect(page.locator(FOLIO)).to_have_count(3)
    for n, edge in ((0, "right"), (1, "left")):
        sheet = page.locator(f'.sheet[data-page="{n}"]').bounding_box()
        mark = folio(page, n).bounding_box()
        px = sheet["width"] / MM["upright"]
        if edge == "right":
            gap = sheet["x"] + sheet["width"] - (mark["x"] + mark["width"])
        else:
            gap = mark["x"] - sheet["x"]
        assert abs(gap / px - 15) <= 1, f"page {n + 1}: {gap / px} mm from the {edge} edge"


def test_the_answer_key_pdf_prints_the_of_form_on_page_two_with_and_without_solutions(
    editor, server
):
    """The PDF shows "2 / 3" on page 2, for the pupil's sheet and for the answer key."""
    client = user()
    page = three(editor, client=client)
    numbers(page, form="2 / 5")
    doc(page, client)
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    for solved in (False, True):
        res = httpx.get(
            f"{server}/api/sheets/{sheet_id}/pdf",
            params={"solved": solved},
            headers=cookie,
            timeout=60,
        )
        assert res.status_code == 200
        pages = PdfReader(io.BytesIO(res.content)).pages
        assert "2 / 3" in pages[1].extract_text(), f"solved={solved}"


def test_aus_and_an_again_keep_the_place_and_the_form(editor):
    """Switching off and on again keeps the chosen place and form."""
    page = three(editor)
    numbers(page, at_="Oben rechts", form="Seite 2 von 5")
    switch(page, "Aus").click()
    expect(page.locator(FOLIO)).to_have_count(0)
    page.get_by_role("button", name="An", exact=True).click()
    expect(page.get_by_role("button", name="Oben rechts", exact=True)).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(page.locator(FOLIO)).to_have_text(["Seite 1 von 3", "Seite 2 von 3", "Seite 3 von 3"])


def pdf(server, client, page, **params):
    """The sheet's PDF, as PdfReader pages."""
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(
        f"{server}/api/sheets/{sheet_id}/pdf", params=params, headers=cookie, timeout=60
    )
    assert res.status_code == 200
    return PdfReader(io.BytesIO(res.content)).pages


def test_the_number_is_9_pt_andika_grey_or_black_and_the_thumbnails_show_it(editor):
    """Grey by default, black by the Farbe switch; the thumbnails draw the same number."""
    page = three(editor)
    numbers(page)
    mark = folio(page, 1)
    expect(mark).to_have_css("font-family", "Andika")
    expect(mark).to_have_css("font-size", "12px")
    expect(mark).to_have_css("color", "rgb(112, 112, 112)")
    page.get_by_role("button", name="Schwarz", exact=True).click()
    expect(mark).to_have_css("color", "rgb(0, 0, 0)")
    expect(page.locator(".pages .paper .folio")).to_have_text(["1", "2", "3"])


def test_oben_rechts_moves_the_answer_keys_heading_to_the_left(editor, server):
    """On the key, the heading Lösungen and a number at the top right do not meet."""
    client = user()
    page = three(editor, client=client)
    numbers(page, at_="Oben rechts")
    doc(page, client)
    found = {}

    def seen(text, cm, tm, font, size):
        if text.strip():
            found[text.strip()] = tm[4] * cm[0] + cm[4]

    pdf(server, client, page, solved=True)[1].extract_text(visitor_text=seen)
    half = 105 * 72 / 25.4
    assert found["Lösungen"] < half < found["2"], found


def test_each_variant_prints_its_pages_numbered(editor, server):
    """Varianten: every variant's pages read 1, 2, 3."""
    client = user()
    page = three(editor, client=client)
    numbers(page, form="2 / 5")
    doc(page, client)
    pages = pdf(server, client, page, varianten=2)
    assert len(pages) == 6
    assert ["2 / 3" in p.extract_text() for p in pages] == [False, True, False] * 2
