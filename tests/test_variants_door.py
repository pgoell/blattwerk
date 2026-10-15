"""The doors of "Varianten drucken": the bar's button beside PDF, its item under "Mehr" where the
bar has no room, and the panel Ansicht's button (#477).

The docstrings name the checklist lines: A is the drawing, I the editor's own ways of handling the
dialog. Wait with `expect`, never for a fixed time.
"""

import pytest
from playwright.sync_api import expect
from test_bar import expect_fitted, item, listed, more, sized, text, tool
from ui import box, hold_close, maths, user


def bar_button(page):
    return page.locator("header .top").get_by_label("Varianten drucken", exact=True)


def dialog(page):
    return page.locator("dialog.variants")


def test_the_desktop_bar_holds_the_variants_beside_pdf(editor):
    """A10: on a desktop the button stands in the bar; "Mehr" does not list it."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False, theme="")
    expect_fitted(page)
    expect(bar_button(page)).to_be_visible()
    if more(page).count():
        assert "Varianten drucken" not in listed(page)


def test_the_ipad_bar_folds_the_variants_under_mehr(editor):
    """A10: on an iPad "Mehr" lists the variants, and PDF and undo stay in the window."""
    page = sized(editor, text("a"), width=834, height=1194, touch=True, theme="")
    expect_fitted(page)
    expect(bar_button(page)).to_have_count(0)
    assert "Varianten drucken" in listed(page)


def test_the_desktop_bar_button_opens_the_dialog(editor):
    """A10: the bar's button opens the dialog."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False, theme="")
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()


def test_the_ipad_mehr_entry_opens_the_dialog(editor):
    """A10: on an iPad "Mehr" lists the variants, and its entry opens the dialog."""
    page = sized(editor, text("a"), width=834, height=1194, touch=True, theme="")
    expect_fitted(page)
    more(page).tap()
    item(page, "Varianten drucken").tap()
    expect(dialog(page)).to_be_visible()


def test_the_panel_button_still_opens_the_dialog(editor):
    """A11: the button in the panel Ansicht stays and opens the dialog."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True).click()
    expect(dialog(page)).to_be_visible()


def test_the_tour_names_the_variants_beside_the_pdf(editor):
    """A12: the tour's step on the PDF names "Varianten drucken"."""
    page = editor(text("a"), theme="")
    tool(page, "Rundgang").click()
    step = page.locator(".tour")
    for _ in range(20):
        if step.locator("h2").inner_text() == "Drucken":
            break
        count = step.locator("small").inner_text()
        step.locator(".primary").click()
        expect(step.locator("small")).not_to_have_text(count)
    expect(step.locator("h2")).to_have_text("Drucken")
    expect(step).to_contain_text("„Varianten drucken“")


@pytest.mark.parametrize("count", [1, 3], ids=["one", "three"])
def test_shift_tab_from_the_first_choice_stays_in_the_dialog(editor, count):
    """A13: Shift+Tab from the first row of choices stays in the dialog, whatever the count."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.get_by_role("tab", name="Ansicht").click()
    page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True).click()
    # Picked with the mouse, the checked choice has the focus: it is the group's one tab stop.
    dialog(page).get_by_role("radio", name=str(count), exact=True).check()
    page.keyboard.press("Shift+Tab")
    expect(page.locator("dialog.variants :focus")).to_have_count(1)


def test_escape_gives_the_focus_back_to_the_bar_button(editor):
    """I5: Escape shuts the dialog and the focus goes to the bar's button that opened it."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False, theme="")
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_escape_shuts_the_dialog_at_once_and_gives_the_focus_back(editor):
    """#641 for the variants: the page hears of no close, so Escape must shut the dialog itself."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False, theme="")
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    hold_close(page)
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_schliessen_shuts_the_dialog_at_once_and_gives_the_focus_back(editor):
    """The button Schließen shuts the dialog itself, as Escape does, with no close from the page."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False, theme="")
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    hold_close(page)
    dialog(page).get_by_role("button", name="Schließen").click()
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_escape_gives_the_focus_back_to_the_panel_button(editor):
    """I5: Escape shuts the dialog and the focus goes to the panel's button that opened it."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True)
    panel.click()
    expect(dialog(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(panel).to_be_focused()


def test_escape_gives_the_focus_back_to_mehr(editor):
    """I5: opened from "Mehr", the dialog gives the focus back to "Mehr"."""
    page = editor(text("a"), touch=True, theme="")
    expect_fitted(page)
    tool(page, "Varianten drucken").tap()
    expect(dialog(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(more(page)).to_be_focused()
