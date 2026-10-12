"""Aufgabenfamilien: tasks come in families of two or three, set from the panel (issue #72).

Each test names the line of the checklist it proves. The results of a task are hidden on the
sheet, so the saved tasks are read from the document.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, sheet_id
from test_maths_fit import inside, print_inside
from ui import at, box, doc, maths, pick, reload, user

MINUS, TIMES = chr(0x2212), chr(0x00B7)
SIGN = {"+": "+", "-": MINUS, "*": TIMES, "/": ":"}
FAMILY_ROW = ".maths .family"


def saved(page, client, name="m"):
    """The exercises of a block as the server holds them."""
    sheet = doc(page, client)
    block = next(b for p in sheet["pages"] for b in p["blocks"] if b["id"] == name)
    return block["props"]["exercises"]


def task_of(e):
    return (str(e["a"]), SIGN[e["op"]], str(e["b"]), str(e["result"]))


def tasks(page, client, name="m"):
    """Every task as (a, sign, b, result) in order, families included."""
    return [task_of(e) for e in saved(page, client, name)]


def families(page, client, name="m"):
    """The families in order, each the list of its tasks as (a, sign, b, result)."""
    groups = {}
    for e in saved(page, client, name):
        groups.setdefault(e.get("family"), []).append(task_of(e))
    return list(groups.values())


def pick_family(page, label):
    page.locator(".panel").get_by_label("Aufgabenfamilien", exact=True).select_option(label)


def test_a1_the_panel_offers_the_four_families_for_zeile_and_luecke_only(editor):
    """A1: the four families in Zeile and Lücke only, not in Schriftlich or Vergleichen."""
    client = user()
    block = box("m", "maths", maths(client, ops=["+"], max=20, count=12), y=20, h=60)
    page = editor(block, client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    fam = panel.get_by_label("Aufgabenfamilien", exact=True)
    expect(fam).to_be_visible()
    expect(fam.locator("option")).to_have_text(
        ["Keine", "Tauschaufgaben", "Umkehraufgaben", "Nachbaraufgaben"]
    )
    panel.get_by_role("button", name="Schriftlich", exact=True).click()
    expect(fam).to_have_count(0)
    panel.get_by_role("button", name="Vergleichen", exact=True).click()
    expect(fam).to_have_count(0)


def test_a2_tauschaufgaben_follow_each_task_with_its_swap(editor):
    """A2: each Tauschaufgabe is followed by its swap; only + and · are drawn."""
    client = user()
    block = box("m", "maths", maths(client, ops=["+", "*"], max=20, count=4), y=20, h=60)
    page = editor(block, client=client)
    pick(page, "m")
    pick_family(page, "Tauschaufgaben")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    fams = families(page, client)
    assert len(fams) == 4 and all(len(f) == 2 for f in fams), fams
    for (a, op, b, r), (a2, op2, b2, r2) in fams:
        assert op in "+·" and op2 == op and r == r2
        assert (a2, b2) == (b, a)


def test_a3_umkehraufgaben_follow_each_task_with_its_reverse(editor):
    """A3: the Umkehraufgabe takes the result back: (a + b) minus b for a plus."""
    client = user()
    block = box("m", "maths", maths(client, ops=["+", "*"], max=20, count=4), y=20, h=60)
    page = editor(block, client=client)
    pick(page, "m")
    pick_family(page, "Umkehraufgaben")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    fams = families(page, client)
    assert len(fams) == 4 and all(len(f) == 2 for f in fams), fams
    assert {f[0][1] for f in fams} == {"+", TIMES}
    for (a, op, b, r), (a2, op2, b2, r2) in fams:
        assert op2 == {"+": MINUS, TIMES: ":"}[op]
        assert a2 == r and b2 == b and r2 == a


def test_a4_nachbaraufgaben_move_the_first_number_and_a_button_picks_the_second(editor):
    """A4: a Nachbaraufgabe moves the first number down and up; the button moves the second."""
    client = user()
    block = box(
        "m", "maths", maths(client, ops=["+"], max=20, count=4, family="neighbour"), y=20, h=60
    )
    page = editor(block, client=client)
    pick(page, "m")
    fams = families(page, client)
    assert len(fams) == 4 and all(len(f) == 3 for f in fams), fams
    a, _, b, _ = fams[0][0]
    a, b = int(a), int(b)
    assert [(int(x), int(y)) for x, _, y, _ in fams[0]] == [(a, b), (a - 1, b), (a + 1, b)]
    shown = at(page, "m").locator(".maths").inner_text()
    page.locator(".panel").get_by_role("button", name="2. Zahl wandert").click()
    pressed = page.locator(".panel").get_by_role("button", name="2. Zahl wandert")
    expect(pressed).to_have_attribute("aria-pressed", "true")
    expect(at(page, "m").locator(".maths")).not_to_have_text(shown)
    fams = families(page, client)
    assert [(int(x), int(y)) for x, _, y, _ in fams[0]] == [(a, b), (a, b - 1), (a, b + 1)], fams[0]


def test_a5_a_family_stands_in_one_column_with_a_gap_to_the_next(editor):
    """A5: a family's tasks share a left edge; the gap between families beats the gap inside."""
    client = user()
    props = maths(client, ops=["+"], max=20, count=4, columns=1)
    page = editor(box("m", "maths", props, y=20, h=20), client=client)
    pick(page, "m")
    # Picked in the panel, so the block has the height the editor gives it.
    pick_family(page, "Nachbaraufgaben")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    gaps = at(page, "m").evaluate(
        """block => {
          const fams = [...block.querySelectorAll('.maths .family')];
          const inner = [], between = [], left = [];
          fams.forEach((f, i) => {
            const rows = [...f.children].map(t => t.getBoundingClientRect());
            left.push(new Set(rows.map(r => Math.round(r.left))).size);
            for (let j = 1; j < rows.length; j++) inner.push(rows[j].top - rows[j - 1].bottom);
            if (i + 1 < fams.length) {
              const next = fams[i + 1].children[0].getBoundingClientRect();
              between.push(next.top - rows[rows.length - 1].bottom);
            }
          });
          return { left, inner, between };
        }"""
    )
    assert all(n == 1 for n in gaps["left"]), gaps
    assert min(gaps["between"]) > max(gaps["inner"]), gaps


