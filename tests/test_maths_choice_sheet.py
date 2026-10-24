"""A maths block with gaps, kept on the sheet: an old save, the key, the PDF, and a copy.

The helpers live in test_maths_choice.py.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, sheet_id
from test_maths_choice import (
    DIGITS,
    DISTINCT,
    FIRST,
    ONE,
    RESULT,
    SECOND,
    ZERO,
    control,
    exercises,
    shown,
    view,
)
from test_maths_fit import inside, print_inside
from ui import at, box, doc, maths, pick, reload, user

MINUS, TIMES = chr(0x2212), chr(0x00B7)
SIGN = {"+": "+", "-": MINUS, "*": TIMES, "/": ":"}


def texts(page):
    """Each task on the sheet as its text, spaces collapsed."""
    found = (
        at(page, "m").locator(".maths > div").evaluate_all("els => els.map((e) => e.textContent)")
    )
    return [" ".join(t.split()) for t in found]


def task_parts(e):
    """The numbers and signs of a task in order, and its result."""
    parts = [str(e["a"]), SIGN[e["op"]], str(e["b"])]
    if "op2" in e:
        parts += [SIGN[e["op2"]], str(e["c"])]
    return parts, str(e["result"])


def pattern(e, solved=False):
    """A regex for the task as the PDF prints it: its hidden part left out, unless `solved`."""
    parts, result = task_parts(e)
    seq = [*parts, "=", result]
    if not solved:
        del seq[{"a": 0, "b": 2, "c": 4}.get(e.get("hide"), -1)]
    return r"\s*".join(re.escape(p) for p in seq)


def check_pupil(pupil, tasks):
    """Each task in order with its hidden part missing, and the whole task nowhere in its place."""
    pos = 0
    for e in tasks:
        found = re.compile(pattern(e)).search(pupil, pos)
        assert found, (pattern(e), pupil)
        assert not re.compile(pattern(e, solved=True)).match(pupil, found.start()), e
        pos = found.end()


def check_key(key, tasks):
    """Each task in order, whole, with its result."""
    pos = 0
    for e in tasks:
        found = re.compile(pattern(e, solved=True)).search(key, pos)
        assert found, (pattern(e, solved=True), key)
        pos = found.end()


OLD_SHEET = {
    "ops": ["+", "*"],
    "max": 20,
    "a": DIGITS,
    "b": DIGITS,
    "carry": "either",
    "rest": False,
    "format": "gap",
    "count": 4,
    "seed": 7,
    "columns": 2,
    "size": 14,
    "loosen": None,
    "exercises": [
        {"op": "+", "a": 6, "b": 6, "result": 12, "rest": 0, "hide": "a"},
        {"op": "*", "a": 1, "b": 7, "result": 7, "rest": 0, "hide": "b"},
        {"op": "+", "a": 0, "b": 5, "result": 5, "rest": 0, "hide": "b"},
        {"op": "*", "a": 0, "b": 0, "result": 0, "rest": 0},
    ],
}


def test_a8_a_sheet_saved_before_draws_its_stored_tasks(editor, server):
    """A8: an old sheet shows its stored tasks and gaps, and the panel shows the defaults."""
    client = user()
    page = editor(box("m", "maths", OLD_SHEET, y=20, h=60), client=client)
    before = view(page, client)
    expected = ["+ 6 = 12", "1 · = 7", "0 + = 5", "0 · 0 ="]
    assert texts(page) == expected
    pick(page, "m")
    assert view(page, client) == before
    tasks = OLD_SHEET["exercises"]
    mine = sheet_id(page)
    check_pupil(pdf_text(server, client, mine), tasks)
    check_key(pdf_text(server, client, mine, solved=True), tasks)
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "true")
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "true")
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "false")
    expect(control(page, FIRST)).to_have_attribute("aria-pressed", "true")
    expect(control(page, SECOND)).to_have_attribute("aria-pressed", "true")
    expect(control(page, RESULT)).to_have_attribute("aria-pressed", "false")


@pytest.mark.parametrize(
    "gaps, numbers",
    [(["a"], 2), (["b"], 2), (["result"], 2), (["c"], 3)],
)
def test_a10_the_key_prints_the_hidden_number_for_every_gap_position(editor, server, gaps, numbers):
    """A10: the key prints every task whole; the pupil's PDF leaves the hidden number out."""
    client = user()
    props_in = maths(client, format="gap", gaps=gaps, ops=["+"], max=20, count=4, numbers=numbers)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    tasks = exercises(page, client)
    mine = sheet_id(page)
    check_pupil(pdf_text(server, client, mine), tasks)
    check_key(pdf_text(server, client, mine, solved=True), tasks)


