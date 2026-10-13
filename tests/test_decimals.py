"""Decimals in a maths block: Nachkommastellen, Geld, the digits of the places after the comma, the
printed comma, the gap's width, the carry across the comma, the greyed setting, the key, the PDF,
and the undo of each setting.

The docstrings name the lines of the checklist that each test proves. Printed numbers are read as
Decimal, never as float.
"""

import re
from decimal import Decimal

import pytest
from playwright.sync_api import expect
from test_compare import changed, ctl, shown
from test_feed_print import pdf_text, printed, sheet_id
from test_fix_mix import key
from test_gaps import step
from test_three import SIGNS, carries
from test_words import redo, undo
from ui import at, box, maths, pick, saved, tool, user


def fmt(n, d, money=False):
    """A whole number of the smallest place as the sheet writes it: 350 with 2 places is 3,5."""
    digits = str(n).zfill(d + 1)
    whole, fraction = digits[: len(digits) - d], digits[len(digits) - d :]
    if not money:
        fraction = fraction.rstrip("0")
    return f"{whole},{fraction}" if fraction else whole


def amount(text):
    """A printed number as a Decimal: 3,50 € reads as 3.50, and spaces are dropped."""
    return Decimal("".join(text.replace("€", "").split()).replace(",", "."))


def true_line(line):
    """A line of the key, with its signs read by Decimal, is a true equation."""
    lhs, rhs = line.split("=")
    tokens = lhs.replace("\N{MINUS SIGN}", "-").split()
    total = amount(tokens[0])
    for op, n in zip(tokens[1::2], tokens[2::2], strict=True):
        total = total + amount(n) if op == "+" else total - amount(n)
    return total == amount(rhs)


