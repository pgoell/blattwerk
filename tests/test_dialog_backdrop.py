"""A click on the backdrop shuts every showModal() dialog, through one shared hook (#1083)."""

# ruff: noqa: F811

from playwright.sync_api import expect
from test_account_tokens import account, make  # noqa: F401
from test_bar import item, more, sized
from test_loading import window  # noqa: F401
from test_variants import open_dialog
from test_variants import opener as variants_opener
from ui import TEXT, block, box, pick, reload, sheet, user

CONNECTION = {"id": 7, "name": "Claude", "created": "2026-10-06 09:30:00", "last_used": None}


def check_backdrop(page, dialog, opener, text, reopen):
    """Inside the box and drags across its edge keep it open. A right click does too. A click on the backdrop shuts it,
    the focus goes back, and Escape shuts it after a reopen."""
    expect(dialog).to_be_visible()
    text.click()
    expect(dialog).to_be_visible()
    at = text.bounding_box()
    inside = (at["x"] + 2, at["y"] + 2)
    page.mouse.move(*inside)
    page.mouse.down()
    page.mouse.move(4, 4)
    page.mouse.up()
    expect(dialog).to_be_visible()
    page.mouse.move(4, 4)
    page.mouse.down()
    page.mouse.move(*inside)
    page.mouse.up()
    expect(dialog).to_be_visible()
    page.mouse.click(4, 4, button="right")
    expect(dialog).to_be_visible()
    page.mouse.click(4, 4)
    expect(dialog).not_to_be_visible()
    expect(opener).to_be_focused()
    reopen()
    expect(dialog).to_be_visible()
    page.keyboard.press("Escape")
    expect(dialog).not_to_be_visible()
    expect(opener).to_be_focused()


def test_teilen_closes_on_a_backdrop_click(window, server):
    page, client = window()
    sheet(client, [block("text", 20, 20, TEXT)], title="Sachaufgaben")
    page.goto(server + "/")
    opener = page.get_by_role("button", name="Sachaufgaben teilen")
    dialog = page.locator("dialog.ask")
    opener.click()
    check_backdrop(page, dialog, opener, dialog.get_by_role("heading"), opener.click)


def test_teilen_stays_open_while_the_link_is_switched_on(window, server):
    page, client = window()
    sheet(client, [block("text", 20, 20, TEXT)], title="Sachaufgaben")
    page.goto(server + "/")
    page.get_by_role("button", name="Sachaufgaben teilen").click()
    expect(page.get_by_role("button", name="Link einschalten")).to_be_visible()
    held = []

    def hold(route):
        if route.request.method == "POST":
            held.append(route)
        else:
            route.continue_()

    page.route("**/api/sheets/*/share", hold)
    with page.expect_request(lambda r: r.method == "POST" and "/share" in r.url):
        page.get_by_role("button", name="Link einschalten").click()
    page.mouse.click(4, 4)
    held[0].fulfill(json={"on": True, "token": "t" * 40, "updated": "2026-10-06 09:30:00"})
    expect(page.locator("dialog .link")).to_contain_text("/teilen/")
    expect(page.locator("dialog.ask")).to_be_visible()


def test_varianten_closes_on_a_backdrop_click(editor):
    page = editor(box("a", "text", TEXT))
    open_dialog(page)
    dialog = page.get_by_role("dialog")
    check_backdrop(
        page,
        dialog,
        variants_opener(page),
        dialog.get_by_role("heading"),
        lambda: open_dialog(page),
    )


def test_feedback_closes_on_a_backdrop_click(editor):
    page = editor(box("a", "text", TEXT))
    opener = page.get_by_label("Feedback", exact=True)
    opener.click()
    dialog = page.locator("dialog.feedback")
    check_backdrop(page, dialog, opener, dialog.get_by_role("heading"), opener.click)


def test_feedback_from_mehr_gives_the_focus_back_to_mehr(editor):
    page = sized(editor, box("a", "text", TEXT), width=701, height=1000, touch=False, theme="")
    dialog = page.locator("dialog.feedback")

    def reopen():
        more(page).click()
        item(page, "Feedback").click()

    reopen()
    check_backdrop(page, dialog, more(page), dialog.get_by_role("heading"), reopen)


def test_schliessen_gives_the_focus_back_to_the_feedback_button(editor):
    page = editor(box("a", "text", TEXT))
    opener = page.get_by_label("Feedback", exact=True)
    opener.click()
    page.locator("dialog.feedback").get_by_role("button", name="Schließen").click()
    expect(page.locator("dialog.feedback")).to_have_count(0)
    expect(opener).to_be_focused()


def test_text_anpassen_closes_on_a_backdrop_click(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    opener = page.get_by_role("button", name="Text anpassen", exact=True)
    opener.click()
    dialog = page.locator("dialog.texthelp")
    check_backdrop(page, dialog, opener, dialog.get_by_role("heading"), opener.click)


def test_schluessel_widerrufen_closes_on_a_backdrop_click(account):
    page = account(user())
    make(page, "Laptop")
    opener = page.get_by_role("button", name="Widerrufen: Laptop")
    opener.click()
    dialog = page.locator("dialog[aria-labelledby=ask-revoke]")
    check_backdrop(page, dialog, opener, dialog.locator("#ask-revoke"), opener.click)


def test_programm_trennen_closes_on_a_backdrop_click(account):
    page = account(user())
    page.route(
        "**/api/connections",
        lambda route: (
            route.fulfill(json=[CONNECTION]) if route.request.method == "GET" else route.continue_()
        ),
    )
    reload(page, page.url)
    opener = page.get_by_role("button", name="Trennen: Claude")
    opener.click()
    dialog = page.locator("dialog[aria-labelledby=ask-unlink]")
    check_backdrop(page, dialog, opener, dialog.locator("#ask-unlink"), opener.click)
