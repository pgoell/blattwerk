"""A row height set by hand holds when text, a row, or the table's turn changes.

The helpers live in test_table_holds.py.
"""

from test_cells import GRID, cell, open_cell, print_page, props
from test_sizes import EDGE, H, W, block, mm_height, num, typed
from test_table_holds import (
    LONG,
)
from ui import box, centre, drag, pick, thumb, unpick, user


def test_a_set_row_height_holds_when_a_row_comes_or_goes(editor):
    """Issue 520: a row set to 20 mm stays 20 mm when a row comes below it or goes, and the block's
    height changes by the row that came or went."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 0)
    typed(page, "Zeilenhöhe", "20")
    before = block(page, client)["h"]
    open_cell(page, "t", 3)
    page.get_by_role("button", name="Zeile darunter", exact=True).click()
    came = block(page, client)["h"]
    assert came > before
    open_cell(page, "t", 0)
    expect_height(page, 20)
    open_cell(page, "t", 6)
    page.get_by_role("button", name="Zeile löschen", exact=True).click()
    assert block(page, client)["h"] < came
    open_cell(page, "t", 0)
    expect_height(page, 20)
    assert abs(mm_height(page, cell(page, "t", 0)) - 20) <= 0.1


def expect_height(page, mm):
    assert abs(float(num(page, "Zeilenhöhe").input_value().replace(",", ".")) - mm) <= 0.05


def test_a_set_row_height_comes_back_when_the_long_text_is_deleted(editor):
    """Issue 520: a row set to 20 mm, grown by a long text, is 20 mm again when the text goes. The
    other rows and the block keep their heights."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    typed(page, "Zeilenhöhe", "20")
    before = block(page, client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 6)]
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > before["h"] + 10
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    back = block(page, client)
    assert abs(back["h"] - before["h"]) <= 0.05
    assert abs(back["props"]["rows"][1] - 20) <= 0.05
    assert abs(mm_height(page, cell(page, "t", 3)) - 20) <= 0.1
    for n, was in zip((0, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_table_goes_back_when_its_long_text_is_deleted(editor):
    """Issue 520: a table of 30 mm, grown by a long text, goes back to 30 mm, rows as they were."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > H + 20
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - H) <= 0.05
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - H) <= 0.05
    for n, was in zip((0, 3, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_table_made_taller_by_hand_goes_back_to_that_height(editor):
    """Issue 520: a table of 60 mm with no rows set, grown by a long text, goes back to 60 mm."""
    client = user()
    page = editor(box("t", "table", GRID, h=60), client=client)
    rows_before = [mm_height(page, cell(page, "t", n)) for n in (0, 3, 6)]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG + " " + LONG)
    assert block(page, client)["h"] > 60
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 60) <= 0.05
    # The rows too: the row typed into did not keep the room it took from the others.
    for n, was in zip((0, 3, 6), rows_before, strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - was) <= 0.05


def test_a_typed_height_holds_on_a_table_with_rows_and_solution_words(editor):
    """From the review: the rows of a table with a box of solution words do not sum to its height,
    so such a table does not shrink by itself and a typed `Höhe` holds."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    open_cell(page, "t", 3)
    typed(page, "Zeilenhöhe", "12")
    page.keyboard.press("Escape")
    pick(page, "t")
    typed(page, "Höhe", "90")
    assert block(page, client)["h"] == 90


def test_a_height_set_on_a_table_grown_by_its_text_holds(editor):
    """A table that a text made tall and the teacher then made taller keeps that height: on its
    own, and when one more letter is typed. Only a table with no spare room comes down."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert 60 < block(page, client)["h"] < 85
    page.keyboard.press("Escape")
    pick(page, "t")
    typed(page, "Höhe", "90")
    assert block(page, client)["h"] == 90
    open_cell(page, "t", 4)
    page.keyboard.press("End")
    page.keyboard.type("x")
    assert props(page, client)["cells"][1][1].endswith("x")
    assert block(page, client)["h"] == 90


def test_a_shrunk_table_agrees_on_screen_thumb_and_pdf(editor, browser, server):
    """Issue 520: a table that shrank back to its height draws alike on screen, thumb and PDF."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client, theme="")
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    on_screen = cell(page, "t", 0)
    height = mm_height(page, on_screen)
    assert abs(block(page, client)["h"] - H) <= 0.05

    shown = thumb(page, 0).locator(".table")
    small = thumb(page, 0).locator('.table > div[data-cell="0"]')
    th = shown.bounding_box()["height"]
    assert abs(small.bounding_box()["height"] / th - height / (H - EDGE)) <= 0.02

    context, printed = print_page(browser, server, client, page.url.rsplit("/", 1)[1])
    drawn = printed.locator('.table > div[data-cell="0"]')
    # A millimetre is 96 / 25.4 px in the PDF.
    assert abs(drawn.bounding_box()["height"] - height * 96 / 25.4) <= 0.3
    context.close()


def typed_height(page, mm):
    pick(page, "t")
    typed(page, "Höhe", str(mm))


def test_a_typed_height_holds_when_more_text_is_typed_and_deleted(editor):
    """Issue 540: a height typed in the panel holds when more text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    typed_height(page, 90)
    assert block(page, client)["h"] == 90
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - 90) <= 0.1


def test_a_dragged_height_holds_when_text_is_typed_and_deleted(editor):
    """Issue 540: a height dragged on the bottom handle holds when text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    pick(page, "t")
    start = centre(page.locator(".moveable-control.moveable-s"))
    drag(page, start, (start[0], start[1] + 60))
    dragged = block(page, client)["h"]
    assert dragged > H + 5
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - dragged) <= 0.1


def test_a_typed_height_holds_when_the_text_goes_into_another_row(editor):
    """Issue 540: a height typed in the panel holds when the long text goes into another row."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    typed_height(page, 90)
    open_cell(page, "t", 6)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1


def test_a_table_with_solution_words_goes_back_when_its_long_text_is_deleted(editor):
    """Issue 539: a table with a box of solution words goes back to its height after long text."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    before = block(page, client)["h"]
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > before + 10
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - before) <= 0.05


