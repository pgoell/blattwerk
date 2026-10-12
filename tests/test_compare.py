"""The comparisons of Vergleichen in a maths block: the two sides and the ring between them, the
settings Seiten, Knapp and Aufgaben mit =, the limits they keep, the answer key, and the layout.

The docstrings name the lines of the checklist that each test proves. A setting that asks the
server is waited for through the save that follows it, so the tests read the props the server holds.
"""

import pytest
from playwright.sync_api import expect
from test_feed_print import pdf_text, printed, sheet_id
from test_fix_mix import key
from test_gaps import step
from test_words import redo, undo
from ui import at, box, maths, pick, saved, tool, user

SIGNS = {"+": "+", "-": "\u2212", "*": "·", "/": ":"}
# Which sides are terms: "nn" has two numbers, "tn" a term and a number, "tt" two terms.
KINDS = {"nn": (False, False), "tn": (True, False), "tt": (True, True)}


def ctl(page, label):
    """A button or a field of the panel, by its name."""
    return page.locator(".panel").get_by_role("button", name=label, exact=True)


def text_of(side):
    """A side as the sheet writes it: a term with its sign, or the number."""
    return f"{side['a']} {SIGNS[side['op']]} {side['b']}" if "op" in side else str(side["value"])


def shown(root):
    """Each task under a block or a print page as its text reads, with the spaces collapsed."""
    return [" ".join(text.split()) for text in root.locator(".maths > div").all_text_contents()]


def changed(page, client, action):
    """Does an action that the editor saves, and gives the block's props once the save is in."""
    action()
    expect(page.locator("header [role=status]")).to_have_text("Speichert …")
    return saved(page, client)[0]["props"]


def test_vergleichen_shows_two_sides_and_a_ring(editor):
    """C1: Vergleichen shows two sides and an empty ring per task, and no = in the text."""
    client = user()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Vergleichen").click())
    block = at(page, "m")
    expect(block.locator(".maths.compare > div")).to_have_count(3)
    expect(block.locator(".maths.compare > div .ring")).to_have_count(3)
    assert all(not ring.text_content() for ring in block.locator(".ring").all())
    expect(block).not_to_contain_text("=")
    assert props["format"] == "compare"
    for e in props["exercises"]:
        assert {"left", "right", "sign"} <= e.keys()


@pytest.mark.parametrize("sides", ["nn", "tn", "tt"])
def test_the_sides_stand_as_set(editor, sides):
    """C2: Seiten sets numbers and terms on each side, and each task reads as its sides do."""
    client = user()
    # The select starts on another value: choosing the same one saves nothing to wait for.
    start = "nn" if sides == "tn" else "tn"
    page = editor(box("m", "maths", maths(client, format="compare", sides=start)), client=client)
    pick(page, "m")
    props = changed(
        page,
        client,
        lambda: page.locator(".panel").get_by_label("Seiten", exact=True).select_option(sides),
    )
    assert props["sides"] == sides
    for e in props["exercises"]:
        assert ("op" in e["left"], "op" in e["right"]) == KINDS[sides]
    assert shown(at(page, "m")) == [
        " ".join(f"{text_of(e['left'])} {text_of(e['right'])}".split()) for e in props["exercises"]
    ]


