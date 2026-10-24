"""The print matches the screen: each kind of block, level and turned, pixel by pixel."""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import io
from pathlib import Path

import pytest
from PIL import Image
from pixels import (
    as_png,
    dark,
    measures,
    over,
    screen_and_print,
)
from ui import BROWSER, LINE, RECT, RULING, TABLE, TEXT, box, maths, sheet, user

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
FULLER += ["syllables", "tints", "line numbers"]
BLUE_RED = ["#1a56db", "#e02424"]
BLACK_GREY = ["#000000", "#707070"]
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


def bowed(on=True):
    """A page of texts with a bow under each syllable: one-letter syllables and long compounds."""
    words = "Oma und Opa essen am Abend Apfelkuchen. Die Eichhörnchen sammeln Haselnüsse im Radio."
    listed = [
        {"runs": [{"text": "Der "}, {"text": "Igel", "bold": True}, {"text": " baut ein Nest."}]},
        para("Eine rote Erdbeere", list="bullet"),
        para("Zwei Marmeladengläser", list="bullet"),
    ]
    listed[1]["runs"][0]["color"] = "#e03131"
    rich = "Der Igel baut ein Nest.\nEine rote Erdbeere\nZwei Marmeladengläser"
    cells = [["Esel", "Banane"], ["Schmetterling", "Uhu und Ameise"]]
    table = {"cells": cells, "cols": [1, 1], "size": 14, "align": "center", "line": "#222222"}
    more = {"syllables": on}
    # A word the teacher split her own way, and a block turned off the level.
    by_hand = {"breaks": {"radio": [2], "apfelkuchen": [5]}}
    return [
        at("text", {**TEXT, "text": words, **by_hand, **more}, y=20, h=30),
        at(
            "text",
            {**TEXT, "text": "Eine Banane", "font": "va", **more},
            y=260,
            h=12,
            w=40,
            angle=30,
        ),
        at("text", {**TEXT, "text": words, "font": "sas", "size": 18, **more}, y=55, h=45),
        at("text", {**TEXT, "text": rich, "rich": listed, **more}, y=105, h=30),
        at("shape", {**TEXT, **FILLED, "kind": "rounded", "text": "Regenbogen", **more}, y=140),
        at("table", {**table, **more}, y=205, h=30),
    ]


def tinted(pair=BLUE_RED, on=True):
    """A page with Silbenfarbe on each kind of text: the syllables of a word in turn, in `pair`.

    `on` False is the same page with the switch off.
    """
    words = "Oma und Opa essen am Abend Apfelkuchen. Die Eichhörnchen sammeln Haselnüsse im Radio."
    colours = {"tints": list(pair)} if on else {}
    grey = {"tints": list(BLACK_GREY)} if on else {}
    rich = [
        {
            "runs": [
                {"text": "Der "},
                {"text": "Igel", "bold": True},
                {"text": " baut ein "},
                {"text": "Nest", "color": "#2f9e44"},
                {"text": "."},
            ]
        },
        para("Zwei Marmeladengläser"),
    ]
    cells = [["Esel", "Banane"], ["Schmetterling", "Uhu und Ameise"]]
    table = {"cells": cells, "cols": [1, 1], "size": 14, "align": "center", "line": "#222222"}
    return [
        at("text", {**TEXT, "text": words, "size": 18, **colours}, y=15, h=40),
        at(
            "text",
            {
                **TEXT,
                "text": words,
                "breaks": {"radio": [2], "apfelkuchen": [5]},
                "syllables": True,
                **colours,
            },
            y=60,
            h=30,
        ),
        at(
            "text",
            {
                **TEXT,
                "text": "Der Igel baut ein Nest.\nZwei Marmeladengläser",
                "rich": rich,
                **colours,
            },
            y=95,
            h=30,
        ),
        at(
            "text",
            {**TEXT, "text": words, "font": "sas", "size": 18, "tintsAcross": True, **colours},
            y=130,
            h=40,
        ),
        at(
            "text",
            {**TEXT, "text": "Eine Banane", "font": "va", **colours},
            y=185,
            h=12,
            w=40,
            angle=30,
        ),
        at(
            "shape",
            {**TEXT, **FILLED, "kind": "rounded", "text": "Regenbogen", **grey},
            y=205,
            h=20,
        ),
        at("table", {**table, **colours}, y=235, h=30),
    ]


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
    if case == "syllables":
        return bowed()
    if case == "tints":
        return tinted()
    if case == "line numbers":
        # Every fifth line of a long text; a mark and bows; a turned text; every line numbered.
        return [
            at("text", {**TEXT, "text": LONG, "lines": 5}, y=20, h=120, w=100, x=30),
            at(
                "text",
                {**TEXT, "text": "Eins zwei drei vier", "lines": 1, "syllables": True},
                y=150,
                h=20,
                mark="1.",
            ),
            at("text", {**TEXT, "text": LONG, "lines": 1}, y=190, h=60, w=80, angle=20),
        ]
    kinds = ("l1", "l2", "l3", "lines", "k5", "k7")
    rulings = [
        at("ruling", {"kind": kind, "color": "#222222"}, y=15 + 30 * i, h=30, x=15 + 135 * (i % 2))
        for i, kind in enumerate(kinds)
    ]
    written = {"kind": "l1", "color": "#222222", "text": "Igel", "trace": True}
    return {"blocks": [*rulings, at("ruling", written, y=150, h=40, x=150)], "landscape": True}


