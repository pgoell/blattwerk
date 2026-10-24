"""A press that changes nothing leaves redo, a later drag and the save alone."""

import re

import pytest
from playwright.sync_api import expect
from test_undo_same import ACTIVE, GUARDED, field, opened, steps, work
from ui import FIELD, RECT, RULING, TEXT, at, box, centre, drag, pick


def reach(page, control):
    """Takes the focus to a control of the panel as the keys do: F6 to the panel, then Tab."""
    for _ in range(6):
        if page.evaluate("!!document.activeElement.closest('.panel')"):
            break
        page.keyboard.press("F6")
    for _ in range(150):
        if control.evaluate(ACTIVE):
            return
        page.keyboard.press("Tab")
    raise AssertionError("Tab never came to the control")


# Asked #238, A2


def test_seitenbreite_and_bis_seitenende_twice_are_one_step_each(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    undo = page.get_by_label("Rückgängig", exact=True)
    pick(page, "lines")
    for name, label, was, now in (
        ("Seitenbreite", "Breite", "80", "180"),
        ("Bis Seitenende", "Höhe", "20", "230"),
    ):
        for _ in range(2):
            page.get_by_role("button", name=name).click()
            expect(field(page, label)).to_have_value(now)
        page.keyboard.press("Control+z")
        expect(field(page, label)).to_have_value(was)
        expect(undo).to_be_disabled()


# Implied #238, I1


def test_a_press_that_changes_nothing_keeps_redo(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    wide = page.get_by_role("button", name="Seitenbreite")
    pick(page, "lines")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    wide.click()
    expect(field(page, "Breite")).to_have_value("180")
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    # Nothing to change: the block has no number, and lies where it lies.
    page.get_by_role("button", name="Keine", exact=True).click()
    work(page, "same", "Art der Lineatur")
    work(page, "type", "X")
    expect(page.get_by_label("Wiederholen", exact=True)).to_be_enabled()
    page.keyboard.press("Control+y")
    expect(field(page, "Y")).to_have_value("51")
    page.keyboard.press("Control+y")
    expect(field(page, "Breite")).to_have_value("180")
    expect(page.get_by_label("Wiederholen", exact=True)).to_be_disabled()


# Implied #238, I2


def test_a_list_that_asks_for_nothing_new_swallows_no_step(editor):
    page = editor(box("a", "ruling", RULING))
    kind, undo = field(page, "Art der Lineatur"), page.get_by_label("Rückgängig", exact=True)
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("51")
    # The list opened by a press, left on the kind it shows, and then walked by the keys with no
    # press between: the new kind is a step of its own, not a part of the move before it.
    kind.dispatch_event("pointerdown")
    kind.select_option("l4")
    kind.select_option("l3")
    expect(field(page, "Höhe")).to_have_value("23")
    undo.click()
    expect(kind).to_have_value("l4")
    expect(field(page, "Höhe")).to_have_value("20")
    expect(field(page, "Y")).to_have_value("51")
    undo.click()
    expect(field(page, "Y")).to_have_value("50")
    expect(undo).to_be_disabled()


def test_a_drag_after_a_press_that_changes_nothing_is_one_step_of_its_own(editor):
    page = editor(box("a", "text", TEXT, x=0))
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    page.locator(".panel").get_by_role("button", name="Links", exact=True).nth(1).click()
    x, y = centre(at(page, "a"))
    drag(page, (x, y), (x + 40, y + 60), (x + 80, y + 120))
    expect(field(page, "Y")).not_to_have_value("51")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("51")
    expect(field(page, "X")).to_have_value("0")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_nudge_after_a_press_that_changes_nothing_is_its_own_step(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    # No press of the mouse comes between: the button is pressed as the keys press it.
    page.locator(".panel").get_by_role("button", name="Keine", exact=True).dispatch_event("click")
    page.keyboard.press("ArrowDown")
    expect(field(page, "Y")).to_have_value("52")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("51")
    page.keyboard.press("Control+z")
    expect(field(page, "Y")).to_have_value("50")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


@pytest.mark.parametrize("kind, how, label, nth", GUARDED)
def test_a_control_that_finds_nothing_to_change_ends_a_run_of_nudges(editor, kind, how, label, nth):
    page = opened(editor, kind)
    y, undo = field(page, "Y"), page.get_by_label("Rückgängig", exact=True)
    panel = page.locator(".panel")
    page.keyboard.press("ArrowDown")
    expect(y).to_have_value("1")
    # By the mouse: its press ends the run.
    work(page, how, label, nth)
    if how == "type":
        # A number's field has the keys: a press on the empty page gives them back.
        page.locator(".sheet").first.click(position={"x": 400, "y": 400})
        at(page, "a").click()
    page.keyboard.press("ArrowDown")
    expect(y).to_have_value("2")
    # By the keys alone, with no press of the mouse.
    if how == "type":
        number = field(page, label)
        reach(page, number)
        page.keyboard.type(number.input_value())
        page.keyboard.press("Enter")
        # F6 walks on from the panel to the sheet.
        page.keyboard.press("F6")
        expect(page.locator("body")).to_be_focused()
    else:
        # The button for crop mode has another name while the mode is on.
        name = re.compile("^(Zuschneiden|Fertig)$") if how == "twice" else label
        button = panel.get_by_role("button", name=name, exact=True).nth(nth)
        reach(page, button)
        page.keyboard.press("Space")
        if how == "twice":
            expect(button).to_have_text("Fertig")
            page.keyboard.press("Space")
            expect(button).to_have_text("Zuschneiden")
    # The button keeps the focus, and the arrows are still the block's.
    page.keyboard.press("ArrowDown")
    expect(y).to_have_value("3")
    page.keyboard.press("ArrowDown")
    expect(y).to_have_value("4")
    # The two nudges after the control are one step, and each one before it is its own.
    for was in ("2", "1", "0"):
        expect(undo).to_be_enabled()
        undo.click()
        expect(y).to_have_value(was)
    expect(undo).to_be_disabled()


# Implied #238, I3


def test_several_blocks_changed_in_part_are_one_step_and_none_changed_is_none(editor):
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", {**TEXT, "align": "right"}, z=2),
        box("c", "shape", RECT, z=3),
    )
    panel = page.locator(".panel")
    left = panel.get_by_role("button", name="Links", exact=True).first
    top = panel.get_by_role("button", name="Oben", exact=True).first
    pick(page, "a", "b", "c")
    left.click()
    expect(at(page, "b").locator(".frame")).to_have_css("text-align", "left")
    assert steps(page) == 1
    left.click()
    # A text stands at the top and a shape's words in its middle: "Oben" changes the shape alone.
    top.click()
    assert steps(page) == 2
    top.click()
    panel.get_by_role("button", name="Eckig", exact=True).click()
    assert steps(page) == 2
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect(at(page, "b").locator(".frame")).to_have_css("text-align", "right")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Implied #238, I4


@pytest.mark.parametrize(
    "how, label, nth",
    [
        ("same", "Schriftart", 0),
        ("press", "Links", 0),
        ("press", "Oben", 0),
        ("press", "Eckig", 0),
        ("press", "Keine", 0),
    ],
)
def test_a_press_that_changes_nothing_while_a_text_is_written_keeps_the_caret(
    editor, how, label, nth
):
    page = editor(box("a", "text", TEXT))
    words = page.locator(FIELD)
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    # The "l" is typed last, so the field knows where the caret is.
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("l")
    expect(words).to_have_text("Halllo")
    work(page, how, label, nth)
    expect(words).to_be_focused()
    page.keyboard.type("x")
    expect(words).to_have_text("Hallxlo")
    # A letter before the press and one after it: two steps, and the press is none.
    page.keyboard.press("Control+z")
    expect(words).to_have_text("Halllo")
    page.keyboard.press("Control+z")
    expect(words).to_have_text("Hallo")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Implied #238, I5


def test_a_press_that_changes_nothing_measures_no_text(editor):
    # Both texts are higher than their boxes, as a sheet made elsewhere can hold them.
    tall = {**TEXT, "text": "eins\nzwei\ndrei\nvier"}
    page = editor(box("a", "text", tall, h=5), box("b", "text", tall, z=2, h=5))
    pick(page, "a")
    page.locator(".panel").get_by_role("button", name="Links", exact=True).first.click()
    # The next drawing, of another selection, grows neither.
    pick(page, "b")
    expect(field(page, "Höhe")).to_have_value("5")
    pick(page, "a")
    expect(field(page, "Höhe")).to_have_value("5")
    assert page.locator("header [role=status]").inner_text() == "Gespeichert"
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_a_press_that_changes_nothing_sends_no_save(editor):
    page = editor(box("lines", "ruling", RULING, x=40, w=80))
    status = page.locator("header [role=status]")
    sent = []
    page.on("request", lambda r: r.method != "GET" and sent.append(r.url))
    save = "**/api/sheets/*"
    pick(page, "lines")
    with page.expect_response(save):
        page.get_by_role("button", name="Seitenbreite").click()
        expect(status).to_have_text("Speichert …")
    expect(status).to_have_text("Gespeichert")
    assert len(sent) == 1
    for name in ("Seitenbreite", "Keine"):
        page.get_by_role("button", name=name, exact=True).click()
        # At once, with no wait: the sheet was never anything else.
        assert status.inner_text() == "Gespeichert"
    # A change after them is the next thing sent: no save of theirs came in between.
    with page.expect_response(save):
        page.keyboard.press("ArrowDown")
    expect(status).to_have_text("Gespeichert")
    assert len(sent) == 2
