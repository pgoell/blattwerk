"""A click that leads to another page changes the address and the page in one step.

The router once drew a navigation in a transition, a task after the address had changed. An answer for
the page left that landed in between redrew it under the new address: the `flash` of test_loading.
"""

from playwright.sync_api import expect
from test_loading import SHEET, TEXT, hold, sheet, window  # noqa: F401
from ui import box


def test_the_page_swaps_in_the_same_step_as_the_address(window, server):  # noqa: F811
    """A click on a sheet changes the address and the page together: the list never stands under a
    sheet's address, where an answer that lands late could still redraw it (the `flash` above).
    """
    page, client = window()
    sheet(client, [box("a", "text", TEXT)])
    page.goto(server)
    expect(page.locator(".sheets a")).to_be_visible()
    hold(page, SHEET)
    path, bar = page.evaluate(
        """async () => {
            document.querySelector('.sheets a').click();
            // React draws what a click set in a microtask of the click's own task.
            await Promise.resolve();
            const drawn = [...document.querySelectorAll('#root > nav, #root > footer')];
            return [location.pathname, drawn.filter((el) => el.getClientRects().length).length];
        }"""
    )
    assert path.startswith("/blatt/")
    assert bar == 0
