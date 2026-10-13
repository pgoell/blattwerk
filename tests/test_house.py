"""Issue #77: a Lineatur draws a Häuschen and a band per row; its text starts right of the house.

The docstrings name the checklist line that each test proves. The house sits at the left of a row,
its zones in mm from the row's top: roof top, room top, room bottom, cellar bottom.
"""

import math
import re

import httpx
import pytest
from playwright.sync_api import expect
from test_pixels import faults
from ui import BROWSER, at, box, sheet, user

INK = "#222222"
# The zones of a row in mm, and the height of a row, per kind with a house.
ZONES = {"l1": [2.5, 7.5, 12.5, 17.5], "l2": [2, 6, 10, 14], "l3": [0.5, 4, 7.5, 11]}
ROW = {"l1": 20, "l2": 16, "l3": 11.5}
WORDS = ["Haus", "Igel", "Garten"]
FONTS = ["andika", "nord", "sued", "grund", "urff", "va", "sas", "la"]
LOOKS = {
    "none": {},
    "grey": {"trace": True},
    "outline": {"trace": "outline"},
    "dotted": {"trace": "dotted"},
    "fade": {"trace": True, "fade": "row"},
}
PADDING = "el => parseFloat(getComputedStyle(el).paddingLeft)"


def num(locator, attr):
    return float(locator.get_attribute(attr))


def close(got, want):
    assert abs(got - want) < 0.01, (got, want)


def corners(poly):
    """The corners of a polygon as (x, y) pairs, in the order they are written."""
    pairs = poly.get_attribute("points").split()
    return [tuple(float(v) for v in pair.split(",")) for pair in pairs]


def houses(page, name):
    return at(page, name).locator("g.house")


def right(box):
    return box["x"] + box["width"]


def lineature(name, kind, rows=2, **more):
    """A Lineatur of `rows` rows of its kind, in the middle of the page, 180 mm wide."""
    props = {"kind": kind, "color": INK, **more}
    return box(name, "ruling", props, h=ROW.get(kind, 10) * rows)


@pytest.mark.parametrize("kind", ["l1", "l2", "l3"])
def test_house_draws_one_per_row_at_the_zones(editor, kind):
    """A1: a house on l1, l2 and l3 draws one g.house per row, at the zones of that row."""
    page = editor(lineature("a", kind, house=True, text="Igel"))
    expect(houses(page, "a")).to_have_count(2)
    zones, row = ZONES[kind], ROW[kind]
    for i in range(2):
        top = i * row
        group = houses(page, "a").nth(i)
        room = group.locator("rect.room")
        cellar = group.locator("rect.cellar")
        close(num(room, "y"), top + zones[1])
        close(num(room, "height"), zones[2] - zones[1])
        close(num(room, "x"), 0)
        # The house is 1.5 times its room's height wide, so its apex lies at half that.
        width = 1.5 * (zones[2] - zones[1])
        close(num(room, "width"), width)
        close(num(cellar, "y"), top + zones[2])
        close(num(cellar, "height"), zones[3] - zones[2])
        expected = [(0, top + zones[1]), (width / 2, top + zones[0]), (width, top + zones[1])]
        for (got_x, got_y), (want_x, want_y) in zip(
            corners(group.locator("polygon.roof")), expected, strict=True
        ):
            close(got_x, want_x)
            close(got_y, want_y)


@pytest.mark.parametrize(
    "kind, house",
    [("l1", None), ("l1", False), ("l4", True), ("lines", True), ("k5", True)],
)
def test_no_house_when_off_or_without_zones(editor, kind, house):
    """A1, A11: no house when it is off, or when the kind has no zones (l4, lines, k5)."""
    more = {} if house is None else {"house": house}
    page = editor(lineature("a", kind, **more))
    expect(at(page, "a").locator("svg.ruling")).to_be_visible()
    expect(houses(page, "a")).to_have_count(0)


@pytest.mark.parametrize("look", list(LOOKS))
def test_text_starts_right_of_the_house_in_every_font(editor, look):
    """A2: in every font and look the text starts right of the house, on the screen and the page."""
    blocks = [
        box(
            f"f{i}",
            "ruling",
            {
                "kind": "l3",
                "color": INK,
                "house": True,
                "font": font,
                "text": "Igel",
                **LOOKS[look],
            },
            z=i + 1,
            h=ROW["l3"],
        )
        for i, font in enumerate(FONTS)
    ]
    page = editor(*blocks, theme="")
    for i, font in enumerate(FONTS):
        house = houses(page, f"f{i}").first.bounding_box()
        written = at(page, f"f{i}").locator("textarea.written")
        left = written.bounding_box()["x"] + written.evaluate(PADDING)
        assert round(left) >= round(right(house)), font
        assert left - right(house) < house["width"], font


