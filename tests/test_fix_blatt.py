"""Two regressions: the Lernwörter-Blatt on an empty page fills that page, and the small picture
of a Knickblatt on Meine Blätter draws its words under one another.

The docstrings name the lines of the checklist that each test proves.
"""

# The fixture `window` is imported, and each test names it as its argument.
# ruff: noqa: F811

import io
from itertools import pairwise

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from test_feed_print import sheet_id
from test_knick import KNICK
from test_loading import window  # noqa: F401
from test_words import list_tab, redo, rulings, undo
from ui import TEXT, box, doc, sheet, thumb, user

WORDS = ["Hund", "Katze", "Maus"]
BLATT = ["text", "name", "ruling", "ruling", "ruling"]


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def pdf_pages(server, client, mine):
    """The text of each page of a sheet's PDF, as the server makes it."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return [p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages]


def test_the_blatt_fills_an_empty_page(editor, server):
    """#425 Lernwörter-Blatt on an empty page fills that page: the sheet keeps one page, the PDF has
    one page and it is not blank."""
    client = user()
    page = editor(client=client, words=WORDS)
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    stored = doc(page, client)
    assert len(stored["pages"]) == 1
    assert [b["type"] for b in stored["pages"][0]["blocks"]] == BLATT
    texts = pdf_pages(server, client, sheet_id(page))
    assert len(texts) == 1
    assert "Lernwörter" in texts[0]


def test_undo_gives_the_empty_page_back(editor):
    """Implied 1: Rückgängig after Lernwörter-Blatt on an empty page gives the empty page back in
    one step, Wiederholen the Blatt."""
    client = user()
    page = editor(client=client, words=WORDS)
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    undo(page)
    stored = doc(page, client)
    assert len(stored["pages"]) == 1
    assert stored["pages"][0]["blocks"] == []
    redo(page)
    stored = doc(page, client)
    assert len(stored["pages"]) == 1
    assert [b["type"] for b in stored["pages"][0]["blocks"]] == BLATT


def test_the_blatt_takes_the_size_of_its_empty_page(editor):
    """Implied 7: an empty page with a format of its own (Querformat) gets a Blatt of its size."""
    client = user()
    page = editor(
        box("a", "text", TEXT),
        pages=[{"blocks": [], "landscape": True}],
        client=client,
        words=WORDS,
    )
    thumb(page, 1).click()
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    stored = doc(page, client)
    assert len(stored["pages"]) == 2
    lines = rulings(stored, 1)
    assert len(lines) == 3
    assert all(b["w"] == 267 for b in lines)


def test_the_list_shows_a_knickblatts_words_under_one_another(window, server):
    """#426 The small picture on Meine Blätter shows a Knickblatt's words under one another."""
    page, client = window()
    sheet(client, [box("k", "ruling", KNICK, w=180, h=69)], words=WORDS)
    page.goto(server)
    expect(page.locator(".sheets li")).to_have_count(1)
    rows = page.locator(".sheets .written.listed .row")
    expect(rows).to_have_count(len(WORDS))
    spots = rows.evaluate_all(
        "els => els.map((el) => { const r = el.getBoundingClientRect(); return [r.top, r.left]; })"
    )
    tops = [top for top, _ in spots]
    lefts = [left for _, left in spots]
    assert all(a < b for a, b in pairwise(tops)), tops
    assert max(lefts) - min(lefts) <= 0.5, lefts
