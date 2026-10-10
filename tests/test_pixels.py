"""The print matches the screen: each kind of block, level and turned, pixel by pixel."""

import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pixels import LIMIT, LOADED, as_png, diff, screen_and_print
from playwright.sync_api import expect
from ui import BROWSER, LINE, RECT, RULING, TABLE, TEXT, box, maths, pick, png, sheet, user

from blattwerk import pdf

SHOT = Path(__file__).parent.parent / "scripts" / "shot.py"
FILLED = {**RECT, "fill": "#ffd43b", "strokeWidth": 1}
WORDS = {**TEXT, "text": "Der Igel sucht im Herbst nach Futter und baut sich ein Nest aus Laub."}
LONG = (
    "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter und baut sich aus Laub ein "
    "warmes Nest. Die Eichhörnchen sammeln Nüsse und verstecken sie überall im Garten, damit "
    "sie im Winter genug zu fressen haben. Manchmal vergessen sie ein Versteck, und im "
    "Frühling wächst dort ein neuer Baum. Die Vögel ziehen in den Süden."
)
FULLER = ["school script", "lists", "table", "strokes", "dashes", "pictures", "rulings on its side"]
KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group", "name", "points"]
# A table and a line stay level: the panel Format shuts "Drehung" for them and the selection has
# no handle to turn them by. A line points where its two ends are.
TURNED = [kind for kind in KINDS if kind not in ("table", "line")]


def photo(client):
    """A picture of four fields, each of its own colour: turned or flipped it shows another one."""
    # Of more pixels than the page shows it with: made larger, a picture's fields run into one
    # another in the browser and stay sharp in pdfium.
    made = Image.new("RGB", (1200, 800), "#1c7ed6")
    made.paste("#2f9e44", (600, 0, 1200, 400))
    made.paste("#f08c00", (0, 400, 600, 800))
    made.paste("#e03131", (600, 400, 1200, 800))
    data = io.BytesIO()
    made.save(data, "PNG")
    files = {"file": ("bild", data.getvalue(), "image/png")}
    return {"upload": client.post("/api/uploads", files=files).json()["id"], "ratio": 1.5}


def blocks(kind, client, **more):
    """The blocks of one kind in the middle of the page, 120 mm wide; `more` goes to each."""
    props = {
        "text": lambda: [("text", WORDS, 30)],
        "shape": lambda: [("shape", FILLED, 40)],
        "line": lambda: [("shape", {**LINE, "strokeWidth": 1}, 30)],
        "picture": lambda: [("image", {**photo(client), "cut": [0, 0, 0, 0]}, 80)],
        "table": lambda: [("table", {**TABLE, "line": "#222222"}, 30)],
        "ruling": lambda: [("ruling", RULING, 40)],
        "maths": lambda: [("maths", maths(client), 12)],
        "group": lambda: [("text", WORDS, 30), ("shape", FILLED, 30)],
        "name": lambda: [("name", {}, 10)],
        "points": lambda: [("points", {"max": 10}, 10)],
    }[kind]()
    group = {"group": ["g"]} if kind == "group" else {}
    return [
        {**box(f"b{i}", type_, props_, x=45, y=100 + 45 * i, w=120, h=h), **group, **more}
        for i, (type_, props_, h) in enumerate(props)
    ]


def at(kind, props, y=60, h=60, **more):
    return box(f"b{y}", kind, props, **{"x": 45, "y": y, "w": 120, "h": h, **more})


def para(text, **more):
    return {"runs": [{"text": text}], **more}