def test_each_term_keeps_the_limits(editor):
    """C3: Ohne under Übertrag keeps each term in the Zahlenraum, with no carry."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="compare", sides="tt", max=100, count=10)),
        client=client,
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Ohne").click())
    assert props["carry"] == "none"
    terms = [side for e in props["exercises"] for side in (e["left"], e["right"]) if "op" in side]
    assert terms
    for t in terms:
        assert t["a"] <= 100 and t["b"] <= 100 and 0 <= t["value"] <= 100
        if t["op"] == "+":
            assert t["a"] % 10 + t["b"] % 10 < 10 and (t["a"] // 10) % 10 + (t["b"] // 10) % 10 < 10
    props = changed(page, client, lambda: ctl(page, SIGNS["-"]).click())
    assert set(props["ops"]) == {"+", "-"}
    for t in [side for e in props["exercises"] for side in (e["left"], e["right"]) if "op" in side]:
        assert t["op"] in props["ops"]
        assert t["a"] <= 100 and t["b"] <= 100 and 0 <= t["value"] <= 100


def test_knapp_keeps_the_sides_close(editor):
    """C4: Knapp keeps the sides 0, 1, 2, 10 or 20 apart, and 0 only for an = task."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="compare", sides="tn", max=100, count=10)),
        client=client,
    )
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Knapp").click())
    assert props["close"] is True
    expect(ctl(page, "Knapp")).to_have_attribute("aria-pressed", "true")
    for e in props["exercises"]:
        gap = abs(e["left"]["value"] - e["right"]["value"])
        assert gap in {0, 1, 2, 10, 20} and (gap == 0) == (e["sign"] == "=")


def test_the_share_of_equal_tasks_holds(editor):
    """C5: Einige mit = gives two tasks with =, Keine mit = none, and Einige again two."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="compare", sides="tn", max=100, count=10)),
        client=client,
    )
    pick(page, "m")
    assert [e["sign"] for e in saved(page, client)[0]["props"]["exercises"]].count("=") == 2
    props = changed(page, client, lambda: ctl(page, "Keine mit =").click())
    assert [e["sign"] for e in props["exercises"]].count("=") == 0
    props = changed(page, client, lambda: ctl(page, "Einige mit =").click())
    assert [e["sign"] for e in props["exercises"]].count("=") == 2


def test_a_seed_brings_the_same_comparisons_on_every_load(editor):
    """C6: A reload shows the same comparisons, and Neu würfeln brings another seed."""
    client = user()
    page = editor(box("m", "maths", maths(client, format="compare")), client=client)
    expect(at(page, "m").locator(".maths > div")).to_have_count(3)
    before = shown(at(page, "m"))
    assert saved(page, client)[0]["props"]["seed"] == 7
    page.reload()
    expect(at(page, "m").locator(".maths > div")).to_have_count(3)
    assert shown(at(page, "m")) == before
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Neu würfeln").click())
    assert props["seed"] != 7


def test_the_panel_names_what_stands_in_the_way(editor):
    """C6: With no task in the way, the block says so and the panel names Knapp."""
    client = user()
    more = dict(
        format="compare",
        sides="nn",
        max=10,
        count=5,
        close=True,
        equal="none",
        a=[[1, 1], [0, 0]],
        b=[[5, 5], [0, 0]],
    )
    page = editor(box("m", "maths", maths(client, **more)), client=client)
    pick(page, "m")
    expect(at(page, "m").locator(".maths .hint")).to_have_text("Keine Aufgabe möglich")
    expect(page.locator(".panel p.hint[role=status]")).to_contain_text("Knapp")


def test_the_key_prints_the_sign_in_the_ring(editor, browser, server):
    """C7: The pupil's rings are empty, the key writes each sign in red, the PDF follows."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="compare", sides="tn", count=10)), client=client
    )
    pick(page, "m")
    props = saved(page, client)[0]["props"]
    signs = [e["sign"] for e in props["exercises"]]
    pupil = printed(browser, server, sheet_id(page))
    expect(pupil.locator(".maths .ring")).to_have_count(10)
    assert all(not ring.text_content() for ring in pupil.locator(".maths .ring").all())
    pupil.context.close()
    paper = key(browser, server, sheet_id(page))
    expect(paper.locator(".maths .ring")).to_have_text(signs)
    expect(paper.locator(".maths .ring").first).to_have_css("color", "rgb(192, 57, 43)")
    paper.context.close()
    assert any(sign in pdf_text(server, client, sheet_id(page), solved=True) for sign in "<>")
    text = pdf_text(server, client, sheet_id(page), solved=False)
    assert not any(sign in text for sign in "<>=")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "m").locator(".ring")).to_have_text(signs)


