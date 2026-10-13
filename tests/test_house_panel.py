"""The house and the band of a Lineatur in the format panel: the controls, the drawing, the undo
steps, the keys, the brush, and what is saved and copied."""

import pytest
from playwright.sync_api import expect
from test_painter import paint
from test_undo_steps import gesture
from ui import BROWSER, RULING, at, box, doc, pick, reload, user

L1 = {**RULING, "kind": "l1"}
L3 = {**RULING, "kind": "l3"}
SHOWN = ["l1", "l2", "l3"]
HIDDEN = ["l4", "lines", "k5"]


def house(page):
    return page.locator(".panel").get_by_role("button", name="Häuschen", exact=True)


def band(page):
    return page.locator(".panel").get_by_role("button", name="Mittelband einfärben", exact=True)


def tint(page):
    return page.locator(".panel").get_by_label("Häuschen einfärben", exact=True)


def band_colour(page):
    return page.locator(".panel").get_by_label("Farbe des Mittelbands", exact=True)


def kind(page):
    return page.locator(".panel").get_by_label("Art der Lineatur", exact=True)


def undo(page):
    return page.get_by_label("Rückgängig", exact=True)


def redo(page):
    return page.get_by_label("Wiederholen", exact=True)


def fills(scope, css, attr="fill"):
    """The value of `attr` on each element of `css` in the block, as a set."""
    got = scope.locator(css).evaluate_all(f"els => els.map((el) => el.getAttribute('{attr}'))")
    return set(got)


def expect_drawn(scope, css, value, attr="fill"):
    """Waits until the first such element has the value, then checks that every one has it."""
    expect(scope.locator(css).first).to_have_attribute(attr, value)
    assert fills(scope, css, attr) == {value}


def focused(page):
    """The label of the control that has the focus: its aria-label, else the text of its label."""
    return page.evaluate(
        "() => { const el = document.activeElement; const label = el.labels?.[0];"
        " return el.getAttribute('aria-label') ?? (label ? label.textContent.trim()"
        " : el.textContent.trim()); }"
    )


@pytest.mark.parametrize("kind", SHOWN)
def test_a1_the_panel_shows_house_and_band_for_l1_l2_and_l3(editor, kind):
    """A1"""
    page = editor(box("a", "ruling", {**RULING, "kind": kind}))
    pick(page, "a")
    expect(house(page)).to_be_visible()
    expect(band(page)).to_be_visible()


@pytest.mark.parametrize("kind", HIDDEN)
def test_a1_the_panel_shows_no_house_or_band_for_other_kinds(editor, kind):
    """A1"""
    page = editor(box("a", "ruling", {**RULING, "kind": kind}))
    pick(page, "a")
    # The section is drawn once its last control, the width, is there.
    expect(
        page.locator(".panel").get_by_role("button", name="Seitenbreite", exact=True)
    ).to_be_visible()
    expect(house(page)).to_have_count(0)
    expect(tint(page)).to_have_count(0)
    expect(band(page)).to_have_count(0)
    expect(band_colour(page)).to_have_count(0)


def test_a1_a_press_on_haeuschen_draws_the_house_and_takes_it_away_again(editor):
    """A1"""
    page = editor(box("a", "ruling", L1))
    pick(page, "a")
    house(page).click()
    expect(house(page)).to_have_attribute("aria-pressed", "true")
    expect(at(page, "a").locator("g.house").first).to_be_attached()
    house(page).click()
    expect(house(page)).to_have_attribute("aria-pressed", "false")
    expect(at(page, "a").locator("g.house")).to_have_count(0)


def test_a5_the_tint_shows_only_while_the_house_is_on_and_fills_its_parts(editor):
    """A5"""
    page = editor(box("a", "ruling", L1))
    block = at(page, "a")
    pick(page, "a")
    expect(house(page)).to_have_attribute("aria-pressed", "false")
    expect(tint(page)).to_have_count(0)
    house(page).click()
    expect(tint(page)).to_be_visible()
    tint(page).select_option("room")
    expect_drawn(block, "rect.room", "#fcefb4")
    assert fills(block, "polygon.roof") == {"none"}
    assert fills(block, "rect.cellar") == {"none"}
    tint(page).select_option("all")
    expect_drawn(block, "rect.room", "#fcefb4")
    expect_drawn(block, "polygon.roof", "#f6c4bd")
    expect_drawn(block, "rect.cellar", "#d9cdbd")
    tint(page).select_option("none")
    expect_drawn(block, "rect.room", "none")
    assert fills(block, "polygon.roof") == {"none"}
    assert fills(block, "rect.cellar") == {"none"}
    house(page).click()
    expect(tint(page)).to_have_count(0)


