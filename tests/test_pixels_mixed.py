"""Mixed script and a linked Lineatur print as the screen shows them."""

import pytest
from pixels import (
    over,
    screen_and_print,
)
from test_pixels import (
    FULLER,
    KINDS,
    LINEATUR,
    LISTED,
    MIXED,
    MIXED_TEXT,
    TURNED,
    at,
    blocks,
    faults,
    fuller,
    mixed_case,
)
from ui import (
    TEXT,
    box,
    sheet,
    user,
)


@pytest.mark.parametrize("case", MIXED)
def test_a_mixed_text_prints_as_the_screen_shows_it(browser, server, case):
    """The pupil's view: the mixed words on the screen, the lines empty there as in print."""
    client = user()
    assert not faults(browser, server, client, mixed_case(case))


@pytest.mark.parametrize("case", MIXED)
def test_a_mixed_text_prints_as_the_answer_key_shows_it(browser, server, case):
    """The answer key: the words as typed on their lines, in red, on the screen and in the PDF."""
    client = user()
    assert not faults(browser, server, client, mixed_case(case), solved=True)


@pytest.mark.parametrize("font", ["nord", "sued"])
def test_an_outline_in_druckschrift_nord_and_sued_prints_as_the_screen_shows_it(
    browser, server, font
):
    """Issue #499: WebKit's screen laid the outline of a Lineatur a pixel lower than the print."""
    client = user()
    line = {
        **box(
            "a",
            "ruling",
            {
                "kind": "l1",
                "color": "#222222",
                "font": font,
                "text": "jagen Igel und Maus im Garten",
                "trace": "outline",
            },
        ),
        "x": 45,
        "y": 37,
        "w": 120,
    }
    assert not faults(browser, server, client, [line])


def test_a_mix_left_out_of_the_print_is_over_the_limit(browser, server):
    """The mixed words on the screen and the plain words in print: the letters differ."""
    client = user()
    shown = sheet(client, mixed_case("after"))["id"]
    plain = {**TEXT, "text": MIXED_TEXT}
    paper = sheet(client, [at("text", plain, y=20, h=90)])["id"]
    screen, _ = screen_and_print(browser, server, client, shown)
    _, printed = screen_and_print(browser, server, client, paper)
    assert over(screen, printed)


@pytest.mark.parametrize("kind, mode", LINEATUR)
def test_a_linked_lineatur_prints_as_the_screen_shows_it(browser, server, kind, mode):
    client = user()
    props = {"kind": kind, "color": "#222222", "list": mode, "font": "sas"}
    assert not faults(browser, server, client, [at("ruling", props, h=60)], words=LISTED)


@pytest.mark.parametrize("mode", ["copy", "row"])
def test_a_turned_linked_lineatur_prints_as_the_screen_shows_it(browser, server, mode):
    client = user()
    props = {"kind": "l3", "color": "#222222", "list": mode}
    assert not faults(browser, server, client, [at("ruling", props, h=60, angle=30)], words=LISTED)


def test_a_linked_lineatur_in_a_group_prints_as_the_screen_shows_it(browser, server):
    client = user()
    props = {"kind": "l4", "color": "#222222"}
    grouped = [
        at("ruling", {**props, "list": "copy"}, y=60, h=40, group=["g"]),
        at("ruling", {**props, "list": "row"}, y=110, h=40, group=["g"]),
    ]
    assert not faults(browser, server, client, grouped, words=LISTED)


def test_a_list_left_out_of_the_print_is_over_the_limit(browser, server):
    """The words on the screen and the blank print of the same sheet: the letters differ."""
    client = user()
    block = [at("ruling", {"kind": "l4", "color": "#222222", "list": "row"}, h=60)]
    shown = sheet(client, block, words=LISTED)["id"]
    paper = sheet(client, block)["id"]
    screen, _ = screen_and_print(browser, server, client, shown)
    _, printed = screen_and_print(browser, server, client, paper)
    assert over(screen, printed)


@pytest.mark.parametrize("kind", KINDS)
def test_a_block_prints_as_the_screen_shows_it(browser, server, kind):
    client = user()
    assert not faults(browser, server, client, blocks(kind, client))


@pytest.mark.parametrize("kind", TURNED)
def test_a_turned_block_prints_as_the_screen_shows_it(browser, server, kind):
    client = user()
    # Not a right angle: that would hide a turn about another point.
    assert not faults(browser, server, client, blocks(kind, client, angle=30))


@pytest.mark.parametrize("case", FULLER)
def test_a_fuller_page_prints_as_the_screen_shows_it(browser, server, case):
    client = user()
    assert not faults(browser, server, client, fuller(case, client))


def test_the_zoom_and_the_page_number_are_no_difference(browser, server):
    client = user()
    # Three pages: the last ones lie where the zoom and "Seite 1 von 3" float over the desk.
    mine = sheet(client, *(blocks(kind, client) for kind in ("text", "shape", "ruling")))["id"]
    for page in (1, 2):
        assert not over(*screen_and_print(browser, server, client, mine, page))
