"""The numbers of her own that a teacher types into a maths block, on the sheet: a double click on a box opens
the field "Eigene Zahl" there."""

from playwright.sync_api import expect

# The screen centre of a box: its `data-own-box` (in the block's units) where it has one, else its first shape.
OWN_POINT = """(el) => {
    const shape = el.querySelector("rect, circle, polygon, path, ellipse");
    const own = el.dataset.ownBox;
    const [x, y, w, h] = own ? own.split(",").map(Number) : (({ x, y, width, height }) => [x, y, width, height])(shape.getBBox());
    const p = new DOMPoint(x + w / 2, y + h / 2).matrixTransform((own ? el : shape).getScreenCTM());
    return [p.x, p.y];
}"""


def own_field(page):
    """The field a double click opens on a box of a maths block, for a number of the teacher's own."""
    return page.get_by_label("Eigene Zahl", exact=True)


def open_own(page, name, cell):
    """Opens the box `cell` ("1,5": copy, then box, as the view's `data-own` says) of the maths block on the
    sheet, by a double click on the picked block. Gives the field."""
    from ui import at, pick

    if at(page, name).get_attribute("class").split().count("sel") == 0:
        pick(page, name)
    x, y = at(page, name).locator(f'[data-own="{cell}"]').first.evaluate(OWN_POINT)
    page.mouse.dblclick(x, y)
    expect(own_field(page)).to_be_focused()
    return own_field(page)


def type_own(page, name, cell, text):
    """Types a number of the teacher's own into a box of a maths block, on the sheet, and closes the field with
    Enter. An empty text takes the box's own number out."""
    field = open_own(page, name, cell)
    field.fill(text)
    field.press("Enter")
    expect(own_field(page)).to_have_count(0)
