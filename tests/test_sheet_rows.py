"""#1185: Meine Blätter is a list with a row for each sheet, a search, a sort and its own delete dialog."""

import re
from datetime import datetime, timedelta

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from ui import TEXT, box, sheet
from ui_new import delete_sheet, more

TITLES = ".sheets li strong"


def listed(window, server, *titles, pages=()):  # noqa: F811
    """The list of a new teacher with a sheet of each title, made in that order."""
    page, client = window()
    for title in titles:
        sheet(client, [box("a", "text", TEXT)], *pages, title=title)
    page.goto(server)
    expect(page.locator(".sheets li")).to_have_count(len(titles), timeout=10000)
    return page, client


def head(page, column):
    return page.get_by_role("button", name=f"Nach {column} sortieren", exact=True)


def test_a_row_shows_the_page_the_title_the_last_change_and_the_pages(window, server):  # noqa: F811
    page, _ = listed(window, server, "Lesen", pages=[[], []])
    row = page.locator(".sheets li")
    expect(row.locator(".paper")).to_contain_text("Hallo")
    expect(row.locator("strong")).to_have_text("Lesen")
    expect(row.locator("small")).to_have_text(["heute", "3 Seiten"])
    # The picture is small: the row is a line of the list, not a card.
    assert row.locator(".paper").bounding_box()["width"] < 80
    assert row.bounding_box()["width"] > 600
    for name in ("Lesen teilen", "Lesen duplizieren", "Lesen: weitere Aktionen"):
        expect(row.get_by_role("button", name=name, exact=True)).to_be_visible()
    expect(row.get_by_role("button", name="Lesen teilen")).to_have_text("Teilen")
    expect(row.get_by_role("button", name="Lesen duplizieren")).to_have_text("Kopie")


def test_the_last_change_says_heute_gestern_and_then_the_date(window, server):  # noqa: F811
    page, client = window()
    sheet(client, [box("a", "text", TEXT)], title="Lesen")
    page.goto(server)
    changed = page.locator(".sheets li small").first
    expect(changed).to_have_text("heute")
    one_page = page.locator(".sheets li small").last
    expect(one_page).to_have_text("1 Seite")
    # The browser's clock goes on a day, and then a month.
    page.clock.set_fixed_time(datetime.now() + timedelta(days=1))
    page.reload()
    expect(changed).to_have_text("gestern")
    page.clock.set_fixed_time(datetime.now() + timedelta(days=40))
    page.reload()
    expect(changed).to_have_text(re.compile(r"^\d{1,2}\. \S+ \d{4}$"))


def test_the_search_filters_by_title_as_it_is_typed(window, server):  # noqa: F811
    page, _ = listed(window, server, "Plus bis 20", "Minus bis 20", "Lesen: Igel")
    search = page.get_by_label("Blätter suchen")
    search.press_sequentially("bis")
    expect(page.locator(TITLES)).to_have_text(["Minus bis 20", "Plus bis 20"])
    search.press_sequentially(" 20")
    expect(page.locator(TITLES)).to_have_text(["Minus bis 20", "Plus bis 20"])
    # Capitals do not matter.
    search.fill("IGEL")
    expect(page.locator(TITLES)).to_have_text(["Lesen: Igel"])
    search.fill("")
    expect(page.locator(TITLES)).to_have_count(3)


def test_a_search_without_a_hit_says_so_and_offers_a_new_sheet(window, server):  # noqa: F811
    page, _ = listed(window, server, "Plus bis 20")
    page.get_by_label("Blätter suchen").fill("Sachkunde")
    box_ = page.locator(".empty")
    expect(box_).to_contain_text("Kein Blatt passt zu „Sachkunde“.")
    expect(page.locator(".sheets li")).to_have_count(0)
    expect(page.get_by_role("button", name="Neues Blatt", exact=True)).to_have_count(1)
    box_.get_by_role("button", name="Neues Blatt", exact=True).click()
    expect(page.locator("dialog.chooser")).to_be_visible()
    page.keyboard.press("Escape")
    box_.get_by_role("button", name="Suche leeren").click()
    expect(page.locator(TITLES)).to_have_text(["Plus bis 20"])
    expect(page.get_by_label("Blätter suchen")).to_have_value("")


