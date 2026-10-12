"""Three numbers in a task of a maths block: the setting Zahlen pro Aufgabe, the switches Punkt vor
Strich and mit Klammern, the third number's digits, the gap that stands for any of the three, the
answer key, the PDF, and the undo of each setting.

The docstrings name the lines of the checklist that each test proves. A setting that asks the
server is waited for through the save that follows it, so the tests read the props the server holds.
"""

import operator

import pytest
from playwright.sync_api import expect
from test_compare import changed, ctl, shown
from test_feed_print import pdf_text, printed, sheet_id
from test_fix_mix import key
from test_gaps import step
from test_words import redo, undo
from ui import at, box, maths, pick, saved, tool, user

SIGNS = {"+": "+", "-": "\N{MINUS SIGN}", "*": "·", "/": ":"}
PY = {"+": operator.add, "-": operator.sub, "*": operator.mul}


def calc(x, op, y):
    """One step of a task by the rule. A division must come out whole."""
    if op == "/":
        assert y and x % y == 0, f"{x} : {y} has a remainder"
        return x // y
    return PY[op](x, y)


def rule(e):
    """A task's value by the rule: brackets first, then Punkt vor Strich, else left to right."""
    a, b, c = e["a"], e["b"], e["c"]
    if e.get("paren") == "right" or (
        e.get("paren") is None and e["op"] in "+-" and e["op2"] in "*/"
    ):
        return calc(a, e["op"], calc(b, e["op2"], c))
    return calc(calc(a, e["op"], b), e["op2"], c)


def written(e):
    """A task as the sheet writes it up to the result, its brackets included."""
    a, b, c = e["a"], e["b"], e["c"]
    op, op2 = SIGNS[e["op"]], SIGNS[e["op2"]]
    if e.get("paren") == "left":
        return f"({a} {op} {b}) {op2} {c} ="
    if e.get("paren") == "right":
        return f"{a} {op} ({b} {op2} {c}) ="
    return f"{a} {op} {b} {op2} {c} ="


def carries(x, y):
    """Whether adding x and y carries in any place."""
    return any((x // 10**k) % 10 + (y // 10**k) % 10 >= 10 for k in range(len(str(max(x, y)))))


def worth(line):
    """Whether a line of the key is a true equation, read with Python's signs."""
    lhs, rhs = line.split("=")
    lhs = lhs.replace("·", "*").replace(":", "/").replace("\N{MINUS SIGN}", "-")
    return eval(lhs) == int(rhs)


def test_zahlen_pro_aufgabe_shows_for_zeile_and_luecke_only(editor):
    """A1: Zahlen pro Aufgabe shows under Zeile and Lücke only; 3 Zahlen gives three numbers."""
    client = user()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    expect(ctl(page, "2 Zahlen")).to_be_visible()
    changed(page, client, lambda: ctl(page, "Schriftlich").click())
    expect(ctl(page, "2 Zahlen")).to_have_count(0)
    changed(page, client, lambda: ctl(page, "Vergleichen").click())
    expect(ctl(page, "2 Zahlen")).to_have_count(0)
    changed(page, client, lambda: ctl(page, "Lücke").click())
    expect(ctl(page, "2 Zahlen")).to_be_visible()
    changed(page, client, lambda: ctl(page, "Zeile").click())
    expect(ctl(page, "2 Zahlen")).to_be_visible()
    props = changed(page, client, lambda: ctl(page, "3 Zahlen").click())
    expect(at(page, "m").locator(".maths > div")).to_have_count(props["count"])
    assert all("c" in e and "op2" in e for e in props["exercises"])


def test_three_numbers_with_plus_and_minus_make_chains_in_the_zahlenraum(editor):
    """A2: With + and minus only, each chain of three keeps every step in 0 to 20."""
    client = user()
    props = maths(client, ops=["+", "-"], max=20, numbers=3, count=12)
    page = editor(box("m", "maths", props), client=client)
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    assert len(props["exercises"]) == 12
    for e in props["exercises"]:
        assert e["op"] in "+-" and e["op2"] in "+-"
        assert all(0 <= n <= 20 for n in (e["a"], e["b"], e["c"]))
        assert 0 <= calc(e["a"], e["op"], e["b"]) <= 20
        assert 0 <= e["result"] <= 20
    assert shown(at(page, "m")) == [written(e) for e in props["exercises"]]


def test_punkt_vor_strich_is_free_with_three_numbers_and_both_kinds_only(editor):
    """A3: Punkt vor Strich is greyed with two numbers or one kind of sign, and free with both."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+", "*"], max=100, count=6)), client=client)
    pick(page, "m")
    expect(ctl(page, "Punkt vor Strich")).to_be_disabled()
    changed(page, client, lambda: ctl(page, "3 Zahlen").click())
    expect(ctl(page, "Punkt vor Strich")).to_be_enabled()
    changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, "Punkt vor Strich")).to_be_disabled()
    expect(ctl(page, "Punkt vor Strich")).to_have_attribute("aria-pressed", "false")
    changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, "Punkt vor Strich")).to_be_enabled()


def test_punkt_vor_strich_mixes_both_kinds_and_half_start_with_the_punktrechnung(editor):
    """A3: With Punkt vor Strich each task has both kinds; 6 of 12 start with the Punkt sign."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-", "*", "/"], max=100, count=12, numbers=3)),
        client=client,
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Punkt vor Strich").click())
    assert props["pvs"] is True
    for e in props["exercises"]:
        assert (e["op"] in "*/") != (e["op2"] in "*/")
        assert e["result"] == rule(e)
    assert sum(e["op"] in "*/" for e in props["exercises"]) == 6


