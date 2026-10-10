"""A locked block stays as it is, as in PowerPoint: no road deletes, cuts, moves, sizes, turns or
writes in it, alone, among free blocks or in a group. It still takes a format, and unlocks with
one click.

The docstrings name the lines of issue #316's checklist.
"""

import pytest
from playwright.sync_api import expect
from test_bar import expect_fitted, more, sized
from test_bar import item as folded
from test_menu import item as entry
from test_menu import right
from ui import (
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    doc,
    drag,
    expect_picked,
    maths,
    pick,
    picture,
    upload,
    user,
)

KINDS = ["text", "shape", "line", "image", "symbol", "table", "ruling", "maths", "group"]
# The kinds that stand for the others where all go one way through the code.
SOME = ["text", "table", "group"]
FRAMES = "new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))"
CLIP = "JSON.parse(localStorage.getItem('clip') ?? '{}').blocks?.map((b) => b.id) ?? []"
# What a block is moved, sized and turned by on the sheet: Moveable's handles, a line's ends and
# a table's column lines.
HANDLES = ".moveable-control, .sheet .end, .sheet > .bar"
OPEN = ".ProseMirror, .block textarea:not([readonly]), .crop"
PLACE = ("X", "Y")
SIZE = ("Breite", "Höhe")
TURNS = ("Rechtsdrehung 90°", "Linksdrehung 90°", "Horizontal spiegeln", "Vertikal spiegeln")
SIDES = ("Links", "Rechts", "Oben", "Unten")


def los(name="los", z=4, **more):
    """A free text below the others."""
    return box(name, "text", {**TEXT, "text": "Los"}, z=z, **more)


def fest(client, kind):
    """A locked block of the kind, named "fest". A group is "fest" with a free text, "frei"."""
    if kind == "group":
        return [
            box("fest", "text", TEXT, locked=True, group=["g"]),
            box("frei", "text", TEXT, z=2, group=["g"]),
        ]
    made = {"text": TEXT, "shape": RECT, "line": LINE, "table": TABLE, "ruling": RULING}
    made["symbol"] = {"code": "2B50"}
    if kind == "image":
        made[kind] = picture(upload(client))["props"]
    if kind == "maths":
        made[kind] = maths(client)
    return [box("fest", "shape" if kind == "line" else kind, made[kind], locked=True)]


def held(kind):
    """The names of what `fest` makes."""
    return ["fest", "frei"] if kind == "group" else ["fest"]


def opened(editor, kind, *others, **window):
    """The editor on the locked block and the others. Gives the page, the user and the sheet."""
    client = user()
    blocks = [*fest(client, kind), *others]
    if window:
        page = sized(editor, *blocks, client=client, **window)
        expect_fitted(page)
        # A long title takes the bar's room (#318), so that "Mehr" holds every command that folds.
        page.get_by_label("Titel").fill("W" * 80)
        page.get_by_label("Titel").press("Enter")
        expect(in_bar(page, "Ausschneiden")).to_have_count(0)
        expect(page.locator(".top .hint")).to_have_text("Gespeichert", timeout=10000)
    else:
        page = editor(*blocks, client=client)
    return page, client, doc(page, client)


def grab(page, kind, *others):
    """Picks the locked block by a click, a group whole, and the others with Shift."""
    at(page, "fest").click()
    for name in others:
        at(page, name).click(modifiers=["Shift"])
    expect_picked(page, *held(kind), *others)


def part(page):
    """Picks the free block of the group alone: by a second click on it."""
    at(page, "frei").click()
    expect_picked(page, "fest", "frei")
    # By its place: the frame around the group lies over it.
    page.mouse.click(*centre(at(page, "frei")))
    expect_picked(page, "frei")


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def unchanged(page, client, before):
    """The sheet is as it was, and nothing was added to undo."""
    # What a key or a click changed is drawn by the frame after it.
    page.evaluate(FRAMES)
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


def without(before, *names):
    """The sheet with these blocks of its first page gone."""
    first, *rest = before["pages"]
    left = [b for b in first["blocks"] if b["id"] not in names]
    return {**before, "pages": [{**first, "blocks": left}, *rest]}


