"""The feedback form shuts at once on Escape, and its button opens it again at once (#641)."""

from playwright.sync_api import expect
from ui import TEXT, box, hold_close

FORM = "dialog.feedback"


def button(page):
    return page.get_by_label("Feedback", exact=True)


def test_escape_shuts_the_feedback_form_at_once(editor):
    """The page hears of no close, so Escape must shut the form itself."""
    page = editor(box("a", "text", TEXT))
    button(page).click()
    expect(page.locator(FORM)).to_be_visible()
    hold_close(page)
    page.keyboard.press("Escape")
    expect(page.locator(FORM)).to_have_count(0)


def test_escape_then_the_feedback_button_at_once_opens_the_form_again(editor):
    page = editor(box("a", "text", TEXT))
    button(page).click()
    expect(page.locator(FORM)).to_be_visible()
    hold_close(page)
    page.keyboard.press("Escape")
    button(page).click()
    expect(page.locator(FORM)).to_be_visible()
