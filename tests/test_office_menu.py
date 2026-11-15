"""The button beside "PDF": the sheet as a PowerPoint or a Word file."""

import io
import zipfile

import pytest
from playwright.sync_api import expect
from pptx import Presentation
from ui import TEXT, box, pick

OTHER = "Als PowerPoint oder Word laden"
ENTRIES = ["PowerPoint (.pptx)", "Word (.docx)", "PowerPoint mit Lösungen", "Word mit Lösungen"]


def open_menu(page):
    page.locator("header .pdf").get_by_role("button", name=OTHER).click()
    menu = page.get_by_role("menu")
    expect(menu.get_by_role("menuitem")).to_have_text(ENTRIES)
    return menu


@pytest.mark.timeout(120)
def test_the_menu_loads_the_sheet_as_powerpoint_and_as_word(editor):
    page = editor(box("a", "text", {**TEXT, "text": "Lies genau"}))
    with page.expect_download() as got:
        open_menu(page).get_by_role("menuitem", name="PowerPoint (.pptx)").click()
    assert got.value.suggested_filename.endswith(".pptx")
    with open(got.value.path(), "rb") as file:
        (slide,) = Presentation(io.BytesIO(file.read())).slides
    assert [shape.text_frame.text for shape in slide.shapes] == ["Lies genau"]

    with page.expect_download() as got:
        open_menu(page).get_by_role("menuitem", name="Word mit Lösungen").click()
    assert got.value.suggested_filename.endswith(" Lösungen.docx")
    with zipfile.ZipFile(got.value.path()) as z:
        assert ">Lies genau</w:t>" in z.read("word/document.xml").decode()
    expect(page.locator(".fault")).to_have_count(0)


def test_the_keys_open_the_menu_and_escape_gives_the_button_the_focus_back(editor):
    page = editor(box("a", "text", TEXT))
    button = page.locator("header .pdf").get_by_role("button", name=OTHER)
    button.focus()
    page.keyboard.press("Enter")
    menu = page.get_by_role("menu")
    expect(menu.get_by_role("menuitem").first).to_be_focused()
    page.keyboard.press("Escape")
    expect(menu).to_have_count(0)
    expect(button).to_be_focused()


def test_the_menu_has_no_row_of_block_commands_over_a_picked_block(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    menu = open_menu(page)
    expect(menu.get_by_role("toolbar")).to_have_count(0)


def test_a_file_the_server_cannot_make_says_so(editor):
    page = editor(box("a", "text", TEXT))
    page.route("**/api/sheets/*/docx", lambda route: route.fulfill(status=500))
    open_menu(page).get_by_role("menuitem", name="Word (.docx)").click()
    expect(page.locator(".fault")).to_contain_text("Die Datei konnte nicht erstellt werden.")
