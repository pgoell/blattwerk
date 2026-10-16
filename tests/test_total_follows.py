"""The total score box of a sheet follows its task boxes (issue #402).

The Klassenarbeit shape: each page has a total of 60 and two tasks of 10. A task moved to 15 moves
the total to 65 on every page, in the same undo step.
"""

import re

from playwright.sync_api import expect
from test_feed_print import pdf_text, sheet_id
from ui import TEXT, at, box, doc, pick, reload, user

PANEL_SCORE = '.panel input[aria-label="Punkte"]'
PLUS = "Ein Punkt mehr"


def page_of(n, marked=True):
    """A page with its total (60) and two tasks (10 each), numbered n. The total is marked."""
    total = {"max": 60, "total": True} if marked else {"max": 60}
    return [
        box(f"t{n}", "points", total),
        box(f"a{n}", "points", {"max": 10}, z=2),
        box(f"b{n}", "points", {"max": 10}, z=3),
    ]


def klassenarbeit(editor, client=None, marked=True):
    """Three pages of the Klassenarbeit shape."""
    return editor(
        *page_of(1, marked),
        pages=[{"blocks": page_of(2, marked)}, {"blocks": page_of(3, marked)}],
        client=client,
    )


def test_an_ordinary_sheet_that_looks_like_a_klassenarbeit_keeps_its_total(editor, server):
    client = user()
    page = klassenarbeit(editor, client, marked=False)
    at(page, "a1").dblclick()
    page.keyboard.type("15")
    page.keyboard.press("Enter")
    expect(at(page, "a1").locator(".points")).to_have_text("/ 15 Punkte")
    assert maxes(doc(page, client)) == [[60, 15, 10], [60, 10, 10], [60, 10, 10]]
    assert "/60Punkte" in re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))


def test_a_klassenarbeit_from_the_vorlage_follows(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    reload(page, page.url)
    page.get_by_role("tab", name="Vorlagen").click()
    page.get_by_role("button", name="Klassenarbeit", exact=True).click()
    expect(page.get_by_text("/ 60 Punkte").first).to_be_visible()
    blocks = doc(page, client)["pages"]
    total_ids = [
        b["id"]
        for p in blocks
        for b in p["blocks"]
        if b["type"] == "points" and b["props"]["max"] == 60
    ]
    task = next(b for b in blocks[0]["blocks"] if b["type"] == "points" and b["props"]["max"] == 10)
    at(page, task["id"]).dblclick()
    page.keyboard.type("15")
    page.keyboard.press("Enter")
    expect(at(page, total_ids[0]).locator(".points")).to_have_text("/ 65 Punkte")
    assert [
        [b["props"]["max"] for b in p["blocks"] if b["type"] == "points"]
        for p in doc(page, client)["pages"]
    ] == [[65, 15, 10], [65, 10, 10], [65, 10, 10]]


def maxes(saved_doc):
    """The max of each score box, page by page, in the order of the blocks."""
    scores = [
        [b["props"]["max"] for b in p["blocks"] if b["type"] == "points"]
        for p in saved_doc["pages"]
    ]
    return scores


def type_into_panel(page, name, number):
    pick(page, name)
    page.locator(PANEL_SCORE).fill("")
    page.locator(PANEL_SCORE).press_sequentially(number)
    page.locator(PANEL_SCORE).press("Enter")


def test_a_task_typed_to_15_moves_every_total_to_65(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "a1", "15")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    assert maxes(doc(page, client)) == [[65, 15, 10], [65, 10, 10], [65, 10, 10]]


def test_undo_takes_the_total_and_the_task_back_in_one_step(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "a1", "15")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    page.get_by_label("Rückgängig", exact=True).first.click()
    expect(at(page, "t1").locator(".points")).to_have_text("/ 60 Punkte")
    expect(at(page, "a1").locator(".points")).to_have_text("/ 10 Punkte")
    assert maxes(doc(page, client)) == [[60, 10, 10], [60, 10, 10], [60, 10, 10]]
    page.get_by_label("Wiederholen", exact=True).first.click()
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    assert maxes(doc(page, client)) == [[65, 15, 10], [65, 10, 10], [65, 10, 10]]


def test_two_tasks_picked_and_plus_once_give_a_total_of_62(editor):
    client = user()
    page = klassenarbeit(editor, client)
    pick(page, "a1", "b1")
    page.get_by_label(PLUS).click()
    expect(at(page, "t1").locator(".points")).to_have_text("/ 62 Punkte")
    assert maxes(doc(page, client)) == [[62, 11, 11], [62, 10, 10], [62, 10, 10]]


def test_the_total_typed_to_70_moves_every_total(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect_totals(page, "/ 70 Punkte")
    assert maxes(doc(page, client)) == [[70, 10, 10], [70, 10, 10], [70, 10, 10]]


def test_a_task_typed_back_to_10_gives_60_again(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "a1", "15")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    type_into_panel(page, "a1", "10")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 60 Punkte")
    assert maxes(doc(page, client)) == [[60, 10, 10], [60, 10, 10], [60, 10, 10]]


def test_the_minus_button_takes_a_task_down_to_1_and_the_total_follows(editor):
    client = user()
    page = klassenarbeit(editor, client)
    pick(page, "b1")
    for _ in range(9):
        page.get_by_label("Ein Punkt weniger").click()
    expect(at(page, "t1").locator(".points")).to_have_text("/ 51 Punkte")
    assert maxes(doc(page, client)) == [[51, 10, 1], [51, 10, 10], [51, 10, 10]]


def test_a_saved_klassenarbeit_keeps_its_maxes_on_an_unrelated_edit(editor, server):
    client = user()
    page = klassenarbeit(editor, client)
    doc(page, client)
    before = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    assert "/60Punkte" in before
    pick(page, "b1")
    page.keyboard.press("ArrowDown")
    assert maxes(doc(page, client)) == [[60, 10, 10], [60, 10, 10], [60, 10, 10]]
    after = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    assert after == before
    assert "/60Punkte" in after


def test_a_task_typed_in_its_own_box_moves_every_total_to_65(editor):
    client = user()
    page = klassenarbeit(editor, client)
    at(page, "a1").dblclick()
    page.keyboard.type("15")
    page.keyboard.press("Enter")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    expect(at(page, "t2").locator(".points")).to_have_text("/ 65 Punkte")
    expect(at(page, "t3").locator(".points")).to_have_text("/ 65 Punkte")
    assert maxes(doc(page, client)) == [[65, 15, 10], [65, 10, 10], [65, 10, 10]]


def test_the_pdf_says_65_once_a_task_is_15(editor, server):
    client = user()
    page = klassenarbeit(editor, client)
    before = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    assert "/60Punkte" in before
    type_into_panel(page, "a1", "15")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 65 Punkte")
    doc(page, client)
    after = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    assert "/65Punkte" in after
    assert "/60Punkte" not in after


def fresh(page, client, before):
    """The one block that is not in `before`, once the editor has drawn it."""
    drawn = "document.querySelectorAll('.sheet .block[data-id]').length"
    page.wait_for_function(f"{drawn} === {len(before) + 1}")
    blocks = [b for p in doc(page, client)["pages"] for b in p["blocks"]]
    ids = [b["id"] for b in blocks if b["id"] not in before]
    assert len(ids) == 1, ids
    return ids[0]


def ids_of(page, client):
    return {b["id"] for p in doc(page, client)["pages"] for b in p["blocks"]}


def add_points_on_page_2(page, client):
    """A Punkte box of 10 from the left panel, on an empty part of page 2. Gives its id."""
    before = ids_of(page, client)
    page.locator(".sheet").nth(1).click(position={"x": 5, "y": 5})
    page.locator(".dock, .insert").get_by_label("Punkte", exact=True).click()
    return fresh(page, client, before)


def expect_totals(page, text):
    for name in ["t1", "t2", "t3"]:
        expect(at(page, name).locator(".points")).to_have_text(text)


def test_a_new_punkte_box_on_page_2_counts_in_every_total(editor):
    client = user()
    page = klassenarbeit(editor, client)
    new = add_points_on_page_2(page, client)
    expect_totals(page, "/ 70 Punkte")
    type_into_panel(page, new, "5")
    expect_totals(page, "/ 65 Punkte")
    assert sorted(maxes(doc(page, client))[1]) == [5, 10, 10, 65]
    assert maxes(doc(page, client))[0] == [65, 10, 10]


def test_a_new_punkte_box_pdf_prints_the_new_total(editor, server):
    client = user()
    page = klassenarbeit(editor, client)
    new = add_points_on_page_2(page, client)
    type_into_panel(page, new, "5")
    expect_totals(page, "/ 65 Punkte")
    doc(page, client)
    after = re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))
    assert "/65Punkte" in after
    assert "/60Punkte" not in after