@pytest.mark.parametrize("format", ["row", "gap", "written"])
def test_nachkommastellen_sets_the_places_for_zeile_luecke_and_schriftlich(editor, format):
    """A1: 1 and 2 Nachkommastellen save their places, and the tasks show commas."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format=format, ops=["+"], max=10, count=12)), client=client
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "1 Nachkommastelle").click())
    assert props["decimals"] == 1
    props = changed(page, client, lambda: ctl(page, "2 Nachkommastellen").click())
    assert props["decimals"] == 2
    expect(ctl(page, "2 Nachkommastellen")).to_have_attribute("aria-pressed", "true")
    texts = shown(at(page, "m"))
    assert any("," in text for text in texts)
    assert all("." not in text for text in texts)


def test_zehntel_and_hundertstel_take_a_lowest_and_a_highest_digit(editor):
    """A2: With 2 places the panel shows Zehntel and Hundertstel per number; the digits hold."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+"], max=10, count=6)), client=client)
    pick(page, "m")
    changed(page, client, lambda: ctl(page, "2 Nachkommastellen").click())
    for name in ["Zehntel von", "Zehntel bis", "Hundertstel von", "Hundertstel bis"]:
        expect(page.locator(".panel").get_by_label(name, exact=True)).to_have_count(2)
    group = page.locator(".panel .places").nth(0)
    changed(page, client, lambda: group.get_by_label("Zehntel von").select_option("3"))
    changed(page, client, lambda: group.get_by_label("Zehntel bis").select_option("3"))
    props = changed(page, client, lambda: group.get_by_label("Hundertstel bis").select_option("0"))
    # The answer holds whole numbers of the smallest place: the first digit is the Hundertstel.
    assert props["af"] == [[3, 3], [0, 0]]
    assert all(e["a"] % 10 == 0 and e["a"] // 10 % 10 == 3 for e in props["exercises"])
    for text in shown(at(page, "m")):
        first = amount(text.split()[0])
        assert first * 10 % 10 == 3 and first * 100 % 10 == 0


def test_numbers_print_with_a_decimal_comma(editor):
    """A3: Each task's numbers are the test's own formatting of the props, with a comma."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=10, count=12, decimals=2)),
        client=client,
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    texts = shown(at(page, "m"))
    assert texts == [
        f"{fmt(e['a'], 2)} {SIGNS[e['op']]} {fmt(e['b'], 2)} =" for e in props["exercises"]
    ]
    assert all("." not in text for text in texts)


@pytest.mark.parametrize("format", ["row", "gap"])
def test_geld_prints_two_places_and_a_euro_after_each_number(editor, format):
    """A4: Geld gives every number two places and a €; in Lücke the € stands outside the gap."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format=format, ops=["+"], max=10, count=12, money=True)),
        client=client,
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    block = at(page, "m")
    if format == "row":
        assert shown(block) == [
            f"{fmt(e['a'], 2, True)} € + {fmt(e['b'], 2, True)} € = €" for e in props["exercises"]
        ]
    tool(page, "Lösungen zeigen").click()
    expect(block.locator(".maths.solved")).to_be_visible()
    solved = shown(block)
    assert all(re.fullmatch(r"\d+,\d\d € \S \d+,\d\d € = \d+,\d\d €", line) for line in solved)
    assert all("€" not in gap for gap in block.locator(".maths u").all_text_contents())


def test_schriftlich_sets_comma_under_comma(editor):
    """A5: In the written format the commas of a task stand under each other, at one x, and
    both numbers have two digits after it: empty places are filled with 0."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="written", ops=["+"], max=10, count=6, decimals=2)),
        client=client,
    )
    pick(page, "m")
    tasks = (
        at(page, "m")
        .locator(".maths > div")
        .evaluate_all(
            """els => els.map((el) => [...el.querySelectorAll('svg text')]
            .map((t) => [t.textContent, +t.getAttribute('x')]))"""
        )
    )
    assert len(tasks) == 6
    for cells in tasks:
        commas = {x for ch, x in cells if ch == ","}
        assert len(commas) == 1
        assert sum(ch.isdigit() and x > max(commas) for ch, x in cells) == 4


def test_uebertrag_counts_across_the_comma(editor):
    """A6: With Mit each task carries in some place, the carry across the comma counts."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=12, decimals=1)), client=client
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Mit").click())
    assert props["carry"] == "required"
    assert all(carries(e["a"], e["b"]) for e in props["exercises"])
    props = changed(page, client, lambda: ctl(page, "Ohne").click())
    assert all(not carries(e["a"], e["b"]) for e in props["exercises"])


def test_times_or_divide_grey_the_setting_and_it_counts_for_nothing(editor):
    """A7: With · on the four buttons are greyed, and the tasks are whole numbers."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=12, decimals=2)), client=client
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    for name in ["0 Nachkommastellen", "1 Nachkommastelle", "2 Nachkommastellen", "Geld"]:
        expect(ctl(page, name)).to_be_disabled()
    assert props["decimals"] == 2
    assert all("," not in text for text in shown(at(page, "m")))


def test_a_seed_brings_the_same_decimal_tasks_on_every_load(editor):
    """A9: A reload shows the same decimal tasks."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=10, decimals=2)),
        client=client,
    )
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    before = shown(at(page, "m"))
    assert any("," in text for text in before)
    page.reload()
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    assert shown(at(page, "m")) == before


def test_a_block_without_the_new_keys_loads_and_prints_as_before(editor, browser, server):
    """A10: A block with no decimal keys loads and prints as before, with 0 pressed."""
    client = user()
    props = maths(client)
    assert not {"decimals", "money", "af", "bf", "cf"} & props.keys()
    page = editor(box("m", "maths", props), client=client)
    pick(page, "m")
    expect(ctl(page, "0 Nachkommastellen")).to_have_attribute("aria-pressed", "true")
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "false")
    texts = shown(at(page, "m"))
    assert texts == [f"{e['a']} {SIGNS[e['op']]} {e['b']} =" for e in props["exercises"]]
    paper = printed(browser, server, sheet_id(page))
    assert shown(paper) == texts
    paper.context.close()


@pytest.mark.parametrize("format", ["row", "gap"])
def test_the_key_prints_each_result_with_its_comma_and_each_is_right(
    editor, browser, server, format
):
    """A11: Each key line is a true equation in Decimal; the pupil's gaps are empty."""
    client = user()
    more = dict(ops=["+", "-"], max=100, count=12, decimals=2)
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
    assert all(true_line(line) for line in lines)
    assert any("," in line.split("=")[1] for line in lines)
    paper.context.close()