def test_a_typed_height_holds_on_a_table_with_solution_words_after_typing_and_deleting(editor):
    """Issue 539: a height typed on a table with a box of solution words holds after long text."""
    client = user()
    gaps = [[True, False, False], [False] * 3, [False] * 3]
    page = editor(
        box("t", "table", {**GRID, "gaps": gaps, "bank": 3}, w=W, h=50 + EDGE), client=client
    )
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    # The long text alone needs some 96 mm: 120 is a height above that.
    typed_height(page, 120)
    assert block(page, client)["h"] == 120
    open_cell(page, "t", 4)
    page.keyboard.type(LONG)
    assert block(page, client)["h"] > 130
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 120) <= 0.1
    pick(page, "t")
    assert abs(float(num(page, "Höhe").input_value().replace(",", ".")) - 120) <= 0.1


def test_undo_brings_back_the_height_and_rows_before_a_typed_height(editor):
    """Issue 540: one Ctrl+Z after a typed height takes back the height and the rows before it."""
    client = user()
    page = editor(box("t", "table", GRID, h=H), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    start = block(page, client)
    typed_height(page, 90)
    assert block(page, client)["h"] == 90
    unpick(page)
    page.keyboard.press("Control+z")
    after = block(page, client)
    assert abs(after["h"] - start["h"]) <= 0.05
    assert after["props"].get("rows") == start["props"].get("rows")


def saved_rows(page, client, name="t"):
    return block(page, client, name)["props"]["rows"]


def test_a_row_held_up_by_its_text_keeps_the_screens_proportion_when_the_table_grows(editor):
    """Issue 540, PowerPoint: a row its text holds up keeps the screen's proportion as it grows.

    Guards #514: a fix that scales the saved rows must not undo this.
    """
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [10, 10, 10]}, h=30 + EDGE), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(" ".join(f"wort{n}" for n in range(8)))
    page.keyboard.press("Escape")
    ratio = mm_height(page, cell(page, "t", 3)) / mm_height(page, cell(page, "t", 6))
    typed_height(page, 90)
    rows = saved_rows(page, client)
    assert abs(rows[1] / rows[2] - ratio) <= 0.05 * ratio
    assert abs(rows[0] - rows[2]) <= 0.05