def test_typed_text_starts_right_of_the_house(editor):
    """A2: text typed into an l1 house starts right of the house, in whole px."""
    page = editor(lineature("a", "l1", rows=1, house=True))
    at(page, "a").dblclick()
    written = at(page, "a").locator("textarea.written")
    expect(written).to_be_focused()
    page.keyboard.type("Maus")
    expect(written).to_have_value("Maus")
    house = houses(page, "a").first.bounding_box()
    block = at(page, "a").bounding_box()
    assert round(written.evaluate(PADDING)) >= round(right(house) - block["x"])


@pytest.mark.parametrize("mode", ["copy", "trace", "row", "fold"])
@pytest.mark.parametrize("kind", ["l1", "l2", "l3"])
def test_lernwoerter_start_right_of_the_house(editor, kind, mode):
    """A3: each word of a Lernwörter Lineatur starts right of its house; a fold ends left of it."""
    props = {"kind": kind, "color": INK, "list": mode, "house": True}
    if mode == "fold":
        props["folds"] = 2
    page = editor(box("a", "ruling", props, h=ROW[kind] * 3), words=WORDS)
    expect(houses(page, "a")).to_have_count(3)
    rows = at(page, "a").locator(".written.listed .row")
    expect(rows).to_have_count(3)
    for i in range(3):
        house = houses(page, "a").nth(i).bounding_box()
        first = rows.nth(i).locator("span").first.bounding_box()
        assert round(first["x"]) >= round(right(house))
        if mode == "fold":
            fold = at(page, "a").locator("line.fold").first.bounding_box()
            assert right(first) <= fold["x"] + 1


def test_a_narrow_knickblatt_keeps_its_word_left_of_the_fold(editor):
    """A3: a column narrower than the house's indent keeps each word left of the fold."""
    props = {"kind": "l1", "color": INK, "list": "fold", "folds": 3, "house": True}
    page = editor(box("a", "ruling", props, w=36, h=40), words=["Garten", "Igel"])
    rows = at(page, "a").locator(".written.listed .row")
    expect(rows).to_have_count(2)
    fold = at(page, "a").locator("line.fold").first.bounding_box()
    for i in range(2):
        first = rows.nth(i).locator("span").first.bounding_box()
        # The house leaves the word no room here: its span is shut, so none of it shows.
        assert first["width"] == 0 or round(right(first)) <= round(fold["x"] + 1), first


def test_house_takes_the_line_colour(editor):
    """A4: a house in a blue Lineatur is blue in every shape: no stroke of its own."""
    page = editor(lineature("a", "l1", rows=1, house=True, color="#1a56db"))
    expect(at(page, "a").locator("svg.ruling")).to_have_attribute("stroke", "#1a56db")
    # The shapes inherit the stroke from the svg: none of them sets one.
    own = (
        houses(page, "a")
        .locator("*")
        .evaluate_all("els => els.map((el) => el.getAttribute('stroke')).filter((s) => s !== null)")
    )
    assert own == [], own
    for part in ("polygon.roof", "rect.room", "rect.cellar"):
        expect(houses(page, "a").locator(part)).to_have_css("stroke", "rgb(26, 86, 219)")


@pytest.mark.parametrize(
    "tint, fills",
    [
        (None, ("none", "none", "none")),
        ("room", ("none", "#fcefb4", "none")),
        ("all", ("#f6c4bd", "#fcefb4", "#d9cdbd")),
    ],
)
def test_house_tint(editor, tint, fills):
    """A5: the house's fills: none unless tinted; "room" tints the room; "all" tints all three."""
    more = {} if tint is None else {"houseTint": tint}
    page = editor(lineature("a", "l1", rows=1, house=True, **more))
    group = houses(page, "a").first
    for part, fill in zip(("polygon.roof", "rect.room", "rect.cellar"), fills, strict=True):
        expect(group.locator(part)).to_have_attribute("fill", fill)


