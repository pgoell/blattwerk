"""The Selbstkontrolle block in the editor and its panel: the results it lists, the links, the
sources it follows and the words it checks.

The docstrings name what each test proves. The contract of the block is the comment at the top of
frontend/src/selbstkontrolle.ts.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import at, box, doc, maths, pick, user

SK = {
    "form": "mixed",
    "links": [],
    "word": "",
    "title": "Selbstkontrolle",
    "size": 14,
    "turn": "none",
    "seed": 7,
}
HINT = "Die Selbstkontrolle hat ihre Quelle verloren."


def ex(a, op, b, result):
    """A stored exercise, its result written by hand."""
    return {"op": op, "a": a, "b": b, "result": result, "rest": 0}


SUMS = [ex(3, "+", 4, 7), ex(2, "+", 5, 7), ex(6, "+", 6, 12)]
WORDED = [ex(3, "+", 4, 7), ex(4, "+", 5, 9), ex(6, "+", 1, 7)]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def props_of(stored, name):
    """The props of the block of that name on the sheet's first page, as the server holds them."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["id"] == name]
    return block["props"]


def results(stored, name):
    """The results of a maths block as the server holds it, as the texts the list prints."""
    return sorted(str(e["result"]) for e in props_of(stored, name)["exercises"])


def texts(locator):
    return sorted(t.strip() for t in locator.all_text_contents())


def test_mixed_lists_each_result_of_the_linked_block_once_with_a_tick(editor):
    """Sums 3+4, 2+5 and 6+6 list 7, 7 and 12 in a shuffle, each result with its tick."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60),
        client=client,
    )
    items = at(page, "s").locator("ul.mixed li")
    expect(items).to_have_count(3)
    assert texts(items) == ["12", "7", "7"]
    expect(items.locator("span.tick")).to_have_count(3)


def test_ticking_rechnen_in_the_panel_links_it_and_undo_and_redo_unlink_and_link(editor):
    """Ticking Rechnen stores its id in links; Ctrl+Z empties links, Ctrl+Y puts the id back."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
        box("s", "selbstkontrolle", SK, z=2, w=180, h=60),
        client=client,
    )
    pick(page, "s")
    step(page, lambda: field(page, "Rechnen").check())
    assert props_of(doc(page, client), "s")["links"] == ["m"]
    undo(page)
    assert props_of(doc(page, client), "s")["links"] == []
    redo(page)
    assert props_of(doc(page, client), "s")["links"] == ["m"]


def test_neu_wuerfeln_on_the_linked_block_changes_the_list_to_its_new_results(editor):
    """Neu würfeln on the maths block rolls new exercises, and the list shows their results."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60),
        client=client,
    )
    pick(page, "m")
    step(page, lambda: panel(page, "Neu würfeln").click())
    stored = doc(page, client)
    expect(at(page, "s").locator("ul.mixed li")).to_have_count(len(SUMS))
    assert texts(at(page, "s").locator("ul.mixed li")) == results(stored, "m")


def test_a_new_max_on_the_linked_block_changes_the_list_too(editor):
    """Größte Zahl 9 on the maths block: the list shows the results of the new exercises."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60),
        client=client,
    )
    pick(page, "m")
    step(page, lambda: field(page, "Größte Zahl").fill("9"))
    stored = doc(page, client)
    assert texts(at(page, "s").locator("ul.mixed li")) == results(stored, "m")


def test_deleting_the_linked_block_gives_the_hint_and_undo_brings_the_list_back(editor):
    """Deleting the source: the hint says the source is lost and no result is listed; undo brings
    the three results back."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=SUMS), z=1, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60),
        client=client,
    )
    pick(page, "m")
    page.keyboard.press("Delete")
    expect(at(page, "s").locator("p.hint")).to_have_text(HINT)
    expect(at(page, "s").locator("li")).to_have_count(0)
    undo(page)
    expect(at(page, "s").locator("ul.mixed li")).to_have_count(3)


@pytest.mark.parametrize(
    "word, hint",
    [
        ("ABC", "Aufgabe 1 und 3 haben dasselbe Ergebnis 7, das Wort braucht dort A und C."),
        ("AB", "Das Wort hat 2 Buchstaben, die Aufgaben sind 3."),
    ],
    ids=["same-result-other-letter", "wrong-length"],
)
def test_a_word_that_does_not_fit_the_tasks_gives_its_fault(editor, word, hint):
    """ABC asks two letters for the results 7; AB has two letters for three tasks."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=WORDED), z=1, w=180, h=20),
        box(
            "s",
            "selbstkontrolle",
            {**SK, "form": "word", "word": word, "links": ["m"]},
            z=2,
            w=180,
            h=60,
        ),
        client=client,
    )
    expect(at(page, "s").locator("p.hint")).to_have_text(hint)


def test_word_aba_fills_the_table_and_puts_a_letter_box_on_each_task(editor):
    """ABA over results 7, 9, 7: the table holds A and B under the results, and each of the three
    sums has a letter box."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=WORDED), z=1, w=180, h=20),
        box(
            "s",
            "selbstkontrolle",
            {**SK, "form": "word", "word": "ABA", "links": ["m"]},
            z=2,
            w=180,
            h=60,
        ),
        client=client,
    )
    expect(at(page, "s").locator("table.word tr.letters td")).to_have_count(2)
    assert texts(at(page, "s").locator("table.word tr.letters td")) == ["A", "B"]
    expect(at(page, "m").locator(".letter")).to_have_count(3)


def test_sum_form_prints_the_sum_of_each_linked_block_with_its_number(editor):
    """Two maths blocks: Rechnen 1 sums 7 and 7 to 14; Rechnen 2 sums 2 to 2."""
    client = user()
    page = editor(
        box("m1", "maths", maths(client, exercises=SUMS[:2]), z=1, w=180, h=20),
        box("m2", "maths", maths(client, exercises=[ex(1, "+", 1, 2)]), z=2, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "form": "sum", "links": ["m1", "m2"]}, z=3, w=180, h=60),
        client=client,
    )
    expect(at(page, "s").locator("ul.sums li")).to_have_count(2)
    assert texts(at(page, "s").locator("ul.sums li")) == ["Rechnen 1: 14", "Rechnen 2: 2"]


def test_a_word_form_with_no_word_asks_for_one(editor):
    """Extra: Form Lösungswort with the word left empty says so in the hint, and lists nothing."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, exercises=WORDED), z=1, w=180, h=20),
        box("s", "selbstkontrolle", {**SK, "form": "word", "links": ["m"]}, z=2, w=180, h=60),
        client=client,
    )
    expect(at(page, "s").locator("p.hint")).to_have_text("Gib ein Lösungswort ein.")
    expect(at(page, "s").locator("table.word")).to_have_count(0)


def test_the_lost_link_in_the_panel_is_a_ticked_box_that_unlinks_it(editor):
    """Extra: a lost link shows as a ticked box "Gelöschter Block"; unticking it stores no link."""
    client = user()
    page = editor(
        box("s", "selbstkontrolle", {**SK, "links": ["gone"]}, z=1, w=180, h=60),
        client=client,
    )
    pick(page, "s")
    step(page, lambda: field(page, "Gelöschter Block").uncheck())
    assert props_of(doc(page, client), "s")["links"] == []
