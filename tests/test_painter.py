"""The format painter: one block's look carried to the next one picked, in Chromium."""

import re

from playwright.sync_api import expect
from ui import (
    FIELD,
    ITEM,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    maths,
    pick,
    picture,
    saved,
    stopped,
    unpick,
    upload,
    user,
)

# All that travels, each unlike what a new text has.
LOOK = {
    "font": "grund",
    "size": 20,
    "bold": True,
    "italic": True,
    "underline": True,
    "color": "#ff0000",
    "spacing": 1.6,
    "align": "right",
    "valign": "bottom",
    "fill": "#00ff00",
    "opacity": 0.5,
    "stroke": "#0000ff",
    "strokeWidth": 2,
    "dash": "dashed",
}
FINE = {**TEXT, **LOOK}
# A shape of 60 by 40 mm with room around it.
ROOM = {"x": 75, "y": 150, "w": 60, "h": 40}


def brush(page):
    return page.get_by_label("Format übertragen", exact=True)


def expect_brush(page, on):
    """Waits until the brush is on or off: the button, the cursor over the desk and the editor."""
    expect(brush(page)).to_have_attribute("aria-pressed", "true" if on else "false")
    desk, main = page.locator(".desk"), page.locator("main.editor")
    if on:
        expect(desk).to_have_css("cursor", "copy")
        expect(main).to_have_class(re.compile(r"\bbrush\b"))
    else:
        expect(desk).not_to_have_css("cursor", "copy")
        expect(main).not_to_have_class(re.compile(r"\bbrush\b"))


def paint(page, source, target, *group):
    """Picks the look of `source` up with one click on the brush and lays it on `target`."""
    pick(page, source)
    brush(page).click()
    expect_brush(page, True)
    at(page, target).click()
    # The painted block is the selected one, with its group, and the brush is spent.
    expect_picked(page, target, *group)
    expect_brush(page, False)


def held(page, client):
    """The props of each block as the server holds them, by the block's name."""
    return {b["id"]: b["props"] for b in saved(page, client)}


def look(props):
    """What of the look these props set. A key they lack counts as one set to nothing."""
    return {key: props.get(key) for key in LOOK}


def whole(page, client):
    """Each block as the server holds it, by the block's name: its numbering and its box too."""
    return {b["id"]: b for b in saved(page, client)}


def marks(page, client):
    """The numbering before each block. A block with none has no `mark` at all."""
    return {b["id"]: b.get("mark", "keins") for b in saved(page, client)}


STAR = {"code": "2B50"}
SCRIPT = {**RULING, "font": "grund", "color": "#ff0000"}
# One block of every type by name, "b" and "c" in one group.
EVERY = ("text", "form", "strich", "bild", "stern", "tabelle", "lines", "rechnen", "name", "punkte")
EVERY = (*EVERY, "b")


def cell(name, kind, props, i, **more):
    """A block 80 mm wide at the `i`th place of two columns, so more of them fit a page."""
    place = {"z": i + 1, "x": 15 + 100 * (i % 2), "y": 20 + 30 * (i // 2), "w": 80}
    return box(name, kind, props, **{**place, **more})


def every(client):
    """One block of every type, each with room of its own, and two texts in a group."""
    kinds = {
        "text": ("text", TEXT),
        "form": ("shape", RECT),
        "strich": ("shape", LINE),
        "bild": ("image", picture(upload(client))["props"]),
        "stern": ("symbol", STAR),
        "tabelle": ("table", TABLE),
        "lines": ("ruling", RULING),
        "rechnen": ("maths", maths(client)),
        "name": ("name", {}),
        "punkte": ("points", {"max": 10}),
        "b": ("text", TEXT),
        # A list, which a brush with no look for a text must leave whole.
        "c": ("text", ITEM),
    }
    return [
        cell(name, kind, props, i, **({"group": ["g"]} if name in ("b", "c") else {}))
        for i, (name, (kind, props)) in enumerate(kinds.items())
    ]


def test_a_lineatur_carries_its_script(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "font": "grund"}),
        box("b", "ruling", {**RULING, "text": "du"}, z=2),
        box("c", "ruling", RULING, z=3),
        box("d", "ruling", {**RULING, "font": "va"}, z=4),
        client=client,
    )
    paint(page, "a", "b")
    # A Lineatur with no script of its own is in print, and so is the one it paints.
    paint(page, "c", "d")
    now = held(page, client)
    assert now["b"] == {**RULING, "text": "du", "font": "grund"}
    assert now["d"] == RULING


