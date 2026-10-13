"""Issue #75: the school scripts Grundschrift (Urff), Fibel Nord and Fibel Süd as editor fonts.

Checklist ids are in each docstring.
"""

import re
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image
from playwright.sync_api import expect
from test_undo_steps import step
from ui import BROWSER, RECT, RULING, TABLE, TEXT, at, block, box, pick, saved, sheet, unpick, user

from blattwerk import pdf

NEW = {"urff": "Grundschrift Urff", "nord": "Fibel Nord", "sued": "Fibel Sued"}
FAMILY = {
    "andika": "Andika",
    **NEW,
    "grund": "Playwrite DE Grund Variable",
    "va": "Playwrite DE VA Variable",
    "sas": "Playwrite DE SAS Variable",
    "la": "Playwrite DE LA Variable",
}
# The embedded PostScript name of each new font's regular cut.
PDF_NAME = {"urff": b"Grundschrift-Regular", "nord": b"FibelNord", "sued": b"FibelSued"}
UMLAUT = "äöüß 0123456789"
MENU = [
    "andika",
    "nord",
    "sued",
    "grund",
    "urff",
    "va",
    "sas",
    "la",
]
KIND_LABEL = {
    "text": "Schriftart",
    "shape": "Schriftart",
    "group": "Schriftart",
    "table": "Schriftart der Tabelle",
    "ruling": "Schriftart auf den Zeilen",
}
CHECK = """async (font) => {
    await document.fonts.ready;
    return document.fonts.check(font);
}"""
MEASURE = """async (family) => {
    await document.fonts.load(`1000px "${family}"`);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = `1000px "${family}"`;
    // In hundredths of the size; at 1000 px, since a canvas gives whole pixels.
    return ctx.measureText("x").actualBoundingBoxAscent / 10;
}"""


def pdf_fonts(server, client, sheet_id):
    """The PostScript names of the fonts in the sheet's PDF."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    return set(re.findall(rb"/FontName /\w+\+([\w-]+)", res.content))


def choose(page, label, key):
    page.get_by_label(label, exact=True).select_option(key)


def expect_family(locator, family):
    expect(locator).to_have_css("font-family", re.compile(re.escape(family)))


def test_a_new_font_is_chosen_from_the_menu(editor, server):
    """A1/A3 each: a text takes the font from the menu, is drawn in it and the server keeps it."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": UMLAUT}), client=client)
    pick(page, "a")
    for key, family in NEW.items():
        choose(page, "Schriftart", key)
        expect_family(at(page, "a").get_by_text("0123456789").first, family)
        assert page.evaluate(CHECK, f'20px "{family}"')
        stored = next(b for b in saved(page, client) if b["id"] == "a")
        assert stored["props"]["font"] == key