@pytest.mark.parametrize(
    "kind, more, count",
    [
        ("l1", {}, 2),
        ("l2", {}, 2),
        ("l3", {}, 0),
        ("l1", {"band": False}, 0),
        ("l2", {"band": False}, 0),
    ],
)
def test_band_defaults(editor, kind, more, count):
    """A6: l1 and l2 bands one per row by default, l3 none; band false takes them away."""
    page = editor(lineature("a", kind, **more))
    expect(at(page, "a").locator("svg.ruling")).to_be_visible()
    expect(at(page, "a").locator("rect.band")).to_have_count(count)


def test_band_on_l3_sits_in_the_room(editor):
    """A6: l3 with band true draws one band per row, at rowTop + 4, 3.5 mm high."""
    page = editor(lineature("a", "l3", band=True))
    bands = at(page, "a").locator("rect.band")
    expect(bands).to_have_count(2)
    for i in range(2):
        close(num(bands.nth(i), "y"), i * ROW["l3"] + 4)
        close(num(bands.nth(i), "height"), 3.5)


@pytest.mark.parametrize("kind", ["l4", "lines", "k5"])
def test_band_needs_zones(editor, kind):
    """A6: a band on l4, lines or k5 draws nothing: those kinds have no zones."""
    page = editor(lineature("a", kind, band=True))
    expect(at(page, "a").locator("svg.ruling")).to_be_visible()
    expect(at(page, "a").locator("rect.band")).to_have_count(0)


@pytest.mark.parametrize(
    "band_color, fill, opacity",
    [(None, INK, "0.12"), ("#ffe066", "#ffe066", "1")],
)
def test_band_fill(editor, band_color, fill, opacity):
    """A7: a band takes the line colour at 12 %, or its own colour at full strength."""
    more = {} if band_color is None else {"bandColor": band_color}
    page = editor(lineature("a", "l1", rows=1, **more))
    band = at(page, "a").locator("rect.band").first
    expect(band).to_have_attribute("fill", fill)
    expect(band).to_have_attribute("fill-opacity", opacity)


@pytest.mark.parametrize("kind", ["l1", "l2", "l3", "l4"])
def test_a_plain_block_draws_as_before(editor, kind):
    """A8: a block with only kind and colour has no house, its text at no padding, its old bands."""
    page = editor(lineature("a", kind, text="Hallo"))
    expect(houses(page, "a")).to_have_count(0)
    written = at(page, "a").locator(".written").first
    expect(written).to_have_css("padding-left", "0px")
    style = written.get_attribute("style") or ""
    assert "padding" not in style and "box-sizing" not in style, style
    bands = at(page, "a").locator("rect.band")
    if kind not in ("l1", "l2"):
        expect(bands).to_have_count(0)
        return
    expect(bands).to_have_count(2)
    zones, row = ZONES[kind], ROW[kind]
    for i in range(2):
        band = bands.nth(i)
        close(num(band, "y"), i * row + zones[1])
        close(num(band, "height"), zones[2] - zones[1])
        expect(band).to_have_attribute("fill", INK)
        expect(band).to_have_attribute("fill-opacity", "0.12")


@pytest.mark.parametrize("turn", [0, 30])
@pytest.mark.parametrize("kind", ["l1", "l2", "l3"])
def test_print_matches_the_screen_with_houses_and_bands(browser, server, kind, turn):
    """A10: the print of a house with tint and band matches the screen, plain and turned."""
    client = user()
    block = box(
        "a",
        "ruling",
        {
            "kind": kind,
            "color": INK,
            "text": "Igel",
            "house": True,
            "houseTint": "all",
            "band": True,
            "bandColor": "#ffe066",
        },
        x=45,
        y=100,
        w=120,
        h=ROW[kind] * 2,
        angle=turn,
    )
    assert not faults(browser, server, client, [block])


def test_print_matches_the_screen_for_a_knickblatt_with_a_house(browser, server):
    """A10: a Knickblatt with a house prints as the screen shows it."""
    client = user()
    fold = box(
        "a",
        "ruling",
        {"kind": "l3", "color": INK, "list": "fold", "folds": 2, "house": True},
        x=45,
        y=100,
        w=120,
        h=ROW["l3"] * 3,
    )
    assert not faults(browser, server, client, [fold], words=WORDS)


