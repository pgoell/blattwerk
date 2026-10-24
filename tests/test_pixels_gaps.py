"""A gap prints as the screen shows it, and as the answer key shows it."""

import pytest
from pixels import (
    over,
    screen_and_print,
)
from test_pixels import (
    GAPPED,
    LONG_GAP,
    at,
    faults,
    gapped,
)
from ui import (
    TEXT,
    sheet,
    user,
)


@pytest.mark.parametrize("case", GAPPED)
def test_a_gap_prints_as_the_screen_hides_it(browser, server, case):
    """A11 (1): the pupil's view, the words hidden on the screen."""
    client = user()
    assert not faults(browser, server, client, gapped(case), hide_gaps=True)


@pytest.mark.parametrize("case", GAPPED)
def test_a_gap_prints_as_the_answer_key_shows_it(browser, server, case):
    """A11 (2): the answer key, the words in their colour on the screen and in the PDF."""
    client = user()
    assert not faults(browser, server, client, gapped(case), solved=True)


@pytest.mark.parametrize("look", [{"hide_gaps": True}, {"solved": True}], ids=["hidden", "key"])
def test_a_long_gaps_line_is_as_dark_as_it_prints(browser, server, look):
    """#411: before #417 the screen drew a line with a quarter less ink than the print."""
    client = user()
    # No bank: its words would put letters into the tile of the line.
    text = {**TEXT, "text": "Der bellt", "rich": [{"runs": LONG_GAP}]}
    assert not faults(browser, server, client, [at("text", text, y=20, h=60)], **look)


def test_a_gap_left_out_of_the_print_is_over_the_limit(browser, server):
    """A11 (3): a gap on the screen and none in print: the hidden words show in print."""
    client = user()
    shown = sheet(client, gapped("text"))["id"]
    plain = {**TEXT, "text": "Der Hund bellt", "rich": [{"runs": [{"text": "Der Hund bellt"}]}]}
    paper = sheet(client, [at("text", plain, y=20, h=90)])["id"]
    screen, _ = screen_and_print(browser, server, client, shown, hide_gaps=True)
    _, printed = screen_and_print(browser, server, client, paper)
    assert over(screen, printed)