def button(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def act(page, name):
    """A button of the panel that acts at once: a shape's own "Links" for its text is none."""
    return page.locator(".panel .acts").get_by_role("button", name=name, exact=True)


def field(page, label):
    return page.locator(".geo").get_by_label(label, exact=True)


def in_bar(page, name):
    return page.locator("header .top").get_by_label(name, exact=True)


def command(page, road, name):
    """The command by that road: the bar's button, its item under "Mehr", or the menu's of a right
    click on the locked block. The last two open their menu."""
    if road == "bar":
        return in_bar(page, name)
    if road == "mehr":
        more(page).click()
        return folded(page, name)
    right(page, "fest")
    return entry(page, name)


# The window in which, under a long title, "Mehr" holds Ausschneiden, Kopieren, Löschen and Sperren.
NARROW = {"width": 701, "height": 1000, "touch": False, "theme": ""}
ROADS = ["bar", "mehr", "right"]


def window(road):
    return NARROW if road == "mehr" else {}


@pytest.mark.parametrize("key", ["Delete", "Backspace"])
@pytest.mark.parametrize("kind", KINDS)
def test_no_key_deletes_a_locked_block(editor, kind, key):
    """A2, A9, I2"""
    page, client, before = opened(editor, kind)
    grab(page, kind)
    page.keyboard.press(key)
    unchanged(page, client, before)
    expect_picked(page, *held(kind))


@pytest.mark.parametrize("kind", KINDS)
def test_the_bars_loeschen_and_ausschneiden_are_off_for_a_locked_block(editor, kind):
    """A2, A3, A9, I3"""
    page, client, before = opened(editor, kind)
    grab(page, kind)
    for name in ("Löschen", "Ausschneiden"):
        expect(in_bar(page, name)).to_be_disabled()
    expect(in_bar(page, "Kopieren")).to_be_enabled()
    unchanged(page, client, before)


@pytest.mark.parametrize("kind", ["text", "group"])
@pytest.mark.parametrize("road", ["mehr", "right"])
def test_a_menus_loeschen_and_ausschneiden_are_off_for_a_locked_block(editor, road, kind):
    """A2, A3, A9, I3"""
    page, client, before = opened(editor, kind, **window(road))
    grab(page, kind)
    expect(command(page, road, "Löschen")).to_be_disabled()
    # The menu is open: "Mehr" or the right click's.
    item = folded if road == "mehr" else entry
    expect(item(page, "Ausschneiden")).to_be_disabled()
    expect(item(page, "Kopieren")).to_be_enabled()
    page.keyboard.press("Escape")
    unchanged(page, client, before)


@pytest.mark.parametrize("kind", KINDS)
def test_ctrl_x_cuts_no_locked_block_and_the_clipboard_keeps_what_it_held(editor, kind):
    """A3, A9"""
    page, client, before = opened(editor, kind, los())
    pick(page, "los")
    page.keyboard.press("Control+c")
    page.wait_for_function(f"{CLIP}.join() === 'los'")
    grab(page, kind)
    page.keyboard.press("Control+x")
    unchanged(page, client, before)
    assert page.evaluate(CLIP) == ["los"]
    assert page.evaluate("navigator.clipboard.readText()") == "Los"


@pytest.mark.parametrize("kind", KINDS)
def test_no_arrow_and_no_drag_moves_a_locked_block(editor, kind):
    """A4, A9, I2"""
    page, client, before = opened(editor, kind)
    grab(page, kind)
    for key in ("ArrowRight", "ArrowDown", "Shift+ArrowLeft", "Shift+ArrowUp"):
        page.keyboard.press(key)
    x, y = centre(at(page, "fest"))
    drag(page, (x, y), (x + 60, y + 40))
    unchanged(page, client, before)


@pytest.mark.parametrize("kind", KINDS)
def test_the_panel_moves_sizes_and_turns_no_locked_block(editor, kind):
    """A4, A5, A6, A9"""
    page, client, before = opened(editor, kind)
    grab(page, kind)
    for label in (*PLACE, *SIZE, "Drehung"):
        expect(field(page, label)).to_be_disabled()
    for name in (*SIDES, "Waagerecht", "Senkrecht", "Gleiche Breite", "Gleiche Höhe"):
        expect(act(page, name)).to_be_disabled()
    for label in TURNS:
        expect(button(page, label)).to_be_disabled()
    unchanged(page, client, before)


@pytest.mark.parametrize("kind", KINDS)
def test_a_locked_block_has_no_handle(editor, kind):
    """A5, A6, A9: none at a corner or an edge, none to turn by, none at a line's ends and none on
    a table's column lines."""
    page, _, _ = opened(editor, kind, los())
    # A free block has them.
    pick(page, "los")
    expect(page.locator(HANDLES)).not_to_have_count(0)
    grab(page, kind)
    expect(page.locator(HANDLES)).to_have_count(0)


def test_a_locked_tables_rows_and_columns_stay(editor):
    """A5"""
    page, client, before = opened(editor, "table")
    grab(page, "table")
    for name in ("Zeile", "Spalte"):
        for way in ("mehr", "weniger"):
            expect(button(page, f"Eine {name} {way}")).to_be_disabled()
    unchanged(page, client, before)


def test_a_locked_lineatur_keeps_its_size(editor):
    """A5"""
    page, client, before = opened(editor, "ruling")
    grab(page, "ruling")
    for label in ("Eine Zeile mehr", "Eine Zeile weniger"):
        expect(button(page, label)).to_be_disabled()
    for name in ("Seitenbreite", "Bis Seitenende"):
        expect(page.locator(".panel").get_by_role("button", name=name)).to_be_disabled()
    unchanged(page, client, before)


def test_a_locked_line_keeps_its_length(editor):
    """A5"""
    page, client, before = opened(editor, "line")
    grab(page, "line")
    expect(button(page, "Länge in cm")).to_be_disabled()
    unchanged(page, client, before)


def test_a_locked_picture_is_not_cropped(editor):
    """A5"""
    page, client, before = opened(editor, "image")
    grab(page, "image")
    expect(page.locator(".panel").get_by_role("button", name="Zuschneiden")).to_have_count(0)
    unchanged(page, client, before)


@pytest.mark.parametrize("kind", KINDS)
def test_nothing_opens_a_locked_block_to_write_in(editor, kind):
    """A7, A9: Enter, F2, a double click, in a table on a cell, and a letter."""
    page, client, before = opened(editor, kind)
    grab(page, kind)
    for key in ("Enter", "F2"):
        page.keyboard.press(key)
        page.evaluate(FRAMES)
        expect(page.locator(OPEN)).to_have_count(0)
    on = at(page, "fest").locator("[data-cell]").first if kind == "table" else at(page, "fest")
    # By its place: the frame around a group lies over it.
    page.mouse.dblclick(*centre(on))
    page.evaluate(FRAMES)
    expect(page.locator(OPEN)).to_have_count(0)
    page.keyboard.type("x")
    unchanged(page, client, before)


MIXED = [*((kind, "Delete") for kind in KINDS), *((kind, "Backspace") for kind in SOME)]


@pytest.mark.parametrize(("kind", "key"), [*MIXED, *((kind, "Control+x") for kind in SOME)])
def test_a_key_takes_only_the_free_blocks_of_a_pick(editor, kind, key):
    """A8, A9"""
    page, client, before = opened(editor, kind, los())
    grab(page, kind, "los")
    page.keyboard.press(key)
    expect(at(page, "los")).to_have_count(0)
    # The locked one stays picked: "Entsperren" is one click away.
    expect_picked(page, *held(kind))
    assert doc(page, client) == without(before, "los")
    if key == "Control+x":
        assert page.evaluate(CLIP) == ["los"]
    # One step of undo, and no more.
    page.keyboard.press("Control+z")
    expect(at(page, "los")).to_have_count(1)
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


@pytest.mark.parametrize("road", ROADS)
def test_loeschen_and_ausschneiden_take_only_the_free_blocks_of_a_pick(editor, road):
    """A8"""
    page, client, before = opened(editor, "text", los(), los("auch", 5), **window(road))
    grab(page, "text", "los")
    command(page, road, "Löschen").click()
    expect(at(page, "los")).to_have_count(0)
    expect_picked(page, "fest")
    at(page, "auch").click(modifiers=["Shift"])
    expect_picked(page, "fest", "auch")
    command(page, road, "Ausschneiden").click()
    expect(at(page, "auch")).to_have_count(0)
    expect_picked(page, "fest")
    assert page.evaluate(CLIP) == ["auch"]
    assert doc(page, client) == without(before, "los", "auch")


@pytest.mark.parametrize("kind", ["text", "line", "group"])
def test_an_arrow_moves_only_the_free_blocks_of_a_pick(editor, kind):
    """A8, A9"""
    page, client, before = opened(editor, kind, los())
    grab(page, kind, "los")
    page.keyboard.press("ArrowRight")
    after = doc(page, client)
    moved = [b for b in after["pages"][0]["blocks"] if b["id"] == "los"]
    assert [b["x"] for b in moved] == [16]
    assert without(after, "los") == without(before, "los")


@pytest.mark.parametrize("kind", SOME)
def test_a_pick_with_a_locked_block_is_not_dragged_sized_or_turned(editor, kind):
    """A8, A9"""
    page, client, before = opened(editor, kind, los())
    grab(page, kind, "los")
    expect(page.locator(HANDLES)).to_have_count(0)
    for label in (*PLACE, *SIZE, "Drehung"):
        expect(field(page, label)).to_be_disabled()
    for label in TURNS:
        expect(button(page, label)).to_be_disabled()
    x, y = centre(at(page, "los"))
    drag(page, (x, y), (x + 60, y + 40))
    unchanged(page, client, before)


def test_a_free_block_of_a_group_with_a_locked_one_stays(editor):
    """A9: picked alone, by a second click, it is held as the group is."""
    page, client, before = opened(editor, "group", los())
    part(page)
    for key in ("Delete", "Backspace", "Control+x", "ArrowRight", "Shift+ArrowDown", "Enter"):
        page.keyboard.press(key)
    page.evaluate(FRAMES)
    expect(page.locator(OPEN)).to_have_count(0)
    expect(page.locator(HANDLES)).to_have_count(0)
    for label in (*PLACE, *SIZE, "Drehung"):
        expect(field(page, label)).to_be_disabled()
    for name in SIDES:
        expect(act(page, name)).to_be_disabled()
    for name in ("Löschen", "Ausschneiden"):
        expect(in_bar(page, name)).to_be_disabled()
    x, y = centre(at(page, "frei"))
    drag(page, (x, y), (x + 60, y + 40))
    unchanged(page, client, before)
    assert page.evaluate(CLIP) == []


def test_a_group_with_a_locked_block_takes_no_other_blocks_size(editor):
    """A9"""
    # The free block is the widest: the group's own free one would grow to it.
    page, client, before = opened(editor, "group", los(x=10, w=190))
    grab(page, "group", "los")
    # The free block alone still lines up with the page.
    expect(act(page, "Links")).to_be_enabled()
    expect(act(page, "Gleiche Breite")).to_be_disabled()
    expect(act(page, "Gleiche Höhe")).to_be_disabled()
    unchanged(page, client, before)


@pytest.mark.parametrize("road", ROADS)
def test_entsperren_frees_a_locked_block_and_entf_then_deletes_it(editor, road):
    """A10"""
    page, client, _ = opened(editor, "text", **window(road))
    # A click picks it.
    grab(page, "text")
    command(page, road, "Entsperren").click()
    expect(command(page, road, "Sperren")).to_be_visible()
    if road != "bar":
        # Shuts the menu again.
        page.keyboard.press("Escape")
    expect_picked(page, "fest")
    page.keyboard.press("Delete")
    expect(at(page, "fest")).to_have_count(0)
    assert doc(page, client)["pages"][0]["blocks"] == []


@pytest.mark.parametrize("whole", [True, False], ids=["whole", "part"])
def test_entsperren_frees_a_group_that_a_locked_block_holds(editor, whole):
    """A10: the group reads as held, picked whole or by its free block, and one click frees it."""
    page, client, _ = opened(editor, "group")
    if whole:
        grab(page, "group")
    else:
        part(page)
    in_bar(page, "Entsperren").click()
    expect(in_bar(page, "Sperren")).to_be_visible()
    assert [b["locked"] for b in doc(page, client)["pages"][0]["blocks"]] == [False, False]
    page.keyboard.press("Delete")
    assert len(doc(page, client)["pages"][0]["blocks"]) == (0 if whole else 1)


def test_a_key_that_a_lock_stops_makes_no_undo_step(editor):
    """I2"""
    page, client, before = opened(editor, "text", los())
    pick(page, "los")
    page.keyboard.press("ArrowRight")
    expect(undo(page)).to_be_enabled()
    grab(page, "text")
    for key in ("Delete", "Backspace", "Control+x", "ArrowRight", "Enter"):
        page.keyboard.press(key)
    # Undo takes back the step before them: there is none of theirs.
    page.keyboard.press("Control+z")
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


def test_ctrl_a_and_entf_leave_the_locked_blocks_picked(editor):
    """I4"""
    client = user()
    blocks = [los("a", 1), los("b", 2, locked=True), los("c", 3), los("d", 4, locked=True)]
    page = editor(*blocks, client=client)
    before = doc(page, client)
    at(page, "a").click()
    page.keyboard.press("Control+a")
    expect_picked(page, "a", "b", "c", "d")
    page.keyboard.press("Delete")
    expect_picked(page, "b", "d")
    assert doc(page, client) == without(before, "a", "c")
    # One click frees them, and then they go.
    in_bar(page, "Entsperren").click()
    page.keyboard.press("Delete")
    expect(page.locator(".block[data-id]")).to_have_count(0)


def test_a_locked_block_still_takes_a_format(editor):
    """I5"""
    page, client, _ = opened(editor, "text")
    grab(page, "text")
    button(page, "Gestrichelt").click()
    button(page, "Füllung").evaluate(
        """(el) => {
            const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
            own.set.call(el, "#ffee00");
            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }"""
    )
    (block,) = doc(page, client)["pages"][0]["blocks"]
    look = {key: block["props"].get(key) for key in ("dash", "stroke", "fill")}
    assert look == {"dash": "dashed", "stroke": "#222222", "fill": "#ffee00"}
    assert block["locked"]