def test_kontur_and_punkt_load_and_are_not_in_the_menu(editor):
    """A2: the Kontur and Punkt cuts load, and the menu holds only the eight fonts."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    faces = page.evaluate(
        """async () => [
            (await document.fonts.load('20px "Grundschrift Urff Kontur"')).length,
            (await document.fonts.load('20px "Grundschrift Urff Punkt"')).length,
        ]"""
    )
    assert faces == [1, 1]
    values = (
        page.get_by_label("Schriftart", exact=True)
        .locator("option")
        .evaluate_all("els => els.map((o) => o.value)")
    )
    assert values == MENU


def test_the_credits_name_the_new_fonts(browser, server):
    """A4: the page Über names the designers and licences, and the licence files are served."""
    page = browser.new_page()
    with page.expect_response("**/api/me"):
        page.goto(f"{server}/ueber")
    expect(page.locator("body")).to_contain_text("Grundschrift von Christian Urff")
    expect(page.locator("body")).to_contain_text("Peter Wiegel")
    expect(page.locator("body")).to_contain_text("CC BY 3.0")
    # The server answers any unknown path with the app's page, so each licence is read for its text.
    licences = {
        "/fonts/urff/LICENSE.txt": ("Grundschrift von Christian Urff", "CC BY 3.0"),
        "/fonts/urff/CC-BY-3.0.txt": ("Creative Commons Legal Code", "Attribution 3.0"),
        "/fonts/fibel/OFL.txt": ("SIL OPEN FONT LICENSE Version 1.1", "Peter Wiegel"),
    }
    for path, words in licences.items():
        assert page.locator(f'a[href="{path}"]').count() == 1, path
        text = httpx.get(f"{server}{path}").text
        for word in words:
            assert word in text, (path, word)
    for href in (
        "https://github.com/christianurff/grundschrift",
        "https://www.peter-wiegel.de/Fibel.html",
    ):
        assert page.locator(f'a[href="{href}"]').count() == 1, href
    page.close()
    notice = (Path(__file__).resolve().parent.parent / "NOTICE").read_text(encoding="utf-8")
    for words in (
        "Grundschrift von Christian Urff",
        "Peter Wiegel",
        "Creative Commons Attribution 3.0",
        "SIL Open Font License 1.1",
    ):
        assert words in notice


def test_a_text_block_draws_the_font_at_its_own_size(editor):
    """A7/A12: a text draws the font at its natural size; only a Lineatur scales it (A5/A6)."""
    fonts = ["andika", *NEW]
    page = editor(*(box(key, "text", {**TEXT, "font": key}, z=i) for i, key in enumerate(fonts)))
    size = "el => parseFloat(getComputedStyle(el).fontSize)"
    sizes = {key: at(page, key).get_by_text("Hallo").evaluate(size) for key in fonts}
    assert all(px == sizes["andika"] for px in sizes.values()), sizes
    # No face is scaled by the stylesheet either: the box a canvas gives an x, in hundredths of
    # the size, is 45 for Urff and 41 for the two Fibeln. Scaled as on a Lineatur it would be 52.
    bands = {"urff": (44, 47), "nord": (39.5, 42), "sued": (39.5, 42)}
    for key, (low, high) in bands.items():
        ascent = page.evaluate(MEASURE, NEW[key])
        assert low <= ascent <= high, (key, ascent)


def dark(shot):
    """How many pixels are dark in the shot, and the first row that holds one."""
    img = Image.open(BytesIO(shot)).convert("L")
    width, height = img.size
    px = img.tobytes()
    rows = [y for y in range(height) for x in range(width) if px[y * width + x] < 100]
    return len(rows), (min(rows) if rows else None)


@pytest.mark.parametrize("bold", [False, True])
@pytest.mark.parametrize("kind", ["text", "shape"])
@pytest.mark.parametrize("key", NEW)
def test_capital_umlauts_keep_their_dots(editor, key, kind, bold):
    """A7: the dots of Ä Ö Ü are not cut off by a paragraph's box, in a text or a shape."""
    props = {**(TEXT if kind == "text" else RECT), "text": "ÄÖÜ", "font": key, "size": 40}
    # In the block's middle: at its top edge the block itself cuts, with or without the lever.
    props["valign"] = "middle"
    page = editor(box("a", kind, {**props, "bold": bold}, x=10, y=40, w=90, h=40))
    unpick(page)
    page.evaluate("document.fonts.ready.then(() => 0)")
    box_now = at(page, "a").bounding_box()
    # The block and 20 px above it, so that ink lifted out of the block is seen too.
    clip = {
        "x": box_now["x"],
        "y": box_now["y"] - 20,
        "width": box_now["width"],
        "height": box_now["height"] + 20,
    }
    before = page.screenshot(clip=clip)
    page.add_style_tag(content=".frame p, .frame .rich { overflow: visible !important }")
    # The lever works: the paragraph no longer clips before the shot after it is taken.
    assert at(page, "a").locator("p").first.evaluate("el => getComputedStyle(el).overflow") == (
        "visible"
    )
    after = page.screenshot(clip=clip)
    count, top = dark(before)
    count2, top2 = dark(after)
    assert count > 0
    # Urff's Ü ends a hundredth of its size under the line's top, and Chromium cuts at whole
    # pixels of the screen: up to a row of the dots' tops, 1.3 % of the ink. With the dots cut
    # off, as at a line spacing of 1.0 (#487), 4 % and more are gone.
    assert abs(count - count2) <= 0.02 * count2, (count, count2)
    assert abs(top - top2) <= 1, (top, top2)


