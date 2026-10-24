"""A clash stands until the teacher has chosen (issue #345), and a kept change goes only when its
owner's own session learns that the sheet is gone (issue #346).

In a clash the server holds another device's version, and nothing is sent over it: not after a
reload, a second or a third, not by a tab that shuts, a retry, the app's start or a second tab.
The browser's record keeps the version the change was made on, so each visit reads the clash
anew. And a record is one account's: a 404 that another account's session got says nothing
about the owner's sheet.

Built on test_saves.py: the sheet A, its gate, and a clock that stands until a test lets it run
for a reload or a new tab. The clash comes about in two ways: `left`, a change kept by a tab that
shut, which the next visit finds changed elsewhere, and `clash`, a save turned down in the window.

The docstrings name the lines of the checklist.
"""

# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

from contextlib import contextmanager

import pytest
from playwright.sync_api import expect
from test_loading import READY
from test_saves import (
    CHOICES,
    LEFT,
    elsewhere,
    nudge,
    record,
    shut,
    start,
    unsaved,
)
from test_stale import STATUS, TURNS
from ui import at

from blattwerk import sheets

LOAD, OVER = CHOICES
SAYS = "Dieses Blatt wurde in einem anderen Fenster oder auf einem anderen Gerät geändert."
LISTED = "„a“ wurde auf einem anderen Gerät geändert. Öffne das Blatt, um zu wählen."
WAITS = unsaved("a", "Melde dich neu an, dann wird sie gespeichert.")
# Notes from here on whether the page said that the sheet is not there, for however short a time.
WATCH = """() => {
    window.missing = false;
    new MutationObserver(() => {
        const said = [...document.querySelectorAll('h1')].map((h) => h.textContent);
        if (said.includes('Blatt nicht gefunden')) window.missing = true;
    }).observe(document, { subtree: true, childList: true });
}"""
# Waits until the browser's record of the sheet holds the block at that x.
KEEPS = """([id, x]) => {
    const kept = JSON.parse(localStorage.getItem('unsaved:' + id));
    return kept?.doc.pages[0].blocks[0].x === x;
}"""
DROPPED = "(id) => localStorage.getItem('unsaved:' + id) === null"


def left(run):
    """A is changed here, the tab shuts with the change kept and unsent, and another device
    moves the block to 40. Gives where the block showed here, and the sheet as the other device
    left it."""
    page, _ = start(run)
    nudge(run)
    moved = at(page, "a").evaluate(LEFT)
    shut(page, 1)
    return moved, elsewhere(run, 40)


def safe(run, page, sent, theirs, n=0, x=16, base=None):
    """Nothing went over the other device's sheet: `n` saves were sent so far and none more, the
    server holds the other device's sheet, and the browser the kept change with the version it
    was made on."""
    page.evaluate(TURNS)
    assert len(sent) == n
    assert run.held("a") == theirs
    kept = record(page, run.ids["a"])
    assert kept["doc"]["pages"][0]["blocks"][0]["x"] == x
    assert kept["base"] == (base or theirs["version"] - 1)


def stands(run, page, sent, theirs, moved, **more):
    """The clash stands on the page: the banner with both choices, the kept change in the
    editor, the status that says it is not saved, and all of `safe`."""
    expect(page.locator(READY)).to_be_visible(timeout=10000)
    banner = page.locator(".clash")
    expect(banner).to_contain_text(SAYS)
    for name in CHOICES:
        expect(banner.get_by_role("button", name=name)).to_be_enabled()
    expect(banner).not_to_contain_text("Lädt …")
    expect(at(page, "a")).to_have_css("left", moved)
    expect(page.locator(STATUS)).to_have_text("Nicht gespeichert")
    safe(run, page, sent, theirs, **more)


def swap(page, server, client):
    """The browser's session becomes the client's, as a login in another tab does it: this
    tab hears nothing of it."""
    page.context.clear_cookies()
    page.context.add_cookies(
        [{"name": "session", "value": client.cookies["session"], "url": server}]
    )


@contextmanager
def reached():
    """Gives the saves of a document that reach the server meanwhile, whoever sent them: one
    sent as a tab goes passes no route and no listener of the test."""
    came, real = [], sheets.touch_stored

    def count(con, sheet_id, user):
        came.append(sheet_id)
        real(con, sheet_id, user)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sheets, "touch_stored", count)
        yield came


def x_at(client, sheet_id):
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"][0]["x"]


def loads_of(page, gate):
    """The loads of the gate's sheet that the page asks for, from here on."""
    loads = []
    page.on("request", lambda r: gate.asks("GET")(r) and loads.append(r))
    return loads