def test_mit_klammern_is_free_with_punkt_vor_strich_only_and_brackets_half_of_the_tasks(editor):
    """A4: mit Klammern waits for Punkt vor Strich; then 6 of 12 tasks have brackets."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "*"], max=100, count=12, numbers=3)),
        client=client,
    )
    pick(page, "m")
    expect(ctl(page, "mit Klammern")).to_be_disabled()
    changed(page, client, lambda: ctl(page, "Punkt vor Strich").click())
    props = changed(page, client, lambda: ctl(page, "mit Klammern").click())
    assert props["brackets"] is True
    texts = shown(at(page, "m"))
    assert sum("(" in t and ")" in t for t in texts) == 6
    assert texts == [written(e) for e in props["exercises"]]
    for e in props["exercises"]:
        assert e["result"] == rule(e)


def test_a_division_in_a_task_of_three_has_no_remainder(editor):
    """A5: Each division step of a task of three is exact, no task shows R, Mit Rest is gone."""
    client = user()
    page = editor(
        box(
            "m",
            "maths",
            maths(client, ops=["+", "/"], max=100, count=12, numbers=3, pvs=True, brackets=True),
        ),
        client=client,
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    for e in props["exercises"]:
        assert e["result"] == rule(e)
    assert all(" R " not in text for text in shown(at(page, "m")))
    expect(ctl(page, "Mit Rest")).to_have_count(0)


def test_the_third_number_keeps_its_digits_and_the_carry_holds_in_each_step(editor):
    """A6: The third number's digits hold; with Ohne under Übertrag no step of a chain carries."""
    client = user()
    page = editor(box("m", "maths", maths(client, numbers=3, max=100, count=12)), client=client)
    pick(page, "m")
    group = page.locator(".panel .places").nth(2)
    changed(page, client, lambda: group.get_by_label("E von").select_option("2"))
    props = changed(page, client, lambda: group.get_by_label("E bis").select_option("3"))
    assert all(e["c"] % 10 in (2, 3) for e in props["exercises"])
    props = changed(page, client, lambda: ctl(page, "Ohne").click())
    for e in props["exercises"]:
        assert not carries(e["a"], e["b"]) and not carries(calc(e["a"], e["op"], e["b"]), e["c"])


def test_the_gap_stands_for_any_of_the_three_numbers(editor):
    """A7: The gap of a task of three stands for a, b or c; the key shows that number."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="gap", numbers=3, count=30, max=100)),
        client=client,
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    assert {e["hide"] for e in props["exercises"]} == {"a", "b", "c"}
    block = at(page, "m")
    expect(block.locator(".maths > div")).to_have_count(30)
    for row in block.locator(".maths > div").all():
        assert row.locator("u").count() == 1
    tool(page, "Lösungen zeigen").click()
    expect(block.locator(".maths.solved")).to_be_visible()
    expect(block.locator(".maths > div u")).to_have_text(
        [str(e[e["hide"]]) for e in props["exercises"]]
    )


def test_a_seed_brings_the_same_tasks_of_three_on_every_load(editor):
    """A8: A reload shows the same tasks of three, and Neu würfeln brings others."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=10, numbers=3)),
        client=client,
    )
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    before = shown(at(page, "m"))
    page.reload()
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    assert shown(at(page, "m")) == before
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Neu würfeln").click())
    assert props["seed"] != 7
    assert shown(at(page, "m")) != before


