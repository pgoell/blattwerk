"""The chooser of "Neues Blatt" on the sheet list, and the question before a template replaces a sheet."""

from playwright.sync_api import expect

EMPTY = "Leeres Blatt"
REPLACE = "Blatt ersetzen"


def chooser(page):
    """Opens the chooser from the list's button and gives it."""
    page.get_by_role("button", name="Neues Blatt", exact=True).click()
    window = page.locator("dialog.chooser")
    expect(window).to_be_visible()
    return window


def card(window, name=EMPTY):
    return window.get_by_role("button", name=name, exact=True)


def new_sheet(page, name=EMPTY):
    """Makes a sheet from the chooser's card of that name: the empty sheet, or a template."""
    card(chooser(page), name).click()


def apply_template(page, name):
    """Clicks a template in the editor's panel, and says yes where the sheet holds something."""
    held = page.locator(".block[data-id]").count() > 0
    page.locator(".tpl button", has_text=name).click()
    if held:
        page.locator("dialog.confirm").get_by_role("button", name=REPLACE, exact=True).click()
    expect(page.locator("dialog.confirm")).to_have_count(0)


def more(page, title, item):
    """Picks an entry of a row's menu on the sheet list: "Umbenennen", "In den Schulordner", "Löschen"."""
    page.get_by_role("button", name=f"{title}: weitere Aktionen", exact=True).click()
    page.locator("dialog.menu").get_by_role("menuitem", name=item, exact=True).click()


def delete_sheet(page, title):
    """Deletes a sheet from the list and says yes to the app's question."""
    more(page, title, "Löschen")
    question = page.locator("dialog.confirm")
    expect(question.get_by_role("heading")).to_have_text(f"Blatt „{title}“ löschen?")
    question.get_by_role("button", name="Blatt löschen", exact=True).click()
