"""The Zahlenkette on screen and on paper: the given rings, the hidden rings, the steps, the key.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

from itertools import pairwise

from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

KETTE = {
    "count": 4,
    "columns": 2,
    "rings": 6,
    "max": 20,
    "op": "+",
    "showStep": False,
    "given": "start",
    "seed": 7,
}
RED = "rgb(192, 57, 43)"
# Each chain's rings in order: the number in each ring, or None when the ring shows none.
CHAINS = """els => els.map(k => [...k.querySelectorAll('g.chain')].map(c =>
    [...c.querySelectorAll('g.ring')].map(r => {
        const t = r.querySelector('text');
        return [+r.dataset.ring, t ? t.textContent : null];
    })))"""


def chains_of(locator):
    """Each chain of the locator's block as a list of its rings' numbers, None for a blank ring."""
    return [[n for _, n in chain] for block in locator.evaluate_all(CHAINS) for chain in block]


def test_the_pupils_sheet_shows_only_the_given_rings(editor, browser, server):
    """Given start: the pupils' page has the first two rings of each chain, 8 in all, and no answer
    and no step label. The answer key fills every ring: 16 hidden numbers, in red (#c0392b)."""
    client = user()
    page = editor(box("k", "zahlenkette", KETTE, w=180, h=39), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenkette text.given")).to_have_count(8)
    expect(paper.locator(".zahlenkette text.answer")).to_have_count(0)
    expect(paper.locator(".zahlenkette text.step")).to_have_count(0)
    expect(paper.locator(".zahlenkette text")).to_have_count(8)
    for i in range(4):
        expect(paper.locator(f".zahlenkette g.chain[data-chain='{i}'] text.given")).to_have_count(2)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenkette.solved")).to_have_count(1)
    expect(paper.locator(".zahlenkette text.answer")).to_have_count(36)
    fills = paper.locator(".zahlenkette text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )
    assert fills == [RED] * 36
    paper.context.close()


def test_on_the_key_each_chain_keeps_one_step(editor, browser, server):
    """Every chain in the answer key: the numbers go up by the same step from ring to ring, so the
    rings and the arcs agree."""
    client = user()
    page = editor(box("k", "zahlenkette", KETTE, w=180, h=39), client=client)
    paper = key_print(browser, server, sheet_id(page))
    key = chains_of(paper.locator(".zahlenkette"))
    paper.context.close()
    assert len(key) == 4
    for i, rings in enumerate(key):
        assert len(rings) == 6, (i, rings)
        nums = [int(n) for n in rings]
        steps = {b - a for a, b in pairwise(nums)}
        assert len(steps) == 1, (i, nums)


def test_with_show_step_the_pupils_arcs_carry_the_step(editor, browser, server):
    """showStep true: each arc of the pupils' page shows its step as text.step (5 per chain); the
    key adds no answer on the arcs, only the 16 hidden rings."""
    client = user()
    shown = {**KETTE, "showStep": True}
    page = editor(box("k", "zahlenkette", shown, w=180, h=39), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenkette text.step")).to_have_count(20)
    expect(paper.locator(".zahlenkette text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenkette text.answer")).to_have_count(16)
    expect(paper.locator(".zahlenkette text.step")).to_have_count(20)
    paper.context.close()


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print shows the editor's numbers in the same rings of each chain."""
    client = user()
    page = editor(box("k", "zahlenkette", KETTE, w=180, h=39), client=client)
    shown = chains_of(at(page, "k").locator(".zahlenkette"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_chains = chains_of(paper.locator(".zahlenkette"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = chains_of(paper.locator(".zahlenkette"))
    paper.context.close()
    for i in range(len(shown)):
        for j, n in enumerate(shown[i]):
            if n is not None:
                assert printed_chains[i][j] == n, (i, j)
                assert key[i][j] == n, (i, j)


def test_a_typed_chain_that_breaks_its_step_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: chain 0 has 5 in ring 0, 6 in ring 1 and 9 in ring 2, which no step fits. On the key
    that chain shows no answer in red and is marked wrong."""
    client = user()
    typed = {**KETTE, "typed": [[0, 0, 5], [0, 1, 6], [0, 2, 9]]}
    page = editor(box("k", "zahlenkette", typed, w=180, h=39), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".zahlenkette g.chain[data-chain='0'].wrong")).to_have_count(1)
    expect(paper.locator(".zahlenkette g.chain[data-chain='0'] text.answer")).to_have_count(0)
    # Chain 1 has four hidden rings and five arcs.
    expect(paper.locator(".zahlenkette g.chain[data-chain='1'] text.answer")).to_have_count(9)
    paper.context.close()
