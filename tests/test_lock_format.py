"""A locked block takes a format, and its box follows where the content needs it, as in PowerPoint:
a lock stops what is aimed at the block's place and size, not a format. The edge the block starts
at stays. A sheet laid on its side brings a locked block back onto the page as any other.

The docstrings name the lines of issue #323's checklist.
"""

import pytest
from playwright.sync_api import expect
from test_grow_turned import LONG, stays
from test_height_turned import kept, ruling, sums
from test_lock import KINDS, button, fest, grab, opened, undo
from test_painter import paint
from ui import RECT, RULING, TABLE, TEXT, box, doc, expect_picked, maths, pick, user

# The kinds that hold words.
WORDY = ["text", "shape", "table", "group"]
# Where "fest" lies as `box` makes it, but 60 mm wide: the long words need three lines there.
NARROW = {"w": 60}


def redo(page):
    return page.get_by_label("Wiederholen", exact=True)


def named(sheet, n=0):
    """The blocks of page `n` of the sheet, by their names."""
    return {b["id"]: b for b in sheet["pages"][n]["blocks"]}


def place(b):
    return b["x"], b["y"], b["w"]


def one_step(page, client, before, after):
    """I1: one undo gives the sheet as it was, lock and all, and redo the sheet as it became."""
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before
    redo(page).click()
    expect(redo(page)).to_be_disabled()
    assert doc(page, client) == after


def wordy(client, kind, **more):
    """A locked block "fest" of the kind with long words in it; a group has the free "frei" too."""
    table = {**TABLE, "cells": [[LONG["text"], "Z"], ["3", "7"]]}
    props = {"text": LONG, "group": LONG, "shape": {**RECT, "text": LONG["text"]}, "table": table}
    group = {"group": ["g"]} if kind == "group" else {}
    held = "text" if kind == "group" else kind
    made = [box("fest", held, props[kind], locked=True, **NARROW, **group, **more)]
    return [*made, *([box("frei", "text", TEXT, z=2, **group)] if group else [])]


def size(b):
    return b["props"].get("size", 14)


@pytest.mark.parametrize("degrees", [0, 30])
def test_a_locked_lineatur_takes_another_kind_and_its_height_follows(editor, degrees):
    """B1, I1, I2: the rows stay as many, and the edge it starts at stays."""
    client = user()
    was = {**ruling(degrees), "locked": True}
    page = editor(was, client=client)
    before = doc(page, client)
    pick(page, "a")
    button(page, "Art der Lineatur").select_option("l2")
    expect(undo(page)).to_be_enabled()
    after = doc(page, client)
    a = named(after)["a"]
    # Two rows as before, each 16 mm high now.
    assert (a["props"]["kind"], a["h"], a["locked"]) == ("l2", 32, True)
    assert kept(a, was)
    assert degrees or place(a) == place(was)
    one_step(page, client, before, after)


@pytest.mark.parametrize("degrees", [0, 30])
@pytest.mark.parametrize(
    "change", ["Eine Aufgabe mehr", "Eine Spalte weniger", "Schrift größer", "Schriftlich"]
)
def test_a_locked_maths_block_takes_a_setting_and_its_height_follows(editor, change, degrees):
    """B2, I1, I2"""
    client = user()
    was = {**sums(client, degrees), "locked": True}
    page = editor(was, client=client)
    before = doc(page, client)
    pick(page, "a")
    page.locator(".panel").get_by_role("button", name=change, exact=True).click()
    # The exercises come from the server.
    expect(undo(page)).to_be_enabled()
    after = doc(page, client)
    a = named(after)["a"]
    assert a["props"] != was["props"]
    assert a["h"] > 12
    assert a["locked"]
    assert kept(a, was)
    assert degrees or place(a) == place(was)
    one_step(page, client, before, after)


@pytest.mark.parametrize("kind", WORDY)
def test_a_larger_font_grows_a_locked_box_with_its_words(editor, kind):
    """B3, I1, I2: each click is one step, of the font and of the box it grew."""
    client = user()
    page = editor(*wordy(client, kind), client=client)
    steps = [doc(page, client)]
    grab(page, kind)
    for _ in range(2):
        button(page, "Schrift größer").click()
        steps.append(doc(page, client))
    was, now = named(steps[0])["fest"], named(steps[2])["fest"]
    assert (size(now), now["locked"]) == (18, True)
    assert now["h"] > was["h"]
    assert place(now) == place(was)
    # It never shrinks by itself.
    assert named(steps[1])["fest"]["h"] >= was["h"]
    for step in (steps[1], steps[0]):
        undo(page).click()
        assert doc(page, client) == step
    expect(undo(page)).to_be_disabled()
    for step in (steps[1], steps[2]):
        redo(page).click()
        assert doc(page, client) == step
    expect(redo(page)).to_be_disabled()


@pytest.mark.parametrize("kind", ["text", "shape"])
def test_a_larger_font_grows_a_turned_locked_box_from_the_edge_its_words_start_at(editor, kind):
    """B3, I2"""
    client = user()
    (was,) = wordy(client, kind, x=75, y=100, angle=90)
    page = editor(was, client=client)
    grab(page, kind)
    for _ in range(2):
        button(page, "Schrift größer").click()
    a = named(doc(page, client))["fest"]
    assert (size(a), a["w"], a["angle"], a["locked"]) == (18, 60, 90, True)
    assert a["h"] > 25
    assert stays(a, was)


def lay_on(page, client, road, kind):
    """Lays the look of the free "a" on the locked "fest", by the brush or by the keys."""
    if road == "brush":
        paint(page, "a", "fest")
    else:
        pick(page, "a")
        page.keyboard.press("Control+Shift+C")
        grab(page, kind)
        page.keyboard.press("Control+Shift+V")
        expect_picked(page, "fest")
    expect(undo(page)).to_be_enabled()
    return doc(page, client)