def fuller(case, client):
    """A page with more on it than one plain block: where a line breaks, a list, dashes, a cut."""
    if case == "school script":
        # Bold and in a school's script, 120 mm wide: seven rows.
        return [at("text", {**TEXT, "text": LONG, "font": "sas", "bold": True}, h=120)]
    if case == "lists":
        listed = [
            para(f"Erstens {LONG[:70]}", list="bullet"),
            para("Zweitens", list="bullet"),
            para("Darunter", list="bullet", level=1),
            para("Ein Absatz dazwischen."),
            para(f"Eins {LONG[90:160]}", list="number"),
            para("Zwei", list="number"),
        ]
        words = "\n".join(p["runs"][0]["text"] for p in listed)
        return [
            at("text", {**TEXT, "text": words, "rich": listed}, h=80),
            at("text", {**TEXT, "text": LONG, "size": 24, "align": "right"}, y=150, h=130),
        ]
    if case == "table":
        cells = [
            ["Hunderter", "Zehner", "Einer", "Summe"],
            ["Donaudampfschifffahrtsgesellschaft und mehr", "3", "7", ""],
            ["ein langer Satz der in der Zelle umbricht", "", "12", "x"],
            ["1", "2", "3", "4"],
        ]
        look = {"cols": [2, 1, 1, 1], "size": 14, "align": "center", "line": "#222222"}
        return [at("table", {**look, "cells": cells, "head": True}, h=80)]
    if case == "strokes":
        thick = {**RECT, "strokeWidth": 3}
        half = {"x": 120, "w": 60}
        return [
            at("shape", {**thick, "dash": "dashed"}, y=30, h=30),
            at(
                "shape",
                {**thick, "kind": "circle", "fill": "#ffd43b", "dash": "dotted"},
                y=70,
                h=40,
            ),
            at("shape", {**thick, "kind": "star", "text": "Stern"}, y=120, h=50, w=60),
            at("shape", {**FILLED, "kind": "rounded", "text": "Rund"}, y=121, h=30, **half),
            at("shape", {**thick, "kind": "bubble", "text": "Blase"}, y=180, h=40, w=60),
            at("shape", {**thick, "kind": "triangle", "opacity": 0.5}, y=181, h=30, **half),
            at("shape", {**LINE, "strokeWidth": 2, "dash": "dashed", "kind": "arrow"}, y=270, h=10),
        ]
    if case == "dashes":
        # Each kind of box that has a border, and a text with one: level, and turned over a fill.
        thick = {**RECT, "strokeWidth": 3}
        edged = {**WORDS, "stroke": "#222222", "strokeWidth": 1, "dash": "dashed"}
        return [
            at("shape", {**thick, "kind": "rounded", "dash": "dashed"}, y=30, h=30),
            at("shape", {**thick, "dash": "dotted"}, y=70, h=30),
            at("shape", {**thick, "kind": "circle", "dash": "dashed"}, y=110, h=40),
            at("text", edged, y=160, h=30),
            at("text", {**edged, "fill": "#ffd43b"}, y=215, h=40, angle=30),
        ]
    if case == "pictures":
        # A quarter cut off the left and half off the bottom: the blue field and a strip of green.
        cut = {**photo(client), "cut": [0.25, 0, 0, 0.5]}
        whole = {**cut, "cut": [0, 0, 0, 0]}
        return [
            at("image", cut, y=30, h=40, w=90),
            at("image", cut, y=80, h=40, w=90, flipX=True),
            at("image", whole, y=150, h=80, flipY=True, angle=30),
        ]
    kinds = ("l1", "l2", "l3", "lines", "k5", "k7")
    rulings = [
        at("ruling", {"kind": kind, "color": "#222222"}, y=15 + 30 * i, h=30, x=15 + 135 * (i % 2))
        for i, kind in enumerate(kinds)
    ]
    written = {"kind": "l1", "color": "#222222", "text": "Igel", "trace": True}
    return {"blocks": [*rulings, at("ruling", written, y=150, h=40, x=150)], "landscape": True}


def share(browser, server, client, *pages):
    """The share of the first page's pixels that differ between the editor and the PDF."""
    return diff(*screen_and_print(browser, server, client, sheet(client, *pages)["id"]))[0]


@pytest.mark.parametrize("kind", KINDS)
def test_a_block_prints_as_the_screen_shows_it(browser, server, kind):
    client = user()
    assert share(browser, server, client, blocks(kind, client)) < LIMIT


@pytest.mark.parametrize("kind", TURNED)
def test_a_turned_block_prints_as_the_screen_shows_it(browser, server, kind):
    client = user()
    # Not a right angle: that would hide a turn about another point.
    assert share(browser, server, client, blocks(kind, client, angle=30)) < LIMIT


@pytest.mark.parametrize("case", FULLER)
def test_a_fuller_page_prints_as_the_screen_shows_it(browser, server, case):
    client = user()
    assert share(browser, server, client, fuller(case, client)) < LIMIT


def test_the_zoom_and_the_page_number_are_no_difference(browser, server):
    client = user()
    # Three pages: the last ones lie where the zoom and "Seite 1 von 3" float over the desk.
    mine = sheet(client, *(blocks(kind, client) for kind in ("text", "shape", "ruling")))["id"]
    for page in (1, 2):
        assert diff(*screen_and_print(browser, server, client, mine, page))[0] < LIMIT


