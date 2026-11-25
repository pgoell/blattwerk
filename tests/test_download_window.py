"""The download window: a preview left, the choices right, and the bar's two controls beside it (#1186)."""

from playwright.sync_api import expect
from test_pdf_stale import text_of
from ui import TEXT, at, box, maths, user
from ui_download import download_window, saver, variants


def sums(editor):
    client = user()
    return editor(box("m", "maths", maths(client, count=6), y=20, h=60), client=client)


def test_the_window_has_the_preview_left_and_every_choice_right(editor):
    page = editor(box("a", "text", TEXT))
    window = download_window(page)
    look, choices = (
        window.locator(".look").bounding_box(),
        window.locator(".choices").bounding_box(),
    )
    assert look["x"] + look["width"] <= choices["x"]

    right = window.locator(".choices")
    for group, count in (("Format", 3), ("Varianten", 4)):
        expect(right.get_by_role("group", name=group).get_by_role("radio")).to_have_count(count)
    for switch in ("Buchstabe auf jedem Blatt", "Mit Lösungen"):
        expect(right.get_by_role("switch", name=switch, exact=True)).to_be_visible()
    expect(right.get_by_label("Dateiname")).to_be_visible()
    expect(window.locator("button.primary")).to_have_count(1)
    expect(window.locator("button.primary")).to_have_text("Herunterladen")


def test_the_preview_follows_the_answers_the_count_and_the_letter(editor):
    page = sums(editor)
    window = download_window(page)
    preview = window.locator(".preview")
    plain = preview.inner_text()

    window.get_by_role("switch", name="Mit Lösungen", exact=True).click()
    expect(preview).to_have_attribute("data-solved", "true")
    expect(preview).not_to_have_text(plain)
    window.get_by_role("switch", name="Mit Lösungen", exact=True).click()
    expect(preview).to_have_text(plain)

    # One variant is the sheet itself: there is nothing to choose between.
    expect(window.get_by_role("group", name="Vorschau")).to_have_count(0)
    variants(window, 3)
    shown = window.get_by_role("group", name="Vorschau")
    expect(shown.get_by_role("radio")).to_have_count(3)
    shown.get_by_label("B", exact=True).check()
    expect(preview).to_have_attribute("data-variant", "B")
    expect(preview).not_to_have_text(plain)


def test_the_file_carries_the_name_the_teacher_typed(editor):
    page = editor(box("a", "text", TEXT))
    window = download_window(page)
    name = window.get_by_label("Dateiname")
    title = name.input_value()
    assert title
    window.get_by_role("switch", name="Mit Lösungen", exact=True).click()
    expect(name).to_have_value(f"{title} Lösungen")

    # One word: WebKit puts a `_` for a space in the name it suggests.
    name.fill("Montagstest")
    with page.expect_download() as got:
        saver(window).click()
    assert got.value.suggested_filename == "Montagstest.pdf"


def test_herunterladen_in_the_bar_saves_the_plain_pdf_at_once(editor):
    """One click, no window, and no answers even while the screen shows them."""
    page = sums(editor)
    show = page.locator("header .top").get_by_role("switch", name="Lösungen zeigen", exact=True)
    show.click()
    expect(show).to_be_checked()
    solved = at(page, "m").inner_text()

    with page.expect_request(lambda r: "/pdf" in r.url) as request, page.expect_download() as got:
        page.locator("header .pdf").get_by_role("button", name="Herunterladen", exact=True).click()
    assert "solved" not in request.value.url
    expect(page.locator("dialog.variants")).to_have_count(0)
    assert got.value.suggested_filename.endswith(".pdf")
    assert "Lösungen" not in got.value.suggested_filename
    assert text_of(got.value) != solved


def test_loesungen_zeigen_is_one_switch_and_the_eye_and_the_second_button_are_gone(editor):
    page = sums(editor)
    bar = page.locator("header .top")
    show = bar.get_by_role("switch", name="Lösungen zeigen", exact=True)
    expect(show).to_be_visible()
    expect(bar.get_by_role("button", name="Lösungen zeigen", exact=True)).to_have_count(0)
    expect(bar.get_by_role("button", name="Lösungen", exact=True)).to_have_count(0)
    expect(bar.get_by_role("button", name="PDF", exact=True)).to_have_count(0)

    plain = at(page, "m").inner_text()
    show.click()
    expect(at(page, "m")).not_to_have_text(plain)
    show.click()
    expect(at(page, "m")).to_have_text(plain)


def test_undo_and_redo_say_their_names_under_the_mouse(editor):
    page = editor(box("a", "text", TEXT))
    for name in ("Rückgängig", "Wiederholen"):
        tool = page.locator("header .top").get_by_label(name, exact=True)
        tool.hover(force=True)
        shown = tool.evaluate("el => getComputedStyle(el, '::after').content")
        assert shown == f'"{name}"'


def test_no_command_folds_under_mehr_at_1280(editor):
    """Both looks of the editor: the bar holds every command, the answers' switch and the download."""
    for theme in (None, ""):
        page = editor(box("a", "text", TEXT), theme=theme)
        page.set_viewport_size({"width": 1280, "height": 800})
        bar = page.locator("header .top")
        expect(bar.get_by_label("Feedback", exact=True)).to_be_visible()
        expect(bar.get_by_label("Mehr", exact=True)).to_have_count(0)
        expect(bar.get_by_role("switch", name="Lösungen zeigen", exact=True)).to_be_visible()
        expect(bar.get_by_label("Herunterladen", exact=True)).to_be_visible()
        page.context.close()