def test_columns_size_and_numbering_work_as_for_a_row(editor):
    """C8: A column less makes three lines, size and numbering work; I2: one task more."""
    client = user()
    page = editor(box("m", "maths", maths(client, format="compare", count=6)), client=client)
    pick(page, "m")
    block = at(page, "m")
    grid = block.locator(".maths")
    expect(block.locator(".maths > div")).to_have_count(6)
    assert len(grid.evaluate("el => getComputedStyle(el).gridTemplateColumns").split()) == 3
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
    # Each block's numbering sits lower in the panel too: Aufgaben nummerieren comes first.
    numbering = page.locator(".panel").get_by_role("button", name="1 2 3", exact=True).first
    props = changed(page, client, numbering.click)
    assert props["numbering"] == "1."
    expect(block.locator(".maths > div > b")).to_have_text(
        ["1.", "2.", "3.", "4.", "5.", "6.", "7."]
    )


def test_each_setting_undoes_and_redoes(editor):
    """C9: Each setting undoes to what was before and redoes to what came after."""
    client = user()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    actions = [
        lambda: ctl(page, "Vergleichen").click(),
        lambda: page.locator(".panel").get_by_label("Seiten", exact=True).select_option("tt"),
        lambda: ctl(page, "Knapp").click(),
        lambda: ctl(page, "Keine mit =").click(),
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


def test_the_pdf_shows_the_same_comparisons_as_the_editor(editor, browser, server):
    """C9: The texts of the tasks on the print page are those of the editor."""
    client = user()
    page = editor(
        box("m", "maths", maths(client, format="compare", sides="tn", count=10)), client=client
    )
    pick(page, "m")
    expect(at(page, "m").locator(".maths > div")).to_have_count(10)
    paper = printed(browser, server, sheet_id(page))
    expect(paper.locator(".maths > div")).to_have_count(10)
    assert shown(paper) == shown(at(page, "m"))
    paper.context.close()


def test_back_to_zeile_the_row_tasks_come_back(editor):
    """I1: Zeile brings back the row's tasks, with the same ops, max, digits and carry."""
    client = user()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    first = saved(page, client)[0]["props"]
    changed(page, client, lambda: ctl(page, "Vergleichen").click())
    props = changed(page, client, lambda: ctl(page, "Zeile").click())
    assert props["exercises"] == first["exercises"]
    assert all(props[name] == first[name] for name in ("ops", "max", "a", "b", "carry"))


def test_the_new_settings_show_only_under_vergleichen(editor):
    """I3: Seiten, Knapp and Keine mit = show only under Vergleichen, and Mit Rest hides there."""
    client = user()
    page = editor(box("m", "maths", maths(client, ops=["/"])), client=client)
    pick(page, "m")
    panel = page.locator(".panel")
    expect(panel.get_by_role("button", name="Mit Rest", exact=True)).to_be_visible()
    expect(panel.get_by_label("Seiten", exact=True)).to_have_count(0)
    expect(ctl(page, "Knapp")).to_have_count(0)
    expect(ctl(page, "Keine mit =")).to_have_count(0)
    changed(page, client, lambda: ctl(page, "Vergleichen").click())
    expect(panel.get_by_label("Seiten", exact=True)).to_be_visible()
    expect(ctl(page, "Knapp")).to_be_visible()
    expect(ctl(page, "Keine mit =")).to_be_visible()
    expect(ctl(page, "Mit Rest")).to_have_count(0)


def test_a_block_saved_before_opens_and_rolls_as_before(editor):
    """I5: A row saved with no sides opens and rolls as a row; Vergleichen fills the defaults."""
    client = user()
    page = editor(box("m", "maths", maths(client)), client=client)
    pick(page, "m")
    props = changed(page, client, lambda: ctl(page, "Neu würfeln").click())
    expect(at(page, "m").locator(".maths.row > div")).to_have_count(3)
    assert props["format"] == "row" and all("sign" not in e for e in props["exercises"])
    props = changed(page, client, lambda: ctl(page, "Vergleichen").click())
    expect(at(page, "m").locator(".maths.compare > div")).to_have_count(3)
    assert all("sign" in e for e in props["exercises"])
