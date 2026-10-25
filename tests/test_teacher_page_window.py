"""The teacher-page tool's window: where, value, resize, screenshot, pdf and open."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import io
import re
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import (
    Error,
    expect,
)
from pypdf import PdfReader
from test_teacher_page import (
    ONE,
    RED,
    folder,  # noqa: F401
    middle,
    pytestmark,  # noqa: F401
    shape,
    size,
    slider,
    tool,
    xy,
)
from ui import (
    TEXT,
    at,
    box,
    expect_picked,
    user,
)

# The window


def test_where_prints_each_place_of_a_name_and_changes_nothing(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2), pages=[{"blocks": []}])
    places = [middle(at(page, name).get_by_text("Hallo")) for name in "ab"]
    assert tool.where(page, "Hallo") == "\n".join(f"Hallo at {place}" for place in places)
    expect_picked(page)
    # What lies above the window is still on the page, and is said to be out of sight.
    tool.wheel(page, xy(page.locator(".desk")), "600")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 600")
    assert tool.where(page, "Hallo").count("(outside the window)") == 2
    with pytest.raises(tool.Refused, match=r"outside the window.*scroll to it"):
        tool.click(page, "Hallo")


def test_where_gives_a_label_and_its_field_as_one_place_the_fields(editor, browser, server):
    page = shape(editor)
    # The label holds its field.
    assert tool.where(page, "Randstärke") == f"Randstärke at {middle(slider(page))}"
    # A button's words and the button are one place too.
    assert tool.where(page, "PDF").count("\n") == 0
    # On the login page the label stands beside its field.
    context = browser.new_context()
    login = context.new_page()
    login.goto(server)
    # The form still settles by a pixel while it loads, so the one place is asked what it is.
    found = tool.where(login, "E-Mail")
    assert found.count("\n") == 0
    x, y = map(int, found.removeprefix("E-Mail at ").split(","))
    assert login.evaluate("([x, y]) => document.elementFromPoint(x, y).id", [x, y]) == "email"
    context.close()


def test_where_finds_a_part_of_a_text_where_no_whole_one_matches(editor):
    # Issue #321: `where "28"` found nothing, though the number stood in an exercise.
    sum_, more = {**TEXT, "text": "28 + 5"}, {**TEXT, "text": "Eins und"}
    page = editor(box("a", "text", sum_), box("b", "text", ONE, z=2), box("c", "text", more, z=3))
    assert tool.where(page, "28") == f"28 + 5 at {middle(at(page, 'a').get_by_text('28 + 5'))}"
    # A whole name goes first: the text that only holds it is not listed beside it.
    assert tool.where(page, "Eins") == f"Eins at {middle(at(page, 'b').get_by_text('Eins'))}"
    # With capitals as written: a wait for `Gespeichert` does not end on "Nicht gespeichert".
    with pytest.raises(tool.Refused, match='nothing on the page is called "eins"'):
        tool.where(page, "eins")
    # A verb that acts still wants the whole name.
    with pytest.raises(tool.Refused, match='nothing on the page is called "28"'):
        tool.click(page, "28")
    expect_picked(page)


def test_406_8_where_prints_the_zoom_as_it_reads_for_a_percent_sign(editor):
    # Issue #406: `where "%"` printed "% at", not the zoom's number.
    page = editor(box("a", "text", ONE))
    zoom = page.locator("button.zoom")
    text = " ".join(zoom.text_content().split())
    assert re.fullmatch(r"\d+ %", text), text
    lines = tool.where(page, "%").splitlines()
    assert any(line.startswith(f"{text} at ") for line in lines), lines


def test_406_8_where_prints_a_controls_name_for_a_part_of_it(editor):
    # A control has a name and may hold other words: a list its choices, a button a sign.
    page = editor(box("a", "text", ONE))
    at(page, "a").click()
    assert tool.where(page, "Schrifta").startswith("Schriftart at ")
    assert tool.where(page, "Ganze Sei").startswith("Ganze Seite at ")


def test_where_says_that_a_name_may_lie_under_mehr_in_a_narrow_window(editor):
    # Issue #321: at 820 wide the zoom's buttons have no room in the bar.
    page = editor(box("a", "text", ONE), theme="")
    assert tool.where(page, "Ganze Seite").startswith("Ganze Seite at ")
    tool.resize(page, "820", "1180")
    expect(page.get_by_label("Mehr", exact=True)).to_be_visible()
    with pytest.raises(tool.Refused) as refused:
        tool.where(page, "Ganze Seite")
    assert str(refused.value) == (
        'nothing on the page is called "Ganze Seite": it may lie under "Mehr"'
    )


def test_value_reads_a_colour_and_a_slider_and_changes_nothing(editor):
    # Issue #321: a border's new colour is hard to tell in a screenshot.
    client = user()
    page = shape(editor, client)
    assert tool.value(page, "Rand") == "Rand is #222222"
    assert tool.value(page, "Randstärke") == "Randstärke is 0.5"
    expect_picked(page, "a")
    expect(slider(page)).not_to_be_focused()
    with pytest.raises(tool.Refused, match='no field on the page is called "Drei"'):
        tool.value(page, "Drei")
    # A button has a name and holds no value.
    with pytest.raises(tool.Refused, match='no field on the page is called "PDF"'):
        tool.value(page, "PDF")


def test_resize_sets_the_windows_size(editor, folder):
    page = editor(box("a", "text", ONE))
    said = tool.resize(page, "900", "700")
    assert said == f"window is 900 x 700: {folder / 'last.png'}"
    assert page.evaluate("[innerWidth, innerHeight]") == [900, 700]
    assert size(folder / "last.png") == (900, 700)


def test_a_size_the_browser_refuses_is_not_kept_for_the_holder(editor, folder):
    page = editor(box("a", "text", ONE))
    tool.resize(page, "900", "700")
    with pytest.raises(Error):
        tool.resize(page, "-5", "100")
    # The holder sets the kept size each second: a refused one would end it.
    assert tool.wanted() == [900, 700]


def test_screenshot_is_the_window_and_a_point_read_from_it_is_the_mouses(editor, folder):
    page = editor(box("a", "text", ONE), box("red", "shape", RED, z=6), pages=[{"blocks": []}])
    tool.wheel(page, xy(page.locator(".desk")), "250")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 250")
    path = tool.screenshot(page, "sheet-1")
    assert path == str(folder / "sheet-1.png")
    # The window and no more, though the desk holds two pages.
    assert size(path) == (1400, 1000)
    # The red block as the picture shows it: the middle of its red px.
    red = Image.open(path).convert("RGB")
    reds = [
        (x, y)
        for x in range(0, red.width, 4)
        for y in range(0, red.height, 4)
        if red.getpixel((x, y)) == (255, 0, 0)
    ]
    assert reds
    x = (min(p[0] for p in reds) + max(p[0] for p in reds)) / 2
    y = (min(p[1] for p in reds) + max(p[1] for p in reds)) / 2
    expect_picked(page)
    tool.click(page, f"{x:g},{y:g}")
    expect_picked(page, "red")
    # With no name the picture is screen.png.
    assert tool.screenshot(page) == str(folder / "screen.png")
    with pytest.raises(tool.Refused, match="no name for a file"):
        tool.screenshot(page, "../out")


def test_406_6_screenshot_takes_a_comma_in_its_name(editor, folder):
    page = editor(box("a", "text", ONE))
    path = tool.screenshot(page, "4-screen,1")
    assert path == str(folder / "4-screen,1.png")
    assert size(path) == (1400, 1000)
    with pytest.raises(tool.Refused, match="no name for a file"):
        tool.screenshot(page, "../out")


@pytest.mark.parametrize("name, args", [("PDF", ()), ("Lösungen", ("Lösungen",))])
def test_pdf_saves_what_the_bars_button_sends(editor, folder, name, args):
    page = editor(box("a", "text", ONE))
    path = Path(tool.pdf(page, *args))
    assert path.parent == folder and path.suffix == ".pdf", (name, path)
    assert path.read_bytes().startswith(b"%PDF")


def test_497_pdf_with_the_variants_dialog_open_takes_the_dialogs_button(editor):
    # Issue #497: with "Varianten drucken" open, `pdf` and `pdf Lösungen` each found the bar's
    # button and the dialog's, and refused. The dialog's is the one a click can hit, and its file
    # holds one page per variant. The bar's file of this sheet would be a single page.
    page = editor(box("a", "text", ONE))
    panel = page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True)
    if not panel.is_visible():
        page.get_by_role("tab", name="Ansicht").click()
    panel.click()
    dialog = page.locator("dialog.variants")
    expect(dialog).to_be_visible()
    assert tool.where(page, "PDF").count("\n") == 1
    assert tool.where(page, "Lösungen").count("\n") == 1
    plain = PdfReader(io.BytesIO(Path(tool.pdf(page)).read_bytes()))
    assert len(plain.pages) == 2
    expect(dialog).to_be_visible()
    key = PdfReader(io.BytesIO(Path(tool.pdf(page, "Lösungen")).read_bytes()))
    assert len(key.pages) == 2


def test_617_click_on_the_variants_pdf_saves_the_file_in_the_run_folder(editor, folder):
    # `click` on the dialog's PDF failed and the file landed in Downloads. `pdf X,Y` saved it.
    # `click "PDF"` and a click at that button's place do what `pdf` does (#617).
    page = editor(box("a", "text", ONE))
    panel = page.locator(".panel").get_by_role("button", name="Varianten drucken", exact=True)
    if not panel.is_visible():
        page.get_by_role("tab", name="Ansicht").click()
    panel.click()
    dialog = page.locator("dialog.variants")
    expect(dialog).to_be_visible()
    plain = Path(tool.click(page, "PDF"))
    assert plain.parent == folder and plain.suffix == ".pdf"
    assert plain.read_bytes().startswith(b"%PDF")
    assert len(PdfReader(io.BytesIO(plain.read_bytes())).pages) == 2
    expect(dialog).to_be_visible()
    # The same button by its place: `pdf X,Y` saved the file, `click X,Y` did not.
    place = xy(dialog.get_by_role("button", name="Lösungen", exact=True))
    key = Path(tool.click(page, place))
    assert key.parent == folder and key.suffix == ".pdf"
    assert len(PdfReader(io.BytesIO(key.read_bytes())).pages) == 2


def test_pdf_gives_the_focus_back_to_the_slider_that_had_it(editor):
    # Issue #321: after `pdf` the bar's button had the focus, and `key End` did nothing.
    page = shape(editor)
    tool.click(page, "Randstärke")
    expect(slider(page)).to_be_focused()
    tool.pdf(page)
    expect(slider(page)).to_be_focused()
    tool.key(page, "End")
    expect(slider(page)).to_have_value("3")


def test_open_goes_to_a_path_of_the_app(editor, server):
    page = editor(box("a", "text", ONE))
    said = tool.go(page, "/")
    assert said.startswith("opened /: ")
    assert page.url == f"{server}/"
    expect(page.get_by_text("Neues Blatt", exact=True)).to_be_visible()


@pytest.mark.parametrize(
    "path",
    ["/admin", "/admin/users", "/Admin", "/x/../admin", "/%61dmin", "/admin?x=1", "/admin#x"],
)
def test_open_refuses_the_admin_page(editor, path):
    page = editor(box("a", "text", ONE))
    was = page.url
    with pytest.raises(tool.Refused, match="admin page"):
        tool.go(page, path)
    assert page.url == was


@pytest.mark.parametrize("path", ["/api", "/api/sheets", "/API/me", "/x/../api/me", "/%61pi/me"])
def test_open_refuses_what_the_pages_ask_the_server(editor, path):
    page = editor(box("a", "text", ONE))
    was = page.url
    with pytest.raises(tool.Refused, match="under /api"):
        tool.go(page, path)
    assert page.url == was


@pytest.mark.parametrize(
    "path",
    ["http://example.com/", "//example.com/", "/\\example.com", "javascript:alert(1)", "blatt/1"],
)
def test_open_refuses_what_is_no_path_of_the_app(editor, path):
    page = editor(box("a", "text", ONE))
    was = page.url
    with pytest.raises(tool.Refused, match="not a path of the app"):
        tool.go(page, path)
    assert page.url == was
