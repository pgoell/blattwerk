import json
import re
import shutil
import zipfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect
from ui import BROWSER, PASSWORD, reload, user

from blattwerk.app import app


@pytest.fixture
def account(browser, server):
    """Opens /konto logged in as the given client, and gives its page."""
    contexts = []

    def start(client):
        context = browser.new_context()
        contexts.append(context)
        # The session cookie is Secure and this server speaks http, so it goes by hand.
        cookie = {"name": "session", "value": client.cookies["session"], "url": server}
        context.add_cookies([cookie])
        page = context.new_page()
        page.goto(f"{server}/konto")
        return page

    yield start
    for context in contexts:
        context.close()


def bearer(token):
    """A client with no cookie, asking as the key does."""
    client = TestClient(app, base_url="https://testserver")
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def make(page, name):
    """Types the name and presses Enter, then gives the key as the page shows it."""
    field = page.get_by_label("Name des Schlüssels")
    field.fill(name)
    # #749: once in WebKit the name was gone when Enter came. This tells whether the field lost it.
    expect(field).to_have_value(name)
    page.keyboard.press("Enter")
    shown = page.locator("[data-testid=new-token] code")
    expect(shown).to_have_text(re.compile(r"^bt_"))
    return shown.inner_text()


def row(page, name):
    return page.get_by_role("listitem").filter(has_text=name)


def test_key_is_shown_once_and_never_stored(account):
    page = account(user())
    token = make(page, "Claude Desktop")
    expect(row(page, "Claude Desktop")).to_contain_text("zuletzt benutzt: noch nie")

    stored = page.evaluate("() => JSON.stringify([{...localStorage}, {...sessionStorage}])")
    assert token not in stored

    reload(page, page.url)
    expect(row(page, "Claude Desktop")).to_be_visible()
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(page.locator("body")).not_to_contain_text(token)


# Not strict: once in CI, as the first test of a fresh WebKit, the name typed was gone at Enter;
# none in 109 runs here. Cause not found.
@pytest.mark.xfail(
    BROWSER == "webkit", strict=False, reason="#749: the name typed is gone at Enter, once"
)
def test_revoke_takes_the_key_away(account):
    client = user()
    page = account(client)
    token = make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(page, "Laptop")).to_have_count(0)
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    assert bearer(token).get("/api/sheets").status_code == 401


def test_the_revoke_question_names_the_key_and_not_this_device(account):
    page = account(user())
    make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("„Laptop“")
    expect(dialog).not_to_contain_text("diesem Gerät")


def test_last_use_shows_on_the_list(account):
    client = user()
    page = account(client)
    token = make(page, "Schule")
    expect(row(page, "Schule")).to_contain_text("noch nie")
    assert bearer(token).get("/api/sheets").status_code == 200
    reload(page, page.url)
    expect(row(page, "Schule")).not_to_contain_text("noch nie")
    expect(row(page, "Schule")).to_contain_text("zuletzt benutzt")


def test_a_blank_name_makes_nothing(account):
    page = account(user())
    page.get_by_label("Name des Schlüssels").fill("   ")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(page.get_by_role("listitem")).to_have_count(0)


def test_a_list_that_fails_to_load_raises_no_alert(browser, server):
    context = browser.new_context()
    cookie = {"name": "session", "value": user().cookies["session"], "url": server}
    context.add_cookies([cookie])
    page = context.new_page()
    # Offline as the account page opens: the alert stays free for what the teacher does.
    page.route("**/api/tokens", lambda route: route.abort())
    page.goto(f"{server}/konto")
    expect(page.get_by_role("button", name="Abmelden")).to_be_visible()
    page.wait_for_load_state("networkidle")
    expect(page.get_by_role("alert")).to_have_count(0)
    page.unroute("**/api/tokens")
    make(page, "Danach")
    expect(row(page, "Danach")).to_be_visible()
    context.close()


def test_newest_key_comes_first(account):
    page = account(user())
    make(page, "Erster")
    make(page, "Zweiter")
    rows = page.get_by_role("listitem")
    expect(rows).to_have_text([re.compile(r"^Zweiter"), re.compile(r"^Erster")])


def test_revoke_asks_first_and_abbrechen_keeps_the_key(account):
    page = account(user())
    make(page, "Laptop Schule")
    page.get_by_role("button", name="Widerrufen: Laptop Schule").click()
    dialog = page.get_by_role("dialog")
    expect(dialog).to_contain_text("Schlüssel „Laptop Schule“ widerrufen?")
    dialog.get_by_role("button", name="Abbrechen").click()
    expect(dialog).not_to_be_visible()
    expect(row(page, "Laptop Schule")).to_be_visible()
    expect(page.get_by_role("button", name="Widerrufen: Laptop Schule")).to_be_focused()


