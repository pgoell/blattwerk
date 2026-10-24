"""The upright tour opens the drawer the step is about.

The iPad helpers live in test_ipad.py."""

from playwright.sync_api import expect
from test_ipad import (
    inside,
    text,
)
from ui import bar


def test_upright_the_tour_opens_the_drawer_its_step_is_about(editor):
    """I7"""
    page = editor(text("a", 1), touch=True)
    # After the fixture's own script, which says the tour was seen.
    page.context.add_init_script("localStorage.removeItem('tour')")
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

    on("Format")
    expect_ringed(page.locator("aside.panel"))
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")
    # The next step's tool stands in the dock, which lies over the open drawer.
    on("Rechenaufgaben")
    page.locator(".dock").get_by_label("Rechnen", exact=True).tap()
    expect(step).to_have_text("Aufgaben einstellen")
    expect(page.locator(".panel .what")).to_contain_text("Rechnen")
    on("Seiten und Vorlagen")
    expect_ringed(page.locator("aside.left"))
    expect(page.locator("aside.panel")).to_have_count(0)
    # The bar has no room for the tour's own button: the last step is about "Mehr", which holds it.
    on("Das war's")
    expect(page.locator("header").get_by_label("Rundgang", exact=True)).to_have_count(0)
    expect_ringed(page.get_by_label("Mehr", exact=True))
    expect(tour.locator("p")).to_contain_text("Mehr")
