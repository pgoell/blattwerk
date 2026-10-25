"""A turned group sized in the panel shows the size typed, after a size handle drag (#678)."""

import pytest
from playwright.sync_api import expect
from test_fields import enter, field, number
from test_group_scale_turned import SHAPES, turned_group
from ui import BROWSER, centre, drag, user


def drag_se_outward(page):
    """Drags the lower right size handle a little outward, on the screen."""
    x, y = centre(page.locator(".sheet i.end").nth(3))
    drag(page, (x, y), (x + 10, y + 10), (x + 20, y + 20))


@pytest.mark.parametrize(
    "field_name, typed, shown",
    [
        ("Breite", "80", "80"),
        ("Höhe", "50", "50"),
        ("Breite", "9 cm", "90"),
        ("Breite", "4,5cm", "45"),
    ],
)
def test_typed_size_after_a_handle_drag_shows_what_was_typed(editor, field_name, typed, shown):
    page = turned_group(editor, user(), *SHAPES)
    drag_se_outward(page)
    enter(page, field_name, typed)
    expect(field(page, field_name)).to_have_value(shown)


@pytest.mark.parametrize("angle", ["30", "45"])
def test_breite_then_hoehe_after_a_handle_drag_both_show_what_was_typed(editor, angle):
    """The steps of #678: Breite 80, then Höhe 50; Breite still shows 80."""
    page = turned_group(editor, user(), *SHAPES)
    enter(page, "Drehung", angle)
    expect(field(page, "Drehung")).to_have_value(angle)
    drag_se_outward(page)
    enter(page, "Breite", "80")
    enter(page, "Höhe", "50")
    expect(field(page, "Höhe")).to_have_value("50")
    expect(field(page, "Breite")).to_have_value("80")


# Holds React's scheduler, which posts its work through a MessageChannel, until `free` is called:
# so the end of a drag lands late, as it does under load in CI (#727).
HOLD = """() => {
  const post = MessagePort.prototype.postMessage, held = [];
  MessagePort.prototype.postMessage = function (...a) { held.push(() => post.apply(this, a)); };
  window.free = () => new Promise((done) => {
    MessagePort.prototype.postMessage = post;
    held.splice(0).forEach((go) => go());
    const tick = new MessageChannel();
    tick.port1.onmessage = done;
    tick.port2.postMessage(0);
  });
}"""

# React's scheduler 100 ms late, as a loaded runner may make it.
LATE = """() => {
  const post = MessagePort.prototype.postMessage;
  MessagePort.prototype.postMessage = function (...a) {
    setTimeout(() => post.apply(this, a), 100);
  };
}"""
# One trip through a MessageChannel: it comes after the scheduler's task posted before it.
TICK = """() => new Promise((done) => {
  const c = new MessageChannel();
  c.port1.onmessage = done;
  c.port2.postMessage(0);
})"""


def settled(page, label):
    """What the field shows once the drag's last step is on the screen: React's scheduler
    carries it in a task of its own, after the mouse is up (#727). It holds still over one tick."""
    before, now = None, number(page, label)
    while now != before:
        page.evaluate(TICK)
        before, now = now, number(page, label)
    return now


def test_a_size_typed_before_a_late_drag_end_lands_is_kept(editor):
    """A size typed while the drag's last step is on its way counts on Enter, as typed."""
    page = turned_group(editor, user(), *SHAPES)
    page.evaluate(HOLD)
    drag_se_outward(page)
    field(page, "Breite").fill("80")
    page.evaluate("free()")
    expect(field(page, "Breite")).to_have_value("80")
    field(page, "Breite").press("Enter")
    expect(field(page, "Breite")).to_have_value("80")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite")).to_have_value("40")


@pytest.mark.parametrize(
    "field_name, typed, shown",
    [("Breite", "9 cm", "90"), ("Höhe", "50", "50")],
)
def test_a_size_typed_after_a_late_drag_end_replaces_the_shown_size(
    editor, field_name, typed, shown
):
    """The drag's last step lands after the field took the focus and selected its text (#922): what is typed
    takes the place of the size the field shows then, and is not put behind it (691,49 for 9 cm in CI)."""
    page = turned_group(editor, user(), *SHAPES)
    page.evaluate(HOLD)
    drag_se_outward(page)
    field(page, field_name).focus()
    page.evaluate("free()")
    page.keyboard.type(typed)
    page.keyboard.press("Enter")
    expect(field(page, field_name)).to_have_value(shown)


def test_breite_percent_after_a_handle_drag_halves_the_shown_width(editor):
    page = turned_group(editor, user(), *SHAPES)
    drag_se_outward(page)
    enter(page, "Breite", "80")
    expect(field(page, "Breite")).to_have_value("80")
    enter(page, "Breite %", "50")
    expect(field(page, "Breite")).to_have_value("40")


def test_a_percent_of_a_handle_dragged_group_shows_half_its_size(editor):
    """Edge case: the percent field halves a dragged group, measured on what it shows now."""
    page = turned_group(editor, user(), *SHAPES)
    # Late, as on a loaded runner: Höhe read before the drag's last step lands is not its size (#753).
    page.evaluate(LATE)
    drag_se_outward(page)
    before = settled(page, "Höhe")
    enter(page, "Höhe %", "50")
    expect(field(page, "Höhe")).to_have_value(f"{before / 2:g}".replace(".", ","))


@pytest.mark.xfail(
    BROWSER == "webkit",
    reason="#793: in WebKit under CI load the typed 80 is lost and Breite keeps the drag's "
    "69,15; 48 of 48 pass on 48 workers, and in the same CI run a fill into the key's name "
    "was lost too (test_account_tokens), so maybe the fill and not the drag",
    strict=False,
)
def test_a_typed_size_is_one_undo_step_after_a_handle_drag(editor):
    """Edge case: one undo takes back the one typed entry, the handle drag stays."""
    client = user()
    page = turned_group(editor, client, *SHAPES)
    drag_se_outward(page)
    field(page, "Breite").fill("80")
    # #793: tells a fill that was lost from an Enter that set nothing.
    expect(field(page, "Breite")).to_have_value("80")
    field(page, "Breite").press("Enter")
    expect(field(page, "Breite")).to_have_value("80")
    page.keyboard.press("Control+z")
    expect(field(page, "Breite")).not_to_have_value("80")


def test_a_drag_and_an_undo_after_a_typed_size_show_the_measured_size(editor):
    """The width on screen when the drag ends is the one undo restores (#716).

    A pointer move renders on the scheduler. Under load that render lands after the
    pointer is up, so the panel still shows an older width (60.01, or 67.7 in CI)
    while undo brings back the drag's own (69.14). The move is drawn before it returns.
    """
    page = turned_group(editor, user(), *SHAPES)
    # Late, as on a loaded runner: the width is read before the scheduler could paint (#716).
    page.evaluate(LATE)
    drag_se_outward(page)
    measured = number(page, "Breite")
    field(page, "Breite").fill("80")
    # #689, #793: tells a fill that was lost from an Enter that set nothing.
    expect(field(page, "Breite")).to_have_value("80")
    field(page, "Breite").press("Enter")
    expect(field(page, "Breite")).to_have_value("80")
    page.keyboard.press("Control+z")
    assert number(page, "Breite") == pytest.approx(measured, abs=0.02)
    enter(page, "Breite", "80")
    expect(field(page, "Breite")).to_have_value("80")
    drag_se_outward(page)
    expect(field(page, "Breite")).not_to_have_value("80")