def test_a6_anzahl_counts_families_and_the_panel_says_how_many_tasks(editor):
    """A6: Anzahl counts families; the panel says how many tasks that makes."""
    client = user()
    props = maths(client, ops=["+"], max=20, count=4, family="neighbour")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    expect(panel.locator("output").first).to_have_text("4 Familien")
    expect(panel.locator(".hint").filter(has_text="Das sind 12 Aufgaben.")).to_be_visible()
    panel.get_by_label("Eine Aufgabe mehr").click()
    expect(panel.locator("output").first).to_have_text("5 Familien")
    expect(panel.locator(".hint").filter(has_text="Das sind 15 Aufgaben.")).to_be_visible()


def test_a9_the_same_families_come_back_after_a_reload(editor):
    """A9: after a reload the block has the same tasks in the same families."""
    client = user()
    props = maths(client, ops=["+", "*"], max=20, count=4, family="swap")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    before = at(page, "m").locator(".maths").inner_text()
    reload(page, page.url)
    pick(page, "m")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    assert at(page, "m").locator(".maths").inner_text() == before


def test_a10_too_few_families_name_the_limit_in_the_way(editor):
    """A10: 30 Tauschaufgaben to 10 make only 22 families; the hint names the Zahlenraum."""
    client = user()
    props = maths(client, ops=["*"], max=10, count=30, family="swap")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    hint = page.locator(".panel .hint").filter(has_text="nur 22 verschiedene Familien")
    expect(hint).to_be_visible()
    expect(hint).to_contain_text("Zahlenraum")


def test_a11_the_pdf_shows_the_same_tasks_and_the_key_prints_every_result(editor, server):
    """A11/A13: the pupil's PDF holds the tasks in order; the key's PDF holds every result."""
    client = user()
    props = maths(client, ops=["+", "*"], max=20, count=4, family="reverse")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    mine = sheet_id(page)
    shown = tasks(page, client)
    pupil = pdf_text(server, client, mine)
    key = pdf_text(server, client, mine, solved=True)
    pos = 0
    for a, op, b, _ in shown:
        found = re.compile(rf"{a}\s*{re.escape(op)}\s*{b}\s*=").search(pupil, pos)
        assert found, (a, op, b, pupil)
        pos = found.end()
    pos = 0
    for a, op, b, r in shown:
        found = re.compile(rf"{a}\s*{re.escape(op)}\s*{b}\s*=\s*{r}\b").search(key, pos)
        assert found, (a, op, b, r, key)
        pos = found.end()


def test_a12_a_change_of_the_family_is_one_undo_step_and_redo_brings_it_back(editor):
    """A12: Ctrl+Z takes the family back in one step; Ctrl+Y brings the same tasks back."""
    client = user()
    props = maths(client, ops=["+"], max=20, count=4)
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    before = tasks(page, client)
    pick_family(page, "Umkehraufgaben")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    after = tasks(page, client)
    page.keyboard.press("Control+z")
    fam = page.locator(".panel").get_by_label("Aufgabenfamilien", exact=True)
    expect(fam).to_have_value("none")
    assert tasks(page, client) == before
    page.keyboard.press("Control+y")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    assert tasks(page, client) == after


