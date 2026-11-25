"""The download window: the arrow beside "Herunterladen" opens it, and its own button saves the file."""

from playwright.sync_api import expect

DOOR = "Weitere Formate und Optionen"


def door(page):
    """The bar's arrow beside "Herunterladen", which opens the window."""
    return page.locator("header .top").get_by_label(DOOR, exact=True)


def download_window(page):
    """Opens the window from the bar and gives it."""
    door(page).click()
    window = page.locator("dialog.variants")
    expect(window).to_be_visible()
    return window


def saver(window, answers=None):
    """The window's download button, after "Mit Lösungen" is set to `answers` where that is given."""
    if answers is not None:
        switch = window.get_by_role("switch", name="Mit Lösungen", exact=True)
        if (switch.get_attribute("aria-checked") == "true") != answers:
            switch.click()
        expect(switch).to_have_attribute("aria-checked", "true" if answers else "false")
    return window.get_by_role("button", name="Herunterladen", exact=True)


def variants(window, count):
    """Picks how many variants the PDF holds."""
    window.get_by_role("group", name="Varianten").get_by_label(str(count), exact=True).check()
