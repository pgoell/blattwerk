"""The Stellenwerttafel on paper: the pupils' sheet and the answer key, and the Varianten (#1077).

The numbers are read from the printed page, never pinned: the generator may change.
The docstrings name the checklist line that each test proves.
"""

from test_feed_print import printed, sheet_id
from test_stellenwerttafel import SWT, sw
from test_suchsel_print import key_print
from ui import pick, user

from blattwerk import variants


def dots(paper, task):
    """The centre and value of each dot of a task on the printed page, in order."""
    return paper.locator(f".stellenwerttafel g.task[data-task='{task}'] circle.dot").evaluate_all(
        "els => els.map(e => [e.getAttribute('cx'), e.getAttribute('cy'), +e.dataset.v])"
    )


def store(page, client, **more):
    """Sets keys of the whole sheet (Lösungsfarbe) as the server holds it."""
    mine = sheet_id(page)
    got = client.get(f"/api/sheets/{mine}").json()
    body = {"doc": {**got["doc"], **more}, "version": got["version"]}
    assert client.patch(f"/api/sheets/{mine}", json=body).status_code == 200
    return mine


def test_the_print_draws_the_same_dots_as_the_screen(editor, browser, server):
    """Print (#1077): the pupils' sheet draws the same dots, in the same places, as the editor's drawing."""
    page = editor(sw({"count": 2}))
    pick(page, "k")
    on_screen = [
        page.locator(f".stellenwerttafel g.task[data-task='{t}'] circle.dot").evaluate_all(
            "els => els.map(e => [e.getAttribute('cx'), e.getAttribute('cy'), +e.dataset.v])"
        )
        for t in range(2)
    ]
    sheet = printed(browser, server, sheet_id(page))
    assert [dots(sheet, t) for t in range(2)] == on_screen
    sheet.context.close()


def test_the_key_of_a_lay_task_takes_the_losungsfarbe(editor, browser, server):
    """Print (#1077): the key's dots of a "lay" task are in the Lösungsfarbe, blue here."""
    client = user()
    page = editor(sw({"task": "lay", "count": 1}), client=client)
    mine = store(page, client, keyColor="#0000ff")
    paper = key_print(browser, server, mine)
    dot = paper.locator(".stellenwerttafel circle.dot.answer").first
    dot.wait_for()
    assert dot.evaluate("e => getComputedStyle(e).fill") == "rgb(0, 0, 255)"
    paper.context.close()


def test_varianten_b_draw_other_numbers_and_drop_typed():
    """Varianten (#1077): B to D give a Stellenwerttafel a seed of its own and drop `typed`; the other settings stay."""
    props = {**SWT, "typed": [[0, 345]]}
    doc = {"pages": [{"blocks": [{"id": "s", "type": "stellenwerttafel", "props": props}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {SWT["seed"]}
    for letter in "BCD":
        got = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert got == {**{k: v for k, v in SWT.items() if k != "seed"}, "seed": got["seed"]}
        seeds.add(got["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == props
