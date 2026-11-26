"""The editor's two side panels as the tests open and shut them: the pages at the left, the format
at the right. A wide window, a narrow one and the tablet held upright each have their own knobs."""

from contextlib import suppress

from playwright.sync_api import expect


def expect_lit(locator, on="true"):
    """Waits until the knob shows that it is on ("true") or off ("false")."""
    expect(locator).to_have_attribute("aria-pressed", on)


def bar(page, side):
    """The bar's button for the panel on that side: "left" for Seiten, "right" for Format."""
    return page.get_by_label({"left": "Seiten und Vorlagen", "right": "Format und Ansicht"}[side])


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
    """Shows the panel of pages. In a wide window it takes the place of the tools at the left:
    `shown=False` brings those back."""
    modes = page.locator("header .modes")
    if modes.count():
        tab = modes.get_by_role("tab", name="Vorlagen" if shown else "Start")
        tab.click()
        expect(tab).to_have_attribute("aria-selected", "true")
        return
    knob = bar(page, "left")
    if (knob.get_attribute("aria-pressed") == "true") != shown:
        knob.click()
    expect_lit(knob, "true" if shown else "false")