def test_a_key_another_tab_already_revoked_leaves_the_list_quietly(account):
    page = account(user())
    make(page, "Laptop")
    other = page.context.new_page()
    other.goto(page.url)
    other.get_by_role("button", name="Widerrufen: Laptop").click()
    other.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(other, "Laptop")).to_have_count(0)
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(row(page, "Laptop")).to_have_count(0)
    expect(page.get_by_role("alert")).to_have_count(0)


def test_a_revoke_that_finds_the_session_gone_is_said_after_the_login(account, server):
    client = user()
    page = account(client)
    make(page, "Laptop")
    page.context.clear_cookies()
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    page.get_by_role("dialog").get_by_role("button", name="Widerrufen", exact=True).click()
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    said = "Der Schlüssel „Laptop“ ist noch nicht widerrufen"
    expect(page.get_by_role("status")).to_contain_text(said)
    expect(row(page, "Laptop")).to_be_visible()


def test_escape_keeps_the_key_and_gives_the_focus_back(account):
    page = account(user())
    make(page, "Laptop Schule")
    button = page.get_by_role("button", name="Widerrufen: Laptop Schule")
    button.click()
    expect(page.get_by_role("dialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(row(page, "Laptop Schule")).to_be_visible()
    expect(button).to_be_focused()


def test_a_key_not_made_when_the_session_ran_out_is_said_after_the_login(account, server):
    client = user()
    page = account(client)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    page.get_by_label("Name des Schlüssels").fill("Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    said = "Der Schlüssel „Danach“ wurde nicht erstellt"
    expect(page.get_by_role("status")).to_contain_text(said)
    expect(page.get_by_label("Name des Schlüssels")).to_have_value("Danach")
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    expect(row(page, "Danach")).to_have_count(0)


def test_the_note_of_one_teacher_never_shows_to_the_next_one_at_that_login(account, server):
    page = account(user())
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    page.get_by_label("Name des Schlüssels").fill("Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    other = user()
    cookie = {"name": "session", "value": other.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(other.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_label("Name des Schlüssels")).to_have_value("")
    expect(page.get_by_role("status")).to_have_count(0)


def test_the_note_shows_once_and_a_reload_takes_it_away(account, server):
    client = user()
    page = account(client)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    page.wait_for_load_state("networkidle")
    page.context.clear_cookies()
    page.get_by_label("Name des Schlüssels").fill("Danach")
    page.keyboard.press("Enter")
    expect(page.get_by_role("button", name="Anmelden")).to_be_visible()
    cookie = {"name": "session", "value": client.cookies["session"], "url": server}
    page.context.add_cookies([cookie])
    page.get_by_label("E-Mail").fill(client.get("/api/me").json()["email"])
    page.get_by_label("Passwort").fill(PASSWORD)
    page.get_by_role("button", name="Anmelden").click()
    expect(page.get_by_role("status")).to_contain_text("wurde nicht erstellt")
    reload(page, page.url)
    expect(page.get_by_role("button", name="Schlüssel erstellen")).to_be_visible()
    expect(page.get_by_role("status")).to_have_count(0)


def test_a_double_press_on_erstellen_makes_one_key_and_no_more_words(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("Doppelt")
    page.get_by_role("button", name="Schlüssel erstellen").dblclick()
    expect(page.locator("[data-testid=new-token] code")).to_have_text(re.compile(r"^bt_"))
    page.wait_for_timeout(500)
    expect(row(page, "Doppelt")).to_have_count(1)
    # The hint beside the field, and no complaint after it.
    expect(field).to_have_accessible_description(HINT)


def test_enter_on_the_question_keeps_the_key(account):
    page = account(user())
    make(page, "Laptop")
    page.get_by_role("button", name="Widerrufen: Laptop").click()
    expect(page.get_by_role("dialog").get_by_role("button", name="Abbrechen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.get_by_role("dialog")).not_to_be_visible()
    expect(row(page, "Laptop")).to_be_visible()


def test_a_blank_name_says_so_beside_the_field(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("   ")
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description(re.compile("Gib dem Schlüssel einen Namen\\."))
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    field.fill("x")
    expect(field).to_have_accessible_description(HINT)


def test_a_name_already_in_the_list_says_so_beside_the_field(account):
    page = account(user())
    make(page, "Laptop")
    field = page.get_by_label("Name des Schlüssels")
    field.fill(" laptop ")
    page.keyboard.press("Enter")
    taken = "Diesen Namen hat schon ein Schlüssel. Gib jedem Gerät einen eigenen Namen."
    expect(field).to_have_accessible_description(re.compile(re.escape(taken)))
    expect(page.get_by_role("listitem")).to_have_count(1)


def test_a_name_of_81_letters_stays_whole_and_says_so(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("x" * 81)
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description(
        f"{HINT} Der Name ist zu lang: höchstens 80 Zeichen."
    )
    expect(field).to_have_value("x" * 81)


def test_the_extension_downloads_beside_the_key(account, server, tmp_path):
    """The card of the keys offers the Claude Desktop extension, served by the app as a file."""
    page = account(user())
    card = page.locator(".card").filter(has_text="Zugang für Claude")
    with page.expect_download() as download:
        card.get_by_role("link", name="Erweiterung für Claude Desktop herunterladen").click()
    assert download.value.suggested_filename == "blattomat.mcpb"
    path = tmp_path / "blattomat.mcpb"
    download.value.save_as(path)
    with zipfile.ZipFile(path) as bundle:
        assert json.loads(bundle.read("manifest.json"))["name"] == "blattomat"
    answer = httpx.get(f"{server}/blattomat.mcpb")
    assert answer.headers["content-type"] == "application/octet-stream"


DOCS = Path(__file__).resolve().parents[1] / "docs" / "okf"


def test_the_card_says_what_claude_is_does_sees_and_how_to_stop(account):
    page = account(user())
    card = page.locator(".card").filter(has_text="Zugang für Claude")
    for words in (
        "KI-Assistent",
        "Anthropic",
        "USA",
        "anlegen und ändern",
        "Titel",
        "Inhalte",
        "Lernwörter",
        "Bilder der Seiten",
        "entfern die Erweiterung",
        "Widerrufen",
    ):
        expect(card).to_contain_text(words)


def test_the_install_steps_open_from_the_card_in_a_new_tab(account):
    page = account(user())
    make(page, "Claude Desktop")
    with page.context.expect_page() as new:
        page.get_by_role("link", name="So installierst du die Erweiterung").click()
    tab = new.value
    tab.wait_for_load_state()
    expect(tab.get_by_role("heading", name="Dein erstes Blatt mit Claude")).to_be_visible()
    expect(tab.locator("body")).to_contain_text("Schritt 3: Die Erweiterung installieren")
    expect(tab.locator("body")).to_contain_text("blattomat.mcpb")
    expect(page.get_by_test_id("new-token")).to_be_visible()


def test_datenschutz_section_9_opens_from_the_card(account):
    page = account(user())
    make(page, "Claude Desktop")
    with page.context.expect_page() as new:
        page.get_by_role("link", name="Was an Anthropic geht: Datenschutz, Abschnitt 9").click()
    tab = new.value
    tab.wait_for_load_state()
    assert tab.url.endswith("/datenschutz#claude")
    section = tab.locator("#claude")
    expect(section).to_have_text("9. Claude (freiwillig)")
    expect(section).to_be_in_viewport()
    expect(page.get_by_test_id("new-token")).to_be_visible()


def test_the_install_page_opens_without_a_login_and_numbers_its_steps():
    response = TestClient(app).get("/anleitung/claude")
    assert response.status_code == 200
    html = response.text
    assert "viewport" in html
    assert "prefers-color-scheme: dark" in html
    assert "← Blattomat" in html
    # Schritt 3 has a paragraph between steps 3 and 4, so its list starts at 4.
    before_key_step = html[: html.index("API-Schlüssel")]
    assert before_key_step.rsplit("<ol", 1)[1].startswith(' start="4">')


def test_the_install_page_reads_the_docs_folder_from_the_env(tmp_path, monkeypatch):
    docs = tmp_path / "okf"
    shutil.copytree(DOCS, docs)
    tutorial = docs / "tutorials" / "dein-erstes-blatt-mit-claude.md"
    text = tutorial.read_text(encoding="utf-8")
    changed = text.replace("# Dein erstes Blatt mit Claude", "# Ein anderes Blatt", 1)
    tutorial.write_text(changed, encoding="utf-8")
    monkeypatch.setenv("BLATTWERK_DOCS", str(docs))
    assert "<h1>Ein anderes Blatt</h1>" in TestClient(app).get("/anleitung/claude").text


LABEL = "Name des Schlüssels, z. B. Laptop Schule"
HINT = "Gib jedem Schlüssel einen eigenen Namen, einen je Gerät."


def test_the_key_name_has_a_visible_label_tied_to_the_field(account):
    page = account(user())
    field = page.get_by_role("textbox", name=LABEL)
    expect(field).to_be_visible()
    label_for = page.locator("label", has_text=LABEL).get_attribute("for")
    assert label_for
    expect(field).to_have_attribute("id", label_for)


def test_the_key_name_field_has_no_placeholder(account):
    page = account(user())
    expect(page.get_by_role("textbox", name=LABEL)).to_be_visible()
    assert page.get_by_role("textbox", name=LABEL).get_attribute("placeholder") is None


@pytest.mark.parametrize("dark", [False, True])
def test_the_key_name_field_looks_like_the_other_app_fields(account, dark):
    page = account(user())
    page.emulate_media(color_scheme="dark" if dark else "light")
    field = page.get_by_role("textbox", name=LABEL)
    # A plain text field, as the stylesheet styles every other one, is the reference.
    look = """e => {
        const pick = (s) => ({
            radius: s.borderTopLeftRadius, width: s.borderTopWidth,
            top: s.borderTopColor, right: s.borderRightColor,
            bottom: s.borderBottomColor, left: s.borderLeftColor,
        });
        const plain = document.createElement("input");
        plain.type = "text";
        e.after(plain);
        const reference = pick(getComputedStyle(plain));
        plain.remove();
        return { field: pick(getComputedStyle(e)), reference };
    }"""
    looks = field.evaluate(look)
    assert looks["field"] == looks["reference"]
    assert looks["field"]["width"] == "1px"
    assert looks["field"]["top"] == looks["field"]["left"]


def test_the_hint_for_the_name_sits_by_the_field_and_not_in_the_stop_paragraph(account):
    page = account(user())
    field = page.get_by_role("textbox", name=LABEL)
    expect(page.get_by_text(HINT, exact=True)).to_be_visible()
    expect(field).to_have_attribute("aria-describedby", "name-hint name-note")
    expect(page.locator("p.hint", has_text="Willst du aufhören")).not_to_contain_text("Gerät")


def test_the_key_form_fits_a_375_px_phone(account):
    page = account(user())
    page.set_viewport_size({"width": 375, "height": 800})
    field = page.get_by_role("textbox", name=LABEL)
    expect(field).to_be_visible()
    button = page.get_by_role("button", name="Schlüssel erstellen")
    expect(button).to_be_visible()
    scroll = "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    assert page.evaluate(scroll), "the page scrolls sideways at 375 px"
    for part in (field, button):
        box = part.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375


COPY_STUB = "() => { window.copiedKey = null; Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: (t) => { window.copiedKey = t; return Promise.resolve(); }}}); }"
REFUSED_STUB = "() => { Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: () => Promise.reject(new DOMException('denied', 'NotAllowedError'))}}); }"


def test_a7_kopieren_says_kopiert_and_puts_the_key_on_the_clipboard(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(COPY_STUB)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    assert page.evaluate("() => window.copiedKey") == key
    expect(box.get_by_role("button", name="Kopieren", exact=True)).to_be_visible()


def test_a8_a_refused_clipboard_says_so_and_marks_the_key(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(REFUSED_STUB)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(page.get_by_role("alert")).to_contain_text("Kopieren hat nicht geklappt")
    expect(box.get_by_role("button", name="Kopieren", exact=True)).to_be_visible()
    assert page.evaluate("() => String(getSelection())") == key


def test_i6_a_second_click_keeps_kopiert_and_the_key_stays(account):
    page = account(user())
    key = make(page, "Laptop")
    page.evaluate(COPY_STUB)
    box = page.get_by_test_id("new-token")
    box.get_by_role("button", name="Kopieren", exact=True).click()
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    page.wait_for_timeout(1200)
    box.get_by_role("button", name="Kopiert", exact=True).click()
    page.wait_for_timeout(1200)
    expect(box.get_by_role("button", name="Kopiert", exact=True)).to_be_visible()
    expect(box.locator("code")).to_have_text(key)


def test_i7_a_new_key_takes_the_failure_line_away(account):
    page = account(user())
    make(page, "Laptop")
    page.evaluate(REFUSED_STUB)
    page.get_by_test_id("new-token").get_by_role("button", name="Kopieren", exact=True).click()
    expect(page.get_by_role("alert")).to_have_count(1)
    make(page, "zweiter")
    expect(page.get_by_role("alert")).to_have_count(0)
    expect(
        page.get_by_test_id("new-token").get_by_role("button", name="Kopieren", exact=True)
    ).to_be_visible()
