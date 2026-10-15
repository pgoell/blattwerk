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


def test_the_total_typed_to_70_moves_nothing_else(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect(at(page, "t1").locator(".points")).to_have_text("/ 70 Punkte")
    assert maxes(doc(page, client)) == [[70, 10, 10], [60, 10, 10], [60, 10, 10]]


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