def test_a_lineatur_carries_its_colour(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "color": "#ff0000"}),
        box("b", "ruling", {**RULING, "kind": "l1", "trace": True}, z=2),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    # The source has no Nachspuren, so the painted one loses its own.
    assert held(page, client)["b"] == {**RULING, "kind": "l1", "color": "#ff0000"}


GREY = "rgb(170, 170, 170)"


def test_a_lineatur_carries_nachspuren(editor):
    client = user()
    karo = {"kind": "k5", "color": "#222222", "text": "du"}
    page = editor(
        box("a", "ruling", {**RULING, "text": "ich", "trace": True}),
        box("b", "ruling", {**RULING, "text": "du"}, z=2),
        box("k", "ruling", karo, z=3),
        box("c", "ruling", {**RULING, "kind": "l1", "text": "wir"}, z=4),
        client=client,
    )
    expect(at(page, "b").locator(".written")).not_to_have_css("color", GREY)
    paint(page, "a", "b")
    expect(at(page, "b").locator(".written")).to_have_css("color", GREY)
    # Karo draws its letters itself, and they turn grey too. It gives the grey on as well.
    paint(page, "a", "k")
    expect(at(page, "k").locator("svg.ruling text").first).to_have_attribute("fill", "#aaaaaa")
    paint(page, "k", "c")
    expect(at(page, "c").locator(".written")).to_have_css("color", GREY)
    now = held(page, client)
    assert now["b"] == {**RULING, "text": "du", "trace": True}
    assert now["k"] == {**karo, "trace": True}
    assert now["c"] == {**RULING, "kind": "l1", "text": "wir", "trace": True}


def test_no_nachspuren_takes_nachspuren_off(editor):
    client = user()
    traced = {**RULING, "text": "du", "trace": True}
    page = editor(
        box("a", "ruling", {**RULING, "text": "ich"}),
        box("b", "ruling", traced, z=2),
        client=client,
    )
    undo = page.get_by_label("Rückgängig")
    paint(page, "a", "b")
    expect(at(page, "b").locator(".written")).not_to_have_css("color", GREY)
    assert held(page, client)["b"] == {**RULING, "text": "du"}
    undo.click()
    # One step is all there is.
    expect(undo).to_be_disabled()
    expect(at(page, "b").locator(".written")).to_have_css("color", GREY)
    assert held(page, client)["b"] == traced


RED_LINE = "rgb(255, 0, 0)"