def test_a_block_that_prints_elsewhere_is_over_the_limit(browser, server):
    client = user()
    # A sentence 10 mm lower: far less of the page than a filled box.
    here, there = (sheet(client, blocks("text", client, y=y))["id"] for y in (100, 110))
    screen, _ = screen_and_print(browser, server, client, here)
    _, printed = screen_and_print(browser, server, client, there)
    found = diff(screen, printed)[0]
    assert found > LIMIT, found


def test_grid_and_guide_lines_are_no_difference(browser, server):
    client = user()
    page = {"blocks": blocks("text", client), "grid": 5, "guides": {"x": [50], "y": [80]}}
    assert share(browser, server, client, page) < LIMIT


def test_diff_counts_the_pixels_that_differ():
    red, white = png(), png(b"\xff\xff\xff")
    assert diff(red, red)[0] == 0
    assert diff(red, white)[0] == 1
    # Less than the tolerance apart is the same: an edge that is smoothed another way.
    assert diff(png(b"\xff\xff\xff"), png(b"\xd0\xd0\xd0"))[0] == 0
    # A page cut to half its height differs by the half that is gone; a row of rounding does not.
    page = Image.new("RGB", (200, 300), "white")
    assert diff(as_png(page), as_png(page.crop((0, 0, 200, 150))))[0] == 0.5
    assert diff(as_png(page), as_png(page.crop((0, 0, 200, 299))))[0] == 0
    marked = Image.open(io.BytesIO(diff(red, white)[1]))
    assert marked.size == (3, 2) and marked.convert("RGB").getpixel((0, 0)) == (255, 0, 0)