@pytest.mark.parametrize("kind, pressed", [("l1", "true"), ("l2", "true"), ("l3", "false")])
def test_a6_the_band_is_pressed_by_default_for_l1_and_l2_only(editor, kind, pressed):
    """A6"""
    page = editor(box("a", "ruling", {**RULING, "kind": kind}))
    pick(page, "a")
    expect(band(page)).to_have_attribute("aria-pressed", pressed)


def test_a6_a_press_on_the_band_of_an_l1_removes_every_band(editor):
    """A6"""
    page = editor(box("a", "ruling", L1))
    pick(page, "a")
    expect(at(page, "a").locator("rect.band").first).to_be_attached()
    band(page).click()
    expect(band(page)).to_have_attribute("aria-pressed", "false")
    expect(at(page, "a").locator("rect.band")).to_have_count(0)


def test_a6_a_press_on_the_band_of_an_l3_adds_the_bands(editor):
    """A6"""
    page = editor(box("a", "ruling", L3))
    pick(page, "a")
    expect(at(page, "a").locator("rect.band")).to_have_count(0)
    band(page).click()
    expect(band(page)).to_have_attribute("aria-pressed", "true")
    expect(at(page, "a").locator("rect.band").first).to_be_attached()


def test_a7_the_band_colour_shows_the_line_colour_at_12_percent_and_takes_a_colour(editor):
    """A7"""
    page = editor(box("a", "ruling", {**RULING, "kind": "l1", "color": "#555555"}))
    block = at(page, "a")
    pick(page, "a")
    expect(band_colour(page)).to_have_value("#ebebeb")
    band_colour(page).fill("#ffe066")
    expect_drawn(block, "rect.band", "#ffe066")
    expect_drawn(block, "rect.band", "1", "fill-opacity")
    band(page).click()
    expect(band_colour(page)).to_have_count(0)
    expect(block.locator("rect.band")).to_have_count(0)


def test_a9_a_press_on_haeuschen_is_one_undo_step_and_comes_back_with_redo(editor):
    """A9"""
    page = editor(box("a", "ruling", L1))
    block = at(page, "a")
    pick(page, "a")
    house(page).click()
    expect(block.locator("g.house").first).to_be_attached()
    page.keyboard.press("Control+z")
    expect(block.locator("g.house")).to_have_count(0)
    expect(undo(page)).to_be_disabled()
    page.keyboard.press("Control+y")
    expect(block.locator("g.house").first).to_be_attached()
    expect(redo(page)).to_be_disabled()


def test_a9_a_choice_in_the_tint_is_one_undo_step_and_comes_back_with_redo(editor):
    """A9"""
    page = editor(box("a", "ruling", {**L1, "house": True}))
    block = at(page, "a")
    pick(page, "a")
    tint(page).select_option("all")
    expect_drawn(block, "polygon.roof", "#f6c4bd")
    undo(page).click()
    expect_drawn(block, "rect.room", "none")
    assert fills(block, "polygon.roof") == {"none"}
    expect(undo(page)).to_be_disabled()
    redo(page).click()
    expect_drawn(block, "polygon.roof", "#f6c4bd")
    expect(redo(page)).to_be_disabled()


