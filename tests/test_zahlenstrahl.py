"""The Zahlenstrahl: its format panel.

The docstrings name what each test proves. The drawing is tested with the model.
"""

import itertools
import re

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, pick, user

STRAHL = {
    "start": 0,
    "end": 20,
    "minor": 1,
    "major": 5,
    "labels": "major",
    "size": 12,
    "cut": False,
    "tasks": "random",
    "boxes": 3,
    "arrows": 0,
    "jumps": False,
    "seed": 7,
}


def zs(name, props, w=180):
    """A Zahlenstrahl block of w by 40 mm."""
    return box(name, "zahlenstrahl", props, w=w, h=40)


def props_of(stored):
    """The props of the one Zahlenstrahl of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "zahlenstrahl"]
    return block["props"]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def hint(page):
    return page.locator(".panel p.hint[role=status]")


@pytest.mark.parametrize(
    "key, before, after, act",
    [
        ("end", 20, 50, lambda p: field(p, "Ende").fill("50")),
        ("minor", 1, 2, lambda p: field(p, "Schritt kleine Striche").fill("2")),
        ("major", 5, 10, lambda p: field(p, "Schritt lange Striche").fill("10")),
        ("labels", "major", "all", lambda p: field(p, "Zahlen").select_option("all")),
        ("size", 12, 14, lambda p: field(p, "Schriftgröße").fill("14")),
        ("cut", False, True, lambda p: field(p, "Bruchstelle").check()),
        ("tasks", "random", "free", lambda p: field(p, "Aufgaben").select_option("free")),
        ("boxes", 3, 4, lambda p: panel(p, "Ein Kästchen mehr").click()),
        ("arrows", 0, 1, lambda p: panel(p, "Ein Pfeil mehr").click()),
        ("jumps", False, True, lambda p: field(p, "Sprungbögen").check()),
    ],
    ids=[
        "ende",
        "kleine",
        "lange",
        "zahlen",
        "groesse",
        "bruch",
        "aufgaben",
        "kaestchen",
        "pfeil",
        "sprung",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, before, after, act):
    """A1/A14: each setting stores its prop; Ctrl+Z brings the old value, Ctrl+Y the new."""
    client = user()
    page = editor(zs("z", {**STRAHL, "start": 5}), client=client)
    pick(page, "z")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_typing_340_into_anfang_is_one_undo_step(editor):
    """A2/A14: 340 typed digit by digit is one step; one Ctrl+Z brings back 0."""
    client = user()
    page = editor(zs("z", {**STRAHL, "end": 1000}), client=client)
    pick(page, "z")
    number = field(page, "Anfang")
    step(page, lambda: (number.press("Control+a"), number.press_sequentially("340")))
    assert props_of(doc(page, client))["start"] == 340
    undo(page)
    assert props_of(doc(page, client))["start"] == 0


def test_an_anfang_past_the_ende_takes_the_ende_along(editor):
    """A2: 340 typed into the Anfang of a line 0 to 20 gives 340 to 360, one undo step; the field
    has its name beside it."""
    client = user()
    page = editor(zs("z", STRAHL), client=client)
    pick(page, "z")
    expect(page.locator(".panel label", has_text="Anfang")).to_have_count(1)
    number = field(page, "Anfang")
    step(page, lambda: (number.press("Control+a"), number.press_sequentially("340")))
    stored = props_of(doc(page, client))
    assert (stored["start"], stored["end"]) == (340, 360)
    undo(page)
    stored = props_of(doc(page, client))
    assert (stored["start"], stored["end"]) == (0, 20)


def test_bruchstelle_is_disabled_at_start_zero(editor):
    """A3: with Anfang at 0 the Bruchstelle box cannot be ticked."""
    page = editor(zs("z", STRAHL))
    pick(page, "z")
    expect(field(page, "Bruchstelle")).to_be_disabled()


def test_a_tick_cycles_none_box_arrow_and_stores_marks(editor):
    """A6: a click on Strich 3 cycles none, box, arrow, none; the marks follow."""
    client = user()
    page = editor(
        zs("z", {**STRAHL, "tasks": "free", "boxes": 0, "end": 5, "marks": [[3, "box"]]}),
        client=client,
    )
    pick(page, "z")
    tick = panel(page, "Strich 3")
    expect(tick).to_have_attribute("data-task", "box")
    step(page, tick.click)
    assert props_of(doc(page, client))["marks"] == [[3, "arrow"]]
    expect(tick).to_have_attribute("data-task", "arrow")
    expect(tick).to_have_attribute("aria-pressed", "true")
    step(page, tick.click)
    assert 3 not in [m[0] for m in props_of(doc(page, client)).get("marks", [])]
    expect(tick).not_to_have_attribute("data-task", "box")


@pytest.mark.parametrize(
    "setting, label",
    [
        ({"boxes": 0}, "Ein Kästchen weniger"),
        ({"boxes": 12}, "Ein Kästchen mehr"),
        ({"arrows": 0}, "Ein Pfeil weniger"),
        ({"arrows": 6}, "Ein Pfeil mehr"),
    ],
)
def test_the_counts_stop_at_their_limits(editor, setting, label):
    """A7: the box count stops at 0 and 12, the arrow count at 0 and 6."""
    page = editor(zs("z", {**STRAHL, **setting}))
    pick(page, "z")
    expect(panel(page, label)).to_be_disabled()


def test_neu_wuerfeln_stores_another_seed_and_keeps_the_rest(editor):
    """A8: "Neu würfeln" stores another seed, keeps the other props; undo brings the old seed."""
    client = user()
    page = editor(zs("z", STRAHL), client=client)
    pick(page, "z")
    before = props_of(doc(page, client))
    step(page, lambda: panel(page, "Neu würfeln").click())
    after = props_of(doc(page, client))
    assert after["seed"] != STRAHL["seed"]
    assert {k: v for k, v in after.items() if k != "seed"} == {
        k: v for k, v in before.items() if k != "seed"
    }
    undo(page)
    assert props_of(doc(page, client))["seed"] == STRAHL["seed"]


def test_the_warning_comes_with_a_tiny_step_and_goes_with_a_bigger_one(editor):
    """A9: 1001 ticks on 180 mm warn; a step of 10 gives 101 ticks and no warning."""
    client = user()
    page = editor(zs("z", {**STRAHL, "end": 1000, "major": 100}), client=client)
    pick(page, "z")
    expect(hint(page)).to_have_text(
        "Die Striche stehen enger als 1 mm. Größerer Schritt oder breiterer Block."
    )
    step(page, lambda: field(page, "Schritt kleine Striche").fill("10"))
    expect(hint(page)).to_have_count(0)


def test_arc_labels_are_stored_and_empty_text_stores_null(editor):
    """A12: "Bogen 1" stores its text; an emptied "Bogen 2" stores null."""
    client = user()
    page = editor(zs("z", {**STRAHL, "jumps": True, "arcs": ["Sprung", "+5"]}), client=client)
    pick(page, "z")
    step(page, lambda: field(page, "Bogen 1").fill("Hopp"))
    assert props_of(doc(page, client))["arcs"][0] == "Hopp"
    step(page, lambda: field(page, "Bogen 2").fill(""))
    assert props_of(doc(page, client))["arcs"][1] is None


def test_a_label_of_an_arc_a_shorter_line_hides_stays(editor):
    """Found by the review of #570: on 0 to 25 two of five arcs show; typing into "Bogen 1" kept
    only the labels of the arcs shown, so the fifth was lost when the line grew back."""
    client = user()
    labels = ["a", None, None, None, "fünf"]
    short = {**STRAHL, "end": 25, "jumps": True, "jump": 10, "arcs": labels}
    page = editor(zs("z", short), client=client)
    pick(page, "z")
    step(page, lambda: field(page, "Bogen 1").fill("b"))
    assert props_of(doc(page, client))["arcs"] == ["b", None, None, None, "fünf"]


def test_a_small_step_that_breaks_the_long_step_stores_the_long_step_shown(editor):
    """Found by the review of #570: small step 10 under a long step 5 showed 50 long in the panel
    but kept 5 stored."""
    client = user()
    page = editor(zs("z", {**STRAHL, "end": 100}), client=client)
    pick(page, "z")
    number = field(page, "Schritt kleine Striche")
    step(page, lambda: (number.press("Control+a"), number.press_sequentially("10")))
    stored = props_of(doc(page, client))
    assert (stored["minor"], stored["major"]) == (10, 50)
    expect(field(page, "Schritt lange Striche")).to_have_value("50")


def test_more_than_200_ticks_show_a_hint_instead_of_the_buttons(editor):
    """Own case: 300 ticks in "Selbst wählen" give a hint and no "Strich" buttons."""
    page = editor(zs("z", {**STRAHL, "tasks": "free", "end": 300}))
    pick(page, "z")
    # The review of #570: this counted the 1 mm warning, not the hint of its own.
    expect(page.locator(".panel p.hint[data-hint=many]")).to_have_text(re.compile("Mehr als 200"))
    expect(page.locator(".panel").get_by_role("button", name="Strich 1", exact=True)).to_have_count(
        0
    )


def test_a_sprungweite_that_is_no_multiple_of_minor_is_not_applied(editor):
    """Own case: with Schritt kleine Striche 2, a Sprungweite of 3 is refused; the field keeps 3."""
    client = user()
    page = editor(zs("z", {**STRAHL, "minor": 2, "major": 10, "jumps": True}), client=client)
    pick(page, "z")
    jump = field(page, "Sprungweite")
    jump.press("Control+a")
    jump.press_sequentially("3")
    expect(jump).to_have_value("3")
    # The editor saves 1.1 s after a change; a refused number saves nothing, so wait that out.
    page.wait_for_timeout(2000)
    assert "jump" not in props_of(doc(page, client))


def test_the_boxes_of_the_issues_line_do_not_overlap_on_the_page(editor):
    """#593: 180 by 40 mm, 0 to 1000 step 10, seed 123: no two boxes overlap on the page."""
    client = user()
    block = zs("z", {**STRAHL, "end": 1000, "minor": 10, "major": 100, "seed": 123})
    page = editor(block, client=client)
    pick(page, "z")
    rects = page.locator(".zahlenstrahl g.box rect")
    expect(rects.first).to_be_visible()
    boxes = [rects.nth(i).bounding_box() for i in range(rects.count())]
    spans = sorted((b["x"], b["x"] + b["width"]) for b in boxes)
    assert spans
    for (_, left_end), (right_start, _) in itertools.pairwise(spans):
        assert right_start >= left_end - 0.5, spans
