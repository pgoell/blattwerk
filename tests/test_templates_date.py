"""The Elternbrief and the Klassenarbeit Deckblatt ask for the date once (#599)."""

import pytest
from playwright.sync_api import expect
from test_templates_print import printed, template
from ui import sheet, user
from ui_new import from_template


@pytest.mark.parametrize("name", ["Elternbrief", "Klassenarbeit Deckblatt"])
def test_template_shows_the_date_once_on_screen(editor, name):
    page = editor()
    from_template(page, name)
    sheet_page = page.locator(".sheet").first
    expect(sheet_page.get_by_text("Datum").first).to_be_visible()
    shown = sheet_page.inner_text()
    assert shown.count("Datum") == 1


def test_deckblatt_keeps_its_name_line_on_screen(editor):
    page = editor()
    from_template(page, "Klassenarbeit Deckblatt")
    fields = page.locator(".sheet").first.locator(".fields > span")
    expect(fields).to_have_text(["Name:", "Klasse:"])


@pytest.mark.parametrize("name", ["Elternbrief", "Klassenarbeit Deckblatt"])
def test_template_prints_the_date_once(server, name):
    client = user()
    made = sheet(client, *template(name)["doc"]["pages"])
    _, text = printed(server, client, made)
    assert text.count("Datum") == 1


def test_deckblatt_prints_its_name_line(server):
    client = user()
    made = sheet(client, *template("Klassenarbeit Deckblatt")["doc"]["pages"])
    _, text = printed(server, client, made)
    assert "Name:" in text.split()
    assert "Klasse:" in text.split()
