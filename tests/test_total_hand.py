"""A total typed by hand is the total of every page (issue #662).

The Klassenarbeit shape: three pages, each with a total of 60 and two tasks of 10. Typing 70 into
the total of page 1 sets the total on every page, in one undo step, on the screen and in the PDF.
"""

import re

from playwright.sync_api import expect
from test_feed_print import pdf_text, sheet_id
from test_total_follows import expect_totals, klassenarbeit, maxes, type_into_panel
from ui import at, doc, reload, unpick, user


def pdf_compact(server, client, page):
    return re.sub(r"\s", "", pdf_text(server, client, sheet_id(page)))


def test_a_total_typed_by_hand_on_page_1_goes_to_every_page(editor, server):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect_totals(page, "/ 70 Punkte")
    assert maxes(doc(page, client)) == [[70, 10, 10], [70, 10, 10], [70, 10, 10]]
    printed = pdf_compact(server, client, page)
    assert printed.count("/70Punkte") == 3
    assert "/60Punkte" not in printed
    assert "/65Punkte" not in printed


def test_one_undo_takes_every_total_back_and_redo_gives_70_again(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect_totals(page, "/ 70 Punkte")
    unpick(page)
    page.keyboard.press("Control+z")
    expect_totals(page, "/ 60 Punkte")
    assert maxes(doc(page, client)) == [[60, 10, 10], [60, 10, 10], [60, 10, 10]]
    unpick(page)
    page.keyboard.press("Control+y")
    expect_totals(page, "/ 70 Punkte")
    assert maxes(doc(page, client)) == [[70, 10, 10], [70, 10, 10], [70, 10, 10]]


def test_a_task_changed_after_the_total_typed_by_hand_sets_every_total_to_the_sum(editor):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect_totals(page, "/ 70 Punkte")
    type_into_panel(page, "a1", "15")
    expect_totals(page, "/ 65 Punkte")
    assert maxes(doc(page, client)) == [[65, 15, 10], [65, 10, 10], [65, 10, 10]]


def test_a_reload_keeps_the_total_typed_by_hand_on_every_page(editor, server):
    client = user()
    page = klassenarbeit(editor, client)
    type_into_panel(page, "t1", "70")
    expect_totals(page, "/ 70 Punkte")
    doc(page, client)
    reload(page, page.url)
    expect(at(page, "t3").locator(".points")).to_have_text("/ 70 Punkte")
    expect_totals(page, "/ 70 Punkte")
    assert maxes(doc(page, client)) == [[70, 10, 10], [70, 10, 10], [70, 10, 10]]
    assert pdf_compact(server, client, page).count("/70Punkte") == 3
