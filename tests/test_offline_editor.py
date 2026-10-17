"""What the editor asks the server for and does not get stays in the app (issues #361, #362, #363):
the PDF, a template stored, deleted or loaded, a picture by the button, by a paste and by a drop,
the exercises of a maths block. A line above the page says so and tries the same again.

Each with no connection and with a fault of the server.

The docstrings name the lines of the checklist.
"""

import re

import pytest
from playwright.sync_api import expect
from test_clipboard import no_picture
from test_drop import PDF, PNG, landed, spot
from ui import TEXT, at, box, centre, copy_picture, drop, maths, pick, saved, sheet, user

from blattwerk import db

HOW = ["offline", "500"]
WHY = {
    "offline": "Prüfe deine Verbindung und versuche es noch einmal.",
    "500": "Blattomat hat gerade eine Störung. Versuche es gleich noch einmal.",
}
LINE = ".notice.fault"
NO_PDF = "Das PDF konnte nicht erstellt werden."
NO_STORE = "Die Vorlage konnte nicht gespeichert werden."
NO_DELETE = "Die Vorlage konnte nicht gelöscht werden."
NO_LOAD = "Die Vorlagen konnten nicht geladen werden."
NO_PICTURE = "Das Bild konnte nicht hochgeladen werden."
NO_FILE = (
    "Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB, SVG bis 2 MB."
)
NO_MATHS = "Die Aufgaben konnten nicht erzeugt werden."
# A text file with a picture's name.
FAKE = ("bild.png", "image/png", b"Kein Bild.")
FILE = dict(zip(("name", "mimeType", "buffer"), PNG, strict=True))


def broken(page, how, path):
    """The call of the path fails from here on: for want of a connection, or by the server's
    fault. Gives the way to mend it."""
    if how == "offline":
        page.context.set_offline(True)
        return lambda: page.context.set_offline(False)
    pattern = re.compile(f"/api{path}")
    page.route(pattern, lambda route: route.fulfill(status=500))
    return lambda: page.unroute(pattern)


def said(page, what, how):
    """The one line says what could not be done and why. Gives it."""
    line = page.locator(LINE)
    expect(line).to_have_count(1)
    expect(line).to_contain_text(f"{what} {WHY[how]}")
    return line


def again(page):
    page.locator(LINE).get_by_role("button", name="Erneut versuchen").click()


def dialogs(page):
    """The dialogs the page opens from here on, each one accepted."""
    asked = []
    page.on("dialog", lambda dialog: (asked.append(dialog.message), dialog.accept()))
    return asked


def own(client):
    """The names of the teacher's own templates as the server holds them."""
    return [t["name"] for t in client.get("/api/templates").json() if t["id"] > 0]


def panel(page):
    """Opens the panel of the templates. Gives the field for a new one's name."""
    page.get_by_role("tab", name="Vorlagen").click()
    return page.get_by_label("Name der Vorlage")


def store(page):
    page.get_by_role("button", name="Dieses Blatt als Vorlage").click()


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("name", ["PDF", "Lösungen"])
def test_a_pdf_that_cannot_be_made_leaves_the_sheet_and_comes_with_the_next_try(editor, how, name):
    """A17, I6: the editor stays, the change made just before is kept and saved, and the PDF
    comes as a download with the sheet's name."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    address = page.url
    asked = dialogs(page)
    left = []
    page.on("framenavigated", lambda frame: left.append(frame.url))
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    mend = broken(page, how, r"/sheets/\d+/pdf")
    page.get_by_role("button", name=name, exact=True).click()
    said(page, NO_PDF, how)
    expect(page.locator("main.editor")).to_be_visible()
    expect(page).to_have_url(address)
    expect(at(page, "a")).to_have_text("Hallo")
    mend()
    with page.expect_download() as got:
        again(page)
    assert got.value.suggested_filename == f"Plus bis 20{' Lösungen' * (name != 'PDF')}.pdf"
    with open(got.value.path(), "rb") as file:
        assert file.read(5) == b"%PDF-"
    expect(page.locator(LINE)).to_have_count(0)
    assert saved(page, client)[0]["x"] == 16
    assert left == []
    assert asked == []


@pytest.mark.parametrize("how", HOW)
def test_a_template_that_cannot_be_stored_keeps_its_name_and_is_stored_once(editor, how):
    """A16"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    field = panel(page)
    field.fill("Neu")
    mend = broken(page, how, "/templates$")
    store(page)
    said(page, NO_STORE, how)
    expect(field).to_have_value("Neu")
    mend()
    assert own(client) == []
    again(page)
    expect(page.get_by_label("Vorlage Neu löschen")).to_have_count(1)
    expect(page.locator(LINE)).to_have_count(0)
    expect(field).to_have_value("")
    assert own(client) == ["Neu"]


