"""The download window's other files: the sheet as a PowerPoint or a Word file (#1186)."""

import io
import zipfile

import pytest
from playwright.sync_api import expect
from pptx import Presentation
from ui import TEXT, box, maths, user
from ui_download import door, download_window, saver

HINT = "In Word und PowerPoint bleibt Text bearbeitbar. Aufgaben und Tabellen werden Bilder."


def pick_format(window, name):
    window.get_by_role("group", name="Format").get_by_label(name, exact=True).check()


@pytest.mark.timeout(120)
def test_the_window_loads_the_sheet_as_powerpoint_and_as_word(editor):
    page = editor(box("a", "text", {**TEXT, "text": "Lies genau"}))
    window = download_window(page)
    pick_format(window, "PowerPoint")
    with page.expect_download() as got:
        saver(window).click()
    assert got.value.suggested_filename.endswith(".pptx")
    with open(got.value.path(), "rb") as file:
        (slide,) = Presentation(io.BytesIO(file.read())).slides
    assert [shape.text_frame.text for shape in slide.shapes] == ["Lies genau"]

    pick_format(window, "Word")
    with page.expect_download() as got:
        saver(window, answers=True).click()
    assert got.value.suggested_filename.endswith("Lösungen.docx")
    with zipfile.ZipFile(got.value.path()) as z:
        assert ">Lies genau</w:t>" in z.read("word/document.xml").decode()
    expect(window.get_by_role("alert")).to_have_count(0)
    expect(page.locator(".fault")).to_have_count(0)


def test_the_window_says_what_stays_editable_under_the_formats(editor):
    """The line under the format choice names what Word and PowerPoint keep as text."""
    page = editor(box("a", "text", TEXT))
    window = download_window(page)
    formats = window.get_by_role("group", name="Format")
    expect(formats.get_by_role("radio")).to_have_count(3)
    expect(formats.get_by_label("PDF", exact=True)).to_be_checked()
    hint = window.get_by_text(HINT, exact=True)
    expect(hint).to_be_visible()
    assert hint.bounding_box()["y"] > formats.bounding_box()["y"]


def test_only_a_pdf_comes_in_variants(editor):
    """Word and PowerPoint are one sheet: the variants and the letter are off, and come back with PDF."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=6), y=20, h=60), client=client)
    window = download_window(page)
    window.get_by_role("group", name="Varianten").get_by_label("3", exact=True).check()
    expect(window.get_by_role("group", name="Vorschau").get_by_role("radio")).to_have_count(3)
    pick_format(window, "Word")
    expect(
        window.get_by_role("group", name="Varianten").get_by_label("3", exact=True)
    ).to_be_disabled()
    expect(window.get_by_role("switch", name="Buchstabe auf jedem Blatt")).to_be_disabled()
    expect(window.get_by_role("group", name="Vorschau")).to_have_count(0)
    expect(window.locator(".preview")).to_have_attribute("data-variant", "A")
    pick_format(window, "PDF")
    expect(
        window.get_by_role("group", name="Varianten").get_by_label("3", exact=True)
    ).to_be_checked()


def test_the_keys_open_the_window_and_escape_gives_the_arrow_the_focus_back(editor):
    page = editor(box("a", "text", TEXT))
    door(page).focus()
    page.keyboard.press("Enter")
    window = page.locator("dialog.variants")
    expect(window).to_be_visible()
    page.keyboard.press("Escape")
    expect(window).to_have_count(0)
    expect(door(page)).to_be_focused()


def test_a_file_the_server_cannot_make_says_so(editor):
    page = editor(box("a", "text", TEXT))
    page.route("**/api/sheets/*/docx", lambda route: route.fulfill(status=500))
    window = download_window(page)
    pick_format(window, "Word")
    saver(window).click()
    expect(window.get_by_role("alert")).to_have_text("Die Datei konnte nicht erstellt werden.")
    expect(saver(window)).to_be_enabled()