def test_a12_the_pdf_shows_the_gap_where_the_screen_has_it(editor, server):
    """A12: the pupil's PDF misses each hidden part, and the screen shows the same gaps."""
    client = user()
    props_in = maths(
        client, format="gap", gaps=["a", "b", "result"], count=9, ops=["+", "-"], max=20
    )
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    tasks = exercises(page, client)
    assert shown(page) == [e.get("hide", "result") for e in tasks]
    mine = sheet_id(page)
    check_pupil(pdf_text(server, client, mine), tasks)
    check_key(pdf_text(server, client, mine, solved=True), tasks)


@pytest.mark.parametrize("max", [10, 20, 100, 1000, 1000000])
@pytest.mark.parametrize("gaps", [["a"], ["b"], ["result"], ["a", "b", "result"]])
def test_a14_no_task_leaves_its_block_for_any_gap_position(editor, server, gaps, max):
    """A14: no task leaves its block for any gap; for the largest room, the PDF fits too."""
    client = user()
    props_in = maths(client, format="gap", gaps=gaps, ops=["+", "*"], count=12, max=max)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    inside(page, "m")
    if max == 1000000:
        print_inside(server, client, sheet_id(page))
        print_inside(server, client, sheet_id(page), solved=True)


def test_a14_three_numbers_with_a_gap_at_c_and_the_result_stay_inside(editor, server):
    """A14: three numbers, gaps at c and the result, the largest room, all signs, brackets."""
    client = user()
    props_in = maths(
        client,
        format="gap",
        gaps=["c", "result"],
        numbers=3,
        ops=["+", "-", "*", "/"],
        max=1000000,
        count=12,
        pvs=True,
        brackets=True,
    )
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    inside(page, "m")
    print_inside(server, client, sheet_id(page))
    print_inside(server, client, sheet_id(page), solved=True)


def test_i4_the_switches_show_their_state_after_a_reload(editor):
    """I4: the pressed states that were set are the ones after a reload."""
    client = user()
    props_in = maths(client, format="gap", ops=["+", "*"], max=20, count=4)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    control(page, ZERO).click()
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "false")
    control(page, ONE).click()
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "false")
    control(page, DISTINCT).click()
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    control(page, RESULT).click()
    expect(control(page, RESULT)).to_have_attribute("aria-pressed", "true")
    doc(page, client)
    reload(page, page.url)
    pick(page, "m")
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "false")
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "false")
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    expect(control(page, RESULT)).to_have_attribute("aria-pressed", "true")


def test_i5_a_copy_of_the_block_keeps_its_switches_and_tasks(editor):
    """I5: a pasted block has the same gaps, switches and tasks as the one it copies."""
    client = user()
    props_in = maths(client, format="gap", gaps=["a"], ops=["+", "*"], max=20, count=4)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    control(page, DISTINCT).click()
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    # The switch takes effect in the block once the server has answered: copy after that.
    expect(page.locator("header [role=status]")).to_have_text(re.compile("^Speichert"))
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(page.locator("header [role=status]")).to_have_text(re.compile("^Speichert"))
    sheet = doc(page, client)
    blocks = [b for b in sheet["pages"][0]["blocks"] if b["type"] == "maths"]
    assert len(blocks) == 2, blocks
    keys = ("gaps", "zero", "one", "distinct", "exercises")
    original = next(b for b in blocks if b["id"] == "m")["props"]
    copy = next(b for b in blocks if b["id"] != "m")["props"]
    assert {k: original.get(k) for k in keys} == {k: copy.get(k) for k in keys}
