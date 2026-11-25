"""#1189: the handle that turns keeps off the block above, "von" shows its whole choice, lengths show rounded."""

from playwright.sync_api import expect
from ui import TEXT, at, box, centre, doc, pick, user

HANDLE = ".moveable-rotation-control"
PLACE = ".panel .geo"


def place(page):
    """The fields of place and size."""
    return page.locator(PLACE)


def test_the_handle_that_turns_stands_below_where_a_block_lies_above(editor):
    page = editor(box("a", "text", TEXT, y=20, h=12), box("b", "text", TEXT, y=38, h=12))
    pick(page, "b")
    handle, own, above = (
        page.locator(HANDLE).bounding_box(),
        at(page, "b").bounding_box(),
        at(page, "a").bounding_box(),
    )
    assert handle["y"] >= own["y"] + own["height"]
    # A click on the block above picks it: no handle takes the press.
    assert not (
        handle["y"] < above["y"] + above["height"] and handle["y"] + handle["height"] > above["y"]
    )
    page.mouse.click(*centre(at(page, "a")))
    expect(at(page, "a")).to_have_class("block sel")
    expect(at(page, "b")).not_to_have_class("block sel")


def test_the_handle_stays_on_top_with_room_above_and_between_two_blocks(editor):
    page = editor(
        box("a", "text", TEXT, y=20, h=12),
        box("b", "text", TEXT, y=38, h=12),
        box("c", "text", TEXT, y=56, h=12),
        box("d", "text", TEXT, y=150, h=12),
    )
    # Room above: the handle is where it was.
    pick(page, "d")
    assert page.locator(HANDLE).bounding_box()["y"] < at(page, "d").bounding_box()["y"]
    # A block above and one below: no side is free, and it keeps its place on top.
    pick(page, "b")
    assert page.locator(HANDLE).bounding_box()["y"] < at(page, "b").bounding_box()["y"]


def test_the_handle_below_still_turns_the_block(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT, y=20, h=12), box("b", "text", TEXT, y=38, h=12), client=client
    )
    pick(page, "b")
    x, y = centre(page.locator(HANDLE))
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 60, y - 10, steps=8)
    page.mouse.up()
    turned = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "b")
    assert turned.get("angle")


def test_von_shows_its_whole_choice(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    choice = place(page).get_by_label("von", exact=True)
    expect(choice).to_have_value("corner")
    # The words fit the field: nothing of "Ecke oben links" is cut.
    words = choice.evaluate(
        """el => {
            const probe = document.createElement('span');
            probe.textContent = el.selectedOptions[0].textContent;
            probe.style.cssText = `font: ${getComputedStyle(el).font}; position: absolute; visibility: hidden`;
            document.body.append(probe);
            const wide = probe.getBoundingClientRect().width;
            probe.remove();
            return wide;
        }"""
    )
    assert choice.bounding_box()["width"] >= words + 40


def test_a_length_a_drag_left_shows_as_whole_mm_and_the_sheet_keeps_it_exact(editor):
    client = user()
    page = editor(box("a", "text", TEXT, x=20.04, y=30, w=59.91, h=20.5), client=client)
    pick(page, "a")
    fields = place(page)
    expect(fields.get_by_label("Breite", exact=True)).to_have_value("60")
    expect(fields.get_by_label("X", exact=True)).to_have_value("20")
    # A tenth is what a teacher sets: it stays.
    expect(fields.get_by_label("Höhe", exact=True)).to_have_value("20,5")
    # Looking at the field changes nothing on the sheet.
    width = fields.get_by_label("Breite", exact=True)
    width.click()
    page.keyboard.press("Tab")
    held = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "a")
    assert (held["x"], held["w"]) == (20.04, 59.91)

    # Enter on the number shown changes nothing either.
    width.click()
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    assert doc(page, client)["pages"][0]["blocks"][0]["w"] == 59.91

    # An arrow steps from the number shown, and a typed number is taken as typed.
    width.click()
    page.keyboard.press("ArrowUp")
    expect(width).to_have_value("61")
    width.fill("72,25")
    page.keyboard.press("Enter")
    expect(width).to_have_value("72")
    held = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "a")
    assert held["w"] == 72.25
