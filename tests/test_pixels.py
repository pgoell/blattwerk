"""The print matches the screen: each kind of block, level and turned, pixel by pixel."""

import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pixels import LIMIT, diff, screen_and_print
from ui import BROWSER, LINE, RECT, RULING, TABLE, TEXT, box, maths, png, sheet, user

SHOT = Path(__file__).parent.parent / "scripts" / "shot.py"
FILLED = {**RECT, "fill": "#ffd43b", "strokeWidth": 1}
WORDS = {**TEXT, "text": "Der Igel sucht im Herbst nach Futter und baut sich ein Nest aus Laub."}
LONG = (
    "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter und baut sich aus Laub ein "
    "warmes Nest. Die Eichhörnchen sammeln Nüsse und verstecken sie überall im Garten, damit "
    "sie im Winter genug zu fressen haben. Manchmal vergessen sie ein Versteck, und im "
    "Frühling wächst dort ein neuer Baum. Die Vögel ziehen in den Süden."
)
FULLER = ["school script", "lists", "table", "strokes", "pictures", "rulings on its side"]
KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group", "name", "points"]
# A table and a line stay level: the panel Format shuts "Drehung" for them and the selection has
# no handle to turn them by. A line points where its two ends are.
TURNED = [kind for kind in KINDS if kind not in ("table", "line")]
# What WebKit shows another way than Chromium prints it, each just over what it differs by today.
# A table's lines are one pixel of the screen wide and pale there, half of what prints: 0.004.
# A dashed border has longer dashes and wider gaps and a dotted one square dots: 0.015.
OWN = {
    "table": 0.006,  # issue #280
    "strokes": 0.02,  # issue #279
}
OWN = OWN if BROWSER == "webkit" else {}


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
    assert share(browser, server, client, blocks(kind, client)) < OWN.get(kind, LIMIT)


@pytest.mark.parametrize("kind", TURNED)
def test_a_turned_block_prints_as_the_screen_shows_it(browser, server, kind):
    client = user()
    # Not a right angle: that would hide a turn about another point.
    assert share(browser, server, client, blocks(kind, client, angle=30)) < LIMIT


@pytest.mark.parametrize("case", FULLER)
def test_a_fuller_page_prints_as_the_screen_shows_it(browser, server, case):
    client = user()
    assert share(browser, server, client, fuller(case, client)) < OWN.get(case, LIMIT)


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
