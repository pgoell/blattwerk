"""Print variants: the dialog "Varianten drucken" prints the sheet once per variant and shows them
in a preview. Nothing it does is stored: no save, no undo step, nothing in the browser storage.

The docstrings name the checklist lines: A is the drawing, I the editor's own ways of handling the
dialog. Wait with `expect`, never for a fixed time.
"""

import io
import re

from playwright.sync_api import expect
from pypdf import PdfReader
from ui import TEXT, at, box, doc, maths, pick, tool, user

SUCHSEL = {
    "words": ["BLUMEN", "KERZEN", "GARTEN", "SONNEN", "WASSER", "MONDEN"],
    "cols": 6,
    "rows": 6,
    "ways": "across",
    "caps": True,
    "umlauts": False,
    "show": "words",
    "seed": 3,
}
TASK = re.compile(r"\d+\s*\+\s*\d+")


SEARCH = {
    "words": ["Hund", "Katze", "Maus", "Igel"],
    "cols": 10,
    "rows": 10,
    "ways": "down",
    "caps": True,
    "umlauts": True,
    "show": "words",
    "seed": 5,
}
MIXED = {**TEXT, "text": "Der Hund bellt laut im Garten", "mix": 7}
BOXED = {
    **TEXT,
    "text": "Der Hund bellt laut im Garten",
    "bank": 3,
    "rich": [
        {
            "runs": [
                {"text": "Der "},
                {"text": "Hund", "gap": True},
                {"text": " bellt "},
                {"text": "laut", "gap": True},
                {"text": " im "},
                {"text": "Garten", "gap": True},
            ]
        }
    ],
}
# The grid's letters, row by row, as the preview draws them.
GRID = """els => {
    const rows = {};
    for (const el of els) {
        const [c, r] = el.dataset.at.split(",").map(Number);
        (rows[r] ??= []).push([c, el.textContent]);
    }
    return Object.keys(rows).map(Number).sort((a, b) => a - b)
        .flatMap((r) => rows[r].sort((a, b) => a[0] - b[0]).map(([, letter]) => letter)).join("");
}"""


def in_order(text, words):
    """Each word stands in the text, after the one before it."""
    at = 0
    for word in words:
        at = text.find(word, at)
        assert at >= 0, word
        at += len(word)


def opener(page):
    # The panel's button; the bar has one of the same name on a wide window.
    return page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True)


def open_dialog(page):
    """The button stands in the panel Ansicht, which the bar's "Ansicht" opens."""
    if not opener(page).is_visible():
        page.get_by_role("tab", name="Ansicht").click()
    opener(page).click()
    expect(page.get_by_role("dialog")).to_be_visible()


def press(page, name):
    page.get_by_role("dialog").get_by_role("button", name=name, exact=True).click()


def pages_text(data):
    return [p.extract_text() for p in PdfReader(io.BytesIO(data)).pages]


def download_pdf(page, name="PDF"):
    with page.expect_download() as got:
        press(page, name)
    return open(got.value.path(), "rb").read()


def test_the_dialog_offers_one_to_four_variants_and_the_pdf_holds_them_all(editor):
    """A1: four choices, 2 picked at first; three picked, the PDF has three pages."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    open_dialog(page)
    for n in ("1", "2", "3", "4"):
        expect(page.get_by_role("radio", name=n, exact=True)).to_have_count(1)
    expect(page.get_by_role("radio", name="2", exact=True)).to_be_checked()
    page.get_by_role("radio", name="3", exact=True).check()
    data = download_pdf(page)
    assert len(PdfReader(io.BytesIO(data)).pages) == 3


def test_variant_a_is_the_sheet_as_it_stands_a_waiting_change_is_saved_first(editor):
    """A2: a word typed just before the press is on page 1 of the PDF."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Neu")
    expect(page.locator(".block.sel .ProseMirror")).to_have_text("Neu")
    open_dialog(page)
    data = download_pdf(page)
    assert "Neu" in pages_text(data)[0]


