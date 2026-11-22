"""Background colour and padding for single cells of a table (#862)."""

from playwright.sync_api import expect
from test_cells import GRID, cell, open_cell, print_page, props
from ui import box, pick, unpick, user

YELLOW = "rgb(255, 230, 128)"
CLEAR = "rgba(0, 0, 0, 0)"


def panel(page):
    return page.locator(".panel")


def padding(page, n, name="t"):
    """The cell's padding in mm: top, right, bottom, left."""
    return cell(page, name, n).evaluate(
        """el => {
            const s = getComputedStyle(el);
            const k = 96 / 25.4;
            return [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft].map((v) => Math.round(parseFloat(v) / k * 10) / 10);
        }"""
    )


def test_the_background_goes_on_the_picked_cells_only_and_one_undo_takes_it_back(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 0)
    cell(page, "t", 4).click(modifiers=["Shift"])
    panel(page).get_by_label("Hintergrund", exact=True).fill("#ffe680")
    for n in range(9):
        expect(cell(page, "t", n)).to_have_css(
            "background-color", YELLOW if n in (0, 1, 3, 4) else CLEAR
        )
    assert props(page, client)["looks"] == [
        [{"fill": "#ffe680"}, {"fill": "#ffe680"}, None],
        [{"fill": "#ffe680"}, {"fill": "#ffe680"}, None],
        [None, None, None],
    ]
    page.get_by_label("Rückgängig", exact=True).click()
    expect(cell(page, "t", 0)).to_have_css("background-color", CLEAR)
    assert "looks" not in props(page, client)


def test_kein_hintergrund_clears_the_picked_cells_and_keeps_their_text_format(editor):
    client = user()
    looks = [
        [{"fill": "#ffe680", "bold": True}, {"fill": "#ffe680"}, None],
        [None, None, None],
        [None, None, None],
    ]
    page = editor(box("t", "table", {**GRID, "looks": looks}), client=client)
    expect(cell(page, "t", 1)).to_have_css("background-color", YELLOW)
    open_cell(page, "t", 0)
    page.get_by_role("button", name="Ganze Zeile", exact=True).click()
    page.get_by_role("button", name="Kein Hintergrund", exact=True).click()
    expect(cell(page, "t", 0)).to_have_css("background-color", CLEAR)
    expect(cell(page, "t", 1)).to_have_css("background-color", CLEAR)
    assert props(page, client)["looks"] == [
        [{"bold": True}, None, None],
        [None, None, None],
        [None, None, None],
    ]


def test_a_padding_goes_on_the_open_cell_and_its_row_grows(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, "t", 4)
    before = cell(page, "t", 4).bounding_box()["height"]
    usual = cell(page, "t", 4).evaluate("el => getComputedStyle(el).paddingTop")
    field = panel(page).get_by_label("Abstand oben", exact=True)
    field.fill("6")
    field.press("Enter")
    expect(cell(page, "t", 4)).not_to_have_css("padding-top", usual)
    assert padding(page, 4)[0] == 6
    pad = props(page, client)["looks"][1][1]["pad"]
    assert pad[0] == 6
    # The other sides keep the room they had: .15em below, .3em at the sides, of 14 pt.
    assert pad[1:] == [1.48, 0.74, 1.48]
    assert padding(page, 3) != padding(page, 4)
    assert cell(page, "t", 4).bounding_box()["height"] > before + 10
    # Its neighbours in the row are as high as it is.
    assert (
        abs(
            cell(page, "t", 3).bounding_box()["height"]
            - cell(page, "t", 4).bounding_box()["height"]
        )
        < 1
    )


def test_with_no_cell_open_the_background_and_padding_go_on_the_whole_table(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    unpick(page)
    pick(page, "t")
    panel(page).get_by_label("Hintergrund", exact=True).fill("#ffe680")
    field = panel(page).get_by_label("Abstand links", exact=True)
    field.fill("4")
    field.press("Enter")
    for n in range(9):
        expect(cell(page, "t", n)).to_have_css("background-color", YELLOW)
    looks = props(page, client)["looks"]
    assert all(look["fill"] == "#ffe680" and look["pad"][3] == 4 for row in looks for look in row)


def test_the_print_draws_the_background_and_the_padding(editor, browser, server):
    client = user()
    looks = [
        [{"fill": "#ffe680"}, None, None],
        [None, {"pad": [5, 0, 0, 8]}, None],
        [None, None, None],
    ]
    page = editor(box("t", "table", {**GRID, "align": "left", "looks": looks}), client=client)
    expect(cell(page, "t", 0)).to_have_css("background-color", YELLOW)
    sheet_id = page.url.rsplit("/", 1)[1]
    context, printed = print_page(browser, server, client, sheet_id)
    try:
        expect(printed.locator('.table > div[data-cell="0"]')).to_have_css(
            "background-color", YELLOW
        )
        expect(printed.locator('.table > div[data-cell="1"]')).to_have_css(
            "background-color", CLEAR
        )
        padded = printed.locator('.table > div[data-cell="4"]')
        left, top = padded.evaluate(
            "el => [getComputedStyle(el).paddingLeft, getComputedStyle(el).paddingTop].map(parseFloat)"
        )
        assert abs(left / top - 8 / 5) < 0.01
        assert padded.evaluate("el => getComputedStyle(el).paddingRight") == "0px"
    finally:
        context.close()
