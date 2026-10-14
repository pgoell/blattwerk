"""The Uhr on screen and on paper: its hands, faces, tasks, key and shape.

The docstrings name what each test proves. The model in frontend/src/uhr.ts sets the times and the
words; the tests read the svg's lines and texts, on the screen and in the print.
"""

import pytest
from pixels import LIMITS, measures, over, screen_and_print
from test_feed_print import printed, sheet_id
from test_suchsel_print import key_print
from ui import at, box, sheet, user

PROPS = {
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
    "fill": "free",
    "times": [210, 585, 720, 370],
    "seed": 7,
}
RED = "rgb(192, 57, 43)"
# A gap in a text: the helper waits for its answer colour, which a field alone never shows.
GAP = {
    "text": "Der Hund bellt",
    "size": 14,
    "align": "left",
    "bank": 1,
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
}
# The centre of a face is at (50, 50) of its cell; each hand's angle, clockwise from 12, in degrees.
ANGLES = """els => els.map(g => {
    const c = g.querySelector('circle.face');
    const cx = +c.getAttribute('cx'), cy = +c.getAttribute('cy');
    const angle = s => {
        const l = g.querySelector(`line.${s}`);
        const dx = +l.getAttribute('x2') - cx, dy = +l.getAttribute('y2') - cy;
        return (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360;
    };
    return [g.getAttribute('data-time'), angle('hour'), angle('minute')];
})"""
# Each hand's length and stroke width, of the first clock.
HANDS = """g => ['hour', 'minute'].map(s => {
    const l = g.querySelector(`line.${s}`);
    const dx = +l.getAttribute('x2') - 50, dy = +l.getAttribute('y2') - 50;
    return [Math.hypot(dx, dy), +l.getAttribute('stroke-width')];
})"""


def clocks(page):
    return at(page, "u").locator("g.clock")


def expected(time):
    """The hour hand's and the minute hand's angle, as the contract says."""
    h, m = divmod(time, 60)
    return 30 * (h % 12) + m / 2, 6 * m


def turned(got, want):
    """The angle apart, on the circle: 359.9 and 0.1 are 0.2 degrees apart."""
    return abs((got - want + 180) % 360 - 180)


def check_hands(rows):
    for time, hour, minute in rows:
        want_hour, want_minute = expected(int(time))
        assert turned(hour, want_hour) <= 0.5, (time, hour, want_hour)
        assert turned(minute, want_minute) <= 0.5, (time, minute, want_minute)


def test_the_hands_stand_at_the_right_angle_on_screen_and_in_print(editor, browser, server):
    """3:30, 9:45, 12:00 and 6:10: the hands on screen and in print, to half a degree."""
    page = editor(box("u", "uhr", PROPS, w=200, h=60), client=user())
    check_hands(clocks(page).evaluate_all(ANGLES))
    paper = printed(browser, server, sheet_id(page))
    check_hands(paper.locator(".uhr g.clock").evaluate_all(ANGLES))
    paper.context.close()


@pytest.mark.parametrize("solved", [False, True])
def test_the_screen_and_the_print_draw_the_same_clock(browser, server, solved):
    """The screen and the PDF of four clocks, the pupil's sheet and the key."""
    client = user()
    mine = sheet(
        client,
        [box("t", "text", GAP, z=1, h=20), box("u", "uhr", PROPS, z=2, w=200, h=60)],
    )["id"]
    screen, printed_png = screen_and_print(
        browser, server, client, mine, hide_gaps=not solved, solved=solved
    )
    found, _ = measures(screen, printed_png)
    assert not over(screen, printed_png), {name: found[name] for name in LIMITS}


def test_the_hour_hand_is_shorter_and_thicker_than_the_minute_hand(editor):
    """Each hand's length and stroke: the hour hand 25 long and 4.5 thick, the minute 40 and 1.6."""
    page = editor(box("u", "uhr", PROPS, w=200, h=60), client=user())
    [hour, minute] = clocks(page).first.evaluate(HANDS)
    assert hour[0] < minute[0]
    assert hour[1] > minute[1]


@pytest.mark.parametrize(
    "numbers, ring, minutes, figures, ticks",
    [
        ("all", False, True, 12, 60),
        ("quarters", False, True, 4, 60),
        ("none", False, True, 0, 60),
        ("all", True, True, 24, 60),
        ("all", False, False, 12, 12),
    ],
)
def test_the_face_shows_the_numbers_and_ticks_it_is_set_to(
    editor, numbers, ring, minutes, figures, ticks
):
    """Numbers all, quarters or none give 12, 4 or 0 numbers; the ring adds 13 to 24; minutes off
    leaves the 12 hour ticks of the 60."""
    props = {**PROPS, "numbers": numbers, "ring": ring, "minutes": minutes, "times": [210]}
    page = editor(box("u", "uhr", props, w=100, h=60), client=user())
    face = clocks(page).first
    assert face.locator("text.number").count() == figures
    assert face.locator("g.ticks line").count() == ticks
    if ring:
        assert face.locator("text.number").evaluate_all(
            "els => els.map(e => +e.textContent).slice(12)"
        ) == list(range(13, 25))


