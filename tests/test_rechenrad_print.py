"""The Rechenrad on screen and on paper: the given boxes, the empty boxes, the key in red.

The docstrings name what each test proves. The numbers are read from the page, never pinned: the
generator may change.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, user

RR = {
    "count": 2,
    "columns": 2,
    "rings": 2,
    "segments": 8,
    "max": 20,
    "op": "+",
    "task": "outer",
    "seed": 7,
}
MINUS = "\N{MINUS SIGN}"
DOT = "\N{MIDDLE DOT}"
RED = "rgb(192, 57, 43)"
NOTE = "Auch andere Lösungen sind richtig."
H = 85.53  # the default height: 67 * 180 / 141, rounded as insert.ts does
# Each wheel: its centre's label, whether it is wrong, and each box as [segment, ring, number or None, is an answer].
WHEELS = """els => els.map(w => ({
    wrong: w.classList.contains('wrong'),
    centre: (w.querySelector('g.centre text.given, g.centre text.answer') || {}).textContent ?? null,
    boxes: [...w.querySelectorAll('g.box')].map(b => {
        const t = b.querySelector('text.given, text.answer');
        return [+b.dataset.segment, +b.dataset.ring, t ? Number(t.textContent) : null,
                !!t && t.classList.contains('answer')];
    }),
}))"""


def apply(label, x):
    """The number that the centre's label gives from x."""
    n = int(label[1:])
    return {"+": x + n, MINUS: x - n, DOT: x * n, ":": x // n}[label[0]]


def wheels_of(locator):
    """Each wheel of the locator's Rechenrad, as WHEELS reads it."""
    return locator.locator("g.wheel").evaluate_all(WHEELS)


def fill_colours(paper):
    return paper.locator(".rechenrad text.answer").evaluate_all(
        "els => els.map(e => getComputedStyle(e).fill)"
    )


def test_the_pupils_sheet_shows_only_the_given_boxes(editor, browser, server):
    """Task outer: the pupils' page shows the centre and the inner ring of each wheel, 9 numbers per wheel,
    and no empty box; the key shows the 16 empty outer boxes."""
    client = user()
    page = editor(box("k", "rechenrad", RR, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad text.given")).to_have_count(18)
    expect(paper.locator(".rechenrad text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad text.answer")).to_have_count(16)
    paper.context.close()


def test_the_key_fills_the_empty_boxes_in_red_and_the_pupils_sheet_has_no_answer(
    editor, browser, server
):
    """Task outer: the key fills each empty box in red, and the pupils' sheet has no answer in any colour."""
    client = user()
    page = editor(box("k", "rechenrad", RR, w=180, h=H), client=client)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad text.answer")).to_have_count(0)
    paper.context.close()
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad text.answer")).to_have_count(16)
    assert fill_colours(paper) == [RED] * 16
    paper.context.close()


@pytest.mark.parametrize("op", ["+", "-", "*", ":"], ids=["plus", "minus", "mal", "geteilt"])
def test_on_the_key_each_chain_gives_the_next_ring(editor, browser, server, op):
    """On the key, in every segment of every wheel, applying the centre's number to ring r gives ring r + 1."""
    client = user()
    page = editor(box("k", "rechenrad", {**RR, "op": op}, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    wheels = wheels_of(paper.locator(".rechenrad"))
    paper.context.close()
    assert len(wheels) == RR["count"]
    for wheel in wheels:
        label = wheel["centre"]
        assert label, wheel
        rings = {}
        for segment, ring, number, _ in wheel["boxes"]:
            rings.setdefault(segment, {})[ring] = number
        assert len(rings) == RR["segments"]
        for segment, numbers in rings.items():
            assert None not in numbers.values(), (segment, numbers)
            for r in range(1, int(RR["rings"])):
                assert apply(label, numbers[r]) == numbers[r + 1], (label, segment, numbers)


def test_the_print_has_the_editors_numbers(editor, browser, server):
    """The print shows the editor's numbers in the same boxes of each wheel."""
    client = user()
    page = editor(box("k", "rechenrad", RR, w=180, h=H), client=client)
    shown = wheels_of(at(page, "k").locator(".rechenrad"))
    mine = sheet_id(page)
    paper = printed(browser, server, mine)
    printed_wheels = wheels_of(paper.locator(".rechenrad"))
    paper.context.close()
    paper = key_print(browser, server, mine)
    key = wheels_of(paper.locator(".rechenrad"))
    paper.context.close()
    for i, wheel in enumerate(shown):
        assert printed_wheels[i]["centre"] == wheel["centre"], i
        assert key[i]["centre"] == wheel["centre"], i
        for (segment, ring, number, _), (_, _, printed_n, _), (_, _, key_n, _) in zip(
            wheel["boxes"], printed_wheels[i]["boxes"], key[i]["boxes"], strict=True
        ):
            if number is not None:
                assert printed_n == number, (i, segment, ring)
                assert key_n == number, (i, segment, ring)


def test_a_wrong_typed_wheel_shows_no_answer_in_the_key(editor, browser, server):
    """Typed: wheel 0 has 5 in ring 1 and 9999 in ring 2 of segment 0, which no centre number between 1 and 10
    gives. On the key that wheel is marked wrong and shows no answer; wheel 1 keeps its answers."""
    client = user()
    typed = {**RR, "typed": [[0, 1, 0, 5], [0, 2, 0, 9999]]}
    page = editor(box("k", "rechenrad", typed, w=180, h=H), client=client)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad g.wheel[data-wheel='0'].wrong")).to_have_count(1)
    expect(paper.locator(".rechenrad g.wheel[data-wheel='0'] text.answer")).to_have_count(0)
    expect(paper.locator(".rechenrad g.wheel[data-wheel='1'] text.answer")).to_have_count(8)
    paper.context.close()


def test_the_key_never_has_the_other_answers_note(editor, browser, server):
    """Other answers: a Rechenrad has one right answer per empty box, so the key never carries the note
    "Auch andere Lösungen sind richtig.", with Mal and with a mixed task either."""
    client = user()
    page = editor(
        box("m", "rechenrad", {**RR, "op": "*"}, w=180, h=H),
        box("x", "rechenrad", {**RR, "task": "mixed"}, w=180, h=H, y=150),
        client=client,
    )
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".rechenrad")).to_have_count(2)
    expect(paper.get_by_text(NOTE)).to_have_count(0)
    paper.context.close()


def test_with_task_mixed_the_key_has_exactly_one_answer_per_segment(editor, browser, server):
    """Task mixed: each segment of each wheel has one empty box on the key, so one answer per segment."""
    client = user()
    page = editor(
        box("k", "rechenrad", {**RR, "task": "mixed", "count": 1, "columns": 1}, w=180, h=H),
        client=client,
    )
    paper = key_print(browser, server, sheet_id(page))
    wheels = wheels_of(paper.locator(".rechenrad"))
    paper.context.close()
    assert len(wheels) == 1
    answers = [segment for segment, _, _, is_answer in wheels[0]["boxes"] if is_answer]
    assert sorted(answers) == list(range(int(RR["segments"])))
