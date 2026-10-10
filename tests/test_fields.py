"""The fields for position, size and angle in the Format panel, in Chromium on the built app."""

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
    TABLE,
    TEXT,
    angle,
    at,
    box,
    caret,
    centre,
    drag,
    drawer,
    expect_picked,
    grow,
    pick,
    picture,
    saved,
    unpick,
    upload,
    user,
)

LABELS = ("X", "Y", "Breite", "Höhe", "Drehung")
# A rect with room around it to move, grow and turn in.
ROOM = {"x": 40, "y": 60, "w": 80, "h": 40}


def field(page, label):
    return page.locator(".geo").get_by_label(label, exact=True)


def enter(page, label, value):
    """Writes the value into the field and commits it with Enter."""
    field(page, label).fill(value)
    field(page, label).press("Enter")


def lock(page):
    return page.get_by_label("Seitenverhältnis sperren", exact=True)


def expect_fields(page, *values):
    """Waits until X, Y, Breite, Höhe and Drehung show these values."""
    for label, value in zip(LABELS, values, strict=True):
        expect(field(page, label)).to_have_value(value)


def number(page, label):
    """What the field shows as a number: the comma is German."""
    return float(field(page, label).input_value().replace(",", "."))


def by_id(blocks):
    return {block["id"]: block for block in blocks}


def test_x_and_y_show_and_set_the_place(editor):
    client = user()
    page = editor(box("a", "shape", RECT), client=client)
    pick(page, "a")
    expect(field(page, "X")).to_have_value("15")
    expect(field(page, "Y")).to_have_value("50")
    was = at(page, "a").bounding_box()
    enter(page, "X", "40")
    enter(page, "Y", "12,5")
    expect(field(page, "X")).to_have_value("40")
    expect(field(page, "Y")).to_have_value("12,5")
    (a,) = saved(page, client)
    assert (a["x"], a["y"], a["w"], a["h"]) == (40, 12.5, 180, 20)
    now = at(page, "a").bounding_box()
    assert now["x"] > was["x"]
    assert now["y"] < was["y"]


def test_width_and_height_show_and_set_the_size(editor):
    client = user()
    page = editor(box("a", "shape", RECT), client=client)
    pick(page, "a")
    expect(field(page, "Breite")).to_have_value("180")
    expect(field(page, "Höhe")).to_have_value("20")
    enter(page, "Breite", "90")
    enter(page, "Höhe", "35")
    expect_fields(page, "15", "50", "90", "35", "0")
    (a,) = saved(page, client)
    assert (a["x"], a["y"], a["w"], a["h"]) == (15, 50, 90, 35)