def test_a_table_pressed_below_its_texts_keeps_its_rows_proportions(editor):
    """Issue 514: rows of 20, 10 and 10 mm, pressed with Höhe 5, then set to 40,26, are 20, 10 and 10 again.

    At 5 the table stays as high as its texts need. The rows on the screen are equal then, and growing
    it must scale the saved rows, which still hold 2 : 1 : 1.
    """
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [20, 10, 10]}, h=40 + EDGE), client=client)
    typed_height(page, 5)
    pressed = block(page, client)
    # The texts need more than 5 mm, and the saved rows still hold 2 : 1 : 1.
    assert pressed["h"] > 20
    assert abs(pressed["props"]["rows"][0] / pressed["props"]["rows"][1] - 2) <= 0.05
    typed_height(page, "40,26")
    rows = saved_rows(page, client)
    for got, want in zip(rows, (20, 10, 10), strict=True):
        assert abs(got - want) <= 0.05
    for n, want in zip((0, 3, 6), (20, 10, 10), strict=True):
        assert abs(mm_height(page, cell(page, "t", n)) - want) <= 0.15


def test_uneven_rows_pressed_below_their_texts_come_back(editor):
    """Issue 514, from the review of #545: rows 10, 40, 10 at 60,26, Höhe 15, then 60,26, are 10, 40, 10.

    The middle row still covers its text at 15, so the screen is not three equal rows. Scaling that
    screen gave about 18,7, 22,6, 18,7.
    """
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [10, 40, 10]}, h=60 + EDGE), client=client)
    typed_height(page, 15)
    assert block(page, client)["h"] > 20
    typed_height(page, "60,26")
    rows = saved_rows(page, client)
    for got, want in zip(rows, (10, 40, 10), strict=True):
        assert abs(got - want) <= 0.05


def test_rows_pressed_below_their_texts_keep_their_proportion_grown_in_steps(editor):
    """Issue 514, the steps folded in from #730: Höhe 5, then 30, then 40,26 brings 20, 10, 10 back.

    At 30 the short rows are still under what their texts need. The next height must not scale the
    equal rows the screen shows.
    """
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [20, 10, 10]}, h=40 + EDGE), client=client)
    typed_height(page, 5)
    typed_height(page, 30)
    typed_height(page, "40,26")
    rows = saved_rows(page, client)
    for got, want in zip(rows, (20, 10, 10), strict=True):
        assert abs(got - want) <= 0.05


def test_a_handle_grows_a_pressed_table_back_in_its_rows_proportions(editor):
    """Issue 514, the drag folded in from #730: after Höhe 5, pulling the bottom handle keeps 2 : 1 : 1."""
    client = user()
    page = editor(box("t", "table", {**GRID, "rows": [20, 10, 10]}, h=40 + EDGE), client=client)
    typed_height(page, 5)
    pick(page, "t")
    start = centre(page.locator(".moveable-control.moveable-s"))
    drag(page, start, (start[0], start[1] + 80))
    rows = saved_rows(page, client)
    assert block(page, client)["h"] > 35
    assert abs(rows[0] / rows[1] - 2) <= 0.08
    assert abs(rows[1] - rows[2]) <= 0.15


def test_a_turned_table_holds_its_typed_height(editor):
    """Issue 540: a turned table keeps a typed height when long text is typed and deleted."""
    client = user()
    page = editor(box("t", "table", GRID, h=H, angle=90), client=client)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Escape")
    typed_height(page, 90)
    open_cell(page, "t", 3)
    page.keyboard.type(LONG)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    assert abs(block(page, client)["h"] - 90) <= 0.1
