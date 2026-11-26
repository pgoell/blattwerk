"""The button "Neues Blatt" keeps the focus when the list comes late and draws it in another place."""

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from ui_new import chooser


def late_list(window, server):  # noqa: F811
    """The list's page with the answer for its sheets held back, and what lets the answer go."""
    page, _ = window()
    held = []
    page.route("**/api/sheets", lambda route: held.append(route))
    page.goto(server)
    button = page.get_by_role("button", name="Neues Blatt", exact=True)
    expect(button).to_be_visible()

    def come():
        # The page asks for its sheets once it is drawn: up to 5 s for that.
        for _ in range(50):
            if held:
                break
            page.wait_for_timeout(100)
        assert held
        for route in held:
            route.continue_()
        expect(page.locator(".empty")).to_be_visible()

    return page, button, come


def test_the_button_keeps_the_focus_when_the_list_comes(window, server):  # noqa: F811
    _page, button, come = late_list(window, server)
    button.focus()
    come()
    expect(button).to_be_focused()


def test_escape_gives_the_focus_to_the_button_that_stands_now(window, server):  # noqa: F811
    page, button, come = late_list(window, server)
    shelf = chooser(page)
    come()
    page.keyboard.press("Escape")
    expect(shelf).to_have_count(0)
    expect(button).to_be_focused()
