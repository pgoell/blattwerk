"""The Stellenwert-Bild block on paper: the pupils' sheet and the answer key, and the Varianten (#1076).

The numbers are read from the printed page, never pinned: the generator may change.
The docstrings name the checklist line that each test proves.
"""

from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_stellenwertbild import SW, sw
from test_suchsel_print import key_print
from ui import pick, user

from blattwerk import variants

NOTE = "Auch andere Lösungen sind richtig."


def pieces(paper, task):
    """The value (data-v) of each piece of a task on the printed page, in order."""
    return paper.locator(f".stellenwertbild g.task[data-task='{task}'] g.piece").evaluate_all(
        "els => els.map(e => +e.dataset.v)"
    )


def test_the_print_draws_the_same_pieces_as_the_screen(editor, browser, server):
    """Print (#1076): the pupils' sheet draws the same pieces, in the same places, as the editor's drawing."""
    page = editor(sw({"count": 2}))
    pick(page, "k")
    on_screen = [
        page.locator(f".stellenwertbild g.task[data-task='{t}'] g.piece").evaluate_all(
            "els => els.map(e => +e.dataset.v)"
        )
        for t in range(2)
    ]
    sheet = printed(browser, server, sheet_id(page))
    assert [pieces(sheet, t) for t in range(2)] == on_screen
    sheet.context.close()


def test_the_key_has_no_note_about_other_solutions(editor, browser, server):
    """Key (#1076): every task has one answer, so the key never says "Auch andere Lösungen sind richtig."."""
    page = editor(sw({"count": 6, "bundle": True}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.get_by_text(NOTE)).to_have_count(0)
    paper.context.close()


def test_the_key_of_a_draw_task_shows_the_symbols(editor, browser, server):
    """Key (#1076): the key of a "draw" task shows its symbols, the pupils' sheet shows none."""
    page = editor(sw({"task": "draw", "count": 2}))
    pick(page, "k")
    sheet = printed(browser, server, sheet_id(page))
    expect(sheet.locator(".stellenwertbild .sym")).to_have_count(0)
    sheet.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".stellenwertbild .sym").first).to_be_visible()
    paper.context.close()


def store(page, client, **more):
    """Sets keys of the whole sheet (place colours, Lösungsfarbe) as the server holds it."""
    mine = sheet_id(page)
    got = client.get(f"/api/sheets/{mine}").json()
    body = {"doc": {**got["doc"], **more}, "version": got["version"]}
    assert client.patch(f"/api/sheets/{mine}", json=body).status_code == 200
    return mine


def test_each_table_digit_in_the_key_takes_its_own_places_colour(editor, browser, server):
    """Print matches (#1076, review): with place colours on, the key's H, Z and E digits are red, blue, green."""
    client = user()
    page = editor(sw({"count": 1}), client=client)
    mine = store(page, client, places={"on": True})
    paper = key_print(browser, server, mine)
    cells = paper.locator(".stellenwertbild g.cell text.answer tspan")
    expect(cells).to_have_count(3)
    assert cells.evaluate_all("els => els.map(e => e.dataset.place)") == [
        "hunderter",
        "zehner",
        "einer",
    ]
    expect(cells.nth(0)).to_have_css("fill", "rgb(227, 6, 19)")
    expect(cells.nth(1)).to_have_css("fill", "rgb(0, 87, 168)")
    expect(cells.nth(2)).to_have_css("fill", "rgb(0, 150, 64)")
    paper.context.close()


def test_the_symbols_of_a_draw_key_take_the_losungsfarbe(editor, browser, server):
    """Print matches (#1076, review): a blue Lösungsfarbe colours the key's squares, strokes and dots."""
    client = user()
    page = editor(sw({"task": "draw", "count": 1}), client=client)
    mine = store(page, client, keyColor="#0000ff")
    paper = key_print(browser, server, mine)
    expect(paper.locator(".stellenwertbild rect.sym").first).to_have_css("stroke", "rgb(0, 0, 255)")
    expect(paper.locator(".stellenwertbild circle.sym").first).to_have_css("fill", "rgb(0, 0, 255)")
    paper.context.close()


def test_varianten_b_draw_other_numbers_and_drop_typed():
    """Varianten (#1076): B to D give a Stellenwert-Bild a seed of its own and drop `typed`; `zero` and `bundle` stay."""
    props = {**SW, "typed": [[0, 345]]}
    doc = {"pages": [{"blocks": [{"id": "s", "type": "stellenwertbild", "props": props}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {SW["seed"]}
    for letter in "BCD":
        got = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert got == {**SW, "seed": got["seed"]}
        seeds.add(got["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == props
