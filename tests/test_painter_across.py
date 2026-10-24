"""The brush carries numbering, font and size across block types, including maths and a mixed selection."""

from playwright.sync_api import expect
from test_painter import (
    EVERY,
    FINE,
    SCRIPT,
    STAR,
    brush,
    cell,
    every,
    expect_brush,
    held,
    marks,
    paint,
    whole,
)
from ui import (
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
    stopped,
    upload,
    user,
)


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
