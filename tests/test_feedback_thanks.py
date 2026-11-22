"""#1155: a send that arrives puts a thank-you in the form's place, which nobody misses."""

# The fixture `window` is imported, and each test names it as its argument.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from test_signed_out import photographed, written

THANKS = "Danke! Ist angekommen."


def test_the_feedback_form_gives_way_to_a_thank_you_and_opens_empty_again(window, server):
    page, _ = window()
    page.goto(server)
    expect(page.get_by_role("heading", name="Meine Blätter")).to_be_visible(timeout=10000)
    written(page)
    form = page.locator("dialog.feedback")
    form.get_by_role("button", name="Abschicken").click()
    expect(form.get_by_role("status")).to_have_text(THANKS)
    expect(form.locator(".thanks .check")).to_be_visible()
    expect(form.locator("textarea")).to_have_count(0)
    close = form.get_by_role("button", name="Schließen")
    expect(close).to_be_focused()
    close.click()
    expect(page.locator("dialog")).to_have_count(0)
    page.get_by_role("button", name="Feedback").click()
    expect(form.locator("textarea")).to_have_value("")
    expect(form.locator("figure")).to_have_count(0)


def test_the_photo_page_gives_way_to_a_thank_you_and_then_to_an_empty_form(window, server):
    page, _ = window()
    page.goto(f"{server}/feedback/fotos")
    photographed(page)
    main = page.locator("main")
    main.get_by_role("button", name="Abschicken").click()
    expect(main.get_by_role("status")).to_have_text(THANKS)
    expect(main.locator(".thanks .check")).to_be_visible()
    expect(main.locator("form")).to_have_count(0)
    again = main.get_by_role("button", name="Noch eins schicken")
    expect(again).to_be_focused()
    again.click()
    expect(main.get_by_label("Was gefällt dir daran?")).to_have_value("")
    expect(main.get_by_label("Was ist das?")).to_have_value("")
    expect(main.locator("figure")).to_have_count(0)
