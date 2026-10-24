"""Space and a drag move the desk. The hand takes the left button, and a pan is no undo step."""

import pytest
from playwright.sync_api import expect
from test_drop import spot
from test_fields import by_id, field
from test_zoom import (
    HAND,
    KINDS,
    PAN,
    PANNING,
    PLACE,
    expect_fitted,
    expect_in_place,
    expect_scroll,
    expect_width,
    fit,
    of_kind,
    pan,
    percent,
    places,
    roomy,
    scroll,
    settled,
    wheel,
    width,
)
from ui import (
    FIELD,
    LINE,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    centre,
    doc,
    drag,
    expect_picked,
    pick,
    saved,
    user,
)


def test_space_and_drag_moves_the_desk(editor):
    """A3"""
    page = editor(box("a", "text", TEXT))
    roomy(page)
    wide = width(page)
    middle = centre(page.locator(".desk"))
    pan(page, middle, 100, 60)
    pan(page, middle, -40, -90)
    pan(page, middle, 0, 30)
    pan(page, middle, -30, 0)
    # Space on a zoom button that has the focus pans too, and does not press the button.
    page.get_by_label("Größer", exact=True).first.focus()
    pan(page, middle, 20, 20)
    settled(page)
    assert width(page) == pytest.approx(wide, abs=1)
    expect(page.locator(HAND)).to_have_count(0)


@pytest.mark.parametrize("kind", KINDS)
def test_a_space_drag_leaves_the_block_alone(editor, kind):
    """I1"""
    client = user()
    blocks = of_kind(kind, client)
    names = [b["id"] for b in blocks]
    page = editor(*blocks, client=client)
    roomy(page)
    before = places(page, *names)
    # Not selected: the drag starts on the block and neither picks nor moves it.
    pan(page, centre(at(page, "a")), 100, 60)
    expect_picked(page)
    expect_in_place(page, names, before)
    # Selected, a group by one click: it stays so, and where it was.
    at(page, "a").click()
    expect_picked(page, *names)
    pan(page, centre(at(page, "a")), -60, -40)
    expect_picked(page, *names)
    expect_in_place(page, names, before)
    # Nothing opened either: no text, no cell, no crop.
    expect(page.locator(".ProseMirror, .block textarea:not([readonly]), .crop")).to_have_count(0)
    expect(page.locator(HAND)).to_have_count(0)


def test_a_space_drag_keeps_a_selection_of_several(editor):
    """I1"""
    low, lower = {**PLACE, "y": 110}, {**PLACE, "y": 160}
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("b", "shape", RECT, z=2, **low),
        box("c", "shape", LINE, z=3, **lower),
        box("d", "shape", RECT, z=4, x=15, y=110, w=35, h=40),
    )
    names = ["a", "b", "c"]
    pick(page, *names)
    roomy(page)
    before = places(page, *names, "d")
    # On the empty page, on a block that is not picked, and on one that is.
    for start in (
        lambda: spot(page, 40, 90),
        lambda: centre(at(page, "d")),
        lambda: centre(at(page, "b")),
    ):
        pan(page, start(), 60, 40)
        expect_picked(page, *names)
        expect_in_place(page, [*names, "d"], before)


@pytest.mark.parametrize("where", ["text", "cell", "field"])
def test_space_in_a_text_types_a_space(editor, where):
    """I2"""
    page = editor(
        box("a", "text", TEXT, **PLACE),
        box("t", "table", TABLE, z=2, x=60, y=120, w=60, h=40),
    )
    if where == "text":
        caret(page, "Hallo", 2)
        held = page.locator(FIELD)
    elif where == "cell":
        pick(page, "t")
        page.keyboard.press("Enter")
        held = at(page, "t").locator("textarea")
        expect(held).to_be_focused()
        page.keyboard.press("End")
    else:
        pick(page, "t")
        held = field(page, "X")
        held.click()
        expect(held).to_be_focused()
        # The click picked all of the number.
        page.keyboard.press("End")
    page.keyboard.down("Space")
    if where == "text":
        expect(held).to_have_text("Ha llo")
    else:
        expect(held).to_have_value("H " if where == "cell" else "60 ")
    expect(page.locator(HAND)).to_have_count(0)
    expect(page.locator("main.editor")).not_to_have_class(PAN)
    # The page is higher than the desk: a pan by a drag upwards would scroll it down.
    assert scroll(page) == [0, 0]
    if where == "text":
        # Along the first line and a little up, from behind the last letter to before the first.
        edge = held.bounding_box()
        drag(page, (edge["x"] + 80, edge["y"] + 16), (edge["x"] + 2, edge["y"] + 4))
    else:
        x, y = centre(held)
        drag(page, (x, y), (x - 30, y - 40))
    settled(page)
    page.keyboard.up("Space")
    assert scroll(page) == [0, 0]
    expect(page.locator("main.editor")).not_to_have_class(PANNING)
    expect(held).to_be_focused()
    if where == "text":
        # The drag picked letters, as it does with no key held.
        assert page.evaluate("getSelection().toString()") != ""