def test_a_table_gives_a_lineatur_the_colour_of_its_lines(editor):
    client = user()
    # The table's text is blue and its lines are red: the lines of the Lineatur take the red.
    table = {**TABLE, "color": "#0000ff", "line": "#ff0000"}
    page = editor(
        box("tabelle", "table", table, h=30),
        box("b", "ruling", {**RULING, "color": "#888888", "trace": True}, z=3),
        client=client,
    )
    paint(page, "tabelle", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    # A table has no Nachspuren to give or to take off.
    assert held(page, client)["b"] == {**RULING, "color": "#ff0000", "trace": True}


def test_a_table_that_names_no_line_colour_leaves_a_lineatur_its_own(editor):
    client = user()
    # A table made outside the editor may have no `line`: the Lineatur's lines must not vanish.
    page = editor(
        box("tabelle", "table", TABLE, h=30, mark="1."),
        box("b", "ruling", {**RULING, "color": "#888888"}, z=3),
        client=client,
    )
    paint(page, "tabelle", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#888888")
    b = whole(page, client)["b"]
    assert (b["mark"], b["props"]) == ("1.", {**RULING, "color": "#888888"})


def test_a_lineatur_gives_a_table_the_colour_of_its_lines(editor):
    client = user()
    table = {**TABLE, "color": "#0000ff", "line": "#ff0000"}
    page = editor(
        box("a", "ruling", {**RULING, "color": "#888888", "trace": True}),
        box("tabelle", "table", table, z=2, h=30),
        client=client,
    )
    paint(page, "a", "tabelle")
    expect(at(page, "tabelle").locator(".table")).to_have_css("border-color", "rgb(136, 136, 136)")
    # The text of the table keeps its colour: the brush brought the colour of lines alone.
    expect(at(page, "tabelle").locator(".table")).to_have_css("color", "rgb(0, 0, 255)")
    assert held(page, client)["tabelle"] == {**table, "line": "#888888"}


def test_a_table_gives_a_table_the_colour_of_its_lines(editor):
    client = user()
    page = editor(
        box("a", "table", {**TABLE, "color": "#0000ff", "line": "#ff0000"}, h=30),
        box("tabelle", "table", {**TABLE, "color": "#00ff00", "line": "#222222"}, z=3, h=30),
        client=client,
    )
    paint(page, "a", "tabelle")
    expect(at(page, "tabelle").locator(".table")).to_have_css("border-color", RED_LINE)
    # Text colour to text colour, line colour to line colour.
    assert held(page, client)["tabelle"] == {**TABLE, "color": "#0000ff", "line": "#ff0000"}


def test_a_table_and_a_lineatur_take_the_colour_of_lines_together(editor):
    client = user()
    group = {"group": ["g"]}
    table = {**TABLE, "color": "#0000ff", "line": "#222222"}
    page = editor(
        box("a", "ruling", {**RULING, "color": "#ff0000"}),
        box("tabelle", "table", table, z=2, h=20, **group),
        box("b", "ruling", RULING, z=3, **group),
        box("c", "table", table, z=4, h=20),
        box("d", "ruling", RULING, z=5),
        client=client,
    )
    paint(page, "a", "tabelle", "b")
    # A selection takes it as a group does.
    pick(page, "a")
    page.keyboard.press("Control+Shift+C")
    pick(page, "c", "d")
    page.keyboard.press("Control+Shift+V")
    for name in ("tabelle", "c"):
        expect(at(page, name).locator(".table")).to_have_css("border-color", RED_LINE)
        expect(at(page, name).locator(".table")).to_have_css("color", "rgb(0, 0, 255)")
    for name in ("b", "d"):
        expect(at(page, name).locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    now = held(page, client)
    assert now["tabelle"] == now["c"] == {**table, "line": "#ff0000"}
    assert now["b"] == now["d"] == {**RULING, "color": "#ff0000"}


def test_a_maths_block_carries_its_size(editor):
    client = user()
    page = editor(
        box("a", "maths", maths(client, size=28), h=24),
        box("b", "maths", maths(client, seed=8), z=2, h=12),
        client=client,
    )
    paint(page, "a", "b")
    b = whole(page, client)["b"]
    # The exercises stay, and the block is as high as they need now.
    assert b["props"] == {**maths(client, seed=8), "size": 28}
    assert b["h"] == 24


def test_the_numbering_travels_to_every_block_type(editor):
    client = user()
    blocks = every(client)
    # A name field and a symbol have the numbering alone to give.
    page = editor(
        *blocks,
        cell("eins", "name", {}, 12, mark="1."),
        cell("zwei", "symbol", STAR, 13, mark="2B50"),
        client=client,
    )
    for source, mark in (("eins", "1."), ("zwei", "2B50")):
        pick(page, source)
        brush(page).dblclick()
        expect_brush(page, True)
        for name in EVERY:
            at(page, name).click()
            expect_picked(page, *(["b", "c"] if name == "b" else [name]))
        page.keyboard.press("Escape")
        expect_brush(page, False)
        now = marks(page, client)
        assert now == {"eins": "1.", "zwei": "2B50", **{b["id"]: mark for b in blocks}}
    # The numbering alone came: no block has more or less than before.
    assert held(page, client) == {
        **{b["id"]: b["props"] for b in blocks},
        "eins": {},
        "zwei": STAR,
    }


def test_font_and_size_cross_between_types(editor):
    client = user()
    text = {**FINE, "font": "va"}
    plain = {key: value for key, value in FINE.items() if key != "font"}
    page = editor(
        cell("lines", "ruling", SCRIPT, 0),
        cell("rechnen", "maths", maths(client, size=28), 1, h=24),
        cell("a", "text", text, 2),
        cell("b", "text", plain, 3),
        cell("form", "shape", {**RECT, "size": 20, "color": "#0000ff"}, 4),
        cell("tabelle", "table", TABLE, 5),
        cell("d", "ruling", RULING, 6),
        cell("e", "maths", maths(client), 7, h=12),
        client=client,
    )
    for name in ("b", "form", "tabelle"):
        paint(page, "lines", name)
    now = held(page, client)
    # The script alone: a Lineatur's colour is that of its lines, and no text's.
    assert now["b"] == {**plain, "font": "grund"}
    assert now["form"] == {**RECT, "size": 20, "color": "#0000ff", "font": "grund"}
    # A table has lines too, and they take the colour.
    assert now["tabelle"] == {**TABLE, "font": "grund", "line": "#ff0000"}
    for name in ("b", "form", "tabelle"):
        paint(page, "rechnen", name)
    now = held(page, client)
    assert now["b"] == {**plain, "font": "grund", "size": 28}
    assert now["form"] == {**RECT, "size": 28, "color": "#0000ff", "font": "grund"}
    assert now["tabelle"] == {**TABLE, "font": "grund", "size": 28, "line": "#ff0000"}
    # And back: a text gives its script and its size, and its colour stays a text's.
    paint(page, "a", "d")
    paint(page, "a", "e")
    now = whole(page, client)
    assert now["d"]["props"] == {**RULING, "font": "va"}
    assert now["e"]["props"] == {**maths(client), "size": 20}
    assert now["e"]["h"] == 17


def test_no_numbering_takes_the_numbering_off(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2, mark="1."),
        box("lines", "ruling", RULING, z=3, mark="2B50"),
        box("c", "text", TEXT, z=4, mark="a)"),
        client=client,
    )
    paint(page, "a", "b")
    paint(page, "a", "lines")
    assert marks(page, client) == {"a": "keins", "b": "keins", "lines": "keins", "c": "a)"}


def test_undo_takes_a_paint_on_a_maths_block_back_in_one_step(editor):
    client = user()
    large = maths(client, size=28, numbering="1.")
    page = editor(
        box("a", "maths", large, h=24, mark="a)"),
        box("b", "maths", large, z=2, h=24, mark="a)"),
        box("c", "maths", maths(client), z=3, h=12),
        client=client,
    )
    undo, redo = page.get_by_label("Rückgängig"), page.get_by_label("Wiederholen")
    # A block that looks like the source already has nothing to take back.
    paint(page, "a", "b")
    expect(undo).to_be_disabled()
    paint(page, "a", "c")
    expect(undo).to_be_enabled()
    undo.click()
    # Size, height and both numberings came in one step, so one undo is all there is.
    expect(undo).to_be_disabled()
    c = whole(page, client)["c"]
    assert (c["props"], c["h"], "mark" in c) == (maths(client), 12, False)
    redo.click()
    expect(redo).to_be_disabled()
    c = whole(page, client)["c"]
    assert (c["props"], c["h"], c["mark"]) == (large, 24, "a)")


def test_the_keys_paint_a_mixed_selection(editor):
    client = user()
    page = editor(
        box("lines", "ruling", SCRIPT, mark="1."),
        box("a", "text", TEXT, z=2),
        box("b", "ruling", RULING, z=3),
        box("c", "maths", maths(client), z=4, h=12),
        box("rechnen", "maths", maths(client, size=28), z=5, h=24),
        box("d", "text", TEXT, z=6),
        box("e", "maths", maths(client), z=7, h=12),
        client=client,
    )
    pick(page, "lines")
    assert stopped(page, "Control+Shift+C")
    expect_brush(page, False)
    pick(page, "a", "b", "c")
    assert stopped(page, "Control+Shift+V")
    expect_picked(page, "a", "b", "c")
    pick(page, "rechnen")
    page.keyboard.press("Control+Shift+C")
    pick(page, "d", "e")
    page.keyboard.press("Control+Shift+V")
    expect_picked(page, "d", "e")
    now = whole(page, client)
    assert now["a"]["props"] == {**TEXT, "font": "grund"}
    assert now["b"]["props"] == SCRIPT
    assert now["c"]["props"] == maths(client)
    assert [now[name]["mark"] for name in "abc"] == ["1."] * 3
    assert now["d"]["props"] == {**TEXT, "size": 28}
    assert (now["e"]["props"], now["e"]["h"]) == (maths(client, size=28), 24)


def test_a_mixed_group_takes_the_look(editor):
    client = user()
    group = {"group": ["g"]}
    bild = {**picture(upload(client)), "id": "bild", "z": 5, "y": 200, "h": 30, **group}
    page = editor(
        box("lines", "ruling", SCRIPT, mark="1."),
        box("a", "text", TEXT, z=2, **group),
        box("b", "ruling", RULING, z=3, **group),
        box("c", "maths", maths(client), z=4, h=12, **group),
        bild,
        box("d", "text", TEXT, z=7),
        client=client,
    )
    paint(page, "lines", "a", "b", "c", "bild")
    now = whole(page, client)
    assert now["a"]["props"] == {**TEXT, "font": "grund"}
    assert now["b"]["props"] == SCRIPT
    assert (now["c"]["props"], now["c"]["h"]) == (maths(client), 12)
    assert now["bild"]["props"] == bild["props"]
    assert [now[name]["mark"] for name in ("a", "b", "c", "bild")] == ["1."] * 4
    assert (now["d"]["props"], "mark" in now["d"]) == (TEXT, False)


def test_karo_and_written_maths_leave_script_and_size(editor):
    client = user()
    karo = {"kind": "k5", "color": "#ff0000"}
    script = {**RULING, "font": "grund"}
    written = maths(client, format="written")
    page = editor(
        cell("karo", "ruling", karo, 0),
        cell("a", "text", {**TEXT, "font": "grund"}, 1),
        cell("b", "ruling", script, 2),
        cell("c", "ruling", {**script, "color": "#0000ff"}, 3),
        cell("k", "ruling", {"kind": "k7", "color": "#222222"}, 4),
        cell("d", "text", {**TEXT, "size": 20}, 5),
        cell("e", "maths", maths(client, size=28), 6, h=24),
        cell("f", "maths", maths(client, size=28), 7, h=24),
        cell("schrift", "maths", written, 8, h=40),
        cell("g", "maths", written, 9, h=40),
        client=client,
    )
    # Karo is always in print: it gives the colour of its lines alone, and takes it alone.
    paint(page, "karo", "a")
    paint(page, "karo", "b")
    paint(page, "c", "k")
    # A written exercise is as large as its squares: it gives no size and takes none.
    paint(page, "schrift", "d")
    paint(page, "schrift", "e")
    paint(page, "f", "g")
    now = whole(page, client)
    assert now["a"]["props"] == {**TEXT, "font": "grund"}
    assert now["b"]["props"] == {**script, "color": "#ff0000"}
    assert now["k"]["props"] == {"kind": "k7", "color": "#0000ff"}
    assert now["d"]["props"] == {**TEXT, "size": 20}
    assert (now["e"]["props"], now["e"]["h"]) == (maths(client, size=28), 24)
    assert (now["g"]["props"], now["g"]["h"]) == (written, 40)
    # A paint that brings a block nothing is no step: the two colours are the only ones.
    for _ in range(2):
        expect(page.get_by_label("Rückgängig")).to_be_enabled()
        page.get_by_label("Rückgängig").click()
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_several_blocks_give_the_look_of_the_first_that_has_one(editor):
    client = user()
    page = editor(
        box("n", "name", {}),
        box("a", "text", FINE, z=2, mark="1."),
        box("b", "text", TEXT, z=3, mark="a)"),
        client=client,
    )
    # The name field comes first on the page and has a numbering at most: the text beside it gives.
    pick(page, "a", "n")
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect_picked(page, "b")
    assert held(page, client)["b"] == FINE
    assert marks(page, client)["b"] == "1."


def test_the_exercises_numbering_travels(editor):
    client = user()
    page = editor(
        box("a", "maths", maths(client, numbering="1."), h=12),
        box("b", "maths", maths(client), z=2, h=12),
        box("c", "maths", maths(client), z=3, h=12),
        box("d", "maths", maths(client, numbering="a)"), z=4, h=12),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator("b").first).to_have_text("1.")
    # No numbering is a look too.
    paint(page, "c", "d")
    now = whole(page, client)
    assert now["b"]["props"] == maths(client, numbering="1.")
    assert now["d"]["props"] == maths(client)
    assert (now["b"]["h"], now["d"]["h"]) == (12, 12)


def test_the_brush_works_from_an_open_lineatur(editor):
    client = user()
    page = editor(
        box("a", "ruling", SCRIPT),
        box("b", "ruling", {**RULING, "text": "du"}, z=2),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    field = at(page, "a").locator("textarea")
    expect(field).to_be_focused()
    expect(field).to_be_editable()
    # In the field the keys are the browser's and pick nothing up.
    assert not stopped(page, "Control+Shift+C")
    page.keyboard.type("ich")
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect(field).not_to_be_editable()
    expect_picked(page, "b")
    expect_brush(page, False)
    expect(at(page, "b").locator("textarea")).not_to_be_editable()
    now = held(page, client)
    assert now["a"] == {**SCRIPT, "text": "ich"}
    assert now["b"] == {**SCRIPT, "text": "du"}


def test_a_tap_on_the_selected_lineatur_paints(editor):
    client = user()
    page = editor(
        box("a", "ruling", SCRIPT), box("b", "ruling", RULING, z=2), client=client, touch=True
    )
    at(page, "a").tap()
    expect_picked(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    # With no brush a tap on a selected Lineatur opens it. With one the tap paints.
    at(page, "b").tap()
    expect_picked(page, "b")
    at(page, "b").tap()
    expect_brush(page, True)
    expect_picked(page, "b")
    expect(at(page, "b").locator("textarea")).not_to_be_editable()
    assert held(page, client)["b"] == SCRIPT


def test_the_brush_carries_the_font(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "font": "grund"}),
        box("b", "text", {**TEXT, "text": "du"}, z=2),
        client=client,
    )
    paint(page, "a", "b")
    b = held(page, client)["b"]
    assert (b["font"], b["text"]) == ("grund", "du")


def test_the_brush_carries_the_size(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "size": 24}), box("b", "text", TEXT, z=2), client=client
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator(".frame")).to_have_text("Hallo")
    assert held(page, client)["b"]["size"] == 24


