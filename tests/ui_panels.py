"""The editor's two side panels as the tests open and shut them: the pages at the left, the format
at the right. A wide window, a narrow one and the tablet held upright each have their own knobs."""

from contextlib import suppress

from playwright.sync_api import expect


def expect_lit(locator, on="true"):
    """Waits until the knob shows that it is on ("true") or off ("false")."""
    expect(locator).to_have_attribute("aria-pressed", on)


def bar(page, side):
    """The bar's button for the panel on that side: "left" for Seiten, "right" for Auswahl."""
    names = {"left": "Seiten", "right": "Auswahl und Blatt"}
    return page.locator("header").get_by_label(names[side], exact=True)


def drawer(page, side):
    """Opens a panel on the iPad held upright, where both start shut. Format has come up by itself
    under a picked block (#1187)."""
    knob = bar(page, side)
    if side == "right" and page.locator(".block.sel").count():
        with suppress(AssertionError):
            expect(knob).to_have_attribute("aria-pressed", "true", timeout=500)
    if knob.get_attribute("aria-pressed") != "true":
        knob.tap()
    expect_lit(knob, "true")


def seiten(page, shown=True):
    """Shows the panel of pages. In a wide window it is a tab of the left panel, beside the tools:
    `shown=False` brings those back."""
    tabs = page.locator("aside.left [role=tablist]")
    if tabs.count():
        tab = tabs.get_by_role("tab", name="Seiten" if shown else "Blöcke")
        tab.click()
        expect(tab).to_have_attribute("aria-selected", "true")
        return
    knob = bar(page, "left")
    if (knob.get_attribute("aria-pressed") == "true") != shown:
        knob.click()
    expect_lit(knob, "true" if shown else "false")


def blatt(page, shown=True):
    """Turns the right panel to its tab "Blatt", which holds what goes for the whole sheet, or with
    `shown=False` back to "Auswahl"."""
    tab = page.locator(".panel").get_by_role("tab", name="Blatt" if shown else "Auswahl")
    tab.click()
    expect(tab).to_have_attribute("aria-selected", "true")


def raster(page):
    """Opens the list of the grid and the guide lines, beside the zoom, and gives it. A pick in
    it shuts it; "Nur diese Seite" and "Alle Seiten" leave it open."""
    knob = page.get_by_label("Raster und Hilfslinien", exact=True)
    if knob.count():
        knob.click()
    else:
        # A bar without room for it has it under "Mehr".
        page.get_by_label("Mehr", exact=True).click()
        page.get_by_role("menuitem", name="Raster und Hilfslinien").click()
    box = page.locator("dialog.raster")
    expect(box).to_be_visible()
    return box


def guide(page, axis="x", scope=None):
    """Adds a guide line from that list: `x` upright, `y` level. `scope` is "Nur diese Seite" or
    "Alle Seiten", pressed first; unnamed, the list's choice stays as it is."""
    box = raster(page)
    if scope:
        box.get_by_role("button", name=scope, exact=True).click()
    box.get_by_role("button", name="Senkrecht" if axis == "x" else "Waagerecht").click()
    expect(box).to_have_count(0)
