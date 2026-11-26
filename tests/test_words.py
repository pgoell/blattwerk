"""The Lernwörter: a sheet's list, the Lineatur that takes it, the Blatt, and copies of both."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import io

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import (
    RULING,
    doc,  # noqa: F401
    seiten,
)

LINKED = {**RULING, "list": "copy"}
MODES = ["copy", "trace", "row"]
WORDS = ["Hund", "Katze", "Igel"]


@pytest.fixture
def editor(editor):
    """The editor in a window under 1024 px: there the panel has the tabs Format, Ansicht and
    Lernwörter, which these tests go by. `wide` keeps the window as it opens."""

    def start(*blocks, **more):
        wide = more.pop("wide", False)
        page = editor(*blocks, **more)
        if not wide and not more.get("touch"):
            page.set_viewport_size({"width": 1000, "height": 900})
            expect(page.get_by_role("tab", name="Lernwörter")).to_be_visible()
        return page

    return start


def ready(page):
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()


def list_tab(page):
    """Opens the word list: by the panel's tab in a narrow window, by the tool under "Deutsch" in a
    wide one."""
    tab = page.get_by_role("tab", name="Lernwörter")
    if tab.count():
        return tab.click()
    seiten(page, False)
    page.locator(".insert").get_by_role("button", name="Lernwörter", exact=True).click()


def field(page):
    return page.get_by_role("textbox", name="Lernwörter", exact=True)


def undo(page):
    page.get_by_label("Rückgängig", exact=True).first.click()


def redo(page):
    page.get_by_label("Wiederholen", exact=True).click()


def store_words(page, client, words):
    """Stores the sheet's list as the server holds it, then opens the sheet again."""
    shown = page.locator(".pages").count()
    sheet_id = page.url.rsplit("/", 1)[1]
    got = client.get(f"/api/sheets/{sheet_id}").json()
    body = {"doc": {**got["doc"], "words": words}, "version": got["version"]}
    assert client.patch(f"/api/sheets/{sheet_id}", json=body).status_code == 200
    page.reload()
    ready(page)
    if shown:
        seiten(page)


def go(page, other):
    """Opens another sheet of the same user in this tab, with the panel of pages as it was."""
    shown = page.locator(".pages").count()
    page.goto(f"{page.url.rsplit('/blatt/', 1)[0]}/blatt/{other['id']}")
    ready(page)
    if shown:
        seiten(page)
    page.bring_to_front()


def rulings(stored, n=0):
    return [b for b in stored["pages"][n]["blocks"] if b["type"] == "ruling"]


def state(stored):
    """The sheet's list, and what the first Lineatur holds of it: its mode and its own text."""
    props = rulings(stored)[0]["props"]
    return stored.get("words"), props.get("list"), props.get("text"), props.get("trace")


def pdf_pages(server, client, mine):
    """The text of each page of a sheet's PDF, as the server makes it."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return [p.extract_text() for p in PdfReader(io.BytesIO(res.content)).pages]


LONG = [f"Wort{n:02d}" for n in range(25)]
