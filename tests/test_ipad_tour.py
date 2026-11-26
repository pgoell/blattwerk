"""The upright tour opens the drawer the step is about.

The iPad helpers live in test_ipad.py."""

from playwright.sync_api import expect
from test_ipad import (
    inside,
    text,
)
from ui import bar, expect_lit


def test_upright_the_tour_opens_the_drawer_its_step_is_about(editor):
    """I7"""
    page = editor(text("a", 1), touch=True)
    # After the fixture's own script, which keeps the tour shut: this account has not seen it.
    page.context.add_init_script("window.toured = false")
    page.reload()
    tour, ring = page.locator(".tour"), page.locator(".tour-ring")
    step = tour.locator("h2")
    expect(step).to_have_text("Willkommen bei Blattomat")
    expect(page.locator("aside")).to_have_count(0)

    def on(title):
        """Steps on until the tour is at this step."""
        for _ in range(15):
            if step.inner_text() == title:
                return
            before = tour.locator("small").inner_text()
            tour.locator(".primary").tap()
            expect(tour.locator("small")).not_to_have_text(before)
        raise AssertionError(f"no step {title}")

    def expect_ringed(panel):
        """Waits until the ring lies round the panel, which lies in the window."""
        expect(panel).to_be_visible()
        assert inside(page, panel)
        place = panel.bounding_box()
        page.wait_for_function(
            """([x, y]) => {
                const ring = document.querySelector(".tour-ring").getBoundingClientRect();
                return ring.width > 0 && Math.abs(ring.x - x) <= 4 && Math.abs(ring.y - y) <= 4;
            }""",
            arg=[place["x"], place["y"]],
        )
        assert inside(page, ring)

    expect(tour.locator("small")).to_have_text("Schritt 1 von 5")
    # The step's tool stands in the rail: Mathe, then Rechnen.
    on("Rechenaufgaben")
    expect(step.locator("..")).to_contain_text("Tippe links auf Mathe und dann auf Rechnen.")
    page.locator(".rail").get_by_label("Mathe", exact=True).tap()
    page.locator("dialog.library .lead").get_by_role("button", name="Rechnen").tap()
    # The block is there, so the tour goes on by itself, to the panel of what is picked.
    expect(step).to_have_text("Auswahl und Blatt")
    expect(page.locator(".panel .what")).to_contain_text("Rechnen")
    expect_ringed(page.locator("aside.panel"))
    expect_lit(bar(page, "right"), "true")
    # The bar has no room for the tour's own button: the last step says that "Mehr" holds it.
    on("Drucken")
    expect(page.locator("header").get_by_label("Rundgang", exact=True)).to_have_count(0)
    expect(tour.locator("p")).to_contain_text("Mehr")
    # Closed once, the account has seen it: it stays shut after a reload, with no word from the device.
    with page.expect_response("**/api/me/tour"):
        tour.locator(".primary").tap()
    expect(tour).to_have_count(0)
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    expect(tour).to_have_count(0)
