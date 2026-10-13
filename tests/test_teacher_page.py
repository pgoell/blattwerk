"""The window of the session that only uses the app: scripts/teacher-page.py.

Each verb is called on the editor's page as the command line calls it, and the test sees what
came of it. The last test runs the command line itself, in a real window: start, a login by the
verbs alone, stop.
"""

import importlib.util
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from PIL import Image, ImageChops
from playwright.sync_api import expect
from test_bar import TIP
from ui import (
    BROWSER,
    FIELD,
    PASSWORD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    expect_picked,
    maths,
    pick,
    saved,
    sheet,
    user,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "teacher-page.py"
spec = importlib.util.spec_from_file_location("teacher_page", SCRIPT)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

# The tool opens Chromium and no other browser, so the WebKit lane has nothing to learn here.
pytestmark = pytest.mark.skipif(BROWSER != "chromium", reason="the tool's window is Chromium")

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
    assert tool.where(page, "Randstärke").endswith("(outside the window)")
    # A heading of the panel that lies in the window: the one over the border has moved below it.
    tool.wheel(page, "Schrift", "400")
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


def test_406_1_click_takes_the_button_when_a_heading_shares_its_name(editor):
    # With a text picked, the left panel's button and the right panel's heading are both "Text".
    page = editor(box("a", "text", ONE))
    tool.click(page, "Eins")
    expect_picked(page, "a")
    button = page.get_by_label("Text", exact=True)
    said = tool.click(page, "Text")
    assert said.startswith(f"clicked at {middle(button)}: ")
    # The button adds a text, and the new one is picked.
    expect(page.locator(".block")).to_have_count(2)
    expect(at(page, "a")).not_to_have_class("block sel")


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


def far(colour):
    """How far `#rrggbb` lies from the text's #222222, in its widest channel: 60 is plain to see."""
    return max(abs(int(colour[n : n + 2], 16) - 0x22) for n in (1, 3, 5))


@pytest.mark.native
def test_key_arrows_60_times_and_enter_pick_a_colour_the_eye_can_tell(editor):
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
        tool.key(page, "ArrowUp")
        if field.input_value() != "#222222":
            break
    expect(field).not_to_have_value("#222222")
    # As the brief's recipe says: one arrow alone is a step too small to see.
    tool.key(page, "ArrowUp", "60")
    tool.key(page, "ArrowRight", "60")
    tool.key(page, "Enter")
    expect(page.locator(POPUP)).to_have_count(0)
    picked = field.input_value()
    assert far(picked) >= 60, picked
    red, green, blue = (int(picked[n : n + 2], 16) for n in (1, 3, 5))
    # The arrows to the right gave the grey a tint.
    assert red > green
    expect(words).to_have_css("color", f"rgb({red}, {green}, {blue})")


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


def run(folder, server, *words, limit=120):
    """The command line, as `mise run teacher:page --` calls it. A call past `limit` s fails."""
    env = {**os.environ, "TEACHER_PAGE_DIR": str(folder), "TEACHER_PAGE_URL": server}
    return subprocess.run(
        [sys.executable, SCRIPT, *words], env=env, capture_output=True, text=True, timeout=limit
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


def test_stop_leaves_a_process_alone_that_only_has_the_holders_pid(folder, server):
    # The holder died without `stop` and the system gave its pid to someone else.
    other = subprocess.Popen(["sleep", "60"])
    (folder / "page.json").write_text(f'{{"pid": {other.pid}, "group": {other.pid}}}')
    done = run(folder, server, "stop")
    assert (done.returncode, done.stdout, done.stderr) == (0, "no page was running\n", "")
    assert other.poll() is None
    other.kill()
    other.wait()


def test_stop_takes_a_file_that_names_no_holder_for_nothing_running(folder, server):
    (folder / "page.json").write_text("{")
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
        # The verb's first line: the page's line after it is no part of what each call checks.
        return done.stdout.strip().splitlines()[0]

    try:
        assert call("start") == f"started: a window of 1280 x 1024 on {server}"
        # A second start replaces the first: one window, and a profile with no login in it.
        first = left(folder)
        assert call("start") == f"started: a window of 1280 x 1024 on {server}"
        assert len(left(folder)) == len(first)
        # Two places, and the page's line after them.
        lines = run(folder, server, "where", "Anmelden").stdout.splitlines()
        assert len([line for line in lines if " at " in line]) == 2, lines
        call("click", "E-Mail")
        call("type", email)
        call("click", "Passwort")
        call("type", PASSWORD)
        call("key", "Enter")
        # The session cookie is Secure and the server speaks http: Chromium keeps it on 127.0.0.1.
        place = call("where", "Neues Blatt").splitlines()[0]
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
        call("key", "ArrowUp", "60")
        call("key", "ArrowRight", "60")
        call("key", "Enter")
        late = time.monotonic() + 10
        while colour() == "#222222" and time.monotonic() < late:
            time.sleep(0.1)
        assert far(colour()) >= 60, colour()
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


def test_click_takes_the_one_control_of_a_name_beside_a_heading(editor):
    # Issue #430: "Zahlenraum" is a heading of the panel and the select that holds that label.
    client = user()
    page = editor(box("a", "maths", maths(client)), client=client)
    pick(page, "a")
    tool.click(page, "Zahlenraum")
    expect(page.get_by_label("Zahlenraum", exact=True)).to_be_focused()


def test_where_takes_a_slash_and_a_quote_in_a_name(editor):
    # Issue #430: `where "/ 7"` failed with a selector error on the slash.
    page = editor(box("a", "text", {**TEXT, "text": "12 / 7 = 5"}))
    found = at(page, "a").get_by_text("12 / 7 = 5")
    assert tool.where(page, "/ 7") == f"12 / 7 = 5 at {middle(found)}"
    with pytest.raises(tool.Refused, match="nothing on the page"):
        tool.where(page, '"/\\')


def test_where_does_not_read_a_select_as_the_text_of_its_options(editor):
    # Issue #430: `where "123"` matched a select whose options 0 to 9 ran together as "0123456789".
    page = editor(box("a", "text", ONE))
    page.evaluate(
        """() => {
            const select = document.createElement("select");
            select.setAttribute("aria-label", "Ziffern");
            for (let i = 0; i < 10; i++) select.add(new Option(String(i)));
            document.body.append(select);
        }"""
    )
    with pytest.raises(tool.Refused, match='nothing on the page is called "123"'):
        tool.where(page, "123")
    assert tool.where(page, "Ziffern").startswith("Ziffern at ")


def test_click_turns_the_page_to_the_one_control_below_the_window(editor):
    # Issue #430: after a pick the panel jumped to its top, and the slider below failed.
    page = editor(box("a", "shape", RECT))
    tool.click(page, xy(at(page, "a")))
    expect(slider(page)).to_have_value("0.5")
    said = tool.click(page, "Randstärke")
    assert said.endswith(": " + str(tool.STATE / "last.png") + " (turned the page to it)"), said
    expect(slider(page)).to_be_focused()


def test_click_says_a_greyed_control_does_nothing(editor):
    # Issue #430: `click "0"` on a greyed button reported "clicked" though nothing happened.
    page = editor(box("a", "text", ONE))
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    assert "on a greyed control: nothing happens" in tool.click(page, "Rückgängig")


def test_every_verb_says_the_page_it_is_on(editor, monkeypatch):
    # Issue #430: `open` needs the sheet's number, and the output did not print it.
    page = editor(box("a", "text", ONE))

    @contextmanager
    def joined_here():
        yield page

    monkeypatch.setattr(tool, "joined", joined_here)
    said = tool.verb("where", ("Eins",), False)
    assert said.splitlines()[-1] == f"The page is {urlsplit(page.url).path}"


def test_drag_reads_its_start_anew_once_the_page_turned_to_its_end(editor, monkeypatch):
    # The page turned to TO after FROM was read: the mouse must go down where FROM stands now.
    page = editor(box("a", "text", ONE))
    asked = []

    def point(page, target):
        asked.append(target)
        if target == "TO" and asked.count("TO") == 1:
            tool.NOTES.append("turned the page to it")
        return {"FROM": (300.0 + 10 * asked.count("FROM"), 300.0), "TO": (400.0, 400.0)}[target]

    monkeypatch.setattr(tool, "point", point)
    said = tool.drag(page, "FROM", "TO")
    assert asked == ["FROM", "TO", "FROM"]
    assert said.startswith("dragged from 320,300 to 400,400")
    assert said.endswith("(turned the page to it)")


def test_drag_refuses_two_names_that_are_never_in_the_window_together(editor, monkeypatch):
    page = editor(box("a", "text", ONE))

    def point(page, target):
        tool.NOTES.append("turned the page to it")
        return 300.0, 300.0

    monkeypatch.setattr(tool, "point", point)
    with pytest.raises(tool.Refused, match="not in the window together"):
        tool.drag(page, "FROM", "TO")
    tool.NOTES.clear()


# The downloads, the session and the boxes


def test_tidy_deletes_the_tr_pdfs_in_downloads_and_nothing_else(
    folder, server, tmp_path, monkeypatch
):
    downloads = tmp_path / "downloads"
    (downloads / "sub").mkdir(parents=True)
    monkeypatch.setenv("TEACHER_PAGE_DOWNLOADS", str(downloads))
    for name in ("TR1 Rechnen.pdf", "TR2.pdf", "TR1.png", "Other.pdf", "sub/TR4.pdf"):
        (downloads / name).write_bytes(b"%PDF")
    (downloads / "TR3.pdf").mkdir()

    done = run(folder, server, "tidy")
    assert (done.returncode, done.stderr) == (0, "")
    assert sorted(done.stdout.splitlines()) == [
        "deleted downloads/TR1 Rechnen.pdf",
        "deleted downloads/TR2.pdf",
    ]
    kept = sorted(str(path.relative_to(downloads)) for path in downloads.rglob("*"))
    assert kept == ["Other.pdf", "TR1.png", "TR3.pdf", "sub", "sub/TR4.pdf"]
    assert run(folder, server, "tidy").stdout == "nothing to delete\n"


def test_tidy_deletes_the_pdfs_that_pdf_saved_in_the_tool_folder(
    folder, server, tmp_path, monkeypatch
):
    # Issue #430: `pdf` saves into the tool's folder, and `tidy` left those files behind.
    monkeypatch.setenv("TEACHER_PAGE_DOWNLOADS", str(tmp_path / "empty"))
    (tmp_path / "empty").mkdir()
    (folder / "Blatt 3.pdf").write_bytes(b"%PDF")
    (folder / "last.png").write_bytes(b"png")

    done = run(folder, server, "tidy")
    assert (done.returncode, done.stderr) == (0, "")
    assert done.stdout == f"deleted {folder.name}/Blatt 3.pdf\n"
    assert [path.name for path in folder.iterdir()] == ["last.png"]


def test_expire_drops_the_session_and_the_page_stays(editor):
    page = editor(box("a", "text", ONE))
    said = tool.expire(page)
    assert said.startswith("the session has run out: ")
    expect(at(page, "a")).to_be_visible()
    tool.go(page, "/")
    expect(page.get_by_role("button", name="Anmelden", exact=True)).to_be_visible()


def test_a_box_is_answered_no_and_named_and_box_yes_answers_yes(browser):
    page = browser.new_page()
    asked = tool.answered(page, yes=False)
    assert page.evaluate("confirm('Weg?')") is False
    assert asked == [("confirm", "Weg?")]
    page.close()
    page = browser.new_page()
    asked = tool.answered(page, yes=True)
    assert page.evaluate("confirm('Ja?')") is True
    assert asked == [("confirm", "Ja?")]
    page.close()


def test_a_box_nobody_answered_in_time_is_answered_no(browser):
    # The holder's way: it remembers each box with its time, and `overdue` says no to the old ones.
    page = browser.new_page()
    waiting: list = []
    page.on("dialog", tool.remember(waiting))
    with page.expect_event("dialog"):
        page.evaluate("setTimeout(() => (window.said = confirm('Weg?')), 0)")
    assert len(waiting) == 1
    # A young box stays open: it is still on the list, and no answer has gone out.
    tool.overdue(waiting, now=waiting[0][1] + 1)
    assert len(waiting) == 1
    tool.overdue(waiting, now=waiting[0][1] + tool.PATIENCE + 1)
    assert waiting == []
    page.wait_for_function("window.said === false")
    assert page.evaluate("1 + 1") == 2
    page.close()


def test_a_box_a_verb_answered_first_is_no_error_for_the_holder(browser):
    page = browser.new_page()
    waiting: list = []
    page.on("dialog", tool.remember(waiting))
    asked = tool.answered(page, yes=True)
    with page.expect_event("dialog"):
        page.evaluate("setTimeout(() => (window.said = confirm('Ja?')), 0)")
    page.wait_for_function("window.said === true")
    # The second answer raises inside `overdue`, and the holder shrugs it off.
    tool.overdue(waiting, now=waiting[0][1] + tool.PATIENCE + 1)
    assert waiting == []
    assert asked == [("confirm", "Ja?")]
    page.close()


@pytest.mark.parametrize("words", [["box"], ["box", "yes"], ["box", "maybe", "click", "PDF"]])
def test_box_refuses_what_is_no_answer_in_plain_words(folder, server, words):
    done = run(folder, server, *words)
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.startswith('box takes yes or no, then a verb: box yes click "Löschen"')
    assert "Traceback" not in done.stderr


@pytest.mark.native
def test_a_click_on_a_box_names_it_and_box_yes_takes_the_yes_answer(folder, server):
    # The app's delete asks `Blatt „Probe“ löschen?`: the plain click says no, `box yes` says yes.
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    made = sheet(client, [box("a", "text", ONE)], title="Probe")

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        ok("where", "Neues Blatt")
        said = ok("click", "Probe löschen")
        assert 'A box asked: "Blatt „Probe“ löschen?" (confirm). Answered no.' in said
        assert client.get(f"/api/sheets/{made['id']}").status_code == 200
        said = ok("box", "yes", "click", "Probe löschen")
        assert "Answered yes." in said
        assert client.get(f"/api/sheets/{made['id']}").status_code == 404
    finally:
        run(folder, server, "stop")


@pytest.mark.native
def test_open_meets_the_leave_question_stays_on_no_and_goes_on_box_yes(folder, server):
    # A typed text is an unsaved change until the save goes out, two seconds on: `open` comes first.
    email = f"{uuid4().hex}@example.com"
    client = user(email)
    made = sheet(client, [box("a", "text", ONE)], title="Probe")

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        ok("click", "Probe")
        ok("where", "Gespeichert")
        ok("click", "Eins")
        ok("key", "Enter")
        ok("type", " Neu")
        ok("key", "Escape")
        said = ok("open", "/")
        assert 'A box asked: "" (beforeunload). Answered no.' in said
        assert "To say yes: box yes open /" in said
        assert ok("where", "Neu").startswith("Neu at ")
        ok("box", "yes", "open", "/")
        assert ok("where", "Neues Blatt").startswith("Neues Blatt at ")
    finally:
        run(folder, server, "stop")
    assert client.get(f"/api/sheets/{made['id']}").status_code == 200


@pytest.mark.native
def test_a_box_left_open_by_a_dead_verb_is_answered_no_and_the_next_verb_acts(
    folder, server, playwright
):
    # The verb's client is gone with its box open: only the holder can answer that box now.
    limit = tool.PATIENCE + 10

    def join():
        """A client of the holder's window, as a verb is one, on the suite's own Playwright."""
        client = playwright.chromium.connect_over_cdp(tool.running()["endpoint"])
        page = client.contexts[0].pages[0]
        # A client that answers nothing: Playwright would otherwise dismiss the box by itself.
        page.on("dialog", lambda dialog: None)
        return client, page

    try:
        started = run(folder, server, "start")
        assert started.returncode == 0, (started.stdout, started.stderr)
        client, page = join()
        with page.expect_event("dialog"):
            page.evaluate("setTimeout(() => (window.said = confirm('Weg?')), 0)")
        client.close()
        # The page waits on the open box; the holder's no is what frees it for the next verb.
        done = run(folder, server, "where", "Anmelden", limit=limit)
        assert done.returncode == 0, (done.stdout, done.stderr)
        assert done.stdout.startswith("Anmelden at ") and "A box asked" not in done.stdout
        client, page = join()
        assert page.evaluate("window.said") is False
        client.close()
    finally:
        run(folder, server, "stop")


@pytest.mark.native
def test_einfuegen_pastes_what_ctrl_c_copied_in_the_window(folder, server):
    # Issue #430: the bar's Einfügen read the clipboard, and the window never answered its question.
    email = f"{uuid4().hex}@example.com"
    client = user(email)

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        said = ok("click", "Neues Blatt")
        found = re.search(r"The page is /blatt/(\w+)", said)
        assert found, said
        sheet_id = found.group(1)
        ok("click", "Beenden")
        ok("click", "Text")
        ok("type", "Hallo")
        ok("key", "Escape")
        ok("key", "Control+c")
        ok("click", "Einfügen")

        def blocks():
            return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]

        late = time.monotonic() + 10
        while len(blocks()) < 2 and time.monotonic() < late:
            time.sleep(0.1)
        assert len(blocks()) == 2
    finally:
        run(folder, server, "stop")