def test_a_second_press_while_a_template_is_on_its_way_stores_no_second_one(editor):
    """I1"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    panel(page).fill("Neu")
    held = []
    page.route(
        re.compile("/api/templates$"),
        lambda route: held.append(route) if route.request.method == "POST" else route.continue_(),
    )
    with page.expect_request(re.compile("/api/templates$")):
        store(page)
    store(page)
    held[0].continue_()
    expect(page.get_by_label("Vorlage Neu löschen")).to_have_count(1)
    assert len(held) == 1
    assert own(client) == ["Neu"]


def test_the_line_goes_with_a_press_on_schliessen_and_a_second_failure_takes_its_place(editor):
    """I4: and it goes with a try that works."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    panel(page).fill("Neu")
    mend = broken(page, "500", "/templates$")
    store(page)
    said(page, NO_STORE, "500")
    mend()
    mend = broken(page, "offline", "")
    again(page)
    said(page, NO_STORE, "offline")
    page.locator(LINE).get_by_role("button", name="Schließen").click()
    expect(page.locator(LINE)).to_have_count(0)
    store(page)
    said(page, NO_STORE, "offline")
    mend()
    again(page)
    expect(page.get_by_label("Vorlage Neu löschen")).to_have_count(1)
    expect(page.locator(LINE)).to_have_count(0)
    assert own(client) == ["Neu"]


@pytest.mark.parametrize("how", HOW)
def test_a_template_that_cannot_be_deleted_stays_and_goes_with_no_second_question(editor, how):
    """A20"""
    client = user()
    made = sheet(client, [])
    assert client.post("/api/templates", json={"name": "Alt", "doc": made["doc"]}).is_success
    page = editor(box("a", "text", TEXT), client=client)
    panel(page)
    asked = dialogs(page)
    mend = broken(page, how, r"/templates/\d+$")
    page.get_by_label("Vorlage Alt löschen").click()
    said(page, NO_DELETE, how)
    expect(page.get_by_label("Vorlage Alt löschen")).to_have_count(1)
    mend()
    assert own(client) == ["Alt"]
    again(page)
    expect(page.get_by_label("Vorlage Alt löschen")).to_have_count(0)
    expect(page.locator(LINE)).to_have_count(0)
    assert own(client) == []
    assert asked == ["Vorlage „Alt“ löschen?"]


@pytest.mark.parametrize("how", HOW)
def test_templates_that_cannot_be_loaded_say_so_and_load_with_the_next_try(editor, how):
    """A20: with no connection the app itself would not load, so the templates' own request is
    cut off, which the page sees as it sees no connection."""
    client = user()
    made = sheet(client, [])
    assert client.post("/api/templates", json={"name": "Alt", "doc": made["doc"]}).is_success
    page = editor(box("a", "text", TEXT), client=client)
    pattern = re.compile("/api/templates$")
    page.route(pattern, lambda r: r.abort() if how == "offline" else r.fulfill(status=500))
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    said(page, NO_LOAD, how)
    panel(page)
    expect(page.get_by_label("Vorlage Alt löschen")).to_have_count(0)
    page.unroute(pattern)
    again(page)
    expect(page.get_by_label("Vorlage Alt löschen")).to_have_count(1)
    expect(page.locator(LINE)).to_have_count(0)


def by_button(page, file=PNG):
    page.locator("input[type=file]").set_input_files(dict(zip(FILE, file, strict=True)))


def by_paste(page):
    copy_picture(page)
    page.keyboard.press("Control+v")


def by_drop(page, file=PNG):
    drop(page, *spot(page, 105, 150), file)