def test_an_empty_list_says_so_and_offers_a_new_sheet(window, server):  # noqa: F811
    page, _ = window()
    page.goto(server)
    box_ = page.locator(".empty")
    expect(box_).to_contain_text("Noch kein Blatt. Leg dein erstes an.")
    expect(page.get_by_role("button", name="Neues Blatt", exact=True)).to_have_count(1)
    expect(box_.get_by_role("button", name="Neues Blatt", exact=True)).to_be_visible()
    # Nothing to search or to sort yet.
    expect(page.get_by_label("Blätter suchen")).to_have_count(0)
    expect(head(page, "Titel")).to_have_count(0)


def test_a_click_on_a_column_head_sorts_and_the_newest_stand_first(window, server):  # noqa: F811
    page, _ = listed(window, server, "Birne", "Zitrone", "apfel", "Blatt 10", "Blatt 9")
    newest = ["Blatt 9", "Blatt 10", "apfel", "Zitrone", "Birne"]
    by_title = ["apfel", "Birne", "Blatt 9", "Blatt 10", "Zitrone"]
    expect(page.locator(TITLES)).to_have_text(newest)
    expect(head(page, "Zuletzt geändert")).to_have_attribute("data-order", "down")
    expect(head(page, "Zuletzt geändert")).to_have_attribute("aria-pressed", "true")
    expect(head(page, "Titel")).to_have_attribute("aria-pressed", "false")

    head(page, "Titel").click()
    expect(page.locator(TITLES)).to_have_text(by_title)
    expect(head(page, "Titel")).to_have_attribute("data-order", "up")
    head(page, "Titel").click()
    expect(page.locator(TITLES)).to_have_text(by_title[::-1])
    expect(head(page, "Titel")).to_have_attribute("data-order", "down")

    head(page, "Zuletzt geändert").click()
    expect(page.locator(TITLES)).to_have_text(newest)
    head(page, "Zuletzt geändert").click()
    expect(page.locator(TITLES)).to_have_text(newest[::-1])


def test_deleting_asks_in_the_apps_own_dialog_with_the_sheets_name(window, server):  # noqa: F811
    page, client = listed(window, server, "Probe", "Bleibt")
    boxes = []
    page.on("dialog", lambda dialog: (boxes.append(dialog.message), dialog.dismiss()))
    more(page, "Probe", "Löschen")
    question = page.locator("dialog.confirm")
    expect(question.get_by_role("heading")).to_have_text("Blatt „Probe“ löschen?")
    expect(question).to_contain_text("Das Blatt mit 1 Seite wird gelöscht und kommt nicht zurück.")
    # The way out leaves the sheet, by the button and by Escape.
    question.get_by_role("button", name="Abbrechen").click()
    expect(question).to_have_count(0)
    more(page, "Probe", "Löschen")
    page.keyboard.press("Escape")
    expect(question).to_have_count(0)
    expect(page.locator(TITLES)).to_have_text(["Bleibt", "Probe"])

    delete_sheet(page, "Probe")
    expect(page.locator(TITLES)).to_have_text(["Bleibt"])
    assert [s["title"] for s in client.get("/api/sheets").json()] == ["Bleibt"]
    assert boxes == []


def test_the_rows_menu_renames_the_sheet(window, server):  # noqa: F811
    page, client = listed(window, server, "Alt")
    page.once("dialog", lambda dialog: dialog.accept("Neu"))
    more(page, "Alt", "Umbenennen")
    expect(page.locator(TITLES)).to_have_text(["Neu"])
    assert [s["title"] for s in client.get("/api/sheets").json()] == ["Neu"]


def test_the_nav_names_the_form_for_photos_as_feedback(window, server):  # noqa: F811
    page, _ = window()
    page.goto(server)
    expect(page.get_by_role("link", name="Fotos", exact=True)).to_have_count(0)
    page.get_by_role("link", name="Foto-Feedback", exact=True).click()
    expect(page.get_by_role("heading", name="Fotos von Blättern")).to_be_visible()
