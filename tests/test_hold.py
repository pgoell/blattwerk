"""A finger held on blocks that are already selected: Moveable's box lies over them."""

import pytest
from playwright.sync_api import expect
from test_menu import several, spot
from ui import TEXT, at, box, centre, expect_picked, finger, jitter, outlast

OPEN = ".ProseMirror, .block textarea:not([readonly]), .crop"
NAMES = {"one": "a", "group": "ab", "several": "ab"}


def chosen(editor, kind):
    """The texts selected by taps, with Mehrere off: "a", or "a" and "b" as a group or several."""
    group = {"group": ["g"]} if kind == "group" else {}
    names = NAMES[kind]
    page = editor(
        *(box(n, "text", TEXT, z=z + 1, **group) for z, n in enumerate(names)), touch=True
    )
    if kind == "several":
        several(page).tap()
        at(page, "b").tap()
    at(page, "a").tap()
    expect_picked(page, *names)
    if kind == "several":
        several(page).tap()
    expect(several(page)).to_have_attribute("aria-pressed", "false")
    return page


def where(page, on):
    """The middle of the block "a", or of the gap between the two blocks."""
    x, y = centre(at(page, "a"))
    return (x, (y + centre(at(page, "b"))[1]) / 2) if on == "gap" else (x, y)


# A finger never rests still, but Chrome keeps its small moves from the page: both are a hold.
@pytest.mark.parametrize("by", [(), ((3, 0), (0, 4))], ids=["still", "jitter"])
@pytest.mark.parametrize(
    ("kind", "on"),
    [
        ("group", "block"),
        ("group", "gap"),
        ("several", "block"),
        ("several", "gap"),
        ("one", "block"),
    ],
)
def test_a_finger_held_on_what_is_selected_starts_selecting_several(editor, kind, on, by):
    """#200"""
    page = chosen(editor, kind)
    names = NAMES[kind]
    before = [spot(page, name) for name in names]
    start = where(page, on)
    with finger(page, start):
        jitter(at(page, "a"), start, *by)
        expect(several(page)).to_have_attribute("aria-pressed", "true")
        expect_picked(page, *names)
    # The lift is no tap: it takes no block out of the selection and opens none.
    expect(several(page)).to_have_attribute("aria-pressed", "true")
    expect_picked(page, *names)
    expect(page.locator(OPEN)).to_have_count(0)
    assert [spot(page, name) for name in names] == before
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    # The next tap is one again: with Mehrere on it takes its block out, a group as a whole.
    page.touchscreen.tap(*centre(at(page, names[-1])))
    expect_picked(page, *("a" if kind == "several" else ""))


@pytest.mark.parametrize("kind", ["group", "several"])
def test_a_finger_that_moves_away_on_what_is_selected_drags_it(editor, kind):
    """#200"""
    page = chosen(editor, kind)
    before = [spot(page, name) for name in "ab"]
    start = centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (0, 9), (0, 14))
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        assert all(spot(page, name) != was for name, was in zip("ab", before, strict=True))
    expect(several(page)).to_have_attribute("aria-pressed", "false")
    expect_picked(page, "a", "b")
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