@pytest.mark.parametrize("how", HOW)
@pytest.mark.parametrize("add", [by_button, pytest.param(by_paste, marks=no_picture), by_drop])
def test_a_picture_that_cannot_be_sent_names_the_cause_and_lands_with_the_next_try(
    editor, how, add
):
    """A18, A19: the same file goes again, with no second file dialog, and a dropped one lands
    where it was dropped."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    asked = dialogs(page)
    page.on("filechooser", lambda chooser: asked.append(chooser))
    mend = broken(page, how, "/uploads$")
    add(page)
    said(page, NO_PICTURE, how)
    expect(page.locator(".block[data-id]")).to_have_count(1)
    mend()
    again(page)
    [point] = [centre(landed(page, 2))]
    expect(page.locator(LINE)).to_have_count(0)
    if add is by_drop:
        assert point == pytest.approx(spot(page, 105, 150), abs=1)
    assert [b["type"] for b in saved(page, client)] == ["text", "image"]
    assert asked == []


@pytest.mark.parametrize(
    ("add", "file", "answer"),
    [(by_button, FAKE, 415), (by_drop, FAKE, 415), (by_button, PDF, 415)],
    ids=["button", "drop", "button, refused by the server"],
)
def test_a_file_that_is_no_picture_is_named_as_such_with_nothing_to_try_again(
    editor, add, file, answer
):
    """A18, A19: a text file with a picture's name, which the server refuses by its bytes, and a
    file the server does not take."""
    page = editor(box("a", "text", TEXT))
    asked = dialogs(page)
    with page.expect_response(re.compile("/api/uploads$")) as got:
        add(page, file)
    assert got.value.status == answer
    line = page.locator(LINE)
    expect(line).to_contain_text(NO_FILE)
    expect(line.get_by_role("button")).to_have_text(["Schließen"])
    expect(page.locator(".block[data-id]")).to_have_count(1)
    assert asked == []


def test_a_text_file_named_as_a_picture_leaves_no_upload_on_the_server(editor):
    """19: the bytes say no picture, whatever the name and type say: the server keeps no row."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    with page.expect_response(re.compile("/api/uploads$")) as got:
        by_button(page, FAKE)
    assert got.value.status == 415
    expect(page.locator(LINE)).to_contain_text(NO_FILE)
    user_id = client.get("/api/me").json()["id"]
    rows = db.open_db().execute("SELECT count(*) FROM uploads WHERE user_id = ?", (user_id,))
    assert rows.fetchone()[0] == 0


def test_of_two_dropped_pictures_only_the_one_that_did_not_arrive_goes_again(editor):
    """A19"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    sent = []
    pattern = re.compile("/api/uploads$")
    # The first upload arrives, the second finds a fault.
    page.route(
        pattern,
        lambda route: (
            sent.append(route),
            route.fulfill(status=500) if len(sent) == 2 else route.continue_(),
        ),
    )
    drop(page, *spot(page, 105, 150), PNG, ("zwei.png", *PNG[1:]))
    said(page, NO_PICTURE, "500")
    landed(page, 2)
    again(page)
    landed(page, 3)
    expect(page.locator(LINE)).to_have_count(0)
    assert len(sent) == 3
    assert [b["type"] for b in saved(page, client)] == ["text", "image", "image"]


@pytest.mark.parametrize("how", HOW)
def test_a_maths_block_that_cannot_be_made_says_so_in_a_line_and_comes_with_the_next_try(
    editor, how
):
    """A21"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    asked = dialogs(page)
    mend = broken(page, how, "/maths$")
    page.get_by_role("button", name="Rechnen", exact=True).first.click()
    said(page, NO_MATHS, how)
    expect(page.locator(".block[data-id]")).to_have_count(1)
    mend()
    again(page)
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(page.locator(LINE)).to_have_count(0)
    assert [b["type"] for b in saved(page, client)] == ["text", "maths"]
    assert asked == []


@pytest.mark.parametrize("how", HOW)
def test_a_limit_that_brings_no_exercises_stays_as_set_and_brings_them_with_the_next_try(
    editor, how
):
    """A21"""
    client = user()
    page = editor(box("a", "maths", maths(client)), client=client)
    pick(page, "a")
    count = page.locator(".panel output", has_text="Aufgaben")
    expect(count).to_have_text("3 Aufgaben")
    mend = broken(page, how, "/maths$")
    page.locator(".panel").get_by_label("Eine Aufgabe mehr").click()
    said(page, NO_MATHS, how)
    expect(count).to_have_text("4 Aufgaben")
    expect(at(page, "a").locator(".maths > div")).to_have_count(3)
    mend()
    again(page)
    expect(at(page, "a").locator(".maths > div")).to_have_count(4)
    expect(page.locator(LINE)).to_have_count(0)
    expect(count).to_have_text("4 Aufgaben")
    [held] = saved(page, client)
    assert (held["props"]["count"], len(held["props"]["exercises"])) == (4, 4)
