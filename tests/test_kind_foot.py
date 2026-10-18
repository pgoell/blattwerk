"""A kind change keeps a Lineatur's rows up to the page foot, and says when a Lineatur covers a text."""

import pytest
from playwright.sync_api import expect
from test_fix_blatt import pdf_pages
from ui import RULING, TEXT, box, pick, saved, user

SENTENCE = "Am Montag gehen wir mit der ganzen Klasse in den Wald und sammeln bunte Blaetter, Eicheln und Kastanien fuer unser grosses Herbstbild im Klassenzimmer. Danach malen wir Regenschirme."
FOOT = 297


def kind_to(page, kind):
    page.get_by_label("Art der Lineatur").select_option(kind)


def foot_to(page):
    page.get_by_role("button", name="Bis Seitenende").click()


@pytest.mark.parametrize("start, end, text", [("k5", "k7", SENTENCE), ("l4", "l1", "")])
def test_a4_a_kind_change_after_bis_seitenende_ends_at_the_foot(editor, start, end, text):
    """A4: 'Bis Seitenende' then a bigger kind ends at the page foot, without the over-foot hint."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": start, "text": text}, h=15, y=20), client=client
    )
    pick(page, "l")
    foot_to(page)
    kind_to(page, end)
    expect(page.get_by_label("Art der Lineatur")).to_have_value(end)
    stored = saved(page, client)[0]
    assert stored["y"] + stored["h"] <= FOOT + 0.01, stored
    expect(page.locator('[data-foot="over"]')).to_have_count(0)


def test_a12_a_kind_change_over_a_text_shows_the_cover_hint_and_moves_nothing(editor):
    """A12: a Karo grows over a text below it; the text stays and the panel says the Lineatur covers it."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": SENTENCE}, h=30, y=15),
        box("t", "text", TEXT, y=47),
        client=client,
    )
    pick(page, "l")
    kind_to(page, "k7")
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["t"]["y"] == 47, stored["t"]
    expect(page.locator('[data-cover="over"]')).to_be_visible()


def test_i1_one_undo_takes_the_kind_change_and_its_height_back(editor):
    """I1: one undo after a kind change to the foot takes the kind and the height back."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": SENTENCE}, h=30, y=20), client=client
    )
    pick(page, "l")
    kind_to(page, "k7")
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Art der Lineatur")).to_have_value("k5")
    stored = saved(page, client)[0]
    assert stored["h"] == 30 and stored["props"]["kind"] == "k5", stored


def test_a_turned_lineatur_far_from_the_foot_keeps_its_rows_on_a_kind_change(editor):
    """Review: the foot is measured by the lowest corner, so a Lineatur turned upright whose unturned
    box would reach past the foot keeps its ten rows."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": "l4"}, x=50, y=200, w=20, h=100, angle=90),
        client=client,
    )
    pick(page, "l")
    kind_to(page, "l1")
    expect(page.get_by_text("10 Zeilen")).to_be_visible()
    assert saved(page, client)[0]["h"] == 200


def test_i2_a_kind_change_well_above_the_foot_keeps_its_rows(editor):
    """I2: a Karo well above the foot keeps its six rows when the kind grows."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": "Hallo"}, h=30, y=20), client=client
    )
    pick(page, "l")
    kind_to(page, "k7")
    expect(page.get_by_text("6 Zeilen")).to_be_visible()
    assert saved(page, client)[0]["h"] == 42


def test_a5_the_pdf_of_a_kind_change_at_the_foot_has_one_page_and_stops_at_the_foot(editor, server):
    """A5: after 'Bis Seitenende' and a bigger kind the PDF has one page and the block ends at the foot."""
    client = user()
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": SENTENCE}, h=15, y=20), client=client
    )
    pick(page, "l")
    foot_to(page)
    kind_to(page, "k7")
    stored = saved(page, client)[0]
    assert stored["y"] + stored["h"] <= FOOT + 0.01, stored
    pages = pdf_pages(server, client, page.url.rsplit("/", 1)[1])
    assert len(pages) == 1, pages


def test_i3_moving_the_text_away_takes_the_cover_hint(editor):
    """I3: with the cover hint showing, moving the text down to Y 150 takes the hint away."""
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": SENTENCE}, h=30, y=15),
        box("t", "text", TEXT, y=47),
    )
    pick(page, "l")
    kind_to(page, "k7")
    expect(page.locator('[data-cover="over"]')).to_be_visible()
    pick(page, "t")
    page.locator(".geo").get_by_label("Y", exact=True).fill("150")
    page.locator(".geo").get_by_label("Y", exact=True).press("Enter")
    expect(page.locator('[data-cover="over"]')).to_have_count(0)


def test_i3_the_cover_hint_goes_after_undo(editor):
    """I3: after the cover hint shows, one undo takes the kind back and the hint with it."""
    page = editor(
        box("l", "ruling", {**RULING, "kind": "k5", "text": SENTENCE}, h=30, y=15),
        box("t", "text", TEXT, y=47),
    )
    pick(page, "l")
    kind_to(page, "k7")
    expect(page.locator('[data-cover="over"]')).to_be_visible()
    page.keyboard.press("Control+z")
    expect(page.locator('[data-cover="over"]')).to_have_count(0)