@pytest.mark.parametrize("max", [10, 20, 100, 1000, 1000000])
@pytest.mark.parametrize("family", ["swap", "reverse", "neighbour"])
def test_a14_no_task_of_a_family_leaves_its_block(editor, server, family, max):
    """A14: no task of a family leaves its block; for the largest room, the PDF and key hold too."""
    client = user()
    props = maths(client, ops=["+", "*"], max=max, count=4, family=family, format="gap")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    inside(page, "m")
    if max == 1000000:
        print_inside(server, client, sheet_id(page))
        print_inside(server, client, sheet_id(page), solved=True)


def test_i2_three_numbers_grey_the_families_and_keep_the_value(editor):
    """I2: with 3 Zahlen the select is greyed and keeps its value; 2 Zahlen brings families back."""
    client = user()
    props = maths(client, ops=["+", "*"], max=20, count=4, family="swap")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    fam = panel.get_by_label("Aufgabenfamilien", exact=True)
    panel.get_by_label("3 Zahlen", exact=True).click()
    expect(fam).to_be_disabled()
    expect(fam).to_have_value("swap")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(0)
    panel.get_by_label("2 Zahlen", exact=True).click()
    expect(fam).to_be_enabled()
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)


def test_i3_tauschaufgaben_say_that_only_plus_and_times_are_drawn(editor):
    """I3: with + and minus the hint shows and all tasks are plus; with minus only, Aufgaben."""
    client = user()
    props = maths(client, ops=["+", "-"], max=20, count=4)
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    pick_family(page, "Tauschaufgaben")
    hint = "Tauschaufgaben gibt es nur für + und ·."
    expect(page.locator(".panel .hint").filter(has_text=hint)).to_be_visible()
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    assert all(op == "+" for _, op, _, _ in tasks(page, client))
    page.locator(".panel").get_by_role("button", name="+", exact=True).click()
    expect(page.locator(".panel output").first).to_have_text("4 Aufgaben")
    expect(at(page, "m").locator(".maths")).to_contain_text(MINUS)
    assert all(op == SIGN["-"] for _, op, _, _ in tasks(page, client)), tasks(page, client)


def test_i4_the_numbering_runs_through_every_task_of_every_family(editor):
    """I4: the numbers run 1 to N over every task, families included."""
    client = user()
    props = maths(client, ops=["+", "*"], max=20, count=4, family="swap", numbering="1.")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    marks = at(page, "m").locator(".maths b").all_inner_texts()
    numbers = [int(re.findall(r"\d+", n)[0]) for n in marks]
    assert numbers == list(range(1, 9)), numbers


def test_i5_fewer_columns_keep_each_family_whole_and_the_block_grows(editor):
    """I5: one column fewer keeps each family in one column and the block grows; all stay inside."""
    client = user()
    # Six families make two lines in three columns and three lines in two: the block must grow.
    props = maths(client, ops=["+"], max=20, count=6, family="neighbour")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    before = at(page, "m").bounding_box()["height"]
    page.locator(".panel").get_by_label("Eine Spalte weniger").click()
    expect(page.locator(".panel output").filter(has_text="2 Spalten")).to_be_visible()
    lefts = at(page, "m").evaluate(
        """block => [...block.querySelectorAll('.maths .family')].map(f =>
          new Set([...f.children].map(t => Math.round(t.getBoundingClientRect().left))).size)"""
    )
    assert all(n == 1 for n in lefts), lefts
    assert at(page, "m").bounding_box()["height"] > before
    inside(page, "m")


def test_i6_geteilt_in_a_family_leaves_no_rest_and_moves_the_quotient(editor):
    """I6: a Umkehraufgabe greys Mit Rest and has no rest; Nachbar moves the dividend by b."""
    client = user()
    props = maths(client, ops=["/"], max=20, count=4, rest=True, family="reverse")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    mit_rest = page.locator(".panel").get_by_role("button", name="Mit Rest", exact=True)
    expect(mit_rest).to_be_disabled()
    assert all(int(e.get("rest", 0)) == 0 for e in saved(page, client))
    pick_family(page, "Nachbaraufgaben")
    fams = families(page, client)
    assert len(fams) == 4 and all(len(f) == 3 for f in fams), fams
    a, _, b, _ = fams[0][0]
    a, b = int(a), int(b)
    assert [(int(x), int(y)) for x, _, y, _ in fams[0]] == [(a, b), (a - b, b), (a + b, b)]


def test_i7_loosen_can_name_the_families_themselves(editor):
    """I7: when the families are the limit in the way, the hint names Aufgabenfamilien."""
    client = user()
    props = maths(client, ops=["+"], max=10, carry="required", count=12, family="neighbour")
    page = editor(box("m", "maths", props, y=20, h=60), client=client)
    pick(page, "m")
    hint = page.locator(".panel .hint").filter(has_text="Aufgabenfamilien")
    expect(hint).to_be_visible()