def faults(browser, server, client, *pages, words=None, **look):
    """What of the first page is over a limit between the editor and the PDF."""
    return over(
        *screen_and_print(browser, server, client, sheet(client, *pages, words=words)["id"], **look)
    )


# A text of two paragraphs, a gap on the last line of each, and a gap of two words in the first.
GAP_RUNS = [
    [
        {"text": "Der "},
        {"text": "Hund", "gap": True},
        {"text": " bellt laut und die Katze schläft heute lange im warmen Haus, "},
        {"text": "Maus pfeift leise", "gap": True},
    ],
    [{"text": "Die Vögel singen "}, {"text": "laut", "gap": True}],
]


def gapped(case):
    """The gap cases of a page: a text, one with gap widths, a box with a gap, a table, and a text
    with bows and colours. Each has a gap on the last line of a paragraph."""
    text = {
        **TEXT,
        "text": "Der Hund bellt",
        "rich": [{"runs": runs} for runs in GAP_RUNS],
        "bank": 1,
    }
    if case == "text":
        return [at("text", text, y=20, h=90)]
    if case == "gapWidth":
        return [at("text", {**text, "gapWidth": 30}, y=20, h=90)]
    if case == "shape":
        shape = {**TEXT, **FILLED, "kind": "rounded", "rich": [{"runs": GAP_RUNS[1]}]}
        return [at("shape", shape, y=120, h=20)]
    if case == "table":
        props = {**TABLE, "line": "#222222", "gaps": [[True, False], [False, True]], "bank": 1}
        return [at("table", props, y=150, h=40)]
    # Bows and colours on a gap's page: the words after the gap keep their colours.
    return [at("text", {**text, "syllables": True, "tints": BLUE_RED}, y=20, h=90)]


GAPPED = ["text", "gapWidth", "shape", "table", "bows"]


# A gap so long that a tile of the measure holds its line and no letters (#411).
LONG_GAP = [{"text": "Der "}, {"text": "Donaudampfschifffahrtsgesellschaft", "gap": True}]
LONG_GAP += [{"text": " bellt"}]


def mixed_case(case):
    """The scrambled-word cases of a page (Schüttelwörter): a text that wraps onto several rows, one
    with a line after each word, one with a line under each, one in capitals, and a shape with its
    text. A line on a second row is where a wrong drawing hid."""
    text = {**TEXT, "text": MIXED_TEXT, "mix": 7}
    if case == "plain":
        return [at("text", text, y=20, h=60)]
    if case == "after":
        return [at("text", {**text, "mixLine": "after"}, y=20, h=90)]
    if case == "under":
        return [at("text", {**text, "mixLine": "under"}, y=20, h=120)]
    if case == "caps":
        return [at("text", {**text, "mixCaps": True}, y=20, h=60)]
    return [at("shape", {**FILLED, **text, "kind": "rounded"}, y=120, h=60)]


MIXED_TEXT = "Der Hund bellt laut und die Katze schläft in der Straße vor dem Haus"
MIXED = ["plain", "after", "under", "caps", "shape"]


LISTED = ["Hund", "Katze", "Maus"]
LINEATUR = [
    (kind, mode)
    for kind in ("l1", "l2", "l3", "l4", "lines", "k5", "k7")
    for mode in ("copy", "trace", "row")
]


def planted(browser, server, here, there):
    """The screen of one page against the print of another: each measure's highest value."""
    client = user()
    shown, paper = (sheet(client, page)["id"] for page in (here, there))
    screen, _ = screen_and_print(browser, server, client, shown)
    _, printed = screen_and_print(browser, server, client, paper)
    return {name: value for name, (value, _) in measures(screen, printed)[0].items()}


# What the share of the page passes over (issue #282), each planted as the print of another page.
# WebKit sees the colours and neither shift. A shift is 0.059 of a tile for the outline and 0.0045
# for the word, and rows of a school's script differ by 0.065, which is what the browsers round
# (ROWS below): see TILE in pixels.py.
BLIND = pytest.mark.webkit_xfail(299, "a row's place differs by more")
GREY = {"color": "#555555"}
COLOURS = {
    "fill": (at("shape", FILLED), at("shape", {**FILLED, "fill": "#ffe066"})),
    "ruling": (at("ruling", {**RULING, **GREY}), at("ruling", RULING)),
    "text": (at("text", {**WORDS, "color": "#222222"}), at("text", {**WORDS, **GREY})),
}
# A box of 30 mm and a word: the same shift of a box or a sentence 120 mm wide is 0.0025 of the
# page, over Chromium's limit.
SHIFTS = {
    "outline": lambda y: at("shape", RECT, y=y, w=30, h=30),
    "word": lambda y: at("text", {**TEXT, "text": "Igel"}, y=y, w=30, h=30),
}


def drawn(*boxes):
    """An upright page of four pixels to a millimetre with a box of each place and colour."""
    page = Image.new("RGB", (840, 1188), "white")
    for place, colour in boxes:
        page.paste(colour, tuple(4 * v for v in place))
    return as_png(page)


# Each cell of a table and each cell's text: left, top, width and height in the page's own pixels.
PLACES = """() => {
    const page = document.querySelector('.scaled');
    const from = page.getBoundingClientRect(), k = from.width / page.offsetWidth;
    return [...document.querySelectorAll('.table > div, .table p')].map((el) => {
        const r = el.getBoundingClientRect();
        return [(r.x - from.x) / k, (r.y - from.y) / k, r.width / k, r.height / k];
    });
}"""


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
