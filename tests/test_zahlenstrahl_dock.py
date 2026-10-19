"""The dock's "Mathe-Blöcke" menu: one button for the maths blocks, and the dock keeps one row."""

import pytest
from playwright.sync_api import expect
from ui import doc, insert, user

ROWS = """() => new Set([...document.querySelectorAll(".stage .dock .ib")]
    .map((el) => Math.round(el.getBoundingClientRect().top))).size"""


ZAHLENSTRAHL = {
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
}


@pytest.mark.parametrize(
    "label, kind, defaults",
    [
        (
            "Zahlenmauer",
            "zahlenmauer",
            {
                "base": 3,
                "count": 4,
                "columns": 2,
                "max": 20,
                "op": "+",
                "given": "base",
                "empty": False,
            },
        ),
        (
            "Zahlenhaus",
            "zahlenhaus",
            {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side"},
        ),
        (
            "Zahlenkette",
            "zahlenkette",
            {
                "count": 4,
                "columns": 2,
                "rings": 6,
                "max": 20,
                "op": "+",
                "showStep": False,
                "given": "start",
            },
        ),
        (
            "Pfeilbild",
            "pfeilbild",
            {
                "count": 4,
                "columns": 2,
                "boxes": 4,
                "max": 20,
                "ops": ["+", "-"],
                "arrows": "one",
                "given": "start",
                "drawOps": True,
            },
        ),
        (
            "Operatorfeld",
            "operatorfeld",
            {
                "centre": False,
                "count": 2,
                "columns": 2,
                "boxes": 4,
                "max": 20,
                "ops": ["+", "-"],
                "only": "none",
                "given": "start",
                "drawOps": True,
            },
        ),
        (
            "Rechendreieck",
            "rechendreieck",
            {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False},
        ),
        ("Zahlenstrahl", "zahlenstrahl", ZAHLENSTRAHL),
        (
            "Hunderterfeld",
            "hunderterfeld",
            {
                "look": "tafel",
                "from": 1,
                "show": "all",
                "hide": 20,
                "tint": "none",
                "times": 2,
                "line": 1,
                "color": 1,
                "cut": False,
                "shape": [34, 43, 44, 45, 54],
                "given": 44,
                "fill": "count",
                "dots": 0,
            },
        ),
        (
            "Uhr",
            "uhr",
            {
                "numbers": "all",
                "minutes": True,
                "ring": False,
                "task": "read",
                "answer": "box",
                "format": "12",
                "region": "nach",
                "count": 4,
                "cols": 4,
                "step": 15,
                "fill": "random",
            },
        ),
        (
            "Selbstkontrolle",
            "selbstkontrolle",
            {
                "form": "mixed",
                "links": [],
                "word": "",
                "title": "Selbstkontrolle",
                "size": 14,
                "turn": "none",
            },
        ),
    ],
)
def test_the_menu_adds_each_maths_block_with_its_default_props(editor, label, kind, defaults):
    """Z1: each item of "Mathe-Blöcke" adds its block with the default props and a whole seed."""
    client = user()
    page = editor(client=client)
    insert(page, label)
    expect(page.locator(".panel").get_by_role("heading", name=label, exact=True)).to_be_visible()
    [block] = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == kind]
    props = block["props"]
    assert isinstance(props["seed"], int)
    assert {k: v for k, v in props.items() if k != "seed"} == defaults


def test_escape_shuts_the_maths_menu_and_adds_nothing(editor):
    """Escape shuts "Mathe-Blöcke" and the sheet keeps no block."""
    client = user()
    page = editor(client=client)
    page.locator(".dock, .insert").get_by_label("Mathe-Blöcke", exact=True).click()
    expect(page.locator("dialog.menu")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("dialog.menu")).not_to_be_visible()
    assert doc(page, client)["pages"][0]["blocks"] == []


def test_the_dock_keeps_one_row_in_a_desktop_window(editor):
    """The dock's tools stand in one row at 1400 px, with the maths group under one button."""
    page = editor(client=user())
    page.set_viewport_size({"width": 1400, "height": 1000})
    expect(page.locator(".stage .dock .ib").first).to_be_visible()
    assert page.evaluate(ROWS) == 1
