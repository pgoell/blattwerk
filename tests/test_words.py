"""The Lernwörter: a sheet's list, the Lineatur that takes it, the Blatt, and copies of both."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import io
import re

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import (
    RULING,
    box,
    doc,  # noqa: F401
    seiten,
)

LINKED = {**RULING, "list": "copy"}
MODES = ["copy", "trace", "row"]
WORDS = ["Hund", "Katze", "Igel"]


@pytest.fixture
def editor(editor):
    """The editor as it opens. `wide` is taken and means nothing any more: the list's field stands in
    the panel of a block that shows the list, in a window of any width."""

    def start(*blocks, **more):
        more.pop("wide", None)
        return editor(*blocks, **more)

    return start


def ready(page):
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()


def list_tab(page):
    """Shows the list's field. It stands in the panel of a picked block that shows the list; with
    none picked, the tool "Lernwörter" puts such a Lineatur on the page, picked."""
    if field(page).count():
        return
    if page.locator(".pages").count():
        seiten(page, False)
    page.locator(".insert, .dock").get_by_role("button", name="Lernwörter", exact=True).click()
    expect(field(page)).to_be_visible()


def blatt(rows=6):
    """The page of the template "Lernwörter", with so many rows to a Lineatur: a heading, a name
    line and three Lineaturen 3 one under the next that take the list, to copy, to trace and to
    trace along the row. They are named by what they do."""
    head = {"text": "Lernwörter", "size": 20, "align": "left", "bold": True}
    blocks = [box("h", "text", head, y=15, h=12), box("n", "name", {}, y=31, h=10, z=2)]
    y = 47
    for z, mode in enumerate(MODES, 3):
        props = {"kind": "l3", "color": "#222222", "list": mode}
        blocks.append(box(mode, "ruling", props, y=y, h=rows * 11.5, z=z))
        y += rows * 11.5 + 6
    return blocks


def lernen(page):
    """The switch that makes the picked Lineatur show the sheet's list. Picked beside a text, which
    has the same switch, it says that it is the Lineatur's."""
    name = re.compile(r"^Lernwörter des Blatts( in der Lineatur)?$")
    return page.locator(".panel").get_by_role("switch", name=name)


def sollen(page):
    """What the children do with the words on the picked Lineatur."""
    return page.locator(".panel").get_by_label("Die Kinder sollen")


def link(page, mode):
    """Makes the picked Lineatur show the list in `mode`, or with "own" its own text again."""
    on = lernen(page).get_attribute("aria-checked") == "true"
    if (mode != "own") != on:
        lernen(page).click()
    if mode == "own":
        return expect(lernen(page)).to_have_attribute("aria-checked", "false")
    if sollen(page).input_value() != mode:
        sollen(page).select_option(mode)
    expect(sollen(page)).to_have_value(mode)


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
