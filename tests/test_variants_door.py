"""The doors of "Varianten drucken": the bar's button beside PDF, its item under "Mehr" where the
bar has no room, and the panel Ansicht's button (#477).

The docstrings name the checklist lines: A is the drawing, I the editor's own ways of handling the
dialog. Wait with `expect`, never for a fixed time.
"""

import pytest
from playwright.sync_api import expect
from test_bar import expect_fitted, listed, more, sized, text, tool
from ui import box, maths, user

WINDOWS = pytest.mark.parametrize(
    ("width", "height", "touch"),
    [(1400, 1000, False), (834, 1194, True)],
    ids=["desktop", "ipad"],
)


def bar_button(page):
    return page.locator("header .top").get_by_label("Varianten drucken", exact=True)


def dialog(page):
    return page.locator("dialog.variants")


@WINDOWS
def test_the_variants_stand_in_the_bar_or_under_mehr(editor, width, height, touch):
    """A10: the button stands in the bar where there is room, else under "Mehr"; PDF stays."""
    page = sized(editor, text("a"), width=width, height=height, touch=touch, theme="")
    expect_fitted(page)
    assert bar_button(page).count() + listed(page).count("Varianten drucken") == 1


@WINDOWS
def test_the_door_in_the_bar_or_mehr_opens_the_dialog(editor, width, height, touch):
    """A10: the bar's button, or its item under "Mehr", opens the dialog."""
    page = sized(editor, text("a"), width=width, height=height, touch=touch, theme="")
    expect_fitted(page)
    if bar_button(page).count():
        bar_button(page).click()
    else:
        tool(page, "Varianten drucken").tap() if touch else tool(page, "Varianten drucken").click()
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
        step.locator("button.primary").click()
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