def test_the_brush_carries_the_colour(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "color": "#ff0000"}),
        box("b", "text", TEXT, z=2),
        box("c", "text", TEXT, z=3),
        box("d", "text", {**TEXT, "color": "#0000ff"}, z=4),
        client=client,
    )
    paint(page, "a", "b")
    # A text with no colour of its own is black, and so is the one it paints.
    paint(page, "c", "d")
    now = held(page, client)
    assert now["b"]["color"] == "#ff0000"
    assert now["d"].get("color") is None


def test_the_brush_carries_the_fill(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "fill": "#ff0000", "opacity": 0.25}),
        box("b", "text", TEXT, z=2),
        box("c", "text", {**TEXT, "fill": "none"}, z=3),
        box("d", "shape", {**RECT, "fill": "#00ff00", "opacity": 0.5}, z=4),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator(".frame")).to_have_css("background-color", "rgba(255, 0, 0, 0.25)")
    # No fill is a look too: it clears the fill and how far it let through.
    paint(page, "c", "d")
    now = held(page, client)
    assert (now["b"]["fill"], now["b"]["opacity"]) == ("#ff0000", 0.25)
    assert (now["d"]["fill"], now["d"].get("opacity")) == ("none", None)


def test_the_brush_carries_the_border(editor):
    client = user()
    border = {"stroke": "#0000ff", "strokeWidth": 2, "dash": "dashed"}
    page = editor(
        box("a", "text", {**TEXT, **border}),
        box("b", "text", TEXT, z=2),
        box("c", "shape", {**RECT, "stroke": "none"}, z=3),
        box("d", "text", {**TEXT, "size": 20, "stroke": "#222222", "dash": "dotted"}, z=4),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator(".frame")).to_have_css("border-top-color", "rgb(0, 0, 255)")
    paint(page, "c", "d")
    now = held(page, client)
    assert {key: now["b"][key] for key in border} == border
    d = now["d"]
    assert (d["stroke"], d["strokeWidth"], d.get("dash")) == ("none", 0.5, None)
    # A shape that sets no size and no place for its text gives the ones it draws with.
    assert (d["size"], d["align"], d["valign"]) == (14, "center", "middle")