@pytest.mark.parametrize("road", ["brush", "keys"])
def test_format_uebertragen_gives_a_locked_maths_block_its_height(editor, road):
    """B4, I1, I2"""
    client = user()
    source = box("a", "maths", maths(client, size=28), z=4, h=24)
    target = box("fest", "maths", maths(client, seed=8), h=12, locked=True)
    page = editor(source, target, client=client)
    before = doc(page, client)
    after = lay_on(page, client, road, "maths")
    was, now = named(before)["fest"], named(after)["fest"]
    assert (now["props"]["size"], now["h"], now["locked"]) == (28, 24, True)
    assert place(now) == place(was)
    one_step(page, client, before, after)


@pytest.mark.parametrize("road", ["brush", "keys"])
@pytest.mark.parametrize("kind", ["text", "shape", "table"])
def test_format_uebertragen_grows_a_locked_box_with_its_words(editor, kind, road):
    """B4, I1, I2: a bigger font from another block."""
    client = user()
    source = box("a", "text", {**TEXT, "size": 28}, z=4)
    page = editor(source, *wordy(client, kind), client=client)
    before = doc(page, client)
    after = lay_on(page, client, road, kind)
    was, now = named(before)["fest"], named(after)["fest"]
    assert (size(now), now["locked"]) == (28, True)
    assert now["h"] > was["h"]
    assert place(now) == place(was)
    one_step(page, client, before, after)


def on_page(b, w, h):
    return b["x"] >= 0 and b["y"] >= 0 and b["x"] + b["w"] <= w and b["y"] + b["h"] <= h


@pytest.mark.parametrize("kind", KINDS)
def test_quer_and_hoch_bring_a_locked_block_back_onto_the_page(editor, kind):
    """B5, I4: one near the bottom edge when the sheet is laid on its side, and one near the right
    edge of a page that lay so when the sheet stands upright again."""
    client = user()
    low = [{**b, "y": 265} for b in fest(client, kind)]
    # The second page lies on its side by itself, so its block can lie right of an upright page.
    far = [{**b, "x": 200, "w": 80, "y": 100} for b in fest(client, kind)]
    page = editor(*low, client=client, pages=[{"blocks": far, "landscape": True}])
    before = doc(page, client)
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    panel.get_by_role("button", name="Quer", exact=True).click()
    expect(undo(page)).to_be_enabled()
    quer = doc(page, client)
    assert all(on_page(b, 297, 210) for b in quer["pages"][0]["blocks"])
    # Every page follows the sheet, and the second is as wide as it was.
    assert quer["pages"][1]["blocks"] == before["pages"][1]["blocks"]
    panel.get_by_role("button", name="Hoch", exact=True).click()
    hoch = doc(page, client)
    assert all(on_page(b, 210, 297) for b in hoch["pages"][1]["blocks"])
    assert hoch["pages"][0]["blocks"] == quer["pages"][0]["blocks"]
    # As any other block: no farther than onto the page, and along the one side only.
    down, right = named(quer)["fest"], named(hoch, 1)["fest"]
    assert down["locked"] and right["locked"]
    assert (down["x"], down["y"]) == (15, 190)
    assert (right["x"], right["y"]) == (130, 100)
    # Undo puts each back where it lay.
    undo(page).click()
    assert doc(page, client) == quer
    undo(page).click()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before


def test_a_larger_font_goes_to_a_locked_and_a_free_text_and_both_grow(editor):
    """I3"""
    client = user()
    page = editor(*wordy(client, "text"), box("los", "text", LONG, z=4, **NARROW), client=client)
    before = doc(page, client)
    grab(page, "text", "los")
    for _ in range(2):
        button(page, "Schrift größer").click()
    now = named(doc(page, client))
    for name in ("fest", "los"):
        assert size(now[name]) == 18
        assert now[name]["h"] > 25
        assert place(now[name]) == place(named(before)[name])
    assert now["fest"]["h"] == now["los"]["h"]
    assert (now["fest"]["locked"], now["los"]["locked"]) == (True, False)


def test_another_kind_goes_to_a_locked_and_a_free_lineatur_and_both_follow(editor):
    """I1, I3"""
    client = user()
    blocks = [box("fest", "ruling", RULING, locked=True), box("los", "ruling", RULING, z=4)]
    page = editor(*blocks, client=client)
    before = doc(page, client)
    grab(page, "ruling", "los")
    button(page, "Art der Lineatur").select_option("l2")
    expect(undo(page)).to_be_enabled()
    after = doc(page, client)
    now = named(after)
    for name in ("fest", "los"):
        assert (now[name]["props"]["kind"], now[name]["h"]) == ("l2", 32)
        assert place(now[name]) == place(named(before)[name])
    assert (now["fest"]["locked"], now["los"]["locked"]) == (True, False)
    one_step(page, client, before, after)


def test_a_locked_lineatur_keeps_what_sizes_it_off_and_its_kind_on(editor):
    """I5"""
    page, client, before = opened(editor, "ruling")
    grab(page, "ruling")
    for label in ("Eine Zeile mehr", "Eine Zeile weniger"):
        expect(button(page, label)).to_be_disabled()
    for name in ("Seitenbreite", "Bis Seitenende"):
        expect(page.locator(".panel").get_by_role("button", name=name)).to_be_disabled()
    expect(button(page, "Art der Lineatur")).to_be_enabled()
    expect(undo(page)).to_be_disabled()
    assert doc(page, client) == before
