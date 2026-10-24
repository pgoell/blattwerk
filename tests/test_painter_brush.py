"""One click, a double click and the keys lay a block's look on the next blocks, and undo takes it back."""

from playwright.sync_api import expect
from test_painter import (
    EVERY,
    FINE,
    LOOK,
    ROOM,
    SCRIPT,
    STAR,
    brush,
    every,
    expect_brush,
    held,
    look,
    paint,
    whole,
)
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    apart,
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
    blocks = apart(box("a", "ruling", SCRIPT), box("b", "ruling", RULING, z=2))
    # On its side and in the plain layout the iPad's bar has room for the brush's own button.
    page = editor(*blocks, client=client, touch="landscape", theme="")
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
    # A dashed border is drawn over the box.
    expect(at(page, "b").locator(".dashes rect")).to_have_attribute("stroke", "#0000ff")
    paint(page, "c", "d")
    now = held(page, client)
    assert {key: now["b"][key] for key in border} == border
    d = now["d"]
    assert (d["stroke"], d["strokeWidth"], d.get("dash")) == ("none", 0.5, None)
    # A shape that sets no size and no place for its text gives the ones it draws with.
    assert (d["size"], d["align"], d["valign"]) == (14, "center", "middle")


def test_a_tap_paints(editor):
    client = user()
    blocks = apart(box("a", "text", FINE), box("b", "text", TEXT, z=2))
    # On its side and in the plain layout the iPad's bar has room for the brush's own button.
    page = editor(*blocks, client=client, touch="landscape", theme="")
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
    blocks = apart(box("a", "text", FINE), box("b", "text", TEXT, z=2))
    # On its side and in the plain layout the iPad's bar has room for the brush's own button.
    page = editor(*blocks, client=client, touch="landscape", theme="")
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
