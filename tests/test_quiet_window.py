"""#720: a window with no change of its own shows the newer sheet another window saved."""

import pytest
from playwright.sync_api import expect
from test_pdf_stale import pdf_button, text_of, type_text
from test_refused_save import open_sheet
from ui import TEXT, at, box, user

NEWER = "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert."


def save_in_other_window(page, text):
    """Another window of the same browser changes block a to `text`, and that save lands."""
    other = page.context.new_page()
    other.goto(page.url)
    expect(at(other, "a")).to_be_visible()
    with other.expect_response(lambda r: r.request.method == "PATCH" and r.ok):
        type_text(other, text)
        other.keyboard.press("Escape")
    expect(other.get_by_role("status").filter(has_text="Gespeichert")).to_have_text("Gespeichert")
    return other


def test_quiet_window_prints_what_it_shows(editor):
    page, _ = open_sheet(editor)
    save_in_other_window(page, "neu")

    with page.expect_download() as got:
        pdf_button(page).click()
    expect(at(page, "a")).to_contain_text("neu")
    assert "neu" in text_of(got.value)


def save_by_the_api(client, sheet_id, text):
    """Another device saves block a as `text`: no tab of this browser hears of it."""
    held = client.get(f"/api/sheets/{sheet_id}").json()
    held["doc"]["pages"][0]["blocks"][0]["props"]["text"] = text
    body = {"doc": held["doc"], "version": held["version"]}
    assert client.patch(f"/api/sheets/{sheet_id}", json=body).status_code == 200


@pytest.mark.parametrize("button", ["PDF", "Lösungen"], ids=["pdf", "loesungen"])
def test_pdf_alone_finds_a_version_saved_elsewhere_and_shows_it_first(editor, button):
    """The press is the only news of the other version: the editor shows it, says so, prints it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    save_by_the_api(client, sheet_id, "Vom Tool")

    with page.expect_download() as got:
        page.locator("header .pdf").get_by_role("button", name=button, exact=True).click()
    expect(at(page, "a")).to_contain_text("Vom Tool")
    expect(page.locator(".fault", has_text=NEWER)).to_have_count(1)
    assert "Vom Tool" in text_of(got.value)


def test_varianten_in_a_quiet_window_open_on_the_newer_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    save_by_the_api(client, sheet_id, "Vom Tool")

    door = page.locator("header .top").get_by_label("Varianten drucken", exact=True)
    door.click()
    expect(at(page, "a")).to_contain_text("Vom Tool")
    expect(page.locator(".fault", has_text=NEWER)).to_have_count(1)
    expect(page.locator("dialog.variants")).to_have_count(0)
    page.locator("header .top").get_by_label("Varianten drucken", exact=True).click()
    expect(page.locator("dialog.variants .preview")).to_contain_text("Vom Tool")


def test_a_window_with_a_change_is_not_reloaded_over_it(editor):
    """CAN STILL LOSE: what was typed here stays; the clash bar asks which version holds."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, wait=2000)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    type_text(page, "Von hier")
    save_by_the_api(client, sheet_id, "Vom Tool")
    page.locator("header .pdf").get_by_role("button", name="PDF", exact=True).click()
    expect(page.locator(".clash")).to_be_visible()
    expect(at(page, "a")).to_contain_text("Von hier")
    expect(page.locator(".fault", has_text=NEWER)).to_have_count(0)


def test_a_change_typed_while_the_check_is_out_stays(editor):
    """CAN STILL LOSE: the newer version comes after a key was typed: the key's change stays."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, wait=2000)
    sheet_id = int(page.url.rsplit("/", 1)[1])
    save_by_the_api(client, sheet_id, "Vom Tool")
    held = []
    page.route(
        f"**/api/sheets/{sheet_id}",
        lambda route: held.append(route) if route.request.method == "GET" else route.continue_(),
    )
    page.evaluate("dispatchEvent(new Event('focus'))")
    while not held:
        page.wait_for_timeout(50)
    type_text(page, "Von hier")
    held[0].continue_()
    page.unroute(f"**/api/sheets/{sheet_id}")
    expect(page.locator(".clash")).to_be_visible(timeout=10000)
    expect(at(page, "a")).to_contain_text("Von hier")
    expect(page.locator(".fault", has_text=NEWER)).to_have_count(0)


def test_quiet_window_loads_the_newer_sheet_as_the_other_saves(editor):
    page, _ = open_sheet(editor)
    save_in_other_window(page, "neu")

    expect(at(page, "a")).to_contain_text("neu")
    expect(page.locator(".fault", has_text=NEWER)).to_have_count(1)
