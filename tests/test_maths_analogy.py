"""Analogieaufgaben, and a family that hides one more number (issue #841).

An Analogieaufgabe is a package of three tasks. One number, the first or the second, grows by
ten down the package: 3 + 4, 13 + 4, 23 + 4. With places after the comma, ten is ten of the
unit the pupil reads, so one place grows by 100 of the smallest place.

"Vollständig anzeigen" is on unless `full` is false. Off, the last task of a family hides one
more number: the number the package changes, or the first number of a Tausch- or Umkehraufgabe.
That number is `also`. When the gap already hides it, the other number is hidden instead.
"""

import pytest
from playwright.sync_api import expect
from test_families import FAMILY_ROW, families, pick_family, saved
from ui import at, box, maths, pick, user

from blattwerk.maths import Settings, generate


def grouped(exercises):
    """The tasks of each family, in the order the block draws them."""
    groups = {}
    for e in exercises:
        groups.setdefault(e["family"], []).append(e)
    return list(groups.values())


def test_an_analogieaufgabe_grows_the_first_number_by_ten():
    """#841: 3 + 4, 13 + 4, 23 + 4. Four packages, the first number up by ten twice."""
    out = generate(Settings(ops=["+"], max=100, family="analogy", count=4, seed=1))
    assert out["loosen"] is None
    fams = grouped(out["exercises"])
    assert len(fams) == 4 and all(len(f) == 3 for f in fams)
    for fam in fams:
        assert {e["op"] for e in fam} == {"+"}
        assert len({e["b"] for e in fam}) == 1
        assert [e["a"] for e in fam] == [fam[0]["a"], fam[0]["a"] + 10, fam[0]["a"] + 20]
        assert [e["result"] for e in fam] == [e["a"] + e["b"] for e in fam]
        assert all("also" not in e for e in fam)
    tasks = [(e["op"], e["a"], e["b"]) for e in out["exercises"]]
    assert len(set(tasks)) == len(tasks)


def test_the_second_number_grows_when_it_is_the_one_asked():
    """#841: the same package with the second number growing: 3 + 4, 3 + 14, 3 + 24."""
    out = generate(Settings(ops=["+"], max=100, family="analogy", moves="b", count=4, seed=1))
    fams = grouped(out["exercises"])
    assert len(fams) == 4 and all(len(f) == 3 for f in fams)
    for fam in fams:
        assert len({e["a"] for e in fam}) == 1
        assert [e["b"] for e in fam] == [fam[0]["b"], fam[0]["b"] + 10, fam[0]["b"] + 20]


def test_one_decimal_place_still_grows_by_ten_on_the_page():
    """#841: one place after the comma stores tenths, and ten on the page is 100 of those."""
    out = generate(
        Settings(ops=["+"], max=100, decimals=1, family="analogy", count=3, seed=1, format="row")
    )
    fams = grouped(out["exercises"])
    assert fams and all(len(f) == 3 for f in fams)
    for fam in fams:
        assert [e["a"] for e in fam] == [fam[0]["a"], fam[0]["a"] + 100, fam[0]["a"] + 200]


@pytest.mark.parametrize("op", ["-", "*"])
def test_minus_and_times_grow_the_same_way(op):
    """#841: the package is not only plus. The result is the operation's own."""
    out = generate(Settings(ops=[op], max=100, family="analogy", count=3, seed=1))
    fams = grouped(out["exercises"])
    assert fams and all(len(f) == 3 for f in fams)
    for fam in fams:
        assert [e["a"] for e in fam] == [fam[0]["a"], fam[0]["a"] + 10, fam[0]["a"] + 20]
        got = [e["result"] for e in fam]
        want = [e["a"] - e["b"] if op == "-" else e["a"] * e["b"] for e in fam]
        assert got == want