def test_shot_writes_the_diff_and_prints_the_share(tmp_path):
    pages = tmp_path / "pages.json"
    pages.write_text(json.dumps([[box("a", "text", TEXT)]]))
    out = tmp_path / "out"
    run = subprocess.run(
        [sys.executable, str(SHOT), str(pages), str(out)], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    assert {p.name for p in out.iterdir()} == {"screen.png", "pdf.png", "diff.png"}
    found = re.search(r"([\d.]+) % of the pixels differ", run.stdout)
    assert found and float(found[1]) < LIMIT * 100


def grey(browser, server, client, page):
    """The page on the screen and in the PDF, in grey and both of the screen's size."""
    mine = sheet(client, page)["id"]
    screen, printed = (
        Image.open(io.BytesIO(data)).convert("L")
        for data in screen_and_print(browser, server, client, mine)
    )
    # pdfium rounds a page's size up: a pixel more would move every part cut out by a pixel.
    return screen, printed.crop((0, 0, *screen.size))


def dark(image, part, down=True):
    """How dark each row of pixels is, from 0 to 1, in the `part` of an upright page given in mm.

    Each column with `down` off.
    """
    cut = image.crop(tuple(round(v * image.width / 210) for v in part))
    # Each row as the mean of its pixels.
    rows = cut.resize((1, cut.height) if down else (cut.width, 1), Image.Resampling.BOX)
    return [1 - v / 255 for v in rows.tobytes()]


def runs(rows):
    """Each stretch of rows with ink in it: its first row, its darkest and the darkness summed."""
    found, start = [], None
    for i, v in enumerate([*rows, 0]):
        if v > 0.05 and start is None:
            start = i
        elif v <= 0.05 and start is not None:
            found.append((start, max(rows[start:i]), sum(rows[start:i])))
            start = None
    return found


def test_a_tables_lines_are_as_wide_and_as_dark_as_they_print(browser, server):
    """A4"""
    client = user()
    page = blocks("table", client)
    screen, printed = grey(browser, server, client, page)
    x, y, w, h = (page[0][side] for side in "xywh")
    # Clear of the letters: a strip down the first column and one along the first row.
    for part, down in (
        ((x + 10, y - 3, x + 14, y + h + 3), True),
        ((x - 3, y + 1, x + w + 3, y + 2), False),
    ):
        shown, paper = (runs(dark(picture, part, down)) for picture in (screen, printed))
        assert len(shown) == len(paper) == 3
        for (_, darkest, ink), (_, on_paper, printed_ink) in zip(shown, paper, strict=True):
            # The ink is the line's width in pixels times its darkness. pdfium fills every pixel a
            # line touches, half a pixel more than the browser draws: 2.2 against 1.8.
            assert abs(darkest - on_paper) < 0.05, (darkest, on_paper)
            assert abs(ink - printed_ink) < 0.5, (ink, printed_ink)


# Each cell of a table and each cell's text: left, top, width and height in the page's own pixels.
PLACES = """() => {
    const page = document.querySelector('.scaled');
    const from = page.getBoundingClientRect(), k = from.width / page.offsetWidth;
    return [...document.querySelectorAll('.table > div, .table p')].map((el) => {
        const r = el.getBoundingClientRect();
        return [(r.x - from.x) / k, (r.y - from.y) / k, r.width / k, r.height / k];
    });
}"""


def test_a_tables_cells_lie_where_they_print(browser, server):
    """I7"""
    client = user()
    mine = sheet(client, fuller("table", client))["id"]
    # A sharp screen, as an iPad has: there WebKit rounds a border under a pixel down to half.
    context = browser.new_context(device_scale_factor=2)
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    shown = context.new_page()
    shown.goto(f"{server}/blatt/{mine}")
    shown.locator('main.editor[data-ready="1"]').wait_for()
    # The page that prints, at one pixel to a pixel as Chromium prints it.
    paper = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    paper.goto(f"{server}/druck/{mine}")
    paper.wait_for_selector("body.ready", state="attached")
    places = [tab.evaluate(f"{LOADED}.then({PLACES})") for tab in (shown, paper)]
    assert len(places[0]) == 32
    for here, there in zip(*places, strict=True):
        assert here == pytest.approx(there, abs=0.01)

    pick(shown, "b60")
    shown.keyboard.press("Enter")
    field = shown.locator(".table textarea")
    expect(field).to_be_focused()
    (left, top, right, low), cell = (
        (b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"])
        for b in (field.bounding_box(), shown.locator('[data-cell="0"]').bounding_box())
    )
    assert cell[0] < left < right < cell[2] and cell[1] < top < low < cell[3]
    paper.close()
    context.close()


def lower(screen, printed, block):
    """How many pixels lower each of seven rows of 14 pt lies on the screen than in the PDF."""
    # A row's place is where its ink has its middle, in the band the row is set in.
    pitch = 14 * 25.4 / 72 * 1.3
    found = []
    for row in range(7):
        top = block["y"] + row * pitch
        band = (block["x"], top, block["x"] + block["w"], top + pitch)
        middles = [
            sum(i * v for i, v in enumerate(ink)) / sum(ink)
            for ink in (dark(picture, band) for picture in (screen, printed))
        ]
        found.append(middles[0] - middles[1])
    return found


def right_edge(image, block):
    """The pixel a block's ink ends at on the right, counted to a part of a pixel."""
    y = block["y"] + block["h"] / 4
    columns = dark(image, (0, y - 5, 210, y + 5), down=False)
    last = max(i for i, v in enumerate(columns) if v > 0.05)
    return last + min(1, columns[last] / columns[last - 1])


# How far the screen may lie from the print (issue #281), in pixels of pictures twice the page's
# size, eight to a millimetre: each just over what it is today. No fix, since this much is what
# the browsers round. Chromium prints at one pixel to a CSS pixel, 0.26 mm, and sets a picture's
# edges on whole ones: the PDF has the right edge at 165.1 mm for 165, and pdfium fills the pixel
# it touches. WebKit lays a text's rows out 0.6 CSS pixels lower than Chromium, by font heights
# it rounds its own way, and draws the letters lower again by up to as much.
# Rows: 4.3 in WebKit (0.54 mm) in a school's script, 2.5 in Andika, and 0.8 in Chromium.
ROWS = 4.5 if BROWSER == "webkit" else 1
# A picture's right edge: 3 in WebKit (0.38 mm), of which 2.3 are the print's, and 1.1 in Chromium.
EDGE = 3.5 if BROWSER == "webkit" else 1.5


@pytest.mark.parametrize(
    "look", [{"font": "sas", "bold": True}, {}], ids=["school script", "andika"]
)
def test_a_row_of_text_lies_as_low_as_it_prints(browser, server, look):
    """A5"""
    client = user()
    page = [at("text", {**TEXT, "text": LONG, **look}, h=120)]
    screen, printed = grey(browser, server, client, page)
    found = lower(screen, printed, page[0])
    assert max(abs(by) for by in found) < ROWS, found


def test_a_picture_ends_where_it_prints(browser, server):
    """A6"""
    client = user()
    page = blocks("picture", client)
    screen, printed = (right_edge(image, page[0]) for image in grey(browser, server, client, page))
    assert abs(screen - printed) < EDGE, (screen, printed)
