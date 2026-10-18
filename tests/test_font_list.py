"""The font menus open a list of their own, each name in its own font (#486)."""

import re

import pytest
from playwright.sync_api import expect
from test_school_scripts import expect_family
from ui import FIELD, RULING, TABLE, TEXT, at, box, pick, reload

# The eight fonts of the menus: key, name, family.
FONTS = [
    ("andika", "Druckschrift", "Andika"),
    ("nord", "Druckschrift Nord", "Fibel Nord"),
    ("sued", "Druckschrift Süd", "Fibel Sued"),
    ("grund", "Grundschrift", "Playwrite DE Grund Variable"),
    ("urff", "Grundschrift (Urff)", "Grundschrift Urff"),
    ("va", "Vereinfachte Ausgangsschrift", "Playwrite DE VA Variable"),
    ("sas", "Schulausgangsschrift", "Playwrite DE SAS Variable"),
    ("la", "Lateinische Ausgangsschrift", "Playwrite DE LA Variable"),
]
MENUS = [
    ("text", "Schriftart", TEXT),
    ("table", "Schriftart der Tabelle", TABLE),
    ("ruling", "Schriftart auf den Zeilen", RULING),
]


def open_list(page, label):
    """Opens a font menu with a mouse click, as a teacher does, and gives its list."""
    page.get_by_label(label, exact=True).click()
    return page.get_by_role("listbox", name=f"Liste: {label}")


@pytest.mark.parametrize("kind, label, props", MENUS)
def test_every_name_draws_in_its_own_font_in_the_open_list(editor, kind, label, props):
    """B1: each of the eight names is in the list, in its own family, and that family is loaded."""
    page = editor(box("a", kind, props))
    pick(page, "a")
    options = open_list(page, label).get_by_role("option")
    expect(options).to_have_count(8)
    for i, (_, name, family) in enumerate(FONTS):
        option = options.nth(i)
        expect(option).to_have_text(name)
        expect_family(option, family)
        page.wait_for_function('f => document.fonts.check(`16px "${f}"`)', arg=family)


@pytest.mark.parametrize("kind, label, props", MENUS)
def test_each_name_shows_when_the_font_files_fail(editor, kind, label, props):
    """B2: with the font files aborted, every name still shows: text, width and visible."""
    page = editor(box("a", kind, props))
    page.context.route("**/fonts/**", lambda route: route.abort())
    reload(page, page.url)
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    pick(page, "a")
    options = open_list(page, label).get_by_role("option")
    expect(options).to_have_count(8)
    for i, (_, name, _) in enumerate(FONTS):
        option = options.nth(i)
        expect(option).to_have_text(name)
        expect(option).to_be_visible()
        assert option.bounding_box()["width"] > 0


# Stamps the press on the font menu, and the moment the list holds its eight options, in the page.
TIMER = """() => {
  window.__press = undefined;
  window.__opened = undefined;
  addEventListener("pointerdown", (e) => {
    if (window.__press === undefined && e.target.getAttribute?.("aria-label") === "Schriftart")
      window.__press = performance.now();
  }, true);
  const options = '[role=listbox][aria-label="Liste: Schriftart"] [role=option]';
  new MutationObserver(() => {
    if (window.__opened === undefined && document.querySelectorAll(options).length === 8)
      window.__opened = performance.now();
  }).observe(document.body, { childList: true, subtree: true });
}"""


def test_the_list_opens_within_300_ms(editor):
    """B3: from the click to the list with its eight options, under 300 ms, timed in the page
    so a loaded shard's round trips do not count."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.evaluate(TIMER)
    page.get_by_label("Schriftart", exact=True).click()
    expect(
        page.get_by_role("listbox", name="Liste: Schriftart").get_by_role("option")
    ).to_have_count(8)
    ms = page.evaluate("() => window.__opened - window.__press")
    print(f"B3 list open: {ms:.0f} ms")
    assert ms < 300


def test_arrow_down_on_the_closed_menu_steps_to_the_next_font(editor):
    """I3: ArrowDown on the closed select steps andika to nord, through the same change."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    select.focus()
    select.press("ArrowDown")
    expect(select).to_have_value("nord")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_have_count(0)


def test_escape_shuts_the_list_with_no_change_and_keeps_the_drawer(editor):
    """I3: Escape shuts the open list, the font stays, and the drawer stays open."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    open_list(page, "Schriftart")
    page.keyboard.press("Escape")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_have_count(0)
    expect(select).to_have_value("andika")
    expect(page.locator(".panel")).to_be_visible()


def test_enter_picks_the_highlighted_font(editor):
    """I3: ArrowDown moves the highlight, Enter picks it and shuts the list."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    listbox = open_list(page, "Schriftart")
    expect(listbox).to_be_visible()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(select).to_have_value("nord")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_have_count(0)


def test_tab_shuts_the_list(editor):
    """I3: Tab shuts the open list and leaves the font as it was."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    open_list(page, "Schriftart")
    page.keyboard.press("Tab")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_have_count(0)
    expect(select).to_have_value("andika")


def test_a_letter_still_steps_the_closed_menu(editor):
    """I3: type-ahead on the closed select picks a font whose name starts with the letter."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    select.focus()
    page.keyboard.press("G")
    expect(select).to_have_value("grund")