def test_a_division_grows_its_dividend_by_ten_and_stays_even():
    """#841: 20 : 2, 30 : 2, 40 : 2. No remainder, the quotient is the division's own."""
    out = generate(Settings(ops=["/"], max=100, family="analogy", count=3, seed=1, rest=False))
    fams = grouped(out["exercises"])
    assert fams and all(len(f) == 3 for f in fams)
    for fam in fams:
        assert [e["a"] for e in fam] == [fam[0]["a"], fam[0]["a"] + 10, fam[0]["a"] + 20]
        assert len({e["b"] for e in fam}) == 1
        assert all(e["rest"] == 0 and e["result"] == e["a"] // e["b"] for e in fam)


@pytest.mark.parametrize(
    ("family", "moves", "size", "key"),
    [
        ("analogy", "a", 3, "a"),
        ("analogy", "b", 3, "b"),
        ("neighbour", "a", 3, "a"),
        ("neighbour", "b", 3, "b"),
        ("swap", "a", 2, "a"),
        ("reverse", "a", 2, "a"),
    ],
)
def test_full_off_hides_one_more_number_on_the_last_task_only(family, moves, size, key):
    """#841: "Vollständig anzeigen" off. The last task of a family loses one more number."""
    shown = generate(Settings(ops=["+"], max=100, family=family, moves=moves, count=4, seed=1))
    hidden = generate(
        Settings(ops=["+"], max=100, family=family, moves=moves, full=False, count=4, seed=1)
    )
    assert shown["loosen"] is None and hidden["loosen"] is None
    same = [(e["op"], e["a"], e["b"], e["result"]) for e in shown["exercises"]]
    assert [(e["op"], e["a"], e["b"], e["result"]) for e in hidden["exercises"]] == same
    fams = grouped(hidden["exercises"])
    assert len(fams) == 4 and all(len(f) == size for f in fams)
    for fam in fams:
        assert all("also" not in e for e in fam[:-1])
        assert fam[-1]["also"] == key
        assert "hide" not in fam[-1]


def test_a_gap_already_on_that_number_hides_the_other_one():
    """#841: the Lücke already hides the growing number, so the other number is the extra one."""
    out = generate(
        Settings(
            ops=["+"],
            max=100,
            format="gap",
            gaps=["a"],
            family="analogy",
            full=False,
            count=3,
            seed=1,
        )
    )
    fams = grouped(out["exercises"])
    assert fams
    for fam in fams:
        assert fam[-1]["hide"] == "a"
        assert fam[-1]["also"] == "b"
        assert all("also" not in e for e in fam[:-1])


def test_the_panel_grows_analogieaufgaben_and_hides_the_last_number(editor):
    """#841: the panel offers Analogieaufgaben. Off, the last task of a package has two gaps."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=4, seed=1)
    page = editor(box("m", "maths", props, y=20, h=80), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    fam = panel.get_by_label("Aufgabenfamilien", exact=True)
    expect(fam.locator("option")).to_have_text(
        ["Keine", "Tauschaufgaben", "Umkehraufgaben", "Nachbaraufgaben", "Analogieaufgaben"]
    )
    whole = panel.get_by_role("button", name="Vollständig anzeigen", exact=True)
    expect(whole).to_have_count(0)
    pick_family(page, "Analogieaufgaben")
    expect(at(page, "m").locator(FAMILY_ROW)).to_have_count(4)
    expect(whole).to_have_attribute("aria-pressed", "true")
    expect(panel.get_by_role("button", name="1. Zahl wächst")).to_have_attribute(
        "aria-pressed", "true"
    )
    fams = families(page, client)
    assert len(fams) == 4 and all(len(f) == 3 for f in fams)
    for (a, _, b, _), (a2, _, b2, _), (a3, _, b3, _) in fams:
        assert b == b2 == b3
        assert int(a2) - int(a) == 10 and int(a3) - int(a2) == 10
    assert all("also" not in e for e in saved(page, client))
    # One gap each, the result. The last task of a package then loses its first number too.
    rows = at(page, "m").locator(FAMILY_ROW).first.locator(":scope > div")
    expect(rows).to_have_count(3)
    expect(rows.nth(0).locator("u")).to_have_count(1)
    shown = at(page, "m").locator(".maths").inner_text()
    whole.click()
    expect(whole).to_have_attribute("aria-pressed", "false")
    expect(at(page, "m").locator(".maths")).not_to_have_text(shown)
    rows = at(page, "m").locator(FAMILY_ROW).first.locator(":scope > div")
    expect(rows.nth(0).locator("u")).to_have_count(1)
    expect(rows.nth(1).locator("u")).to_have_count(1)
    expect(rows.nth(2).locator("u")).to_have_count(2)
    last = grouped(saved(page, client))
    assert all(f[-1]["also"] == "a" and "also" not in f[0] and "also" not in f[1] for f in last)
    shown = at(page, "m").locator(".maths").inner_text()
    panel.get_by_role("button", name="2. Zahl wächst").click()
    expect(panel.get_by_role("button", name="2. Zahl wächst")).to_have_attribute(
        "aria-pressed", "true"
    )
    expect(at(page, "m").locator(".maths")).not_to_have_text(shown)
    grown = families(page, client)
    assert len(grown) == 4 and all(len(f) == 3 for f in grown)
    for (a, _, b, _), (a2, _, b2, _), (a3, _, b3, _) in grown:
        assert a == a2 == a3
        assert int(b2) - int(b) == 10 and int(b3) - int(b2) == 10
    assert all(f[-1].get("also") == "b" for f in grouped(saved(page, client)))
