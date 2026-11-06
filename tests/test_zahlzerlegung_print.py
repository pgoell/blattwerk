"""The Zahlzerlegung block on paper: the pupils' sheet and the answer key, and the Varianten (#1078).

The numbers are read from the printed page, never pinned: the generator may change.
The docstrings name the checklist line that each test proves.
"""

from test_feed_print import printed, sheet_id
from test_zahlzerlegung import ZZ, drawn, grid, zz
from ui import pick

from blattwerk import variants


def test_the_print_draws_the_same_tasks_as_the_screen(editor, browser, server):
    """Print (#1078): the pupils' sheet draws the same items, in the same order, as the editor's drawing."""
    page = editor(zz({"count": 2}))
    pick(page, "k")
    on_screen = [grid(drawn(page), t) for t in range(2)]
    sheet = printed(browser, server, sheet_id(page))
    assert [grid(sheet.locator(".zahlzerlegung"), t) for t in range(2)] == on_screen
    sheet.context.close()


def test_varianten_b_draw_other_numbers_and_drop_typed():
    """Varianten (#1078): B to D give a Zahlzerlegung a seed of its own and drop `typed`; the other settings stay."""
    props = {**ZZ, "typed": [[0, 345]]}
    doc = {"pages": [{"blocks": [{"id": "z", "type": "zahlzerlegung", "props": props}]}]}
    assert variants.vary(doc, "A")[0] is doc
    seeds = {ZZ["seed"]}
    for letter in "BCD":
        got = variants.vary(doc, letter)[0]["pages"][0]["blocks"][0]["props"]
        assert got == {**ZZ, "seed": got["seed"]}
        seeds.add(got["seed"])
    assert len(seeds) == 4
    assert doc["pages"][0]["blocks"][0]["props"] == props