def test_a_tap_paints(editor):
    client = user()
    page = editor(box("a", "text", FINE), box("b", "text", TEXT, z=2), client=client, touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    brush(page).tap()
    expect_brush(page, True)
    at(page, "b").tap()
    expect_picked(page, "b")
    expect_brush(page, False)
    b = held(page, client)["b"]
    # Font, size, colour, fill and border, and the rest of the look with them.
    assert look(b) == LOOK
    assert b["text"] == "Hallo"


def test_one_click_paints_once(editor):
    client = user()
    page = editor(
        box("a", "text", FINE),
        box("b", "text", TEXT, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    paint(page, "a", "b")
    # The next click is a click as ever.
    at(page, "c").click()
    expect_picked(page, "c")
    now = held(page, client)
    assert look(now["b"]) == LOOK
    assert now["c"] == TEXT


def test_a_double_click_keeps_the_brush(editor):
    client = user()
    page = editor(
        box("a", "text", FINE),
        box("b", "text", TEXT, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    pick(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    for name in ("b", "c"):
        at(page, name).click()
        expect_picked(page, name)
        expect_brush(page, True)
    page.keyboard.press("Escape")
    expect_brush(page, False)
    now = held(page, client)
    assert look(now["b"]) == look(now["c"]) == LOOK


def test_the_keys_paint_every_selected_block(editor):
    client = user()
    page = editor(
        box("a", "text", FINE),
        box("b", "text", TEXT, z=2),
        box("c", "shape", {**RECT, "text": "Hallo"}, z=3),
        box("d", "text", TEXT, z=4),
        client=client,
    )
    pick(page, "a")
    assert stopped(page, "Control+Shift+C")
    # The keys carry the look with no brush in the hand, and copy no block.
    expect_brush(page, False)
    assert page.evaluate("localStorage.getItem('clip')") is None
    pick(page, "b", "c")
    assert stopped(page, "Control+Shift+V")
    expect_picked(page, "b", "c")
    # The look stays for the next ones.
    pick(page, "d")
    page.keyboard.press("Control+Shift+V")
    expect_picked(page, "d")
    now = held(page, client)
    assert look(now["b"]) == look(now["c"]) == look(now["d"]) == LOOK
    # Neither key copied or pasted a block.
    assert list(now) == ["a", "b", "c", "d"]
    expect(page.locator(".block")).to_have_count(4)


def test_undo_takes_a_paint_back_in_one_step(editor):
    client = user()
    page = editor(
        box("a", "text", FINE),
        box("b", "text", {**FINE, "text": "du"}, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    undo, redo = page.get_by_label("Rückgängig"), page.get_by_label("Wiederholen")
    # A block that looks like the source already has nothing to take back.
    paint(page, "a", "b")
    expect(undo).to_be_disabled()
    paint(page, "a", "c")
    expect(undo).to_be_enabled()
    undo.click()
    # All of the look came in one step, so one undo is all there is.
    expect(undo).to_be_disabled()
    assert held(page, client)["c"] == TEXT
    redo.click()
    expect(redo).to_be_disabled()
    assert look(held(page, client)["c"]) == LOOK


def test_the_target_keeps_its_words_and_shape(editor):
    client = user()
    style = {
        "bold": True,
        "italic": True,
        "underline": True,
        "align": "right",
        "valign": "bottom",
        "spacing": 1.6,
    }
    star = {**RECT, "kind": "star", "fill": "#ff0000", "text": "Stern"}
    page = editor(
        box("a", "text", {**TEXT, **style}),
        box("stern", "shape", star, z=2, **ROOM, angle=30),
        client=client,
    )
    paint(page, "a", "stern")
    expect(at(page, "stern").locator(".frame")).to_have_text("Stern")
    stern = saved(page, client)[1]
    assert {key: stern[key] for key in (*ROOM, "angle", "type")} == {
        **ROOM,
        "angle": 30,
        "type": "shape",
    }
    props = stern["props"]
    assert (props["kind"], props["text"]) == ("star", "Stern")
    assert {key: props[key] for key in style} == style
    # The text has no fill and no border. A shape says so in full.
    assert (props["fill"], props["stroke"], props["strokeWidth"]) == ("none", "none", 0.5)


def test_words_of_their_own_take_the_look(editor):
    client = user()
    rich = [{"runs": [{"text": "Hallo "}, {"text": "du", "bold": True, "color": "#ff0000"}]}]
    page = editor(
        box("a", "text", {**TEXT, "italic": True, "color": "#0000ff"}),
        box("b", "text", {**TEXT, "text": "Hallo du", "rich": rich}, z=2),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator(".frame")).to_have_text("Hallo du")
    b = held(page, client)["b"]
    assert (b["text"], b["italic"], b["color"], b.get("bold")) == (
        "Hallo du",
        True,
        "#0000ff",
        None,
    )
    runs = [run for para in b.get("rich", []) for run in para["runs"]]
    assert not any("bold" in run or "color" in run for run in runs)
    # With no look of their own left the words may lie in `text` alone.
    assert "".join(run["text"] for run in runs) in ("Hallo du", "")


def test_escape_the_button_and_the_empty_page_end_the_brush(editor):
    client = user()
    page = editor(box("a", "text", FINE), box("b", "text", TEXT, z=2), client=client)
    ends = (
        lambda: page.keyboard.press("Escape"),
        lambda: brush(page).click(),
        lambda: unpick(page),
    )
    for end in ends:
        # From nothing selected each time: a click on a selected text is not a pick.
        unpick(page)
        pick(page, "a")
        brush(page).click()
        expect_brush(page, True)
        end()
        expect_brush(page, False)
    assert held(page, client) == {"a": FINE, "b": TEXT}


def test_every_block_gives(editor):
    client = user()
    page = editor(*every(client), client=client)
    expect(brush(page)).to_be_disabled()
    for name in EVERY:
        at(page, name).click()
        expect_picked(page, *(["b", "c"] if name == "b" else [name]))
        expect(brush(page)).to_be_enabled()
        expect_brush(page, False)
    unpick(page)
    expect(brush(page)).to_be_disabled()


def test_a_tap_on_the_selected_block_paints(editor):
    client = user()
    page = editor(box("a", "text", FINE), box("b", "text", TEXT, z=2), client=client, touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    at(page, "b").tap()
    expect_picked(page, "b")
    # With no brush a tap on a selected text opens it. With one the tap paints.
    at(page, "b").tap()
    expect_brush(page, True)
    expect_picked(page, "b")
    expect(page.locator(FIELD)).to_have_count(0)
    assert look(held(page, client)["b"]) == LOOK


def test_a_group_takes_the_look(editor):
    client = user()
    group = {"group": ["g"]}
    page = editor(
        box("a", "text", FINE),
        box("b", "text", TEXT, z=2, **group),
        box("c", "text", TEXT, z=3, **group),
        box("d", "text", TEXT, z=4),
        client=client,
    )
    paint(page, "a", "b", "c")
    now = held(page, client)
    assert look(now["b"]) == look(now["c"]) == LOOK
    assert now["d"] == TEXT


def test_a_line_takes_the_border_alone(editor):
    client = user()
    place = {"x": 20, "w": 60, "h": 20}
    page = editor(
        box("a", "text", {**FINE, "stroke": "#ff0000"}),
        box("strich", "shape", LINE, z=2, **place, y=90),
        box("c", "text", {**FINE, "stroke": "none"}, z=4),
        box("pfeil", "shape", {**LINE, "kind": "arrow"}, z=5, **place, y=180),
        client=client,
    )
    paint(page, "a", "strich")
    # With no border to give the brush leaves the arrow as it is: a line never vanishes.
    paint(page, "c", "pfeil")
    now = held(page, client)
    # No fill, no font and no place for a text: a line has none of them.
    assert now["strich"] == {**LINE, "stroke": "#ff0000", "strokeWidth": 2, "dash": "dashed"}
    assert now["pfeil"] == {**LINE, "kind": "arrow"}


def test_a_table_takes_font_size_and_colour(editor):
    client = user()
    table = {**TABLE, "line": "#222222"}
    page = editor(box("a", "text", FINE), box("tabelle", "table", table, z=2, h=30), client=client)
    paint(page, "a", "tabelle")
    # The cells, the columns and the lines stay, and a table has no fill or border to take.
    assert held(page, client)["tabelle"] == {
        **table,
        "font": "grund",
        "size": 20,
        "color": "#ff0000",
        "align": "right",
    }


def test_a_picture_and_a_symbol_take_the_numbering_alone(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "z": 2}
    page = editor(
        box("a", "text", FINE, mark="1."),
        bild,
        box("stern", "symbol", STAR, z=7, w=20),
        client=client,
    )
    paint(page, "a", "bild")
    paint(page, "a", "stern")
    assert held(page, client) == {"a": FINE, "bild": bild["props"], "stern": STAR}
    now = whole(page, client)
    assert now["bild"] == {**bild, "mark": "1."}
    assert now["stern"]["mark"] == "1."


def test_the_brush_works_from_an_open_text(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "color": "#ff0000"}),
        box("b", "text", {**TEXT, "text": "du"}, z=2),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    # In the field the keys are the browser's and pick nothing up.
    assert not stopped(page, "Control+Shift+C")
    expect_brush(page, False)
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("Hallo")
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect_picked(page, "b")
    expect_brush(page, False)
    b = held(page, client)["b"]
    # The block's colour and the picked words' bold, both for the whole of the target.
    assert b == {**TEXT, "text": "du", "color": "#ff0000", "bold": True}


def test_a_paint_from_an_open_text_that_changes_nothing_adds_no_step(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT), box("b", "text", {**TEXT, "text": "du"}, z=2), client=client
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    brush(page).click()
    expect_brush(page, True)
    at(page, "b").click()
    expect_brush(page, False)
    # Words that are not bold look as a block does that says nothing of bold.
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert held(page, client)["b"] == {**TEXT, "text": "du"}


def test_the_brush_by_key_takes_no_words_of_an_earlier_press(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("Hallo")
    # The brush goes on by the mouse with bold words picked, and off again.
    brush(page).click()
    expect_brush(page, True)
    brush(page).click()
    expect_brush(page, False)
    pick(page, "c")
    brush(page).focus()
    page.keyboard.press("Space")
    expect_brush(page, True)
    at(page, "b").click()
    expect_brush(page, False)
    assert held(page, client)["b"] == TEXT


def test_escape_in_an_open_text_ends_the_brush(editor):
    page = editor(box("a", "text", FINE), box("b", "text", TEXT, z=2))
    pick(page, "a")
    brush(page).dblclick()
    expect_brush(page, True)
    at(page, "b").click()
    expect_picked(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    # Ctrl+Shift+V is the browser's in the field: it pastes plain text there.
    assert not stopped(page, "Control+Shift+V")
    page.keyboard.press("Escape")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect_brush(page, False)
