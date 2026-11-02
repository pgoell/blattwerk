"""Issue 845: coloured clock hands, both times, the ray's end, times triangles, bases 2 and 6.

The model tests own the numbers. These check that the panel stores the setting and the drawing
follows it.
"""

from playwright.sync_api import expect
from test_gaps import step
from ui import at, box, doc, pick, user

UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "colours": False,
    "region": "nach",
    "count": 1,
    "cols": 1,
    "step": 60,
    "fill": "free",
    "times": [3 * 60 + 30],
    "seed": 1,
}
STRAHL = {
    "start": 0,
    "end": 4,
    "minor": 1,
    "major": 1,
    "labels": "all",
    "size": 12,
    "cut": False,
    "point": False,
    "under": False,
    "tasks": "free",
    "boxes": 0,
    "arrows": 0,
    "jumps": False,
    "seed": 1,
}
DREIECK = {
    "count": 1,
    "columns": 1,
    "max": 20,
    "given": "inner",
    "empty": False,
    "op": "+",
    "seed": 1,
}
WALL = {
    "base": 3,
    "count": 1,
    "columns": 1,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 1,
}


def props(page, client, kind):
    [block] = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == kind]
    return block["props"]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_a_clock_can_show_both_times_and_two_hand_colours(editor):
    """Format both writes 3:30 Uhr and 15:30 Uhr. Zeiger färben paints the hands blue and red."""
    client = user()
    drawn = {**UHR, "task": "draw", "format": "both", "colours": True}
    page = editor(box("u", "uhr", drawn, w=80, h=80), client=client)
    clock = at(page, "u").locator(".uhr")
    assert clock.locator("text.task").all_text_contents() == ["3:30 Uhr", "15:30 Uhr"]
    expect(clock.locator("line.hour")).to_have_count(0)
    pick(page, "u")
    step(page, lambda: field(page, "Aufgabe").select_option("read"))
    assert clock.locator("line.hour").get_attribute("stroke") == "#1a56db"
    assert clock.locator("line.minute").get_attribute("stroke") == "#e02424"
    step(page, lambda: field(page, "Zeiger färben").uncheck())
    assert clock.locator("line.hour").get_attribute("stroke") == "#222"
    assert clock.locator("line.minute").get_attribute("stroke") == "#222"
    stored = props(page, client, "uhr")
    assert stored["format"] == "both"
    assert stored["colours"] is False
    assert stored["task"] == "read"


def test_the_ray_can_end_in_an_arrow_with_ticks_below_the_line(editor):
    """Pfeil am Ende drops the last tick's stroke. Striche durchgehend hangs the others below the line."""
    client = user()
    page = editor(box("z", "zahlenstrahl", STRAHL, w=120, h=40), client=client)
    line = at(page, "z").locator(".zahlenstrahl")
    pick(page, "z")
    step(page, lambda: field(page, "Pfeil am Ende").check())
    step(page, lambda: field(page, "Striche durchgehend").check())
    axis = float(line.locator("line.axis").get_attribute("y1"))
    ticks = line.locator("g.tick")
    assert ticks.count() == 5
    assert ticks.last.locator("line").count() == 0
    stroke = ticks.first.locator("line")
    assert float(stroke.get_attribute("y1")) == axis
    assert float(stroke.get_attribute("y2")) > axis
    tip = line.locator("path.head").evaluate(
        "el => el.getAttribute('d').match(/-?[\\d.]+/g).map(Number)"
    )
    label = ticks.last.locator("text.label")
    assert tip[2] == float(label.get_attribute("x"))
    assert props(page, client, "zahlenstrahl")["point"] is True
    assert props(page, client, "zahlenstrahl")["under"] is True


def test_a_triangle_can_multiply_and_shows_the_times_sign(editor):
    """Mal stores op times, and the times sign sits in the middle of the triangle."""
    client = user()
    page = editor(box("d", "rechendreieck", DREIECK, w=80, h=70), client=client)
    tri = at(page, "d").locator(".rechendreieck")
    expect(tri.locator("text.op")).to_have_count(0)
    pick(page, "d")
    step(page, lambda: page.locator(".panel").get_by_role("button", name="Mal", exact=True).click())
    expect(tri.locator("text.op")).to_have_text("\u00d7")
    assert props(page, client, "rechendreieck")["op"] == "*"


def test_a_wall_can_have_two_or_six_base_stones(editor):
    """Grundsteine 2 draws 3 stones, 6 draws 21, and the choice is what is stored."""
    client = user()
    page = editor(box("w", "zahlenmauer", WALL, w=180, h=80), client=client)
    wall = at(page, "w").locator(".zahlenmauer g.wall").first
    pick(page, "w")
    step(page, lambda: field(page, "Grundsteine").select_option("2"))
    expect(wall.locator("g.stone")).to_have_count(3)
    assert props(page, client, "zahlenmauer")["base"] == 2
    step(page, lambda: field(page, "Grundsteine").select_option("6"))
    expect(wall.locator("g.stone")).to_have_count(21)
    assert props(page, client, "zahlenmauer")["base"] == 6
