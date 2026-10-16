"""A PDF, or a variants print, says so when the server holds an older sheet than the editor shows.

The PDF prints what the server holds. Where the last change has not been saved, the teacher is told
that the PDF shows the saved version. A save that lands in time gives no line at all.
"""

import pypdf
from playwright.sync_api import expect
from test_refused_save import ALERT, break_x, open_sheet
from ui import FIELD, pick

STALE = "Das PDF zeigt den zuletzt gespeicherten Stand"
VARIANTS_STALE = "Die Varianten zeigen den zuletzt gespeicherten Stand"


def pdf_button(page):
    return page.get_by_role("button", name="PDF", exact=True)


def type_text(page, text):
    """Replaces the text of block a with `text`, and leaves the block picked."""
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(text)
    expect(page.locator(FIELD)).to_have_text(text)


def answer_with(status):
    """A route for a sheet: each save gets the status, every other request goes on."""

    def handle(route):
        if route.request.method == "PATCH":
            route.fulfill(status=status, body="")
        else:
            route.continue_()

    return handle


def test_failed_save_pdf_says_it_prints_the_saved_version(editor):
    page, sheet_id = open_sheet(editor)
    page.route(f"**/api/sheets/{sheet_id}", answer_with(500))
    type_text(page, "du")

    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_contain_text(STALE)


def test_refused_save_pdf_says_it_prints_the_saved_version(editor):
    page, sheet_id = open_sheet(editor)
    break_x(page, f"**/api/sheets/{sheet_id}")
    pick(page, "a")
    page.keyboard.press("ArrowRight")

    with page.expect_download():
        pdf_button(page).click()
    # The save's own refusal stays on the page too: the PDF's line is the one to find.
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(1)


def test_hanging_save_pdf_says_it_prints_the_saved_version(editor):
    """The save never gets an answer: after the editor's 20 s limit the PDF goes on, and says so."""
    page, sheet_id = open_sheet(editor)

    def hang(route):
        if route.request.method != "PATCH":
            route.continue_()

    page.route(f"**/api/sheets/{sheet_id}", hang)
    type_text(page, "du")

    with page.expect_download(timeout=30000):
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_contain_text(STALE)


def test_slow_save_that_lands_pdf_prints_the_new_sheet(editor):
    """The save takes 1.5 s and lands: the PDF waits, holds the new text, and no line shows."""
    page, sheet_id = open_sheet(editor)
    held = []

    def hold(route):
        if route.request.method == "PATCH":
            held.append(route)
        else:
            route.continue_()

    page.route(f"**/api/sheets/{sheet_id}", hold)
    type_text(page, "du")

    with page.expect_download(timeout=30000) as got:
        pdf_button(page).click()
        while not held:
            page.wait_for_timeout(50)
        page.wait_for_timeout(1500)
        held[0].continue_()
    text = "".join(p.extract_text() for p in pypdf.PdfReader(got.value.path()).pages)
    assert "du" in text
    expect(page.locator(ALERT)).to_have_count(0)


def test_variants_print_after_failed_save_says_so(editor):
    page, sheet_id = open_sheet(editor)
    page.route(f"**/api/sheets/{sheet_id}", answer_with(500))
    type_text(page, "du")

    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    dialog = page.locator("dialog[open]")
    with page.expect_download():
        dialog.get_by_role("button", name="PDF", exact=True).click()
    expect(dialog.locator(ALERT)).to_contain_text(VARIANTS_STALE)


def test_the_line_goes_once_a_current_pdf_is_made(editor):
    """After the save works again, the next PDF removes the line."""
    page, sheet_id = open_sheet(editor)
    page.route(f"**/api/sheets/{sheet_id}", answer_with(500))
    type_text(page, "du")
    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_contain_text(STALE)

    page.unroute(f"**/api/sheets/{sheet_id}")
    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_have_count(0)


def test_a_pdf_of_a_saved_sheet_says_nothing(editor):
    page, _ = open_sheet(editor)
    type_text(page, "du")

    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_have_count(0)