@pytest.mark.parametrize("key", NEW)
@pytest.mark.parametrize("kind", KIND_LABEL)
def test_a_new_font_draws_in_every_block_with_text(editor, kind, key):
    """A7 each kind: a text, shape, table, ruling or group draws its words in the new font."""
    blocks = {
        "text": [box("a", "text", {**TEXT, "text": UMLAUT})],
        "shape": [box("a", "shape", {**RECT, "text": UMLAUT})],
        "table": [box("a", "table", {**TABLE, "cells": [[UMLAUT, "Z"]]})],
        "ruling": [box("a", "ruling", {**RULING, "kind": "l2", "text": UMLAUT})],
        "group": [
            box("a", "text", {**TEXT, "text": UMLAUT}, w=40, group=["g"]),
            box("b", "text", TEXT, z=2, x=60, y=50, w=40, group=["g"]),
        ],
    }[kind]
    page = editor(*blocks)
    if kind == "group":
        at(page, "a").click()
        expect(page.locator(".block.sel")).to_have_count(2)
    else:
        pick(page, "a")
    choose(page, KIND_LABEL[kind], key)
    expect_family(at(page, "a").get_by_text("0123456789").first, NEW[key])


def first_row_ink(shot, blank, row_mm):
    """The top and the foot of the ink in a block's first row, in mm from its top.

    The block is 40 mm high. Ink is dark in the shot and light in the blank, so the ruling's own
    lines do not count.
    """
    shot_img = Image.open(BytesIO(shot)).convert("L")
    blank_img = Image.open(BytesIO(blank)).convert("L")
    width, height = shot_img.size
    per_mm = height / 40
    shot_px, blank_px = shot_img.tobytes(), blank_img.tobytes()
    ys = [
        y
        for y in range(round(row_mm * per_mm))
        for x in range(width)
        if shot_px[y * width + x] < 100 and blank_px[y * width + x] > 200
    ]
    return min(ys) / per_mm, (max(ys) + 1) / per_mm


@pytest.mark.parametrize("font", ["nord", "sued", "urff"])
@pytest.mark.parametrize("kind", ["l1", "l2", "l3", "l4"])
def test_text_stands_on_the_lineatur_line(editor, kind, font):
    """A5/A6 (by pixels): "xnx" sits on the ruling's line, its x stands half its size high."""
    props = {"kind": kind, "color": "#222222", "font": font}
    page = editor(
        box("typed", "ruling", {**props, "text": "xnx"}, x=10, y=40, w=90, h=40),
        box("blank", "ruling", props, x=10, y=120, w=90, h=40),
    )
    page.evaluate("document.fonts.ready.then(() => 0)")
    blank = at(page, "blank").screenshot()
    top, foot = first_row_ink(
        at(page, "typed").screenshot(), blank, {"l1": 20, "l2": 16, "l3": 11.5, "l4": 10}[kind]
    )
    baseline = {"l1": 12.5, "l2": 10, "l3": 7.5, "l4": 10}[kind]
    assert abs(foot - baseline) <= 0.4, (kind, font, top, foot)
    # The x-height: half the size above the baseline; for l4 the ink rises 3 mm. The x touches
    # the ruling's line there, and WebKit's line hides a row of pixels more, half a millimetre.
    x_top = {"l1": 7.5, "l2": 6, "l3": 4, "l4": 7}[kind]
    assert abs(top - x_top) <= (0.65 if BROWSER == "webkit" else 0.4), (kind, font, top, foot)
    # The same by the numbers, finer than a pixel: the font's size times its x-height.
    written = at(page, "typed").locator(".written")
    px = written.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    per_mm = written.evaluate("el => el.offsetWidth") / 90
    # The height of each font's x in its size, read from the font files' outlines.
    high = px * {"urff": 0.43, "nord": 0.3936, "sued": 0.3936}[font] / per_mm
    assert high == pytest.approx(baseline - x_top, rel=0.04), (kind, font, high)


