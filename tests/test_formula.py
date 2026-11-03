"""Formulas on a sheet: fractions, roots and powers print as text, and the size follows the font (#833)."""

import io

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import box, doc, insert, maths, sheet, user


def printed(server, client, blocks):
    mine = sheet(client, blocks, title="Formeln")
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200, res.text
    return PdfReader(io.BytesIO(res.content)).pages[0]


def glyph_sizes(page, glyphs):
    found = []

    def visit(text, _cm, _tm, _font, font_size):
        if text.strip() in glyphs:
            found.append(font_size)

    page.extract_text(visitor_text=visit)
    return found


def test_a_formula_prints_as_text_and_the_size_follows_the_font(server):
    """Two fractions, 20 pt and 40 pt: the PDF has the digits as text, and the larger is twice the smaller."""
    client = user()
    small = box(
        "small", "formula", {"source": "3/4", "size": 20, "align": "center"}, z=1, w=40, h=18
    )
    big = box("big", "formula", {"source": "3/4", "size": 40, "align": "center"}, z=2, w=70, h=32)
    page = printed(server, client, [small, big])
    assert len(page.images) == 0
    text = page.extract_text()
    assert "3" in text and "4" in text
    sizes = glyph_sizes(page, {"3", "4"})
    smalls = [n for n in sizes if n < 22]
    bigs = [n for n in sizes if n >= 22]
    assert smalls and bigs, sizes
    assert max(bigs) / max(smalls) == pytest.approx(2, rel=0.3)


def test_a_formula_in_text_a_table_cell_and_a_rechnen_cell_prints(server):
    """The same formula inline in a text, a table cell and a written Rechnen cell is text in the PDF."""
    client = user()
    words = box(
        "words",
        "text",
        {"text": "Wurzel \\f{sqrt(16)} und \\f{x_2} und \\f{2+\\ }", "size": 18, "align": "left"},
        z=1,
        w=170,
        h=16,
    )
    table = box(
        "grid",
        "table",
        {
            "cells": [["\\f{1 3/4}", "daneben"]],
            "cols": [1, 1],
            "size": 16,
            "align": "center",
            "line": "#222222",
        },
        z=2,
        w=90,
        h=24,
    )
    props = maths(client, format="written", count=1, columns=1)
    exercise = props["exercises"][0]
    assert "grid" in exercise
    cell = next(c for c in exercise["grid"]["cells"] if c[3] == 0 and c[2].isdigit())
    cell[2] = "3/4"
    calc = box("calc", "maths", props, z=3, w=90, h=50)
    page = printed(server, client, [words, table, calc])
    assert len(page.images) == 0
    text = page.extract_text()
    # The source marker and the word sqrt are the input, not what the sheet prints.
    assert "sqrt" not in text
    assert "f{" not in text
    assert "16" in text
    assert "daneben" in text
    assert "1" in text and "3" in text and "4" in text


def test_the_gallery_and_the_preview_follow_the_source(editor):
    """A Formel block: a template and a typed source show in the preview and on the sheet."""
    client = user()
    page = editor(client=client)
    insert(page, "Formel")
    expect(page.locator(".panel")).to_contain_text("Formel")
    expect(page.locator(".formula-preview .formula")).to_have_attribute("data-formula", "3/4")
    expect(page.locator(".block .formula")).to_have_attribute("data-formula", "3/4")
    page.get_by_role("button", name="Potenz", exact=True).click()
    expect(page.locator(".block .formula")).to_have_attribute("data-formula", "2^3")
    expect(page.locator(".formula-preview .formula")).to_have_attribute("data-formula", "2^3")
    page.get_by_label("Formel", exact=True).fill("sqrt(16)")
    expect(page.locator(".formula-preview .formula")).to_have_attribute("data-formula", "sqrt(16)")
    expect(page.locator(".block .formula")).to_have_attribute("data-formula", "sqrt(16)")
    page.get_by_role("button", name="Schrift größer", exact=True).click()
    assert doc(page, client)["pages"][0]["blocks"][0]["props"]["size"] == 20


def test_a_formula_lands_in_a_text_and_a_table_cell(editor):
    """Einfügen puts the formula into the text being written, and into the open table cell."""
    client = user()
    page = editor(client=client)
    page.locator(".dock, .insert").get_by_label("Text", exact=True).click()
    page.keyboard.type("Siehe ")
    page.get_by_role("button", name="Formel einfügen", exact=True).click()
    page.keyboard.press("F2")
    expect(page.locator(".block .formula")).to_have_attribute("data-formula", "3/4")
    assert "\\f{3/4}" in doc(page, client)["pages"][0]["blocks"][0]["props"]["text"]

    page.locator(".dock, .insert").get_by_label("Tabelle", exact=True).click()
    page.locator(".block.sel [data-cell='0']").dblclick()
    page.get_by_role("button", name="Formel einfügen", exact=True).click()
    page.keyboard.press("Escape")
    cells = doc(page, client)["pages"][0]["blocks"][-1]["props"]["cells"]
    assert cells[0][0] == "\\f{3/4}"
    expect(page.locator(".block").nth(1).locator(".formula")).to_have_attribute(
        "data-formula", "3/4"
    )