def test_each_decimal_setting_undoes_and_redoes(editor):
    """A12: Each decimal setting undoes to what was before and redoes to what came after."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+"], max=10, count=6)), client=client)
    pick(page, "m")
    actions = [
        lambda: ctl(page, "1 Nachkommastelle").click(),
        lambda: ctl(page, "2 Nachkommastellen").click(),
        lambda: ctl(page, "Geld").click(),
        lambda: (
            page.locator(".panel .places").nth(0).get_by_label("Zehntel von").select_option("2")
        ),
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


def test_the_pdf_and_the_key_show_the_same_decimal_tasks_as_the_editor(editor, browser, server):
    """A13: The print page and the key show the editor's tasks; the PDF has commas and €."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=12, money=True)),
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
    text = pdf_text(server, client, sheet_id(page), solved=True)
    assert re.search(r"\d+,\d\d", text) and "€" in text
    assert not re.search(r"\d\.\d", text)


def test_a_greyed_nachkommastellen_keeps_its_value(editor):
    """I1: With · on the places are greyed; with · off the places are back as they were."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=6, decimals=2)), client=client
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    assert props["decimals"] == 2
    props = changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    expect(ctl(page, "2 Nachkommastellen")).to_have_attribute("aria-pressed", "true")
    expect(ctl(page, "2 Nachkommastellen")).to_be_enabled()
    assert props["decimals"] == 2 and props["ops"] == ["+"]


def test_geld_shows_two_places_and_gives_the_earlier_value_back(editor):
    """I2: Geld shows two places, the number buttons stay open; Geld off gives the value back."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+"], max=10, count=6, decimals=1)), client=client
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Geld").click())
    expect(ctl(page, "Geld")).to_have_attribute("aria-pressed", "true")
    expect(ctl(page, "1 Nachkommastelle")).to_have_attribute("aria-pressed", "false")
    expect(ctl(page, "1 Nachkommastelle")).to_be_enabled()
    assert all(re.search(r"\d+,\d\d €", text) for text in shown(at(page, "m")))
    props = changed(page, client, lambda: ctl(page, "Geld").click())
    assert props["money"] is False and props["decimals"] == 1
    expect(ctl(page, "1 Nachkommastelle")).to_have_attribute("aria-pressed", "true")


def test_back_to_zero_the_whole_tasks_of_the_seed_come_back_and_the_digits_stay(editor):
    """I3: Back to 0 the whole tasks of the seed come back, and the digits of the places stay."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+"], max=10, count=6)), client=client)
    pick(page, "m")
    whole = shown(at(page, "m"))
    changed(page, client, lambda: ctl(page, "2 Nachkommastellen").click())
    props = changed(
        page,
        client,
        lambda: (
            page.locator(".panel .places").nth(0).get_by_label("Zehntel von").select_option("3")
        ),
    )
    assert props["af"][0] == [3, 9]
    props = changed(page, client, lambda: ctl(page, "0 Nachkommastellen").click())
    assert props["af"][0] == [3, 9]
    assert shown(at(page, "m")) == whole


def test_three_numbers_take_decimals(editor, browser, server):
    """I4: With three numbers and 1 Nachkommastelle, each key line is a true equation."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, ops=["+", "-"], max=100, count=12, numbers=3, decimals=1)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    assert all(true_line(line) for line in shown(paper))
    paper.context.close()


def test_the_gap_holds_the_longest_decimal_number(editor, browser, server):
    """I5: In Lücke with max 1000 and 2 places, no gap on the key is narrower than its text."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="gap", ops=["+"], max=1000, count=12, decimals=2)),
        client=client,
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(12)
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(12)
    widths = paper.locator(".maths u").evaluate_all(
        "els => els.map((el) => [el.scrollWidth, el.clientWidth])"
    )
    assert widths and all(scroll <= box_width + 0.5 for scroll, box_width in widths)
    paper.context.close()


def test_times_bis_100_shows_school_tasks_in_the_panel(editor):
    """H5: Times up to 100 in the panel: at most 3 of 12 tasks have a factor 0 or 1."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["+"], max=100, count=12)), client=client)
    pick(page, "m")
    changed(page, client, lambda: ctl(page, SIGNS["*"]).click())
    props = changed(page, client, lambda: ctl(page, "+").click())
    assert props["ops"] == ["*"]
    trivial = [e for e in props["exercises"] if {e["a"], e["b"]} & {0, 1}]
    assert len(trivial) <= 3