def test_the_switch_hides_the_letter_on_the_sheets(editor):
    """A5: with the switch off no page has the letter on a line of its own; with it on they do."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    open_dialog(page)
    page.get_by_role("checkbox", name="Buchstabe auf jedem Blatt").uncheck()
    off = pages_text(download_pdf(page))
    assert not any(line.strip() == "B" for text in off for line in text.splitlines())
    page.get_by_role("checkbox", name="Buchstabe auf jedem Blatt").check()
    on = pages_text(download_pdf(page))
    assert any(line.strip() == "B" for text in on for line in text.splitlines())


def test_a_suchsel_a_variant_cannot_fill_is_named_and_nothing_prints(editor):
    """A7: a word search that B leaves a word out of is named; PDF starts no request."""
    client = user()
    page = editor(box("s", "suchsel", SUCHSEL), client=client)
    real = []

    def more_words(route):
        answer = route.fetch().json()
        for block in answer["doc"]["pages"][0]["blocks"]:
            if block["type"] == "suchsel":
                block["props"]["words"] = [*block["props"]["words"], "ANKERN"]
        route.fulfill(json=answer)

    page.route("**/api/sheets/*/variante/B", more_words)
    open_dialog(page)
    expect(page.get_by_role("alert")).to_have_text(
        "Variante B: Der Suchsel-Block auf Seite 1 lässt sich nicht neu füllen. "
        "Würfle ihn neu, lockere die Vorgaben oder drucke weniger Varianten."
    )
    page.on("request", lambda r: real.append(r.url) if "/pdf" in r.url else None)
    press(page, "PDF")
    expect(page.get_by_role("alert")).to_be_visible()
    assert real == []


def test_a_rechnen_block_a_variant_cannot_fill_is_named_and_nothing_prints(editor):
    """A7: a Rechnen block B cannot fill is named from the server's answer; PDF sends no request."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    real = []

    def short(route):
        answer = route.fetch().json()
        answer["short"] = [{"page": 1, "id": "m", "type": "maths"}]
        route.fulfill(json=answer)

    page.route("**/api/sheets/*/variante/B", short)
    open_dialog(page)
    expect(page.get_by_role("alert")).to_have_text(
        "Variante B: Der Rechnen-Block auf Seite 1 lässt sich nicht neu füllen. "
        "Würfle ihn neu, lockere die Vorgaben oder drucke weniger Varianten."
    )
    page.on("request", lambda r: real.append(r.url) if "/pdf" in r.url else None)
    press(page, "Lösungen")
    expect(page.get_by_role("alert")).to_be_visible()
    assert real == []


def test_the_preview_shows_the_tasks_the_pdf_prints(editor):
    """A8: the tasks of B in the preview are the tasks page 2 of the PDF holds, and not A's."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    open_dialog(page)
    page.get_by_role("radio", name="B", exact=True).check()
    expect(page.locator('.preview[data-variant="B"]')).to_be_visible()
    shown = TASK.findall(re.sub(r"\s+", " ", page.locator(".preview").inner_text()))
    printed = TASK.findall(pages_text(download_pdf(page))[1])
    assert shown and [re.sub(r"\s", "", t) for t in shown] == [
        re.sub(r"\s", "", t) for t in printed
    ]
    page.get_by_role("button", name="Schließen").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    own = TASK.findall(at(page, "m").inner_text())
    assert [re.sub(r"\s", "", t) for t in own] != [re.sub(r"\s", "", t) for t in shown]


def test_printing_and_previewing_change_nothing_and_leave_no_undo_step(editor):
    """A9: the stored sheet, its undo step and the browser's storage are as they were."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    before = doc(page, client)
    keys = page.evaluate("Object.keys(localStorage)")
    writes = []
    page.on("request", lambda r: writes.append(r.url) if r.method in ("PUT", "PATCH") else None)
    open_dialog(page)
    page.get_by_role("radio", name="4", exact=True).check()
    page.get_by_role("radio", name="D", exact=True).check()
    download_pdf(page)
    download_pdf(page, "Lösungen")
    page.get_by_role("button", name="Schließen").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    assert doc(page, client) == before
    assert writes == []
    expect(tool(page, "Rückgängig")).to_be_disabled()
    assert page.evaluate("Object.keys(localStorage)") == keys