def test_the_panel_names_what_stands_in_the_way_of_three(editor):
    """A8: Too few digits for the third number: the panel names them as the limit in the way."""
    client = user()
    # Each number is 5, so one task is all there is: the panel names the digits that give more.
    more = dict(
        numbers=3,
        max=20,
        ops=["+"],
        count=12,
        a=[[5, 5], [0, 0]],
        b=[[5, 5], [0, 0]],
        c=[[5, 5], [0, 0]],
    )
    page = editor(box("m", "maths", maths(client, **more)), client=client)
    pick(page, "m")
    expect(page.locator(".panel p.hint[role=status]")).to_contain_text("Ziffern der 3. Zahl")


def test_a_block_of_two_numbers_loads_and_prints_as_before(editor, browser, server):
    """A9: A block of two numbers with no keys for the new settings loads and prints as before."""
    client = user()
    props = maths(client)
    assert not {"numbers", "c", "pvs", "brackets"} & props.keys()
    page = editor(box("m", "maths", props), client=client)
    pick(page, "m")
    expect(ctl(page, "2 Zahlen")).to_have_attribute("aria-pressed", "true")
    texts = shown(at(page, "m"))
    assert texts == [f"{e['a']} {SIGNS[e['op']]} {e['b']} =" for e in props["exercises"]]
    paper = printed(browser, server, sheet_id(page))
    assert shown(paper) == texts
    paper.context.close()


@pytest.mark.parametrize("format", ["row", "gap"])
def test_the_key_prints_each_result_and_each_is_right(editor, browser, server, format):
    """A10: Each key line is a true equation with the result in red; the pupil's gaps are empty."""
    client = user()
    more = dict(ops=["+", "-", "*", "/"], max=100, count=12, numbers=3, pvs=True, brackets=True)
    page = editor(box("m", "maths", maths(client, format=format, **more)), client=client)
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    pupil = printed(browser, server, sheet_id(page))
    expect(pupil.locator(".maths > div")).to_have_count(12)
    assert all(not gap.text_content() for gap in pupil.locator(".maths u").all())
    pupil.context.close()
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    lines = shown(paper)
    assert all(worth(line) for line in lines)
    expect(paper.locator(".maths u").first).to_have_css("color", "rgb(192, 57, 43)")
    paper.context.close()


def test_each_setting_of_three_undoes_and_redoes(editor):
    """A11: Each setting of three undoes to what was before and redoes to what came after."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+", "*"], max=100, count=6)), client=client)
    pick(page, "m")
    actions = [
        lambda: ctl(page, "3 Zahlen").click(),
        lambda: ctl(page, "Punkt vor Strich").click(),
        lambda: ctl(page, "mit Klammern").click(),
        lambda: page.locator(".panel .places").nth(2).get_by_label("E von").select_option("2"),
    ]
    for act in actions:
        before = (shown(at(page, "m")), saved(page, client)[0]["props"])
        step(page, act)
        after = (shown(at(page, "m")), saved(page, client)[0]["props"])
        assert after != before
        step(page, lambda: undo(page))
        assert (shown(at(page, "m")), saved(page, client)[0]["props"]) == before
        step(page, lambda: redo(page))
        assert (shown(at(page, "m")), saved(page, client)[0]["props"]) == after


def test_the_pdf_and_the_key_show_the_same_tasks_as_the_editor(editor, browser, server):
    """A12: The print page and the key show the editor's tasks, and the PDF has the brackets."""
    client = user()
    page = editor(
        box(
            "m",
            "maths",
            maths(client, ops=["+", "*"], max=100, count=12, numbers=3, pvs=True, brackets=True),
        ),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == shown(at(page, "m"))
    paper.context.close()
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator(".maths.solved")).to_be_visible()
    solved = shown(at(page, "m"))
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert shown(paper) == solved
    paper.context.close()
    assert "(" in pdf_text(server, client, sheet_id(page), solved=True)


