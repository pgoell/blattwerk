"""The chooser of "Neues Blatt" on the sheet list, and a sheet made from a template there."""

from playwright.sync_api import expect

EMPTY = "Leeres Blatt"


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


def from_template(page, name):
    """Leaves the editor for the list, makes a sheet from the template of that name under
    "Neues Blatt", and waits until the editor stands with it. A template is picked nowhere else."""
    old = page.url
    page.goto(old.split("/blatt/")[0] + "/")
    new_sheet(page, name)
    page.wait_for_url(lambda url: "/blatt/" in url and url != old)
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()


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