def test_escape_and_schliessen_shut_the_dialog_and_give_the_focus_back(editor):
    """I1: Escape and Schließen both close it, with no download, and Varianten has the focus."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    downloads = []
    page.on("download", lambda d: downloads.append(d))
    open_dialog(page)
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(opener(page)).to_be_focused()
    open_dialog(page)
    page.get_by_role("button", name="Schließen").click()
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(opener(page)).to_be_focused()
    assert downloads == []


def test_keys_in_the_dialog_do_not_reach_the_sheet(editor):
    """I2: Delete, Backspace and a letter in the dialog leave the block; Tab stays in the dialog."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    open_dialog(page)
    for key in ("Delete", "Backspace", "x"):
        page.keyboard.press(key)
    for _ in range(12):
        page.keyboard.press("Tab")
        assert page.evaluate("!!document.activeElement.closest('dialog')")
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(at(page, "a")).to_contain_text("Hallo")


def test_the_varianten_button_opens_with_enter_and_space(editor):
    """I3: Enter and Space open the dialog from the button in the panel Ansicht, the last stop of
    the panel's tab order. The bar keeps its two buttons: it has no room for a third on an iPad."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    assert page.locator(".pdf button").all_inner_texts() == ["Lösungen", "PDF"]
    page.get_by_role("tab", name="Ansicht").click()
    button = opener(page)
    assert page.locator(".panel button").last.inner_text().strip() == "Varianten drucken"
    button.focus()
    page.keyboard.press("Enter")
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).to_have_count(0)
    expect(button).to_be_focused()
    page.keyboard.press("Space")
    expect(page.get_by_role("dialog")).to_be_visible()


def test_the_dialog_keeps_its_choice_while_the_editor_is_open(editor):
    """I4: the count and the switch are as picked when the dialog opens again."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    open_dialog(page)
    page.get_by_role("radio", name="4", exact=True).check()
    page.get_by_role("checkbox", name="Buchstabe auf jedem Blatt").uncheck()
    page.get_by_role("button", name="Schließen").click()
    open_dialog(page)
    expect(page.get_by_role("radio", name="4", exact=True)).to_be_checked()
    expect(page.get_by_role("checkbox", name="Buchstabe auf jedem Blatt")).not_to_be_checked()