SENTENCE = "Der kleine Hund läuft über die große Wiese und sucht seinen roten Ball im hohen Gras."
# The words that start a line: each word's top against the one before it, 2 px more is a new line.
LINE_STARTS = r"""(block) => {
    const starts = [];
    let prev = null;
    const walk = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    while (walk.nextNode()) {
        const node = walk.currentNode;
        for (const m of node.data.matchAll(/\S+/g)) {
            range.setStart(node, m.index);
            range.setEnd(node, m.index + m[0].length);
            const top = range.getBoundingClientRect().top;
            if (prev === null || top > prev + 2) starts.push(m[0]);
            prev = top;
        }
    }
    return starts;
}"""
FAMILY_OF = """(block) => {
    const walk = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    walk.nextNode();
    return getComputedStyle(walk.currentNode.parentElement).fontFamily;
}"""


@pytest.mark.parametrize("key", ["nord", "sued", "urff"])
def test_the_print_page_breaks_lines_where_the_editor_does(editor, browser, server, key):
    """A10/A12: a long sentence breaks at the same words on the screen and on the print page."""
    page = editor(box("a", "text", {**TEXT, "text": SENTENCE, "font": key}, w=70, h=60))
    sheet_id = page.url.rsplit("/", 1)[1]
    shown = at(page, "a")
    expect(shown.get_by_text("Gras.")).to_be_visible()
    editor_lines = shown.evaluate(LINE_STARTS)
    editor_family = shown.evaluate(FAMILY_OF)
    printed = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(int(sheet_id))})
    printed.goto(f"{server}/druck/{sheet_id}")
    printed.wait_for_selector("body.ready", state="attached")
    paper = printed.locator(".paper .block").first
    print_lines = paper.evaluate(LINE_STARTS)
    print_family = paper.evaluate(FAMILY_OF)
    printed.close()
    assert len(editor_lines) >= 2
    assert editor_lines == print_lines
    assert NEW[key] in editor_family and NEW[key] in print_family


@pytest.mark.parametrize("font", ["nord", "sued", "urff"])
@pytest.mark.parametrize("kind", ["l1", "l2", "l3", "l4"])
def test_tall_and_deep_letters_are_whole_on_a_lineatur(editor, kind, font):
    """A7: the capital umlauts and the descenders of a Lineatur are not cut off.

    A Lineatur draws its words in a textarea, and Chromium gives a textarea overflow auto even
    where the CSS says visible, so no style can lift its ink out. The test asks instead whether
    the textarea holds more than it shows: content that does not fit would scroll, and so be cut.
    """
    props = {"kind": kind, "color": "#222222", "font": font, "text": "Äg\nÜp"}
    page = editor(box("a", "ruling", props, x=10, y=40, w=90, h=40))
    unpick(page)
    page.evaluate("document.fonts.ready.then(() => 0)")
    written = at(page, "a").locator(".written").first
    fits = written.evaluate(
        "el => [el.scrollHeight <= el.clientHeight, el.scrollWidth <= el.clientWidth]"
    )
    assert fits == [True, True], (font, kind, fits)


def test_umlauts_and_digits_come_from_the_font_itself(editor, server):
    """A7 each, PDF: umlauts and digits print in the font alone, with no fallback in the file."""
    for key in NEW:
        client = user()
        props = {**TEXT, "text": "äöüß ÄÖÜ 0123456789", "font": key}
        mine = sheet(client, [block("text", 15, 14, props)])
        assert pdf_fonts(server, client, mine["id"]) == {PDF_NAME[key]}


