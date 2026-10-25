"""The teacher-page command line drives the window, and a verb turns the page to its control."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from PIL import (
    Image,
    ImageChops,
)
from playwright.sync_api import expect
from test_teacher_page import (
    ONE,
    below,
    far,
    folder,  # noqa: F401
    left,
    middle,
    pytestmark,  # noqa: F401
    run,
    size,
    slider,
    tool,
    xy,
)
from ui import (
    PASSWORD,
    RECT,
    RULING,
    TEXT,
    at,
    box,
    maths,
    pick,
    sheet,
    user,
)


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


def test_497_click_seitenbreite_is_the_one_panel_button(editor):
    # Issue #497, sheet 2: `click "Seitenbreite"` found the panel's button and the zoom's.
    # The zoom's button is now "Zoom", and "Seitenbreite" is in its list only while that list
    # is open. With the list shut the click is the panel's, and the ruling grows to the page.
    page = editor(box("a", "ruling", {**RULING, "kind": "l2"}, w=80))
    pick(page, "a")
    button = page.locator(".panel").get_by_role("button", name="Seitenbreite", exact=True)
    expect(button).to_be_visible()
    expect(page.locator("dialog.menu")).to_have_count(0)
    lines = tool.where(page, "Seitenbreite").splitlines()
    assert lines == [line for line in lines if line.startswith("Seitenbreite at ")], lines
    assert len(lines) == 1
    wide = at(page, "a").evaluate("e => getComputedStyle(e).width")
    said = tool.click(page, "Seitenbreite")
    assert said.startswith("clicked at "), said
    expect(at(page, "a")).not_to_have_css("width", wide)


def test_497_click_turns_to_the_one_list_that_shares_a_headings_name(editor):
    # Issue #497: "Aufgabenfamilien" is a heading and the list. With both below the window the
    # turn to the one control and the preference for that control did not combine, and the click
    # said to scroll.
    client = user()
    page = editor(box("a", "maths", maths(client)), client=client)
    pick(page, "a")
    select = page.locator(".panel").get_by_label("Aufgabenfamilien", exact=True)
    expect(select).to_be_attached()
    below(page, "Aufgabenfamilien")
    lines = tool.where(page, "Aufgabenfamilien").splitlines()
    assert len(lines) == 2
    assert all("(outside the window)" in line for line in lines), lines
    said = tool.click(page, "Aufgabenfamilien")
    assert said.endswith("(turned the page to it)"), said
    expect(select).to_be_focused()


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
