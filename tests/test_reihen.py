"""Einmaleins-Reihen in the panel, and Geteilt mit Rest (issue #840).

A teacher picks rows 1 to 10, or the Kernaufgaben 1, 2, 5 and 10. The same preset
sits on a Rechentabelle and a Malquadrat. With a remainder, Rest 0 vermeiden keeps
a remainder of 0 out, and the Rest can be the only Lücke.
"""

from playwright.sync_api import expect
from test_compare import changed, ctl
from test_gaps import step
from test_malquadrat import MQ, mq
from test_rechentabelle import RT, rt
from ui import at, box, doc, maths, pick, user

KERN = [1, 2, 5, 10]


def props_of(page, client, name):
    """The block's props as the document holds them."""
    sheet = doc(page, client)
    return next(b["props"] for p in sheet["pages"] for b in p["blocks"] if b["id"] == name)


def test_a_teacher_picks_rows_and_the_kernaufgaben(editor):
    """Kernaufgaben stores 1, 2, 5 and 10, and a further row joins them. Every task stays in them."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["*"], max=100, count=12)), client=client)
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Kernaufgaben").click())
    assert props["reihen"] == KERN
    assert not props.get("small")
    assert all(e["a"] in KERN or e["b"] in KERN for e in props["exercises"])
    assert all(1 <= e["a"] <= 10 and 1 <= e["b"] <= 10 for e in props["exercises"])
    props = changed(page, client, lambda: page.get_by_label("3er-Reihe", exact=True).check())
    assert props["reihen"] == [1, 2, 3, 5, 10]
    assert all(e["a"] in props["reihen"] or e["b"] in props["reihen"] for e in props["exercises"])


def test_avoiding_a_zero_rest_and_allowing_one(editor):
    """Rest 0 vermeiden is on with Mit Rest. Off, an even division may stand among the tasks."""
    client = user()
    made = maths(client, ops=["/"], max=20, count=20, seed=1, rest=True, b=[[2, 4]])
    page = editor(box("m", "maths", made), client=client)
    pick(page, "m")
    expect(ctl(page, "Rest 0 vermeiden")).to_have_attribute("aria-pressed", "true")
    assert all(e["rest"] > 0 for e in made["exercises"])
    props = changed(page, client, lambda: ctl(page, "Rest 0 vermeiden").click())
    assert props["avoid0"] is False
    assert any(e["rest"] == 0 for e in props["exercises"])
    assert any(e["rest"] > 0 for e in props["exercises"])


def test_the_rest_can_be_the_only_gap(editor):
    """Lücke: Rest starts on. With the numbers unticked, only the remainder is a gap."""
    client = user()
    page = editor(
        box(
            "m", "maths", maths(client, ops=["/"], format="gap", rest=True, max=30, count=6, seed=4)
        ),
        client=client,
    )
    pick(page, "m")
    expect(ctl(page, "Lücke: Rest")).to_have_attribute("aria-pressed", "true")
    changed(page, client, lambda: ctl(page, "Lücke: 1. Zahl").click())
    props = changed(page, client, lambda: ctl(page, "Lücke: 2. Zahl").click())
    assert props["gaps"] == ["c", "rest"]
    assert all(e.get("hide") == "rest" and e["rest"] > 0 for e in props["exercises"])
    gaps = at(page, "m").evaluate(
        """(block) => [...block.querySelectorAll(".maths > div")].map((div) => {
            const html = div.innerHTML;
            const at = html.indexOf(" R ");
            return at > 0 && !html.slice(0, at).includes("<u") && html.slice(at).includes("<u");
        })"""
    )
    assert gaps == [True] * len(props["exercises"])


def test_kernaufgaben_sets_the_rows_of_a_table_and_a_square(editor):
    """Kernaufgaben on a Maltabelle and a Malquadrat stores the rows 1, 2, 5 and 10."""
    client = user()
    page = editor(
        rt("t", {**RT, "op": "*"}),
        mq("q", MQ, y=120),
        client=client,
        theme="",
    )
    pick(page, "t")
    step(page, lambda: ctl(page, "Kernaufgaben").click())
    expect(page.get_by_label("1er-Reihe", exact=True)).to_be_checked()
    assert props_of(page, client, "t")["reihen"] == KERN
    pick(page, "q")
    step(page, lambda: ctl(page, "Kernaufgaben").click())
    expect(page.get_by_label("10er-Reihe", exact=True)).to_be_checked()
    assert props_of(page, client, "q")["reihen"] == KERN