def test_a_copy_of_a_task_counts_and_plus_one_moves_the_total_by_one(editor):
    client = user()
    page = klassenarbeit(editor, client)
    before = ids_of(page, client)
    pick(page, "a1")
    page.keyboard.press("Control+d")
    fresh(page, client, before)
    expect_totals(page, "/ 70 Punkte")
    page.get_by_label(PLUS).click()
    expect_totals(page, "/ 71 Punkte")


def test_a_deleted_task_takes_10_off_and_undo_gives_it_back(editor):
    client = user()
    page = klassenarbeit(editor, client)
    pick(page, "a1")
    page.keyboard.press("Delete")
    expect_totals(page, "/ 50 Punkte")
    assert maxes(doc(page, client)) == [[50, 10], [50, 10, 10], [50, 10, 10]]
    page.get_by_label("Rückgängig", exact=True).first.click()
    expect_totals(page, "/ 60 Punkte")


def test_a_task_cut_and_pasted_to_page_2_keeps_the_sum_at_60(editor):
    client = user()
    page = klassenarbeit(editor, client)
    before = ids_of(page, client)
    pick(page, "a1")
    page.keyboard.press("Control+x")
    expect_totals(page, "/ 50 Punkte")
    page.locator(".sheet").nth(1).click(position={"x": 5, "y": 5})
    page.keyboard.press("Control+v")
    fresh(page, client, before - {"a1"})
    expect_totals(page, "/ 60 Punkte")
    tasks = [
        b["props"]["max"]
        for p in doc(page, client)["pages"]
        for b in p["blocks"]
        if b["type"] == "points" and not b["props"].get("total")
    ]
    assert sum(tasks) == 60


def test_two_tasks_deleted_at_once_take_20_off(editor):
    client = user()
    page = klassenarbeit(editor, client)
    pick(page, "a1", "b1")
    page.keyboard.press("Delete")
    expect_totals(page, "/ 40 Punkte")
    page.get_by_label("Rückgängig", exact=True).first.click()
    expect_totals(page, "/ 60 Punkte")
