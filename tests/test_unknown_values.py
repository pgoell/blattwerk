"""A sheet from anywhere may hold a value nobody knows: a font, or a Lineatur's kind.

A font nobody knows draws as Druckschrift, and the block keeps its name
through a save, an undo and a print.
"""

import pytest
from playwright.sync_api import expect
from ui import RECT, TABLE, TEXT, at, box, doc, maths, pick, sheet, user

from blattwerk import pdf

RULING = {"kind": "l1", "color": "#222222", "font": "comic", "text": "Hallo"}
WORDS = ["Hallo"]


def watch(page):
    """Collects the page's errors from now on: uncaught ones and those the console logs."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    return errors


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def comic(kind):
    """A block of the kind, with the unknown font `comic`, as a newer image may leave it."""
    blocks = {
        "text": box("a", "text", {**TEXT, "font": "comic"}),
        "shape": box(
            "a", "shape", {**RECT, "text": "Hallo", "size": 14, "align": "left", "font": "comic"}
        ),
        "table": box("a", "table", {**TABLE, "font": "comic"}),
        "ruling": box("a", "ruling", RULING),
        "ruling_list": box(
            "a", "ruling", {"kind": "l3", "color": "#222222", "font": "comic", "list": "copy"}
        ),
        "ruling_house": box("a", "ruling", {**RULING, "house": True}),
        "bows": box("a", "text", {**TEXT, "font": "comic", "syllables": True}),
        "numbers": box("a", "text", {**TEXT, "font": "comic", "lines": 1}),
    }
    return blocks[kind]


KINDS = ["text", "shape", "table", "ruling", "ruling_list", "ruling_house", "bows", "numbers"]


@pytest.mark.parametrize("kind", KINDS)
def test_an_unknown_font_draws_as_druckschrift(editor, kind):
    page = editor(comic(kind), words=WORDS if kind == "ruling_list" else None)
    families = (
        at(page, "a")
        .locator("*")
        .evaluate_all("els => els.map((e) => getComputedStyle(e).fontFamily)")
    )
    assert any("Andika" in family for family in families), families


def test_a_block_with_an_unknown_font_opens_its_panel(editor):
    page = editor(comic("ruling"), box("t", "text", {**TEXT, "font": "comic"}, z=2))
    errors = watch(page)
    pick(page, "a")
    expect(page.get_by_label("Schriftart auf den Zeilen", exact=True)).to_have_value("andika")
    pick(page, "t")
    expect(page.get_by_label("Schriftart", exact=True)).to_have_value("andika")
    assert not errors, errors


def test_the_row_buttons_work_on_a_lineatur_of_an_unknown_kind_and_keep_it(editor):
    client = user()
    page = editor(box("a", "ruling", {**RULING, "kind": "l9"}), client=client)
    errors = watch(page)
    pick(page, "a")
    rows = page.locator(".panel output", has_text="Zeile")
    expect(rows).to_have_text("1 Zeile")
    page.get_by_label("Eine Zeile mehr").click()
    expect(rows).to_have_text("2 Zeilen")
    # Two rows of Lineatur 1, the kind it draws as.
    assert stored(client, page)["a"]["h"] == 40
    assert stored(client, page)["a"]["props"]["kind"] == "l9"
    assert not errors, errors


@pytest.mark.parametrize("dash", [None, "dashed"])
def test_a_shape_kind_that_every_object_has_draws_as_a_rectangle(editor, dash):
    props = {**RECT, "kind": "toString", **({"dash": dash} if dash else {})}
    page = editor(box("a", "shape", props), box("t", "text", TEXT, z=2))
    errors = watch(page)
    expect(at(page, "a")).to_be_visible()
    expect(at(page, "a").locator("svg.outline")).to_have_count(0)
    pick(page, "a")
    assert not errors, errors


def test_an_unknown_font_survives_a_save(editor):
    client = user()
    page = editor(comic("text"), client=client)
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["a"]["props"]["font"] == "comic"


def test_undo_and_redo_keep_an_unknown_font(editor):
    client = user()
    page = editor(comic("text"), client=client)
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+y")
    assert stored(client, page)["a"]["props"]["font"] == "comic"


def test_picking_a_font_replaces_the_unknown_one_and_undo_brings_it_back(editor):
    client = user()
    page = editor(comic("text"), client=client)
    pick(page, "a")
    page.get_by_label("Schriftart", exact=True).select_option("nord")
    assert stored(client, page)["a"]["props"]["font"] == "nord"
    page.keyboard.press("Control+z")
    assert stored(client, page)["a"]["props"]["font"] == "comic"


def test_a_known_and_an_unknown_font_picked_together_open_the_panel(editor):
    page = editor(comic("text"), box("b", "text", {**TEXT, "font": "nord"}, z=2))
    errors = watch(page)
    pick(page, "a", "b")
    expect(page.locator(".panel")).to_be_visible()
    assert not errors, errors


@pytest.mark.parametrize("kind", ["text", "shape", "ruling", "table"])
def test_the_panel_says_an_unknown_font_prints_as_druckschrift(editor, kind):
    known = comic(kind)
    known["props"] = {**known["props"], "font": "nord"}
    page = editor(comic(kind), box("b", kind, known["props"], z=2))
    pick(page, "a")
    expect(page.locator(".panel")).to_contain_text("kennt Blattomat nicht")
    pick(page, "b")
    expect(page.locator(".panel")).not_to_contain_text("kennt Blattomat nicht")


def test_picking_a_known_font_takes_the_line_away_and_undo_brings_it_back(editor):
    page = editor(comic("text"))
    pick(page, "a")
    expect(page.locator(".panel")).to_contain_text("kennt Blattomat nicht")
    page.get_by_label("Schriftart", exact=True).select_option("nord")
    expect(page.locator(".panel")).not_to_contain_text("kennt Blattomat nicht")
    page.keyboard.press("Control+z")
    expect(page.locator(".panel")).to_contain_text("kennt Blattomat nicht")


def test_two_picked_blocks_one_unknown_say_so(editor):
    page = editor(comic("text"), box("b", "text", {**TEXT, "font": "nord"}, z=2))
    pick(page, "a", "b")
    expect(page.locator(".panel")).to_contain_text("kennt Blattomat nicht")


@pytest.mark.parametrize("font", ["comic", "grundschrift"])
def test_print_and_thumbnail_draw_a_sheet_with_an_unknown_font(browser, server, font):
    client = user()
    mine = sheet(client, [box("a", "text", {**TEXT, "font": font})])["id"]
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.add_init_script("localStorage.setItem('tour', '1')")
    page = context.new_page()
    errors = watch(page)
    page.set_extra_http_headers({"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator("body")).to_contain_text("Hallo")
    assert not errors, errors
    context.close()


def test_the_thumbnail_draws_the_text(editor, server):
    page = editor(comic("text"))
    page.goto(server)
    expect(page.locator(".sheets li .paper")).to_contain_text("Hallo")


def test_a_sheet_with_every_value_unknown_opens_prints_and_saves(editor, browser, server):
    client = user()
    # The server only makes the formats it knows, so a format nobody knows is set on a made block.
    spiral = {**maths(client), "format": "spiral"}
    odd = maths(client)
    odd["exercises"][0]["op"] = "%"
    blocks = [
        box(
            "r",
            "ruling",
            {
                "kind": "l9",
                "color": "nocolour",
                "font": "comic",
                "text": "Hallo",
                "trace": "sparkle",
                "fade": "up",
                "list": "x",
            },
            z=1,
        ),
        box(
            "t",
            "text",
            {
                **TEXT,
                "font": "comic",
                "valign": "side",
                "align": "justify",
                "dash": "wavy",
                "trace": "sparkle",
                "tints": ["x"],
                "kind": "blob",
                "color": "nocolour",
                "stroke": "#222222",
            },
            z=2,
        ),
        box("s", "shape", {**RECT, "kind": "blob", "dash": "wavy"}, z=3),
        box("b", "table", {**TABLE, "font": "comic"}, z=4),
        box("m", "maths", spiral, z=5),
        box("o", "maths", odd, z=6),
    ]
    page = editor(*blocks, client=client)
    errors = watch(page)
    for name in ["r", "t", "s", "b", "m", "o"]:
        expect(at(page, name)).to_be_visible()
        pick(page, name)
    expect(page.locator("body")).not_to_contain_text("undefined")
    # A kind nobody knows draws as Lineatur 1: four lines to a row.
    expect(at(page, "r").locator("svg.ruling > line")).to_have_count(4)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    stored_now = stored(client, page)
    for block in blocks:
        assert stored_now[block["id"]]["props"] == block["props"], block["id"]
    assert not errors, errors
    mine = page.url.rsplit("/", 1)[1]
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.add_init_script("localStorage.setItem('tour', '1')")
    printed = context.new_page()
    print_errors = watch(printed)
    printed.set_extra_http_headers({"X-Render-Token": pdf.new_token(mine)})
    printed.goto(f"{server}/druck/{mine}")
    printed.wait_for_selector("body.ready", state="attached")
    assert not print_errors, print_errors
    context.close()
