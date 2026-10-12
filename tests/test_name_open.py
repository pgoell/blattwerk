"""The name line of the Klassenarbeit, open for writing, stays inside its frame and clear of the
score box (issue #401, a regression of PR #384)."""

from playwright.sync_api import expect
from test_presets import opened
from ui import at

WORD = '.block.sel input[aria-label^="Feld"]'
# The name line has its fields, each in a span over the line that stood there.
LINES = ".fields i"


def klassenarbeit(editor):
    """The editor on the Klassenarbeit, as the template makes it, and the name and score ids."""
    first, rest = opened("Klassenarbeit")
    page = editor(*first, pages=rest)
    name = next(b["id"] for b in first if b["type"] == "name")
    score = next(b["id"] for b in first if b["type"] == "points")
    return page, name, score


def open_name(page, name):
    at(page, name).dblclick()
    expect(page.locator(WORD)).to_have_count(3)


def inside(outer, inner, tolerance=1):
    return (
        inner["x"] >= outer["x"] - tolerance
        and inner["y"] >= outer["y"] - tolerance
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + tolerance
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + tolerance
    )


def overlaps(one, two):
    return (
        one["x"] < two["x"] + two["width"]
        and two["x"] < one["x"] + one["width"]
        and one["y"] < two["y"] + two["height"]
        and two["y"] < one["y"] + one["height"]
    )


def desk_scrolls_sideways(page):
    return page.evaluate(
        "() => { const d = document.querySelector('.desk'); return d.scrollWidth > d.clientWidth; }"
    )


def test_the_open_name_lines_fields_lie_inside_its_frame(editor):
    """A1: each field of the open name line lies inside the line's box, clear of the score box."""
    page, name, score = klassenarbeit(editor)
    frame = at(page, name).bounding_box()
    box = at(page, score).bounding_box()
    open_name(page, name)
    for i in range(3):
        field = page.locator(WORD).nth(i).bounding_box()
        assert inside(frame, field), (i, field, frame)
        assert not overlaps(field, box), (i, field, box)


def test_the_desk_gets_no_bottom_scrollbar_while_the_name_line_is_open(editor):
    """A2: the desk scrolls sideways neither before nor while the name line is open."""
    page, name, _ = klassenarbeit(editor)
    assert not desk_scrolls_sideways(page)
    open_name(page, name)
    assert not desk_scrolls_sideways(page)


def test_each_open_field_stands_where_its_line_stood(editor):
    """I1: each field lies where its line lay, and Enter closes it to the lines as before."""
    page, name, _ = klassenarbeit(editor)
    lines = [at(page, name).locator(LINES).nth(i).bounding_box() for i in range(3)]
    open_name(page, name)
    for i in range(3):
        field = page.locator(WORD).nth(i).bounding_box()
        assert abs(field["x"] - lines[i]["x"]) <= 1.5, (i, field, lines[i])
        right = field["x"] + field["width"]
        assert abs(right - lines[i]["x"] - lines[i]["width"]) <= 1.5, (i, field, lines[i])
    page.keyboard.press("Enter")
    expect(page.locator(WORD)).to_have_count(0)
    for i in range(3):
        after = at(page, name).locator(LINES).nth(i).bounding_box()
        assert abs(after["x"] - lines[i]["x"]) <= 1, (i, after, lines[i])
        assert abs(after["width"] - lines[i]["width"]) <= 1, (i, after, lines[i])


def test_a_long_word_stays_inside_the_open_name_line(editor):
    """I2: sixty letters typed into the third field keep every field inside the frame, and the desk
    scrolls sideways no more than before."""
    page, name, score = klassenarbeit(editor)
    frame = at(page, name).bounding_box()
    box = at(page, score).bounding_box()
    open_name(page, name)
    third = page.locator(WORD).nth(2)
    third.click()
    page.keyboard.press("End")
    page.keyboard.type("abcdefghij" * 6)
    for i in range(3):
        field = page.locator(WORD).nth(i).bounding_box()
        assert inside(frame, field), (i, field, frame)
        assert not overlaps(field, box), (i, field, box)
    assert not desk_scrolls_sideways(page)
    expect(third).to_have_value("Klasse" + "abcdefghij" * 6)
