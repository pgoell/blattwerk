"""The format painter: one block's look carried to the next one picked, in Chromium."""

import re

from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
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
    expect(page.get_by_label("Einfügen", exact=True).first).to_be_disabled()
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


def test_the_brush_is_live_only_with_a_look(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("lines", "ruling", RULING, z=2),
        {**picture(upload(client)), "id": "bild", "z": 3},
        client=client,
    )
    expect(brush(page)).to_be_disabled()
    for names in (["lines"], ["bild"], ["lines", "bild"]):
        pick(page, *names)
        expect(brush(page)).to_be_disabled()
    pick(page, "a")
    expect(brush(page)).to_be_enabled()
    expect_brush(page, False)


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


def test_a_picture_takes_nothing(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "z": 2}
    page = editor(box("a", "text", FINE), bild, client=client)
    # The brush still ends, and the picture is selected as by any click.
    paint(page, "a", "bild")
    assert held(page, client) == {"a": FINE, "bild": bild["props"]}


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
