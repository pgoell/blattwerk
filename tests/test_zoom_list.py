"""The percent button opens a list of zooms and a field to type one, as PowerPoint's zoom dialog."""

import pytest
from playwright.sync_api import expect
from test_bar import resize
from test_zoom import expect_percent, expect_width, fit, page_width, percent, wheel, width
from ui import TEXT, box, pick

LIST = "dialog:modal"
FIELD = "Zoom in Prozent"


def open_list(page):
    page.locator("button.zoom").first.click()
    expect(page.locator(LIST)).to_be_visible()


def field(page):
    return page.get_by_label(FIELD, exact=True)


def type_percent(page, text):
    field(page).fill(text)
    field(page).press("Enter")


def test_the_button_opens_the_list_with_the_current_percent(editor):
    """Z1"""
    page = editor(box("a", "text", TEXT))
    open_list(page)
    for name in ("50 %", "75 %", "100 %", "150 %", "200 %", "Seitenbreite", "Ganze Seite"):
        expect(page.locator(LIST).get_by_role("menuitem", name=name, exact=True)).to_be_visible()
    expect(field(page)).to_have_value(str(percent(page)))
    # Picked whole: a typed value replaces the old one.
    page.keyboard.type("120")
    expect(field(page)).to_have_value("120")


def test_a_pick_sets_the_percent_and_shuts_the_list(editor):
    """Z2"""
    page = editor(box("a", "text", TEXT))
    start = percent(page)
    open_list(page)
    page.locator(LIST).get_by_role("menuitem", name="150 %", exact=True).click()
    expect(page.locator(LIST)).to_have_count(0)
    expect(page.locator("button.zoom").first).to_have_text("150 %")
    expect_percent(page)
    # The list gives the page's width back.
    open_list(page)
    page.locator(LIST).get_by_role("menuitem", name="Seitenbreite", exact=True).click()
    expect_percent(page)
    expect(page.locator("button.zoom").first).to_have_text(f"{start} %")
    # Ganze Seite is the fit button's.
    open_list(page)
    page.locator(LIST).get_by_role("menuitem", name="Ganze Seite", exact=True).click()
    expect(page.locator(LIST)).to_have_count(0)
    expect_percent(page)
    fit(page).click()
    expect_percent(page)


@pytest.mark.parametrize("entry", ["150", "150 %", "150%", "150.0"])
def test_a_typed_percent_sets_the_zoom(editor, entry):
    """Z3"""
    page = editor(box("a", "text", TEXT))
    open_list(page)
    type_percent(page, entry)
    expect(page.locator(LIST)).to_have_count(0)
    expect(page.locator("button.zoom").first).to_have_text("150 %")
    expect_percent(page)


def test_a_typed_decimal_comma_sets_the_zoom(editor):
    """Z3"""
    page = editor(box("a", "text", TEXT))
    open_list(page)
    type_percent(page, "75,5")
    expect(page.locator(LIST)).to_have_count(0)
    assert percent(page) == pytest.approx(75.5, abs=1)
    expect_percent(page)


def test_a_typed_percent_beyond_the_limits_gives_the_limit(editor):
    """Z4"""
    page = editor(box("a", "text", TEXT))
    page_width(page)
    wide = width(page)
    open_list(page)
    type_percent(page, "5")
    expect_width(page, wide * 0.25)
    open_list(page)
    type_percent(page, "2000")
    expect_width(page, wide * 4)


def test_escape_shuts_the_list_and_changes_nothing(editor):
    """Z5"""
    page = editor(box("a", "text", TEXT))
    page_width(page)
    open_list(page)
    type_percent(page, "150")
    wide = width(page)
    shown = page.locator("button.zoom").first.inner_text()
    open_list(page)
    field(page).fill("300")
    page.keyboard.press("Escape")
    expect(page.locator(LIST)).to_have_count(0)
    expect(page.locator("button.zoom").first).to_have_text(shown)
    assert width(page) == pytest.approx(wide, abs=1)


@pytest.mark.parametrize("entry", ["abc", "", "0", "-5"])
def test_a_wrong_entry_changes_nothing_and_keeps_the_list(editor, entry):
    """Z6"""
    page = editor(box("a", "text", TEXT))
    page_width(page)
    wide = width(page)
    open_list(page)
    field(page).fill(entry)
    field(page).press("Enter")
    expect(page.locator(LIST)).to_be_visible()
    expect(field(page)).to_have_value(str(percent(page)))
    assert width(page) == pytest.approx(wide, abs=1)
    # Picked whole again: the next entry replaces the 100.
    page.keyboard.type("120")
    page.keyboard.press("Enter")
    expect(page.locator("button.zoom").first).to_have_text("120 %")


def test_a_block_is_deleted_after_the_list_shuts(editor):
    """Z7"""
    page = editor(box("a", "text", TEXT))
    open_list(page)
    page.locator(LIST).get_by_role("menuitem", name="150 %", exact=True).click()
    pick(page, "a")
    open_list(page)
    page.keyboard.press("Escape")
    # WebKit shuts the dialog a moment after the key.
    expect(page.locator(LIST)).to_have_count(0)
    page.keyboard.press("Delete")
    expect(page.locator(".block[data-id]")).to_have_count(0)


def test_undo_does_not_take_back_a_pick(editor):
    """Z9"""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Delete")
    expect(page.locator(".block[data-id]")).to_have_count(0)
    open_list(page)
    page.locator(LIST).get_by_role("menuitem", name="150 %", exact=True).click()
    expect(page.locator("button.zoom").first).to_have_text("150 %")
    # The undo takes back the delete, and the zoom stays.
    page.keyboard.press("Control+z")
    expect(page.locator(".block[data-id]")).to_have_count(1)
    expect(page.locator("button.zoom").first).to_have_text("150 %")


def test_a_press_beside_the_list_shuts_it(editor):
    """Z extra: a teacher clicks away from the list."""
    page = editor(box("a", "text", TEXT))
    page_width(page)
    wide = width(page)
    open_list(page)
    page.mouse.click(5, 5)
    expect(page.locator(LIST)).to_have_count(0)
    assert width(page) == pytest.approx(wide, abs=1)


def test_the_list_shows_the_percent_a_wheel_set(editor):
    """Z extra: the field follows the zoom the wheel made."""
    page = editor(box("a", "text", TEXT))
    wheel(page, -100)
    open_list(page)
    expect(field(page)).to_have_value(str(percent(page)))


def test_blattform_opens_the_list_upward_from_the_dock(editor):
    """Z8"""
    page = editor(box("a", "text", TEXT), theme=None)
    resize(page, 1200, 800)
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    expect(page.locator("main.editor.leaf")).to_have_count(1)
    button = page.locator(".dock button.zoom").first
    button.click()
    expect(page.locator(LIST)).to_be_visible()
    lens = page.locator(LIST).bounding_box()
    assert lens["y"] + lens["height"] <= button.bounding_box()["y"] + 1
    page.locator(LIST).get_by_role("menuitem", name="50 %", exact=True).click()
    expect(page.locator(".dock button.zoom").first).to_have_text("50 %")
