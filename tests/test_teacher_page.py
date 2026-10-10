"""The window of the session that only uses the app: scripts/teacher-page.py.

Each verb is called on the editor's page as the command line calls it, and the test sees what
came of it. The last test runs the command line itself, in a real window: start, a login by the
verbs alone, stop.
"""

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import expect
from test_bar import TIP
from ui import (
    FIELD,
    PASSWORD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    expect_picked,
    saved,
    sheet,
    user,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "teacher-page.py"
spec = importlib.util.spec_from_file_location("teacher_page", SCRIPT)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

ONE = {**TEXT, "text": "Eins"}
TWO = {**TEXT, "text": "Zwei"}
RED = {**RECT, "fill": "#ff0000", "stroke": "none"}
POPUP = ".panel input[type=color]:open"


@pytest.fixture(autouse=True)
def folder(tmp_path, monkeypatch, server):
    """The tool writes into a folder of the test and knows the test's server as the app."""
    made = tmp_path / "teacher-run"
    made.mkdir()
    monkeypatch.setattr(tool, "STATE", made)
    monkeypatch.setattr(tool, "BASE", server)
    return made


def xy(found):
    """The middle of what the locator finds, as a TARGET of the command line."""
    x, y = centre(found)
    return f"{x:g},{y:g}"


def middle(found):
    """The same, as the tool prints a place it found by name: in whole px."""
    return ",".join(str(round(v)) for v in centre(found))


def slider(page):
    return page.locator(".panel").get_by_label("Randstärke", exact=True)


def shape(editor, client=None):
    """A picked shape, and its panel turned down to the border: the slider lies below the window."""
    page = editor(box("a", "shape", RECT), client=client)
    tool.click(page, xy(at(page, "a")))
    expect(slider(page)).to_have_value("0.5")
    with pytest.raises(tool.Refused, match='"Randstärke" lies outside the window'):
        tool.click(page, "Randstärke")
    tool.wheel(page, "Füllung und Rand", "400")
    expect(slider(page)).to_be_in_viewport(ratio=1)
    return page


def size(path):
    return Image.open(path).size


def scrolled(page):
    return page.locator(".desk").evaluate("el => el.scrollTop")


# The mouse


def test_click_on_a_blocks_words_picks_it_and_shows_the_window(editor, folder):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    said = tool.click(page, "Zwei")
    expect_picked(page, "b")
    assert said == f"clicked at {middle(at(page, 'b').get_by_text('Zwei'))}: {folder / 'last.png'}"
    assert size(folder / "last.png") == (1400, 1000)


def test_shift_click_adds_a_second_block_to_the_first(editor):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    tool.click(page, "Eins")
    expect_picked(page, "a")
    tool.shift_click(page, "Zwei")
    expect_picked(page, "a", "b")


def test_double_click_at_a_table_cell_opens_it_and_type_writes_there(editor):
    page = editor(box("t", "table", TABLE))
    tool.double_click(page, xy(at(page, "t").get_by_text("Z", exact=True)))
    cell = at(page, "t").locator("textarea")
    expect(cell).to_be_focused()
    expect(cell).to_have_value("Z")
    tool.type_(page, "9")
    expect(cell).to_have_value("Z9")


def test_hover_on_an_icon_by_its_name_shows_that_name(editor):
    page = editor(box("a", "text", ONE))
    button = page.get_by_label("Format und Ansicht", exact=True)
    assert button.evaluate(TIP) is None
    said = tool.hover(page, "Format und Ansicht")
    assert said.startswith(f"mouse at {middle(button)}: ")
    assert button.evaluate(TIP)["content"] == '"Format und Ansicht"'


def test_drag_moves_a_block_and_undo_takes_it_back(editor):
    page = editor(box("a", "text", ONE))
    was = at(page, "a").bounding_box()
    x, y = centre(at(page, "a"))
    tool.drag(page, "Eins", f"{x + 100:g},{y + 150:g}")
    expect_picked(page, "a")
    now = at(page, "a").bounding_box()
    # The block may snap to the sheet, by less than it was moved.
    assert abs(now["x"] - was["x"] - 100) < 40 and abs(now["y"] - was["y"] - 150) < 40, now
    tool.key(page, "Control+z")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    assert at(page, "a").bounding_box() == was


def test_drag_along_the_slider_moves_it(editor):
    client = user()
    page = shape(editor, client)
    on = slider(page).bounding_box()
    y = on["y"] + on["height"] / 2
    tool.drag(page, f"{on['x'] + 10:g},{y:g}", f"{on['x'] + on['width'] - 2:g},{y:g}")
    expect(slider(page)).to_have_value("3")
    assert saved(page, client)[0]["props"]["strokeWidth"] == 3


def test_wheel_scrolls_the_desk_down_and_up(editor):
    page = editor(box("a", "text", ONE), pages=[{"blocks": []}])
    assert scrolled(page) == 0
    tool.wheel(page, xy(page.locator(".desk")), "300")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 300")
    tool.wheel(page, xy(page.locator(".desk")), "-200")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 100")
    with pytest.raises(tool.Refused, match='"down" is not a number'):
        tool.wheel(page, "5,5", "down")


# The keys


def test_key_moves_the_slider_randstaerke_after_a_click_on_its_name(editor):
    client = user()
    page = shape(editor, client)
    # The click lands on the slider's middle: it takes the focus, and the knob jumps there.
    tool.click(page, "Randstärke")
    expect(slider(page)).to_be_focused()
    expect(slider(page)).to_have_value("1.5")
    said = tool.key(page, "ArrowRight", "3")
    assert said.startswith("pressed ArrowRight 3 times: ")
    expect(slider(page)).to_have_value("2.25")
    assert saved(page, client)[0]["props"]["strokeWidth"] == 2.25
    expect_picked(page, "a")


def test_key_takes_a_chord(editor):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    tool.key(page, "Control+a")
    expect_picked(page, "a", "b")


def test_type_writes_into_the_text_that_enter_opened(editor):
    page = editor(box("a", "text", ONE))
    tool.click(page, "Eins")
    tool.key(page, "Enter")
    said = tool.type_(page, "du da")
    assert said.startswith("typed 5 letters: ")
    expect(page.locator(FIELD)).to_have_text("du da")


@pytest.mark.native
def test_key_arrow_and_enter_pick_a_colour_in_the_real_picker(editor):
    page = editor(box("a", "text", ONE))
    words = at(page, "a").get_by_text("Eins")
    field = page.locator(".panel").get_by_label("Farbe", exact=True)
    tool.click(page, "Eins")
    expect(words).to_have_css("color", "rgb(34, 34, 34)")
    tool.click(page, "Farbe")
    expect(field).to_be_focused()
    expect(page.locator(POPUP)).to_have_count(1)
    # The picker is `:open` before it listens: an arrow that came too early is pressed again.
    for _ in range(5):
        tool.key(page, "ArrowRight")
        if field.input_value() != "#222222":
            break
    expect(field).not_to_have_value("#222222")
    tool.key(page, "Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    expect(words).not_to_have_css("color", "rgb(34, 34, 34)")


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
    assert tool.where(login, "E-Mail") == f"E-Mail at {middle(login.locator('#email'))}"
    context.close()


def test_resize_sets_the_windows_size(editor, folder):
    page = editor(box("a", "text", ONE))
    said = tool.resize(page, "900", "700")
    assert said == f"window is 900 x 700: {folder / 'last.png'}"
    assert page.evaluate("[innerWidth, innerHeight]") == [900, 700]
    assert size(folder / "last.png") == (900, 700)


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


@pytest.mark.parametrize("name, args", [("PDF", ()), ("Lösungen", ("Lösungen",))])
def test_pdf_saves_what_the_bars_button_sends(editor, folder, name, args):
    page = editor(box("a", "text", ONE))
    path = Path(tool.pdf(page, *args))
    assert path.parent == folder and path.suffix == ".pdf", (name, path)
    assert path.read_bytes().startswith(b"%PDF")


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


# What the tool refuses


def test_click_refuses_a_name_that_is_not_on_the_page(editor):
    page = editor(box("a", "text", ONE))
    with pytest.raises(tool.Refused, match='nothing on the page is called "Drei"'):
        tool.click(page, "Drei")
    expect_picked(page)


def test_click_refuses_a_name_that_is_there_twice_and_lists_the_places(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    places = [middle(at(page, name).get_by_text("Hallo")) for name in "ab"]
    with pytest.raises(tool.Refused) as refused:
        tool.click(page, "Hallo")
    assert str(refused.value) == (
        f'"Hallo" is on the page 2 times, at {places[0]}, {places[1]}: give one as X,Y'
    )
    expect_picked(page)
    # One of the listed places is a target.
    tool.click(page, places[1])
    expect_picked(page, "b")


def run(folder, server, *words):
    """The command line, as `mise run teacher:page --` calls it."""
    env = {**os.environ, "TEACHER_PAGE_DIR": str(folder), "TEACHER_PAGE_URL": server}
    return subprocess.run(
        [sys.executable, SCRIPT, *words], env=env, capture_output=True, text=True, timeout=120
    )


@pytest.mark.parametrize(
    "words, said",
    [
        (["click", "PDF"], "no page is running: start it first, with the verb `start`\n"),
        (["click"], "click takes: TARGET\n"),
        (["press", "Enter"], 'no verb "press": there are start, stop, open, click'),
        ([], 'no verb "": there are start, stop, open, click'),
    ],
)
def test_the_command_line_refuses_in_plain_words_and_fails(folder, server, words, said):
    done = run(folder, server, *words)
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.startswith(said) and "Traceback" not in done.stderr


def test_stop_with_nothing_running_says_so_and_is_no_failure(folder, server):
    done = run(folder, server, "stop")
    assert (done.returncode, done.stdout, done.stderr) == (0, "no page was running\n", "")


def left(folder):
    """The processes that still name the folder: the browser has its profile there."""
    found = []
    for words in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            said = words.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        if str(folder) in said:
            found.append(said[:200])
    return found


@pytest.mark.native
def test_the_command_line_starts_a_window_logs_in_by_the_verbs_alone_and_stops(folder, server):
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    made = sheet(client, [box("a", "text", {**ONE, "color": "#222222"})])

    def colour():
        """The text's colour as the server holds it: the editor saves two seconds after a change."""
        blocks = client.get(f"/api/sheets/{made['id']}").json()["doc"]["pages"][0]["blocks"]
        return blocks[0]["props"].get("color")

    def call(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout.strip()

    try:
        assert call("start") == f"started: a window of 1280 x 1024 on {server}"
        # A second start replaces the first: one window, and a profile with no login in it.
        first = left(folder)
        assert call("start") == f"started: a window of 1280 x 1024 on {server}"
        assert len(left(folder)) == len(first)
        assert call("where", "Anmelden").count("\n") == 1
        call("click", "E-Mail")
        call("type", email)
        call("click", "Passwort")
        call("type", PASSWORD)
        call("key", "Enter")
        # The session cookie is Secure and the server speaks http: Chromium keeps it on 127.0.0.1.
        place = call("where", "Neues Blatt")
        assert place.startswith("Neues Blatt at "), place
        shot = Path(call("screenshot", "home"))
        assert shot == folder / "home.png" and size(shot) == (1280, 1024)
        # The mouse stays where one call left it: the next call's picture still shows the hover.
        said = call("hover", "Neues Blatt")
        assert said == f"mouse at {place.split()[-1]}: {folder / 'last.png'}"
        over = Image.open(call("screenshot", "over")).convert("RGB")
        assert ImageChops.difference(Image.open(shot).convert("RGB"), over).getbbox()
        assert size(folder / "last.png") == (1280, 1024)
        call("resize", "1500", "1100")
        assert size(call("screenshot")) == (1500, 1100)
        call("resize", "1280", "1024")
        # A colour, each key a call of its own: the picker stays open between them.
        assert call("open", f"/blatt/{made['id']}").startswith(f"opened /blatt/{made['id']}: ")
        # The tour opens on a first visit and lies over the sheet.
        call("click", "Beenden")
        call("click", "Eins")
        call("click", "Farbe")
        call("key", "ArrowRight")
        call("key", "Enter")
        late = time.monotonic() + 10
        while colour() == "#222222" and time.monotonic() < late:
            time.sleep(0.1)
        assert colour() not in ("#222222", None)
        assert call("stop") == "stopped"
    finally:
        run(folder, server, "stop")
    late = time.monotonic() + 10
    while left(folder) and time.monotonic() < late:
        time.sleep(0.1)
    assert left(folder) == []
    done = run(folder, server, "hover", "Neues Blatt")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr == "no page is running: start it first, with the verb `start`\n"