def test_the_preview_follows_the_count(editor):
    """I5: preview D, then count 2: the preview shows B and the choices C and D are gone."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    open_dialog(page)
    page.get_by_role("radio", name="4", exact=True).check()
    page.get_by_role("radio", name="D", exact=True).check()
    expect(page.locator('.preview[data-variant="D"]')).to_be_visible()
    page.get_by_role("radio", name="2", exact=True).check()
    expect(page.locator('.preview[data-variant="B"]')).to_be_visible()
    expect(page.get_by_role("radio", name="B", exact=True)).to_be_checked()
    expect(page.get_by_role("radio", name="C", exact=True)).to_have_count(0)
    expect(page.get_by_role("radio", name="D", exact=True)).to_have_count(0)


def test_the_preview_shows_the_grid_and_the_words_the_pdf_prints(editor):
    """A8: the grid and the words of B in the preview are those that page 2 prints."""
    client = user()
    page = editor(
        box("s", "suchsel", SEARCH, x=15, y=20, w=90, h=90),
        box("m", "text", MIXED, x=15, y=130, w=180, h=40),
        box("b", "text", BOXED, x=15, y=190, w=180, h=60),
        client=client,
    )
    open_dialog(page)
    page.get_by_role("radio", name="B", exact=True).check()
    expect(page.locator('.preview[data-variant="B"]')).to_be_visible()
    grid_b = page.locator(".preview text[data-at]").evaluate_all(GRID)
    mixed = [re.sub(r"\s", "", w) for w in page.locator(".preview .mix .mixed").all_text_contents()]
    bank = page.locator(".preview .bank span").all_text_contents()
    assert len(grid_b) == 100 and len(mixed) == 6 and len(bank) == 3

    page.get_by_role("radio", name="A", exact=True).check()
    expect(page.locator('.preview[data-variant="A"]')).to_be_visible()
    assert page.locator(".preview text[data-at]").evaluate_all(GRID) != grid_b

    printed = re.sub(r"\s", "", pages_text(download_pdf(page))[1])
    assert grid_b in printed
    in_order(printed, mixed)
    in_order(printed, bank)


def test_a_failed_pdf_leaves_the_dialog_open_and_says_so(editor):
    """I6: a failed PDF says so and the dialog stays with its count; a second press downloads."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.route("**/api/sheets/*/pdf*", lambda r: r.abort())
    open_dialog(page)
    page.get_by_role("radio", name="3", exact=True).check()
    press(page, "PDF")
    expect(page.get_by_role("alert")).to_have_text("Das PDF konnte nicht erstellt werden.")
    expect(page.get_by_role("dialog")).to_be_visible()
    expect(page.get_by_role("radio", name="3", exact=True)).to_be_checked()
    page.unroute("**/api/sheets/*/pdf*")
    data = download_pdf(page)
    assert len(PdfReader(io.BytesIO(data)).pages) == 3


LOADING = "Die Varianten konnten nicht geladen werden."


def test_a_second_try_after_a_failed_load_shows_the_variants_and_names_a_short_block(editor):
    """I6/B2: after a failed load, a second try shows the variants and names the short block."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.route("**/api/sheets/*/variante/*", lambda r: r.abort())
    open_dialog(page)
    expect(page.get_by_role("alert")).to_have_text(LOADING)
    page.unroute("**/api/sheets/*/variante/*")

    def short(route):
        answer = route.fetch().json()
        answer["short"] = [{"page": 1, "id": "m", "type": "maths"}]
        route.fulfill(json=answer)

    page.route("**/api/sheets/*/variante/B", short)
    real = []
    page.on("request", lambda r: real.append(r.url) if "/pdf" in r.url else None)
    press(page, "PDF")
    expect(page.get_by_role("alert")).to_have_text(
        "Variante B: Der Rechnen-Block auf Seite 1 lässt sich nicht neu füllen. "
        "Würfle ihn neu, lockere die Vorgaben oder drucke weniger Varianten."
    )
    assert real == []
    page.get_by_role("radio", name="B", exact=True).check()
    expect(page.locator('.preview[data-variant="B"] .paper')).to_be_visible()
    expect(page.locator('.preview[data-variant="B"]')).not_to_contain_text("Lädt")


def test_a_second_try_after_a_failed_load_prints_and_shows_the_variants(editor):
    """I6/B2: a second try after a failed load prints both variants; a failed one says so again."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.route("**/api/sheets/*/variante/*", lambda r: r.abort())
    open_dialog(page)
    expect(page.get_by_role("alert")).to_have_text(LOADING)
    press(page, "PDF")
    # The alert's line stood before the press, so it says nothing of the press's end. A press still out at the unroute
    # loads the variants after all and builds a PDF, the button disabled meanwhile (#785): wait for the press to fail.
    expect(page.get_by_role("dialog").get_by_role("button", name="PDF", exact=True)).to_be_enabled()
    expect(page.get_by_role("alert")).to_have_text(LOADING)
    page.unroute("**/api/sheets/*/variante/*")
    data = download_pdf(page)
    assert len(PdfReader(io.BytesIO(data)).pages) == 2
    page.get_by_role("radio", name="B", exact=True).check()
    expect(page.locator('.preview[data-variant="B"] .paper')).to_be_visible()
    expect(page.locator('.preview[data-variant="B"]')).not_to_contain_text("Lädt")