def test_a_pick_is_one_undo_step_and_focus_stays_on_the_select(editor):
    """I4: a pick in the open list is one undo step, and focus stays on the select."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    undo = page.get_by_label("Rückgängig", exact=True)
    open_list(page, "Schriftart").get_by_role(
        "option", name="Druckschrift Nord", exact=True
    ).click()
    expect(select).to_have_value("nord")
    expect(select).to_be_focused()
    undo.click()
    expect(select).to_have_value("andika")
    expect(undo).to_be_disabled()


def test_a_click_outside_shuts_the_list_with_no_change(editor):
    """I4: a click outside the select and the list shuts it and changes nothing."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    open_list(page, "Schriftart")
    page.get_by_role("heading", name="Schrift", exact=True).click()
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_have_count(0)
    expect(select).to_have_value("andika")


def test_the_list_shows_two_groups_and_the_font_now_set_as_selected(editor):
    """I5: the two group headings show, and the font set is aria-selected."""
    page = editor(box("a", "text", {**TEXT, "font": "nord"}))
    pick(page, "a")
    listbox = open_list(page, "Schriftart")
    expect(listbox.get_by_role("heading", name="Druckschriften")).to_be_visible()
    expect(listbox.get_by_role("heading", name="Grund- und Schreibschriften")).to_be_visible()
    expect(listbox.get_by_role("option", name="Druckschrift Nord", exact=True)).to_have_attribute(
        "aria-selected", "true"
    )
    expect(listbox.get_by_role("option", name="Druckschrift", exact=True)).to_have_attribute(
        "aria-selected", "false"
    )


def test_a_pick_sets_both_picked_texts(editor):
    """I6: two texts with different fonts picked: a pick from the list sets both."""
    page = editor(
        box("a", "text", {**TEXT, "font": "andika"}),
        box("b", "text", {**TEXT, "font": "sued"}, z=2),
    )
    pick(page, "a", "b")
    open_list(page, "Schriftart").get_by_role("option", name="Grundschrift", exact=True).click()
    expect(at(page, "a").get_by_text("Hallo").first).to_have_css(
        "font-family", re.compile("Playwrite DE Grund")
    )
    expect(at(page, "b").get_by_text("Hallo").first).to_have_css(
        "font-family", re.compile("Playwrite DE Grund")
    )


def test_space_on_the_closed_menu_opens_the_list_and_keeps_the_focus(editor):
    """Space opens the list, the select keeps the focus, and ArrowDown with Enter picks nord."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    select.focus()
    page.keyboard.press("Space")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_be_visible()
    expect(select).to_be_focused()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(select).to_have_value("nord")


def test_enter_on_the_closed_menu_gives_the_keys_back(editor):
    """Enter on the closed menu opens no list and gives the keys back, as before."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    select.focus()
    page.keyboard.press("Enter")
    expect(select).not_to_be_focused()
    expect(page.get_by_role("listbox")).to_have_count(0)
    expect(select).to_have_value("andika")


def test_home_and_end_with_the_list_open_move_the_highlight(editor):
    """End moves the highlight to the last font and Home to the first; Enter picks it."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    listbox = open_list(page, "Schriftart")
    page.keyboard.press("End")
    expect(listbox.locator(".hi")).to_have_text("Lateinische Ausgangsschrift")
    page.keyboard.press("Home")
    expect(listbox.locator(".hi")).to_have_text("Druckschrift")
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    expect(select).to_have_value("la")


def test_a_letter_with_the_list_open_moves_the_highlight_and_keeps_the_font(editor):
    """A mouse-opened list takes "g": the focus stays, the value does not change, and Enter picks
    the first G font, as one undo step."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    select = page.get_by_label("Schriftart", exact=True)
    undo = page.get_by_label("Rückgängig", exact=True)
    listbox = open_list(page, "Schriftart")
    page.keyboard.press("g")
    expect(select).to_be_focused()
    expect(select).to_have_value("andika")
    expect(listbox.get_by_role("option", name="Grundschrift", exact=True)).to_have_class(
        re.compile("hi")
    )
    page.keyboard.press("Enter")
    expect(select).to_have_value("grund")
    undo.click()
    expect(select).to_have_value("andika")
    expect(undo).to_be_disabled()


def test_a_letter_with_the_list_open_over_a_text_leaves_the_text(editor):
    """With a text open for typing, the mouse opens the list and "g" changes no word of it."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    open_list(page, "Schriftart")
    page.keyboard.press("g")
    expect(page.get_by_role("listbox", name="Liste: Schriftart")).to_be_visible()
    expect(page.locator(FIELD)).to_have_text("Hallo")


@pytest.mark.parametrize("dx, opens", [(0, True), (40, False)])
def test_a_tap_opens_the_list_and_a_swipe_from_the_select_does_not(editor, dx, opens):
    """iPad: a tap opens the list, a finger that moves 40 px scrolls the drawer instead."""
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    # WebKit on a desktop has no Touch to build: the test has nothing to send there.
    can_touch = """() => {
        try { new Touch({ identifier: 1, target: document.body }); return true; }
        catch { return false; }
    }"""
    if not page.evaluate(can_touch):
        pytest.skip("this browser cannot build a Touch")
    page.get_by_label("Schriftart", exact=True).evaluate(
        """(el, dx) => {
            const box = el.getBoundingClientRect();
            const x = box.left + box.width / 2;
            const y = box.top + box.height / 2;
            const at = (cx) => new Touch({ identifier: 1, target: el, clientX: cx, clientY: y });
            const a = at(x);
            const b = at(x + dx);
            const init = { bubbles: true, cancelable: true };
            const send = (type, t, touches) =>
                el.dispatchEvent(new TouchEvent(type, { ...init, touches, changedTouches: [t] }));
            send("touchstart", a, [a]);
            send("touchend", b, []);
        }""",
        dx,
    )
    listbox = page.get_by_role("listbox", name="Liste: Schriftart")
    if opens:
        expect(listbox).to_be_visible()
    else:
        expect(listbox).to_have_count(0)