def test_the_pdf_holds_no_picture_with_houses_and_bands(server):
    """A10: the PDF of tinted houses and bands has no image: the shapes are vectors."""
    client = user()
    looks = {"house": True, "houseTint": "all", "band": True, "bandColor": "#ffe066"}
    blocks = [
        box(
            name,
            "ruling",
            {"kind": kind, "color": INK, "text": "Igel", **looks},
            z=i + 1,
            x=45,
            y=100 + 50 * i,
            w=120,
            h=ROW[kind] * 2,
        )
        for i, (name, kind) in enumerate([("a", "l1"), ("b", "l2"), ("c", "l3")])
    ]
    mine = sheet(client, blocks)
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{mine['id']}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    assert re.search(rb"/Subtype\s*/Image", res.content) is None


@pytest.mark.parametrize("look", list(LOOKS))
def test_print_matches_the_screen_in_every_font_with_a_house(browser, server, look):
    """A10: in every font and look the printed text lies where the editor's field does."""
    client = user()
    blocks = [
        box(
            f"p{i}",
            "ruling",
            {
                "kind": "l1",
                "color": INK,
                "house": True,
                "font": font,
                "text": "jagen Igel und Maus im Garten",
                **LOOKS[look],
            },
            z=i + 1,
            x=45,
            y=15 + 22 * i,
            w=120,
            h=20,
        )
        for i, font in enumerate(FONTS)
        # WebKit's screen draws an outline in Nord and Süd heavier than the print, house or none
        # (issue #499).
        if not (BROWSER == "webkit" and look == "outline" and font in ("nord", "sued"))
    ]
    assert not faults(browser, server, client, blocks)


INK_OF_J = """async (block, outline) => {
    const el = block.querySelector("textarea.written");
    const style = getComputedStyle(el);
    const font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    await document.fonts.load(font);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = font;
    const m = ctx.measureText("j");
    const shade = outline ? 0.02 * parseFloat(style.fontSize) : 0;
    const start = el.getBoundingClientRect().left + parseFloat(style.paddingLeft);
    const ink = start - m.actualBoundingBoxLeft - shade;
    // The house's box leaves out half its stroke: add it, in px at the svg's scale.
    const svg = block.querySelector("svg.ruling");
    const roof = block.querySelector("g.house polygon.roof");
    const scale = svg.getScreenCTM().a;
    const half = (parseFloat(getComputedStyle(roof).strokeWidth) * scale) / 2;
    const house = block.querySelector("g.house").getBoundingClientRect().right + half;
    return [ink, house];
}"""


@pytest.mark.parametrize("look", list(LOOKS))
def test_no_ink_of_the_text_reaches_into_the_house(editor, look):
    """A2: the ink of each font's j, hung left by the joined scripts, stays right of the house."""
    blocks = [
        box(
            f"j{i}",
            "ruling",
            {
                "kind": "l1",
                "color": INK,
                "house": True,
                "font": font,
                "text": "jagen",
                **LOOKS[look],
            },
            z=i + 1,
            h=ROW["l1"],
        )
        for i, font in enumerate(FONTS)
    ]
    page = editor(*blocks, theme="")
    for i, font in enumerate(FONTS):
        ink, house = at(page, f"j{i}").evaluate(INK_OF_J, look == "outline")
        assert math.floor(ink) >= math.ceil(house), (font, ink, house)


def test_a_house_with_an_unknown_tint_draws_untinted(editor):
    """I7: a house with an unknown tint draws its three shapes with no fill."""
    page = editor(
        box("a", "ruling", {"kind": "l1", "color": INK, "house": True, "houseTint": "blue"}, h=20)
    )
    group = houses(page, "a").first
    for part in ("polygon.roof", "rect.room", "rect.cellar"):
        expect(group.locator(part)).to_have_attribute("fill", "none")


def test_values_it_does_not_know_draw_as_the_defaults(editor):
    """I7: a sheet with unknown house, tint, band and colour values draws the defaults."""
    page = editor(
        box(
            "a",
            "ruling",
            {
                "kind": "l1",
                "color": "#1a56db",
                "house": "yes",
                "houseTint": "blue",
                "band": "no",
                "bandColor": "x",
            },
            h=ROW["l1"] * 2,
        )
    )
    expect(at(page, "a")).to_be_visible()
    expect(houses(page, "a")).to_have_count(0)
    bands = at(page, "a").locator("rect.band")
    expect(bands).to_have_count(2)
    for i in range(2):
        expect(bands.nth(i)).to_have_attribute("fill", "#1a56db")
        expect(bands.nth(i)).to_have_attribute("fill-opacity", "0.12")
