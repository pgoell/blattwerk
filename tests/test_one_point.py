"""A score box with a score of 1 says "Punkt", on the sheet and in the PDF (issue #501)."""

import io

import httpx
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import at, box, pick, user

PANEL_SCORE = '.panel input[aria-label="Punkte"]'


def words(page, name):
    return at(page, name).locator(".points")


def printed(page, client, server):
    """The words of the PDF's first page, one space between them."""
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    return " ".join(PdfReader(io.BytesIO(res.content)).pages[0].extract_text().split())


def test_a_score_of_one_says_punkt_on_the_sheet_and_in_the_pdf(editor, server):
    """A3"""
    client = user()
    page = editor(box("a", "points", {"max": 1}), client=client)
    expect(words(page, "a")).to_have_text("/ 1 Punkt")
    text = printed(page, client, server)
    assert "/ 1 Punkt" in text
    assert "Punkte" not in text


def test_a_score_of_two_and_more_says_punkte(editor, server):
    """A3"""
    client = user()
    page = editor(
        box("a", "points", {"max": 2}), box("b", "points", {"max": 10}, y=60), client=client
    )
    expect(words(page, "a")).to_have_text("/ 2 Punkte")
    expect(words(page, "b")).to_have_text("/ 10 Punkte")
    text = printed(page, client, server)
    assert "/ 2 Punkte" in text
    assert "/ 10 Punkte" in text


def test_a_score_typed_as_one_says_punkt_and_undo_brings_punkte_back(editor):
    """A3, I8"""
    page = editor(box("a", "points", {"max": 10}))
    pick(page, "a")
    page.locator(PANEL_SCORE).fill("")
    page.locator(PANEL_SCORE).press_sequentially("1")
    page.locator(PANEL_SCORE).press("Enter")
    expect(words(page, "a")).to_have_text("/ 1 Punkt")
    page.get_by_label("Rückgängig", exact=True).first.click()
    expect(words(page, "a")).to_have_text("/ 10 Punkte")
    page.get_by_label("Wiederholen", exact=True).first.click()
    expect(words(page, "a")).to_have_text("/ 1 Punkt")