def test_zoom_and_pan_are_no_undo_steps(editor):
    """I5"""
    client = user()
    page = editor(box("a", "shape", RECT, **PLACE), box("b", "text", TEXT, z=3), client=client)
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("Rückgängig")).to_be_enabled()
    edited = doc(page, client)
    assert by_id(edited["pages"][0]["blocks"])["a"]["x"] != PLACE["x"]
    wide = width(page)
    wheel(page, -100)
    expect_width(page, wide * 1.25)
    wheel(page, -100)
    expect_width(page, wide * 1.25**2)
    page.locator(".desk").evaluate("el => el.scrollTo(200, 200)")
    pan(page, centre(page.locator(".desk")), 80, 50)
    fit(page).click()
    expect_fitted(page, 0, 210, 297)
    expect_picked(page, "a")
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert")
    assert doc(page, client) == edited
    # One step back is the edit's, and there is no other.
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Rückgängig")).to_be_disabled()
    assert by_id(saved(page, client))["a"]["x"] == PLACE["x"]
    expect_picked(page, "a")


def test_space_shows_a_hand_and_lets_go(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    main, hand, desk = page.locator("main.editor"), page.locator(HAND), page.locator(".desk")
    # On the empty desk, so nothing else has the focus. Space alone scrolls nothing.
    corner = desk.bounding_box()
    page.mouse.click(corner["x"] + 10, corner["y"] + 10)
    page.keyboard.down("Space")
    expect(main).to_have_class(PAN)
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(1)
    expect(hand).to_have_css("cursor", "grab")
    settled(page)
    page.keyboard.up("Space")
    expect(main).not_to_have_class(PAN)
    expect(hand).to_have_count(0)
    settled(page)
    assert scroll(page) == [0, 0]

    # The drag goes on after Space is let go, until the mouse lifts.
    x, y = centre(desk)
    page.keyboard.down("Space")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 50, steps=5)
    expect(main).to_have_class(PANNING)
    expect(hand).to_have_css("cursor", "grabbing")
    expect_scroll(page, 0, 50)
    page.keyboard.up("Space")
    expect(main).not_to_have_class(PAN)
    expect(main).to_have_class(PANNING)
    expect(hand).to_have_count(1)
    page.mouse.move(x, y - 80, steps=5)
    expect_scroll(page, 0, 80)
    page.mouse.up()
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(0)
    # The mouse alone moves no desk now.
    drag(page, (x, y), (x, y - 40))
    settled(page)
    assert scroll(page) == [0, 80]

    # The window losing the focus ends both.
    page.keyboard.down("Space")
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y - 20, steps=5)
    expect(main).to_have_class(PANNING)
    expect(main).to_have_class(PAN)
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    expect(main).not_to_have_class(PAN)
    expect(main).not_to_have_class(PANNING)
    expect(hand).to_have_count(0)
    page.mouse.up()
    page.keyboard.up("Space")
    expect(hand).to_have_count(0)


def test_the_hand_takes_the_left_button_only(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    main = page.locator("main.editor")
    x, y = centre(page.locator(".desk"))
    page.mouse.move(x, y)
    page.keyboard.down("Space")
    expect(main).to_have_class(PAN)
    # Upwards: a pan would scroll the page down.
    page.mouse.down(button="right")
    expect(main).not_to_have_class(PANNING)
    page.mouse.move(x - 30, y - 50, steps=5)
    settled(page)
    expect(main).not_to_have_class(PANNING)
    assert scroll(page) == [0, 0]
    page.mouse.up(button="right")
    page.keyboard.up("Space")
    expect(main).not_to_have_class(PAN)
    assert scroll(page) == [0, 0]


def test_a_plain_wheel_scrolls_under_the_hand(editor):
    """I3"""
    page = editor(box("a", "text", TEXT))
    wide, shown = width(page), percent(page)
    page.keyboard.down("Space")
    expect(page.locator(HAND)).to_have_count(1)
    wheel(page, 100, ctrl=False)
    expect_scroll(page, 0, 100)
    wheel(page, 200, ctrl=False)
    expect_scroll(page, 0, 300)
    wheel(page, -300, ctrl=False)
    expect_scroll(page, 0, 0)
    assert width(page) == pytest.approx(wide, abs=1)
    assert percent(page) == shown
    page.keyboard.up("Space")
    expect(page.locator(HAND)).to_have_count(0)