def test_back_to_two_the_old_tasks_come_back_and_back_to_three_the_same_chains(editor):
    """I1: 2 Zahlen brings back the two-number tasks, and 3 Zahlen the same chains as before."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+", "-"], max=20, count=6)), client=client)
    pick(page, "m")
    first = saved(page, client)[0]["props"]
    chains = changed(page, client, lambda: ctl(page, "3 Zahlen").click())["exercises"]
    back = changed(page, client, lambda: ctl(page, "2 Zahlen").click())
    assert back["exercises"] == first["exercises"]
    again = changed(page, client, lambda: ctl(page, "3 Zahlen").click())
    assert again["exercises"] == chains


def test_a_switch_that_is_not_free_is_greyed_and_counts_for_nothing(editor):
    """I2: A switch that is not free is greyed and counts for nothing; the tasks are chains of +."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "*"], max=100, count=12, numbers=3, pvs=True)),
        client=client,
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, "Punkt vor Strich")).to_be_disabled()
    expect(ctl(page, "Punkt vor Strich")).to_have_attribute("aria-pressed", "false")
    assert props["pvs"] is True
    assert all(e["op"] == "+" and e["op2"] == "+" for e in props["exercises"])


def test_schriftlich_keeps_two_numbers_and_zeile_brings_three_back(editor):
    """I3: Schriftlich writes two numbers, and Zeile brings the three back."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, numbers=3, ops=["+", "-"], max=20, count=12)),
        client=client,
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Schriftlich").click())
    assert all("op2" not in e for e in props["exercises"])
    expect(ctl(page, "2 Zahlen")).to_have_count(0)
    props = changed(page, client, lambda: ctl(page, "Zeile").click())
    assert all("op2" in e for e in props["exercises"])
    expect(ctl(page, "3 Zahlen")).to_have_attribute("aria-pressed", "true")


def test_columns_size_and_numbering_work_with_three_numbers(editor):
    """I5: Columns, size and numbering work with three numbers, and no task crosses its column."""
    client = user()
    page = editor(
        box(
            "m",
            "maths",
            maths(client, ops=["+", "*"], max=100, count=6, numbers=3, pvs=True, brackets=True),
        ),
        client=client,
    )
    pick(page, "m")
    block = at(page, "m")
    grid = block.locator(".maths")
    expect(block.locator(".maths > div")).to_have_count(6)
    assert len(grid.evaluate("el => getComputedStyle(el).gridTemplateColumns").split()) == 3
    overflow = block.locator(".maths > div").evaluate_all(
        """els => els.flatMap((cell) => {
            const edge = cell.getBoundingClientRect().right;
            return [...cell.querySelectorAll(":scope > span")].map(
              (s) => s.getBoundingClientRect().right - edge,
            );
        })"""
    )
    assert overflow and all(x <= 0.5 for x in overflow)
    high = block.bounding_box()["height"]
    changed(page, client, lambda: ctl(page, "Eine Spalte weniger").click())
    assert len(grid.evaluate("el => getComputedStyle(el).gridTemplateColumns").split()) == 2
    assert block.bounding_box()["height"] > high
    high = saved(page, client)[0]["h"]
    props = changed(page, client, lambda: ctl(page, "Eine Aufgabe mehr").click())
    assert props["count"] == 7 and saved(page, client)[0]["h"] > high
    size = grid.evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    props = changed(page, client, lambda: ctl(page, "Schrift größer").click())
    assert props["size"] == 16
    assert grid.evaluate("el => parseFloat(getComputedStyle(el).fontSize)") > size
    numbering = page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first
    props = changed(page, client, numbering.click)
    assert props["numbering"] == "1."
    expect(block.locator(".maths > div > b")).to_have_text(
        ["1.", "2.", "3.", "4.", "5.", "6.", "7."]
    )


def test_without_punkt_vor_strich_each_task_is_of_one_kind(editor):
    """I6: Without Punkt vor Strich each task is of one kind; * and : alone read left to right."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-", "*", "/"], max=100, count=12, numbers=3)),
        client=client,
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    assert all((e["op"] in "+-") == (e["op2"] in "+-") for e in props["exercises"])
    changed(page, client, lambda: ctl(page, "+").click())
    props = changed(page, client, lambda: ctl(page, SIGNS["-"]).click())
    assert set(props["ops"]) == {"*", "/"}
    assert shown(at(page, "m")) == [written(e) for e in props["exercises"]]
    for e in props["exercises"]:
        assert e["result"] == rule(e)