def test_the_menu_groups_and_shows_each_name_in_its_font(editor):
    """A8: the menu has two groups, each option shows its own font, the menu its chosen one."""
    page = editor(
        box("a", "text", TEXT),
        box("t", "table", TABLE, z=2),
        box("r", "ruling", RULING, z=3),
    )
    for name, label in (
        ("a", "Schriftart"),
        ("t", "Schriftart der Tabelle"),
        ("r", "Schriftart auf den Zeilen"),
    ):
        pick(page, name)
        menu = page.get_by_label(label, exact=True)
        groups = menu.locator("optgroup").evaluate_all("els => els.map((g) => g.label)")
        assert groups == ["Druckschriften", "Grund- und Schreibschriften"]
        values = menu.locator("option").evaluate_all("els => els.map((o) => o.value)")
        assert values == MENU
        for key, family in FAMILY.items():
            expect_family(menu.locator(f'option[value="{key}"]'), family)
    pick(page, "a")
    choose(page, "Schriftart", "nord")
    expect_family(page.get_by_label("Schriftart", exact=True), "Fibel Nord")


@pytest.mark.parametrize("key", NEW)
def test_a_font_change_is_one_undo_step(editor, key):
    """A9 each: a font is one undo step, Control+z gives Andika back and Control+y the new font."""
    page = editor(box("a", "text", {**TEXT, "text": UMLAUT}))
    pick(page, "a")
    word = at(page, "a").get_by_text("0123456789").first
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        choose(page, "Schriftart", key)
    expect_family(word, NEW[key])
    step(page, lambda: page.keyboard.press("Control+z"))
    expect_family(word, "Andika")
    step(page, lambda: page.keyboard.press("Control+y"))
    expect_family(word, NEW[key])


def test_an_old_sheet_opens_unchanged(editor, server):
    """A11: a sheet saved before the new fonts keeps each text's font, and the one with none."""
    client = user()
    fonts = ["andika", "grund", "va", "sas", "la", None]
    blocks = [
        box("t" + str(i), "text", {**TEXT, "text": "Alt", **({"font": f} if f else {})}, z=i + 1)
        for i, f in enumerate(fonts)
    ]
    page = editor(*blocks, client=client)
    for i, family in enumerate(
        [
            "Andika",
            "Playwrite DE Grund Variable",
            "Playwrite DE VA Variable",
            "Playwrite DE SAS Variable",
            "Playwrite DE LA Variable",
            "Andika",
        ]
    ):
        expect_family(at(page, "t" + str(i)).get_by_text("Alt").first, family)
    sheet_id = page.url.rsplit("/", 1)[1]
    stored = client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]
    found = {b["id"]: b["props"].get("font") for b in stored}
    assert [found["t" + str(i)] for i in range(6)] == fonts


def test_one_choice_sets_the_font_of_all_picked_blocks(editor):
    """I1: one choice sets the font of every picked block, and one Control+z puts all back."""
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2),
        box("c", "shape", {**RECT, "text": "Im Kasten"}, z=3),
    )
    pick(page, "a", "b", "c")
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        choose(page, "Schriftart", "urff")
    for name in "abc":
        expect_family(
            at(page, name).get_by_text(re.compile(r"Im Kasten|Hallo")).first, "Grundschrift Urff"
        )
    step(page, lambda: page.keyboard.press("Control+z"))
    for name in "abc":
        expect_family(at(page, name).get_by_text(re.compile(r"Im Kasten|Hallo")).first, "Andika")


def test_bold_and_italic_use_the_fonts_own_cuts(server):
    """I4: bold and italic runs take the font's own cuts, and nothing else is embedded."""
    client = user()
    runs = [{"text": "Fett", "bold": True}]
    bold_urff = {**TEXT, "text": "Fett", "font": "urff", "rich": [{"runs": runs}]}
    mine = sheet(client, [block("text", 15, 14, bold_urff)])
    assert pdf_fonts(server, client, mine["id"]) == {b"Grundschrift-Bold"}
    bold = {**TEXT, "text": "Fett", "font": "nord", "rich": [{"runs": runs}]}
    slant = {
        **TEXT,
        "text": "Schief",
        "font": "nord",
        "rich": [{"runs": [{"text": "Schief", "italic": True}]}],
    }
    mine = sheet(client, [block("text", 15, 14, bold), block("text", 40, 14, slant)])
    assert pdf_fonts(server, client, mine["id"]) == {b"FibelNord-Bold", b"FibelNord-Italic"}
