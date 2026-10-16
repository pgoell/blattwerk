"""A PDF, or a variants print, says so when the server holds an older sheet than the editor shows.

The PDF prints what the server holds. Where the last change has not been saved, the teacher is told
that the PDF shows the saved version. A save that lands in time gives no line at all.
"""

# ruff: noqa: F811

import pypdf
from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_refused_save import ALERT, break_x, open_sheet, stored
from test_saves import answer, clash, run, start  # noqa: F401
from test_stale import TURNS
from ui import FIELD, pick, unpick

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


def test_a_change_typed_while_the_pdf_waits_lands_and_no_line_shows(editor):
    """The first save is held; the PDF waits; a newer change lands in its wait. No line shows."""
    page, sheet_id = open_sheet(editor)
    held = []

    def hold_first(route):
        if route.request.method == "PATCH" and not held:
            held.append(route)
        else:
            route.continue_()

    page.route(f"**/api/sheets/{sheet_id}", hold_first)
    type_text(page, "du")
    while not held:
        page.wait_for_timeout(50)

    with page.expect_download(timeout=30000):
        pdf_button(page).click()
        unpick(page)
        pick(page, "a")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(1500)
        held[0].continue_()
    assert stored(sheet_id)["pages"][0]["blocks"][0]["x"] != 15
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(0)


def test_pdf_line_goes_once_the_other_version_is_loaded(run):
    """#699: the PDF line says the change is not saved; loading the other version takes it away."""
    page, _ = start(run)
    clash(run)
    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(1)

    page.locator(".clash").get_by_role("button", name="Andere Version laden").click()
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(0)


def test_variants_pdf_is_off_in_a_clash_and_says_why(run):
    """#698: the dialog's PDF waits for the teacher's choice, and says so."""
    page, _ = start(run)
    clash(run)
    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    dialog = page.locator("dialog.variants")
    expect(dialog).to_contain_text(
        "Dieses Blatt wurde auf einem anderen Gerät geändert. "
        "Wähle erst, welche Version gilt; dann druckt das PDF, was du hier siehst."
    )
    expect(dialog).not_to_contain_text("deine letzte Änderung")
    expect(dialog.get_by_role("button", name="PDF", exact=True)).to_be_disabled()


def clash_on_text(run, mine):
    """B saves the text `Vom Tool`; A types `mine` and its save is refused: the banner stands."""
    other = run.held("a")
    other["doc"]["pages"][0]["blocks"][0]["props"]["text"] = "Vom Tool"
    assert run.client.patch(f"/api/sheets/{run.ids['a']}", json=other).status_code == 200
    gate = run.gates["a"]
    type_text(run.page, mine)
    with run.page.expect_request(gate.asks("PATCH")):
        run.page.clock.run_for(2000)
    run.page.evaluate(TURNS)
    answer(run, "a")
    expect(run.page.locator(".clash")).to_be_visible()


def test_variants_print_shows_and_prints_the_other_version_after_the_choice(run):
    """#698: in the clash the dialog's PDF waits; after „Andere Version laden“ the preview and the
    PDF both hold `Vom Tool`, and not A's `Vom MCP`."""
    page, _ = start(run)
    clash_on_text(run, "Vom MCP")
    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    dialog = page.locator("dialog.variants")
    expect(dialog.get_by_role("button", name="PDF", exact=True)).to_be_disabled()
    expect(dialog.locator(".clash")).to_be_visible()
    dialog.get_by_role("button", name="Schließen").click()

    page.locator(".clash").get_by_role("button", name="Andere Version laden").click()
    expect(page.locator(".clash")).to_have_count(0)
    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    expect(dialog.locator(".preview")).to_contain_text("Vom Tool")
    with page.expect_download() as got:
        dialog.get_by_role("button", name="PDF", exact=True).click()
    text = "".join(p.extract_text() for p in pypdf.PdfReader(got.value.path()).pages)
    assert "Vom Tool" in text
    assert "Vom MCP" not in text


def test_pdf_line_goes_once_the_change_is_kept_as_a_new_sheet(run):
    """#699: the sheet was deleted elsewhere; „Als neues Blatt behalten“ takes the PDF line away."""
    page, _ = start(run)
    clash(run)
    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(1)

    assert run.client.delete(f"/api/sheets/{run.ids['a']}").status_code == 200
    page.locator(".clash").get_by_role("button", name="Andere Version laden").click()
    expect(page.locator(".clash")).to_contain_text("gelöscht")
    page.locator(".clash").get_by_role("button", name="Als neues Blatt behalten").click()
    expect(page.locator(ALERT, has_text=STALE)).to_have_count(0)


def test_pdf_after_loading_the_other_version_shows_no_line(run):
    """#699, beyond the brief: after the other version, a PDF with nothing unsaved says nothing."""
    page, _ = start(run)
    clash(run)
    page.locator(".clash").get_by_role("button", name="Andere Version laden").click()
    expect(page.locator(".clash")).to_have_count(0)
    with page.expect_download():
        pdf_button(page).click()
    expect(page.locator(ALERT)).to_have_count(0)


def test_variants_pdf_works_again_once_the_other_version_is_loaded(run):
    """#698, beyond the brief: after the choice the dialog prints again."""
    page, _ = start(run)
    clash(run)
    page.locator(".clash").get_by_role("button", name="Andere Version laden").click()
    expect(page.locator(".clash")).to_have_count(0)
    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    dialog = page.locator("dialog.variants")
    expect(dialog.get_by_role("button", name="PDF", exact=True)).to_be_enabled()
    with page.expect_download() as got:
        dialog.get_by_role("button", name="PDF", exact=True).click()
    assert pypdf.PdfReader(got.value.path()).pages
    expect(dialog.locator(".clash")).to_have_count(0)


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
