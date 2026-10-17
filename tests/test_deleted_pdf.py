"""A sheet deleted on another device: the PDF says so, and an unchanged tab learns of it (#736)."""

from playwright.sync_api import expect
from test_pdf_stale import pdf_button
from ui import TEXT, box, user


def open_then_delete(editor):
    """The editor on a sheet of one text block, the sheet deleted by the API. Gives the page."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    assert client.delete(f"/api/sheets/{sheet_id}").status_code == 200
    return page


def test_pdf_on_a_sheet_deleted_elsewhere_says_so_and_offers_the_choice(editor):
    page = open_then_delete(editor)
    pdf_button(page).click()
    line = page.get_by_role("alert").filter(has_text="Das PDF konnte nicht erstellt")
    expect(line).to_contain_text("gelöscht")
    expect(page.get_by_text("Versuche es noch einmal")).to_have_count(0)
    keep = page.locator(".clash").get_by_role("button", name="Als neues Blatt behalten")
    expect(keep).to_be_visible()


def test_after_keep_as_new_the_pdf_works_again(editor):
    page = open_then_delete(editor)
    pdf_button(page).click()
    page.locator(".clash").get_by_role("button", name="Als neues Blatt behalten").click()
    expect(page.locator(".clash")).to_have_count(0)
    expect(page.get_by_role("alert").filter(has_text="gelöscht")).to_have_count(0)
    with page.expect_download() as got:
        pdf_button(page).click()
    assert got.value.suggested_filename.endswith(".pdf")


def test_an_unchanged_tab_learns_of_the_delete_on_focus(editor):
    page = open_then_delete(editor)
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page.locator(".clash", has_text="gelöscht")).to_be_visible()
