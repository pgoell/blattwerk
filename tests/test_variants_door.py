"""The door of the download window: the arrow beside the bar's "Herunterladen", which never folds
under "Mehr" (#477, #1186).

The docstrings name the checklist lines: A is the drawing, I the editor's own ways of handling the
dialog. Wait with `expect`, never for a fixed time.
"""

import pytest
from playwright.sync_api import expect
from test_bar import expect_fitted, listed, more, sized, text, tool
from ui import box, hold_close, maths, user


def bar_button(page):
    return page.locator("header .top").get_by_label("Weitere Formate und Optionen", exact=True)


def dialog(page):
    return page.locator("dialog.variants")


SIZES = pytest.mark.parametrize(
    ("width", "height", "touch"),
    [(1400, 1000, False), (834, 1194, True), (768, 1024, True)],
    ids=["desktop", "ipad", "small-ipad"],
)


@SIZES
def test_the_bar_holds_the_arrow_beside_herunterladen_at_every_size(editor, width, height, touch):
    """A10: the arrow stands in the bar on a desktop and on an iPad; "Mehr" does not list it."""
    page = sized(editor, text("a"), width=width, height=height, touch=touch)
    expect_fitted(page)
    expect(bar_button(page)).to_be_in_viewport(ratio=1)
    if more(page).count():
        names = listed(page)
        assert not {"Varianten drucken", "Als PowerPoint oder Word laden", "Lösungen zeigen"} & set(
            names
        )


@SIZES
def test_the_arrow_opens_the_window(editor, width, height, touch):
    """A10: the arrow opens the window, by a click and by a finger."""
    page = sized(editor, text("a"), width=width, height=height, touch=touch)
    expect_fitted(page)
    bar_button(page).tap() if touch else bar_button(page).click()
    expect(dialog(page)).to_be_visible()


def test_the_panel_ansicht_has_no_door_of_its_own(editor):
    """#1186: the bar's arrow is there at every size, so the panel Ansicht has no second button."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.get_by_role("tab", name="Ansicht").click()
    expect(page.locator(".panel").get_by_role("heading", name="Drucken")).to_have_count(0)
    expect(page.locator(".panel").get_by_text("Varianten drucken")).to_have_count(0)


def test_the_tour_names_the_variants_beside_the_pdf(editor):
    """A12: the tour's step on the download names the button and what its arrow opens."""
    page = editor(text("a"))
    tool(page, "Rundgang").click()
    step = page.locator(".tour")
    for _ in range(20):
        if step.locator("h2").inner_text() == "Drucken":
            break
        count = step.locator("small").inner_text()
        step.locator(".primary").click()
        expect(step.locator("small")).not_to_have_text(count)
    expect(step.locator("h2")).to_have_text("Drucken")
    expect(step).to_contain_text("„Herunterladen“")
    expect(step).to_contain_text("Varianten")
    expect(step).not_to_contain_text("„Varianten drucken“")


@pytest.mark.parametrize("count", [1, 3], ids=["one", "three"])
def test_shift_tab_from_the_first_choice_stays_in_the_dialog(editor, count):
    """A13: Shift+Tab from the first row of choices stays in the dialog, whatever the count."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.locator("header .top").get_by_label("Weitere Formate und Optionen", exact=True).click()
    # Picked with the mouse, the checked choice has the focus: it is the group's one tab stop.
    dialog(page).get_by_role("radio", name=str(count), exact=True).check()
    page.keyboard.press("Shift+Tab")
    expect(page.locator("dialog.variants :focus")).to_have_count(1)


def test_escape_gives_the_focus_back_to_the_bar_button(editor):
    """I5: Escape shuts the dialog and the focus goes to the bar's button that opened it."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False)
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_escape_shuts_the_dialog_at_once_and_gives_the_focus_back(editor):
    """#641 for the variants: the page hears of no close, so Escape must shut the dialog itself."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False)
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    hold_close(page)
    page.keyboard.press("Escape")
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_schliessen_shuts_the_dialog_at_once_and_gives_the_focus_back(editor):
    """The button Schließen shuts the dialog itself, as Escape does, with no close from the page."""
    page = sized(editor, text("a"), width=1400, height=1000, touch=False)
    expect_fitted(page)
    bar_button(page).click()
    expect(dialog(page)).to_be_visible()
    hold_close(page)
    dialog(page).get_by_role("button", name="Schließen").click()
    expect(dialog(page)).to_have_count(0)
    expect(bar_button(page)).to_be_focused()


def test_space_opens_the_dialog_when_the_focus_leaves_before_the_key_comes_up(editor):
    """#582: WebKit drops Space's click when the focus leaves the button before the key comes up.
    The key still opens the dialog, as it does after Escape has put the focus back."""
    client = user()
    page = editor(box("m", "maths", maths(client, count=12, max=100)), client=client)
    page.evaluate(
        """() => addEventListener("keydown", (e) => {
          if (e.code === "Space") document.activeElement?.blur();
        }, true)"""
    )
    button = page.locator("header .top").get_by_label("Weitere Formate und Optionen", exact=True)
    button.focus()
    page.keyboard.press("Space")
    expect(page.get_by_role("dialog")).to_be_visible()