def test_the_lock_keeps_the_ratio(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    expect(lock(page)).to_have_attribute("aria-pressed", "false")
    enter(page, "Breite", "100")
    expect(field(page, "Höhe")).to_have_value("40")
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    enter(page, "Breite", "50")
    expect(field(page, "Höhe")).to_have_value("20")
    enter(page, "Höhe", "40")
    expect(field(page, "Breite")).to_have_value("100")
    # A handle keeps the ratio too: the corner goes straight to the right, and the height follows.
    x, y = centre(page.locator(".moveable-control.moveable-se"))
    drag(page, (x, y), (x + 60, y))
    expect(field(page, "Breite")).not_to_have_value("100")
    assert number(page, "Breite") / number(page, "Höhe") == pytest.approx(2.5, rel=0.02)


def test_the_angle_field_turns_the_block(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    expect_fields(page, "40", "60", "80", "40", "0")
    middle = centre(at(page, "a"))
    enter(page, "Drehung", "30")
    expect_fields(page, "40", "60", "80", "40", "30")
    assert angle(page, "a") == 30
    assert centre(at(page, "a")) == pytest.approx(middle, abs=1)


def test_a_finger_sets_a_field(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client, touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    drawer(page, "right")
    x = field(page, "X")
    # The phone shows its keys for numbers, with a comma.
    expect(x).to_have_attribute("inputmode", "decimal")
    x.tap()
    x.fill("25")
    # A tap on another field takes the focus, and the value counts.
    field(page, "Y").tap()
    expect(x).to_have_value("25")
    (a,) = saved(page, client)
    assert a["x"] == 25
    # The fields lie in the panel and are wide enough for a finger.
    panel, geo = (page.locator(css).bounding_box() for css in (".panel", ".panel .geo"))
    assert geo["x"] >= panel["x"]
    assert geo["x"] + geo["width"] <= panel["x"] + panel["width"]
    for label in LABELS:
        assert field(page, label).bounding_box()["width"] >= 60


def test_a_value_counts_on_enter_tab_and_blur(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM), client=client)
    pick(page, "a")
    x, y = field(page, "X"), field(page, "Y")
    was = at(page, "a").bounding_box()
    x.select_text()
    page.keyboard.type("4")
    # Typing alone moves nothing.
    expect(x).to_have_value("4")
    assert at(page, "a").bounding_box() == was
    page.keyboard.press("Enter")
    expect(x).to_have_value("4")
    assert at(page, "a").bounding_box()["x"] < was["x"]
    # Tab commits and goes on to the next field. A point is as good as a comma.
    x.select_text()
    page.keyboard.type("12.5")
    page.keyboard.press("Tab")
    expect(y).to_be_focused()
    expect(x).to_have_value("12,5")
    # A click on another field takes the focus, and the value counts.
    y.fill("12,5")
    field(page, "Breite").click()
    expect(y).to_have_value("12,5")
    (a,) = saved(page, client)
    assert (a["x"], a["y"], a["w"], a["h"]) == (12.5, 12.5, 80, 40)


def test_escape_and_nonsense_change_nothing(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    was = at(page, "a").bounding_box()
    x = field(page, "X")
    x.select_text()
    page.keyboard.type("99")
    page.keyboard.press("Escape")
    expect(x).to_have_value("40")
    # What only JavaScript reads as a number is nonsense too.
    for value in ("abc", "", "1e3", "0x10", "Infinity", "12,5,3"):
        enter(page, "X", value)
        expect(x).to_have_value("40")
    enter(page, "Drehung", "Infinity")
    expect(field(page, "Drehung")).to_have_value("0")
    # A block has a width.
    for value in ("0", "-5"):
        enter(page, "Breite", value)
        expect(field(page, "Breite")).to_have_value("80")
    expect_picked(page, "a")
    expect_fields(page, "40", "60", "80", "40", "0")
    assert at(page, "a").bounding_box() == was
    # Nothing changed, so there is nothing to undo.
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_undo_and_redo_a_typed_value(editor):
    page = editor(box("a", "shape", RECT))
    pick(page, "a")
    enter(page, "X", "40")
    expect(field(page, "X")).to_have_value("40")
    # The focus is still in the field: undo is the sheet's, not the field's own.
    expect(field(page, "X")).to_be_focused()
    page.keyboard.press("Control+z")
    expect(field(page, "X")).to_have_value("15")
    page.keyboard.press("Control+y")
    expect(field(page, "X")).to_have_value("40")
    enter(page, "Breite", "90")
    expect(field(page, "Breite")).to_have_value("90")
    unpick(page)
    pick(page, "a")
    # Each value is a step of its own.
    page.keyboard.press("Control+z")
    expect(field(page, "Breite")).to_have_value("180")
    expect(field(page, "X")).to_have_value("40")


def test_the_fields_follow_the_sheet(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    expect_fields(page, "40", "60", "80", "40", "0")
    page.keyboard.press("ArrowRight")
    expect(field(page, "X")).to_have_value("41")
    page.keyboard.press("Shift+ArrowDown")
    expect(field(page, "Y")).to_have_value("70")
    x, y = centre(at(page, "a"))
    drag(page, (x, y), (x + 50, y + 40))
    expect(field(page, "X")).not_to_have_value("41")
    expect(field(page, "Y")).not_to_have_value("70")
    grow(page, 40)
    expect(field(page, "Breite")).not_to_have_value("80")
    page.get_by_label("Rechtsdrehung 90°", exact=True).click()
    expect(field(page, "Drehung")).to_have_value("90")
    page.keyboard.press("Control+z")
    expect(field(page, "Drehung")).to_have_value("0")


def test_several_blocks_share_a_field(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, w=80, h=40),
        box("b", "shape", RECT, z=2, w=60, h=20),
        client=client,
    )
    pick(page, "a", "b")
    # A field shows what all the blocks share, and nothing where they differ.
    expect_fields(page, "15", "", "", "", "0")
    enter(page, "Y", "100")
    expect(field(page, "Y")).to_have_value("100")
    blocks = by_id(saved(page, client))
    assert [blocks[name]["y"] for name in "ab"] == [100, 100]
    # With the lock each block keeps its own ratio.
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    enter(page, "Breite", "40")
    expect(field(page, "Breite")).to_have_value("40")
    blocks = by_id(saved(page, client))
    assert (blocks["a"]["w"], blocks["a"]["h"]) == (40, 20)
    assert blocks["b"]["w"] == 40
    assert blocks["b"]["h"] == pytest.approx(13.33, abs=0.02)
    # Each block turns about its own centre.
    middles = [centre(at(page, name)) for name in "ab"]
    enter(page, "Drehung", "45")
    expect(field(page, "Drehung")).to_have_value("45")
    for name, middle in zip("ab", middles, strict=True):
        assert angle(page, name) == 45
        assert centre(at(page, name)) == pytest.approx(middle, abs=1)


def test_a_group_moves_as_one_thing(editor):
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=50, w=30, h=20, group=["g"]),
        box("b", "shape", RECT, z=2, x=60, y=50, w=30, h=20, group=["g"]),
        client=client,
    )
    # One click picks a whole group.
    at(page, "a").click()
    expect_picked(page, "a", "b")
    # The fields show the box around the group. It moves, and that is all.
    expect_fields(page, "15", "50", "75", "20", "")
    for label in ("X", "Y"):
        expect(field(page, label)).to_be_enabled()
    for label in ("Breite", "Höhe", "Drehung"):
        expect(field(page, label)).to_be_disabled()
    expect(lock(page)).to_be_disabled()
    enter(page, "X", "25")
    expect(field(page, "X")).to_have_value("25")
    blocks = by_id(saved(page, client))
    assert [blocks[name]["x"] for name in "ab"] == [25, 70]
    assert [blocks[name]["y"] for name in "ab"] == [50, 50]


def test_a_turned_block_and_the_angle_wraps(editor):
    client = user()
    page = editor(box("a", "shape", RECT, **ROOM, angle=30), client=client)
    pick(page, "a")
    # The place and the size are the block's own, as if it lay level.
    expect_fields(page, "40", "60", "80", "40", "30")
    enter(page, "Drehung", "370")
    expect(field(page, "Drehung")).to_have_value("10")
    enter(page, "Drehung", "-90")
    expect(field(page, "Drehung")).to_have_value("270")
    assert angle(page, "a") == 270
    enter(page, "Breite", "100")
    expect_fields(page, "40", "60", "100", "40", "270")
    (a,) = saved(page, client)
    assert (a["x"], a["y"], a["w"], a["h"], a["angle"]) == (40, 60, 100, 40, 270)


def test_fields_that_cannot_change_are_off(editor):
    client = user()
    bild = {**picture(upload(client)), "id": "bild", "z": 4, "x": 20, "y": 150, "w": 60, "h": 40}
    page = editor(
        box("fest", "shape", RECT, locked=True),
        box("table", "table", TABLE, z=2),
        box("line", "shape", LINE, z=3),
        bild,
        client=client,
    )
    # A locked block shows its values and takes none.
    pick(page, "fest")
    expect_fields(page, "15", "50", "180", "20", "0")
    for label in LABELS:
        expect(field(page, label)).to_be_disabled()
    expect(lock(page)).to_be_disabled()
    # A table stays level.
    pick(page, "table")
    expect(field(page, "Drehung")).to_be_disabled()
    for label in ("X", "Y", "Breite", "Höhe"):
        expect(field(page, label)).to_be_enabled()
    # A line turns and grows by its ends.
    pick(page, "line")
    for label in ("Breite", "Höhe", "Drehung"):
        expect(field(page, label)).to_be_disabled()
    for label in ("X", "Y"):
        expect(field(page, label)).to_be_enabled()
    # A picture always keeps its ratio.
    pick(page, "bild")
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    expect(lock(page)).to_be_disabled()
    expect(field(page, "Breite")).to_be_enabled()
    expect(field(page, "Breite")).to_have_value("60")
    ratio = number(page, "Breite") / number(page, "Höhe")
    enter(page, "Breite", "30")
    expect(field(page, "Höhe")).not_to_have_value("40")
    assert number(page, "Breite") / number(page, "Höhe") == pytest.approx(ratio, rel=0.02)


def test_keys_in_a_field_stay_in_it(editor):
    page = editor(box("a", "shape", RECT, **ROOM))
    pick(page, "a")
    x = field(page, "X")
    was = at(page, "a").bounding_box()
    x.click()
    # These keys are the field's own: they delete no block and move none.
    for key in ("Delete", "Backspace", "ArrowLeft", "ArrowRight"):
        page.keyboard.press(key)
    expect(at(page, "a")).to_have_count(1)
    assert at(page, "a").bounding_box() == was
    page.keyboard.press("Escape")
    expect_fields(page, "40", "60", "80", "40", "0")
    # Up and down step by one and count at once.
    x.press("ArrowUp")
    expect(x).to_have_value("41")
    assert at(page, "a").bounding_box()["x"] > was["x"]
    x.press("ArrowDown")
    x.press("ArrowDown")
    expect(x).to_have_value("39")
    assert at(page, "a").bounding_box()["x"] < was["x"]
    field(page, "Drehung").press("ArrowUp")
    expect(field(page, "Drehung")).to_have_value("1")
    assert angle(page, "a") == 1


def test_a_field_while_a_text_is_open(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")
    field(page, "X").click()
    enter(page, "X", "40")
    expect(field(page, "X")).to_have_value("40")
    # The words typed so far are kept.
    expect(at(page, "a")).to_contain_text("du")
    (a,) = saved(page, client)
    assert a["x"] == 40
    assert a["props"]["text"] == "du" or "du" in str(a["props"].get("rich"))


def test_a_text_box_stays_as_high_as_its_text(editor):
    page = editor(box("a", "text", TEXT, h=20))
    pick(page, "a")
    # A height below one line of text does not hold: the box grows back around its words.
    enter(page, "Höhe", "1")
    expect(field(page, "Höhe")).not_to_have_value("1")
    assert 1 < number(page, "Höhe") < 20


# A text of its own blue, whose first word is red.
WORDS = {
    **TEXT,
    "text": "Hallo du",
    "color": "#0000ff",
    "rich": [{"runs": [{"text": "Hallo ", "color": "#ff0000"}, {"text": "du"}]}],
}


def colour(page, value):
    """Picks the colour in "Farbe" as the mouse does: a press in the panel, the focus, the pick.

    Headless Chromium opens no colour picker. The `input` comes while a picker is dragged and
    the `change` when it closes.
    """
    control = page.locator(".panel").get_by_label("Farbe", exact=True)
    control.dispatch_event("pointerdown")
    control.focus()
    # React hears only of a value set as the browser sets it.
    control.evaluate(
        """(el, value) => {
            const own = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
            for (const step of ["#123456", value]) {
                own.set.call(el, step);
                el.dispatchEvent(new Event("input", { bubbles: true }));
            }
            el.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        value,
    )
    return control


# Asked: a colour beside a word


def test_a_colour_beside_a_word_is_for_what_is_typed_next(editor):
    client = user()
    page = editor(box("a", "text", WORDS), client=client)
    caret(page, "du", 2)
    colour(page, "#00ff00")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type(" da")
    expect(page.locator(FIELD)).to_have_text("Hallo du da")
    (a,) = saved(page, client)
    # The block and its words keep their colours.
    assert a["props"]["color"] == "#0000ff"
    assert a["props"]["rich"] == [
        {
            "runs": [
                {"text": "Hallo ", "color": "#ff0000"},
                {"text": "du"},
                {"text": " da", "color": "#00ff00"},
            ]
        }
    ]


# Asked: several texts, bold through their words


@pytest.mark.parametrize(
    "name, label, key",
    [("bold", "Fett", "b"), ("italic", "Kursiv", "i"), ("underline", "Unterstrichen", "u")],
)
def test_a_text_whose_words_all_have_a_look_counts_as_having_it(editor, name, label, key):
    client = user()
    words = [{"runs": [{"text": "Hallo ", name: True}, {"text": "du", name: True}]}]
    page = editor(
        box("a", "text", {**TEXT, "text": "Hallo du", "rich": words}),
        box("b", "text", {**TEXT, name: True}, z=2),
        client=client,
    )
    pick(page, "a", "b")
    button = page.locator(".panel").get_by_label(label, exact=True)
    expect(button).to_have_attribute("aria-pressed", "true")
    page.keyboard.press(f"Control+{key}")
    expect(button).to_have_attribute("aria-pressed", "false")
    for block in saved(page, client):
        assert not block["props"].get(name)
        assert name not in str(block["props"].get("rich"))


# Implied: "Farbe" shows the colour, and one undo


def test_farbe_shows_the_colour_for_what_is_typed_next_and_one_undo_takes_it_away(editor):
    page = editor(box("a", "text", WORDS))
    caret(page, "du", 2)
    expect(colour(page, "#00ff00")).to_have_value("#00ff00")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type(" da so")
    coloured = page.locator(f"{FIELD} span[data-color]")
    expect(coloured).to_have_text(["Hallo ", " da so"])
    page.keyboard.press("Control+z")
    expect(page.locator(FIELD)).to_have_text("Hallo du")
    expect(coloured).to_have_text(["Hallo "])
    expect(at(page, "a").locator(".frame")).to_have_css("color", "rgb(0, 0, 255)")


# Review: a text with no words keeps the colour as its own


def test_a_colour_in_an_empty_text_outlasts_the_field(editor):
    client = user()
    empty = box("a", "text", {**TEXT, "text": ""})
    page = editor(empty, box("b", "shape", RECT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    colour(page, "#00ff00")
    page.keyboard.press("Escape")
    pick(page, "b")
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("x")
    assert saved(page, client)[0]["props"]["color"] == "#00ff00"
