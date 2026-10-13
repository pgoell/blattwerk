"""The counters in the panels say the singular for one: rows, count, columns."""

from playwright.sync_api import expect
from ui import RULING, TABLE, box, maths, pick, user


def counter(page, button):
    """The count between the two buttons of a panel's row, found by the minus button's label."""
    return (
        page.locator(".panel .seg")
        .filter(has=page.get_by_label(button, exact=True))
        .locator("output")
    )


def test_a_lineatur_with_one_row_says_eine_zeile(editor):
    page = editor(box("a", "ruling", {**RULING, "kind": "l1"}, h=20))
    pick(page, "a")
    expect(counter(page, "Eine Zeile weniger")).to_have_text("1 Zeile")


def test_a_lineatur_with_two_rows_says_zwei_zeilen(editor):
    page = editor(box("a", "ruling", {**RULING, "kind": "l1"}, h=40))
    pick(page, "a")
    expect(counter(page, "Eine Zeile weniger")).to_have_text("2 Zeilen")


def test_a_lineatur_from_two_rows_says_eine_zeile_after_one_less(editor):
    page = editor(box("a", "ruling", {**RULING, "kind": "l1"}, h=40))
    pick(page, "a")
    page.get_by_label("Eine Zeile weniger", exact=True).click()
    expect(counter(page, "Eine Zeile weniger")).to_have_text("1 Zeile")


def test_a_table_from_two_rows_says_eine_zeile_after_one_less(editor):
    page = editor(box("t", "table", TABLE))
    pick(page, "t")
    page.get_by_label("Eine Zeile weniger", exact=True).click()
    expect(counter(page, "Eine Zeile weniger")).to_have_text("1 Zeile")


def test_a_maths_block_with_one_of_each_says_the_singular(editor):
    client = user()
    page = editor(box("m", "maths", maths(client, count=1, columns=1)), client=client)
    pick(page, "m")
    expect(counter(page, "Eine Aufgabe weniger")).to_have_text("1 Aufgabe")
    expect(counter(page, "Eine Spalte weniger")).to_have_text("1 Spalte")


def test_a_maths_family_with_one_family_says_eine_familie(editor):
    client = user()
    props = maths(client, count=1, family="reverse", numbering="1")
    page = editor(box("m", "maths", props), client=client)
    pick(page, "m")
    expect(counter(page, "Eine Aufgabe weniger")).to_have_text("1 Familie")
