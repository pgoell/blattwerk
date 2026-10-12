"""Wahl der Aufgaben: the gaps of Lücke, the switches for 0, 1 and equal numbers (issue #73).

Each test names the line of the checklist it proves. The tasks are read from the document, and the
gaps from the sheet: a gap is an empty `<u>` in the task, which the answer key fills in.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, sheet_id
from test_maths_fit import inside, print_inside
from ui import at, box, doc, maths, pick, reload, user

MINUS, TIMES = chr(0x2212), chr(0x00B7)
SIGN = {"+": "+", "-": MINUS, "*": TIMES, "/": ":"}
ZERO = "Aufgaben mit 0"
ONE = "Aufgaben mit 1 beim Malnehmen und Teilen"
DISTINCT = "keine gleichen Zahlen"
FIRST, SECOND, THIRD = "Lücke: 1. Zahl", "Lücke: 2. Zahl", "Lücke: 3. Zahl"
RESULT = "Lücke: Ergebnis"
DIGITS = [[0, 9], [0, 9]]

# Each task as the sheet shows it: the gap in it, "a", "b", "c", "result", or "-" for none.
# A gap is a `<u>` element; its text is marked "\u0001" so that the numbers around it can be told.
SHOWN = """(block) => [...block.querySelectorAll('.maths > div')].map((div) => {
    let text = '';
    const walk = (node) => {
        for (const n of node.childNodes) {
            if (n.nodeName === 'U') text += '\\u0001';
            else if (n.nodeType === 3) text += n.textContent;
            else walk(n);
        }
    };
    walk(div);
    const [left, right] = text.split('=');
    if (right !== undefined && right.includes('\\u0001')) return 'result';
    const numbers = left.split(/[+\\u2212\\u00B7:\\s]+/).filter(Boolean);
    const gap = numbers.findIndex((t) => t.includes('\\u0001'));
    return ['a', 'b', 'c'][gap] ?? '-';
})"""


def control(page, name):
    return page.locator(".panel").get_by_role("button", name=name, exact=True)


def props(page, client, after=False):
    """The block's props as the document holds them, once the editor has saved.

    `after` says that a change was made just before: the editor marks the sheet unsaved only when
    the server has answered and the block took the new tasks, so the wait starts there. Without
    it, the save before the change would pass for the saved one.
    """
    if after:
        expect(page.locator("header [role=status]")).to_have_text(re.compile("^Speichert"))
    sheet = doc(page, client)
    return next(b for p in sheet["pages"] for b in p["blocks"] if b["id"] == "m")["props"]


def exercises(page, client, after=False):
    return props(page, client, after)["exercises"]


def view(page, client, after=False):
    """Every task as (a, op, b, result, hide), in order."""
    return [
        (str(e.get("a")), e.get("op"), str(e.get("b")), str(e.get("result")), e.get("hide"))
        for e in exercises(page, client, after)
    ]


def shown(page):
    """The gap of each task on the sheet, in order."""
    return at(page, "m").evaluate(SHOWN)


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


def test_a1_the_gap_format_has_a_setting_luecke_and_hides_only_what_is_ticked(editor):
    """A1: Lücke has its boxes, the ticked ones hide; Zeile has none."""
    client = user()
    props_in = maths(client, format="gap", ops=["+"], max=20, count=8)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    pressed = "aria-pressed"
    expect(control(page, FIRST)).to_have_attribute(pressed, "true")
    expect(control(page, SECOND)).to_have_attribute(pressed, "true")
    expect(control(page, RESULT)).to_have_attribute(pressed, "false")
    expect(control(page, THIRD)).to_have_count(0)
    assert {e.get("hide") for e in exercises(page, client)} <= {"a", "b"}
    control(page, FIRST).click()
    expect(control(page, FIRST)).to_have_attribute(pressed, "false")
    assert all(e.get("hide") == "b" for e in exercises(page, client, after=True))
    assert shown(page) == ["b"] * 8
    page.get_by_role("button", name="Zeile", exact=True).click()
    expect(control(page, FIRST)).to_have_count(0)
    expect(control(page, RESULT)).to_have_count(0)


def test_a2_ergebnis_beside_a_number_mixes_both_gaps_in_one_block(editor):
    """A2: with a and the result ticked, the block holds both kinds of gap."""
    client = user()
    props_in = maths(client, format="gap", ops=["+", "*"], max=20, count=12)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    control(page, RESULT).click()
    expect(control(page, RESULT)).to_have_attribute("aria-pressed", "true")
    control(page, SECOND).click()
    expect(control(page, SECOND)).to_have_attribute("aria-pressed", "false")
    # Twelve tasks of one kind are rare, and a new roll mends that: each read waits for its change.
    for _ in range(5):
        kinds = {e.get("hide", "result") for e in exercises(page, client, after=True)}
        if kinds == {"a", "result"}:
            break
        page.locator(".panel").get_by_role("button", name="Neu würfeln", exact=True).click()
    assert kinds == {"a", "result"}, kinds
    assert {"a", "result"} <= set(shown(page))


def test_a3_aufgaben_mit_0_off_keeps_0_out(editor):
    """A3: with Aufgaben mit 0 off, no task of the block holds a 0."""
    client = user()
    props_in = maths(client, ops=["+", "-"], max=10, count=20, format="row")
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "true")
    control(page, ZERO).click()
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "false")
    for e in exercises(page, client, after=True):
        assert 0 not in (e["a"], e["b"], e["result"]), e


@pytest.mark.parametrize("fmt", ["row", "gap", "written"])
def test_a3_every_format_keeps_0_out_when_it_is_off(fmt):
    """A3: the server makes no 0 in any format when Aufgaben mit 0 is off."""
    client = user()
    tasks = maths(client, ops=["+", "-"], max=10, count=20, format=fmt, zero=False)["exercises"]
    for e in tasks:
        assert 0 not in (e["a"], e["b"], e["result"]), e


def test_a3_a_comparison_keeps_0_out_when_it_is_off():
    """A3: a comparison with Aufgaben mit 0 off has no 0 on either side."""
    client = user()
    tasks = maths(client, format="compare", sides="nn", zero=False, max=10, count=20)["exercises"]
    for e in tasks:
        assert 0 not in (e["left"]["value"], e["right"]["value"]), e


def test_a4_aufgaben_mit_1_off_keeps_1_out_of_times_and_divide(editor):
    """A4: with Aufgaben mit 1 off, no times task has a 1 and no divide task has a 1 as divisor."""
    client = user()
    props_in = maths(client, ops=["*", "/"], max=20, count=12, format="row")
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    control(page, ONE).click()
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "false")
    for e in exercises(page, client, after=True):
        if e["op"] == "*":
            assert 1 not in (e["a"], e["b"]), e
        else:
            assert e["b"] != 1, e


def test_a5_keine_gleichen_zahlen_keeps_equal_numbers_out(editor):
    """A5: off at first; on, no task has the same number twice."""
    client = user()
    props_in = maths(client, ops=["+", "/"], max=10, count=20, format="row")
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "false")
    control(page, DISTINCT).click()
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    for e in exercises(page, client, after=True):
        assert e["a"] != e["b"], e


def test_a6_the_switches_are_in_the_first_view_of_the_panel(editor):
    """A6: the three switches show without scrolling, and no dialog is open."""
    client = user()
    props_in = maths(client, format="gap", ops=["+", "*"], max=20, count=4)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    for name in (ZERO, ONE, DISTINCT):
        expect(control(page, name)).to_be_visible()
        expect(control(page, name)).to_be_in_viewport()
    expect(page.locator("dialog[open]")).to_have_count(0)


def test_a7_the_same_tasks_come_back_after_a_reload(editor):
    """A7: after a reload the same tasks and switches stand; the server answers the same twice."""
    client = user()
    props_in = maths(client, format="gap", ops=["+", "*"], max=20, count=6)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    control(page, ZERO).click()
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "false")
    control(page, DISTINCT).click()
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    control(page, RESULT).click()
    expect(control(page, RESULT)).to_have_attribute("aria-pressed", "true")
    before = view(page, client, after=True)
    reload(page, page.url)
    pick(page, "m")
    assert view(page, client) == before
    expect(control(page, ZERO)).to_have_attribute("aria-pressed", "false")
    expect(control(page, DISTINCT)).to_have_attribute("aria-pressed", "true")
    body = {
        "ops": ["+", "*"],
        "max": 20,
        "count": 6,
        "seed": 7,
        "a": DIGITS,
        "b": DIGITS,
        "carry": "either",
        "rest": False,
        "format": "gap",
        "gaps": ["a", "result"],
        "zero": False,
        "one": True,
        "distinct": True,
    }
    first = client.post("/api/maths", json=body).json()["exercises"]
    again = client.post("/api/maths", json=body).json()["exercises"]
    assert first == again


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


def test_a9_too_few_tasks_name_the_switch_in_the_way(editor):
    """A9: a block with too few tasks names the switch in the way in its hint."""
    client = user()
    props_in = maths(
        client, ops=["/"], max=10, count=12, rest=False, zero=False, one=False, distinct=True
    )
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    labels = {"zero": ZERO, "one": "Aufgaben mit 1", "distinct": DISTINCT}
    hint = page.locator(".panel .hint[role=status]")
    named = props(page, client)["loosen"]
    assert set(named) & set(labels), named
    for key in named:
        if key in labels:
            expect(hint).to_contain_text(labels[key])


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


@pytest.mark.parametrize("name", [ZERO, ONE, DISTINCT, RESULT])
def test_a11_each_new_setting_is_one_undo_step_and_redo_brings_it_back(editor, name):
    """A11: each control is one undo step; Ctrl+Z takes it back, Ctrl+Y brings it again."""
    client = user()
    props_in = maths(client, ops=["+", "*"], max=20, count=6, format="gap")
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    start = control(page, name).get_attribute("aria-pressed")
    flipped = "false" if start == "true" else "true"
    before = view(page, client)
    control(page, name).click()
    expect(control(page, name)).to_have_attribute("aria-pressed", flipped)
    after = view(page, client, after=True)
    page.keyboard.press("Control+z")
    expect(control(page, name)).to_have_attribute("aria-pressed", start)
    assert view(page, client, after=True) == before
    page.keyboard.press("Control+y")
    expect(control(page, name)).to_have_attribute("aria-pressed", flipped)
    assert view(page, client, after=True) == after


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


def test_i2_the_last_ticked_box_of_luecke_cannot_be_unticked(editor):
    """I2: the only ticked box of Lücke stays ticked and the tasks stay as they are."""
    client = user()
    props_in = maths(client, format="gap", gaps=["a"], ops=["+"], max=20, count=4)
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    before = view(page, client)
    control(page, FIRST).click()
    expect(control(page, FIRST)).to_have_attribute("aria-pressed", "true")
    assert view(page, client) == before


def test_i3_the_switch_for_1_is_greyed_without_times_and_divide_and_keeps_its_value(editor):
    """I3: without · and : the 1 switch is greyed; with · it comes back, still not pressed."""
    client = user()
    props_in = maths(client, ops=["+"], max=20, count=4, one=False, format="row")
    page = editor(box("m", "maths", props_in, y=20, h=60), client=client)
    pick(page, "m")
    expect(control(page, ONE)).to_be_disabled()
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "false")
    control(page, "·").click()
    expect(control(page, ONE)).to_be_enabled()
    expect(control(page, ONE)).to_have_attribute("aria-pressed", "false")


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