def test_a9_a_press_on_the_band_is_one_undo_step_and_comes_back_with_redo(editor):
    """A9"""
    page = editor(box("a", "ruling", L1))
    block = at(page, "a")
    pick(page, "a")
    band(page).click()
    expect(block.locator("rect.band")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(block.locator("rect.band").first).to_be_attached()
    expect(undo(page)).to_be_disabled()
    page.keyboard.press("Control+y")
    expect(block.locator("rect.band")).to_have_count(0)
    expect(redo(page)).to_be_disabled()


def test_a9_a_band_colour_dragged_over_the_picker_is_one_undo_step(editor):
    """A9"""
    page = editor(box("a", "ruling", L1))
    block = at(page, "a")
    pick(page, "a")
    gesture(page, "Farbe des Mittelbands", 1, 2)
    expect_drawn(block, "rect.band", "#00ff00")
    undo(page).click()
    expect_drawn(block, "rect.band", "#222222")
    expect_drawn(block, "rect.band", "0.12", "fill-opacity")
    expect(undo(page)).to_be_disabled()
    redo(page).click()
    expect_drawn(block, "rect.band", "#00ff00")
    expect(redo(page)).to_be_disabled()


def test_i1_haeuschen_on_two_lineaturen_is_one_undo_step_for_both(editor):
    """I1"""
    page = editor(box("a", "ruling", L1), box("b", "ruling", {**RULING, "kind": "l2"}, z=2))
    pick(page, "a", "b")
    house(page).click()
    for name in ("a", "b"):
        expect(at(page, name).locator("g.house").first).to_be_attached()
    page.keyboard.press("Control+z")
    for name in ("a", "b"):
        expect(at(page, name).locator("g.house")).to_have_count(0)
    expect(undo(page)).to_be_disabled()


def test_i1_the_band_press_and_its_colour_on_two_lineaturen_are_one_step_each(editor):
    """I1"""
    page = editor(box("a", "ruling", L1), box("b", "ruling", {**RULING, "kind": "l2"}, z=2))
    pick(page, "a", "b")
    band(page).click()
    for name in ("a", "b"):
        expect(at(page, name).locator("rect.band")).to_have_count(0)
    page.keyboard.press("Control+z")
    for name in ("a", "b"):
        expect(at(page, name).locator("rect.band").first).to_be_attached()
    expect(undo(page)).to_be_disabled()
    gesture(page, "Farbe des Mittelbands", 1, 2)
    for name in ("a", "b"):
        expect_drawn(at(page, name), "rect.band", "#00ff00")
    undo(page).click()
    for name in ("a", "b"):
        expect_drawn(at(page, name), "rect.band", "#222222")
    expect(undo(page)).to_be_disabled()


def test_i2_a_press_on_haeuschen_keeps_the_open_lineatur_open_with_its_words(editor):
    """I2"""
    page = editor(box("a", "ruling", L1))
    written = at(page, "a").locator("textarea.written")
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Maus")
    house(page).click()
    expect(at(page, "a").locator("g.house").first).to_be_attached()
    expect(written).to_be_editable()
    expect(written).to_have_value("Maus")
    # As after any press on a panel button, the caret is back in the Lineatur.
    expect(written).to_be_focused()
    page.keyboard.type("e")
    expect(written).to_have_value("Mause")


def test_i3_tab_from_the_colour_reaches_the_house_controls_in_order_and_space_toggles(editor):
    """I3"""
    page = editor(box("a", "ruling", {**L1, "house": True}))
    pick(page, "a")
    page.locator(".panel").get_by_label("Farbe", exact=True).focus()
    for _ in range(60):
        if focused(page) == "Häuschen":
            break
        page.keyboard.press("Tab")
    else:
        raise AssertionError("Tab never came to Häuschen")
    # WebKit's Tab stops at no colour field, the Lineatur's own "Farbe" neither.
    stops = ["Häuschen einfärben", "Mittelband einfärben", "Farbe des Mittelbands", "Seitenbreite"]
    stops = [stop for stop in stops if BROWSER != "webkit" or not stop.startswith("Farbe")]
    walked = []
    for _ in stops:
        page.keyboard.press("Tab")
        walked.append(focused(page))
    assert walked == stops
    # Back to the house, and Space on it.
    for _ in range(60):
        if focused(page) == "Häuschen":
            break
        page.keyboard.press("Shift+Tab")
    expect(house(page)).to_be_focused()
    page.keyboard.press("Space")
    expect(house(page)).to_have_attribute("aria-pressed", "false")
    expect(house(page)).to_be_focused()
    expect(at(page, "a").locator("g.house")).to_have_count(0)


def test_i4_a_change_to_l3_takes_the_band_default_and_back_to_l1_brings_it(editor):
    """I4"""
    page = editor(box("a", "ruling", L1))
    block = at(page, "a")
    pick(page, "a")
    kind(page).select_option("l3")
    expect(band(page)).to_have_attribute("aria-pressed", "false")
    expect(block.locator("rect.band")).to_have_count(0)
    kind(page).select_option("l1")
    expect(band(page)).to_have_attribute("aria-pressed", "true")
    expect(block.locator("rect.band").first).to_be_attached()


def test_i4_a_band_switched_off_by_hand_stays_off_after_l3_and_back(editor):
    """I4"""
    page = editor(box("a", "ruling", {**L1, "band": False}))
    block = at(page, "a")
    pick(page, "a")
    expect(band(page)).to_have_attribute("aria-pressed", "false")
    kind(page).select_option("l3")
    expect(kind(page)).to_have_value("l3")
    expect(band(page)).to_have_attribute("aria-pressed", "false")
    expect(block.locator("rect.band")).to_have_count(0)
    kind(page).select_option("l1")
    expect(kind(page)).to_have_value("l1")
    expect(band(page)).to_have_attribute("aria-pressed", "false")
    expect(block.locator("rect.band")).to_have_count(0)


def test_i4_a_house_is_gone_on_l4_and_back_on_l1(editor):
    """I4"""
    page = editor(box("a", "ruling", {**L1, "house": True}))
    block = at(page, "a")
    pick(page, "a")
    expect(block.locator("g.house").first).to_be_attached()
    kind(page).select_option("l4")
    expect(house(page)).to_have_count(0)
    expect(block.locator("g.house")).to_have_count(0)
    kind(page).select_option("l1")
    expect(house(page)).to_have_attribute("aria-pressed", "true")
    expect(block.locator("g.house").first).to_be_attached()


def test_i5_the_brush_carries_the_house_and_its_tints_and_takes_the_band_off(editor):
    """I5"""
    page = editor(
        box("a", "ruling", {**L1, "house": True, "houseTint": "all", "band": False}),
        box("b", "ruling", L1, z=2),
    )
    paint(page, "a", "b")
    block = at(page, "b")
    expect_drawn(block, "rect.room", "#fcefb4")
    expect_drawn(block, "polygon.roof", "#f6c4bd")
    expect_drawn(block, "rect.cellar", "#d9cdbd")
    expect(block.locator("rect.band")).to_have_count(0)


def test_i5_the_brush_carries_the_band_colour(editor):
    """I5"""
    page = editor(
        box("a", "ruling", {**RULING, "kind": "l2", "bandColor": "#ffe066"}),
        box("b", "ruling", L1, z=2),
    )
    paint(page, "a", "b")
    expect_drawn(at(page, "b"), "rect.band", "#ffe066")


def test_i6_house_band_and_colour_survive_a_reload_and_a_copy(editor):
    """I6"""
    client = user()
    page = editor(box("a", "ruling", L1), client=client)
    pick(page, "a")
    house(page).click()
    tint(page).select_option("all")
    band(page).click()
    band(page).click()
    band_colour(page).fill("#ffe066")
    props = doc(page, client)["pages"][0]["blocks"][0]["props"]
    assert {key: props[key] for key in ("house", "houseTint", "band", "bandColor")} == {
        "house": True,
        "houseTint": "all",
        "band": True,
        "bandColor": "#ffe066",
    }
    reload(page, page.url)
    block = at(page, "a")
    expect_drawn(block, "rect.room", "#fcefb4")
    expect_drawn(block, "rect.cellar", "#d9cdbd")
    expect_drawn(block, "rect.band", "#ffe066")
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block")).to_have_count(2)
    pasted = page.locator(".block.sel")
    expect(pasted.locator("g.house").first).to_be_attached()
    expect_drawn(pasted, "rect.room", "#fcefb4")
    expect_drawn(pasted, "rect.cellar", "#d9cdbd")
    expect_drawn(pasted, "rect.band", "#ffe066")