def test_read_asks_for_the_time_in_a_box_and_the_key_writes_it_in_red(editor, browser, server):
    """Task read with the box: `__:__ Uhr` for the pupil; the key writes 3:30 Uhr in red for it."""
    props = {**PROPS, "task": "read", "answer": "box", "times": [210]}
    client = user()
    mine = sheet(client, [box("u", "uhr", props, w=100, h=60)])["id"]
    page = editor(box("u", "uhr", props, w=100, h=60), client=client)
    assert clocks(page).first.locator("text.task").text_content() == "__:__ Uhr"
    paper = printed(browser, server, mine)
    assert paper.locator(".uhr text.task").first.text_content() == "__:__ Uhr"
    paper.context.close()
    key = key_print(browser, server, mine)
    answer = key.locator(".uhr text.answer").first
    assert answer.evaluate("e => getComputedStyle(e).fill") == RED
    assert answer.text_content() == "3:30 Uhr"
    key.context.close()


def test_draw_writes_the_time_and_the_key_draws_the_hands_in_red(browser, server):
    """Task draw: no hands and the written time for the pupil; the key draws both hands in red."""
    props = {**PROPS, "task": "draw", "times": [585]}
    client = user()
    mine = sheet(client, [box("u", "uhr", props, w=100, h=60)])["id"]
    paper = printed(browser, server, mine)
    assert paper.locator(".uhr line.hour").count() == 0
    assert paper.locator(".uhr line.minute").count() == 0
    assert paper.locator(".uhr text.task").first.text_content() == "9:45 Uhr"
    paper.context.close()
    key = key_print(browser, server, mine)
    assert (
        key.locator(".uhr line.hour").first.evaluate("e => e.getAttribute('stroke')") == "#c0392b"
    )
    assert (
        key.locator(".uhr line.minute").first.evaluate("e => e.getAttribute('stroke')") == "#c0392b"
    )
    key.context.close()


def test_six_clocks_in_three_columns_and_each_clock_stays_round(editor):
    """Count 6 and cols 3 give 6 clocks in a 300 by 260 viewBox; faces stay round."""
    props = {**PROPS, "count": 6, "cols": 3, "times": [210, 585, 720, 370, 60, 900]}
    page = editor(box("u", "uhr", props, w=180, h=40), client=user())
    assert clocks(page).count() == 6
    assert at(page, "u").locator("svg").get_attribute("viewBox") == "0 0 300 260"
    wide = at(page, "u").locator("circle.face").first.bounding_box()
    assert wide["width"] == pytest.approx(wide["height"], abs=1)
    # Resize the block to 60 by 120 mm: the face keeps its round shape.
    tall = editor(box("u", "uhr", props, w=60, h=120), client=user())
    round_ = at(tall, "u").locator("circle.face").first.bounding_box()
    assert round_["width"] == pytest.approx(round_["height"], abs=1)


def test_the_answer_line_is_drawn_and_the_key_writes_the_time_over_it(browser, server):
    """Answer line: the pupil's writing line, and the key's red time on it."""
    props = {**PROPS, "answer": "line", "count": 1, "times": [210]}
    client = user()
    mine = sheet(client, [box("u", "uhr", props, w=100, h=60)])["id"]
    paper = printed(browser, server, mine)
    assert paper.locator(".uhr line.answer").count() == 1
    assert paper.locator(".uhr text.answer").count() == 0
    paper.context.close()
    key = key_print(browser, server, mine)
    assert key.locator(".uhr text.answer").first.text_content() == "3:30 Uhr"
    key.context.close()


def test_fifteen_thirty_points_where_three_thirty_does(editor):
    """In the 24 hour format 15:30 has the same hand angles as 3:30, as the face is 12 hours."""
    props = {**PROPS, "format": "24", "times": [930, 210]}
    page = editor(box("u", "uhr", props, w=100, h=60), client=user())
    rows = clocks(page).evaluate_all(ANGLES)
    assert turned(rows[0][1], rows[1][1]) <= 0.5
    assert turned(rows[0][2], rows[1][2]) <= 0.5
