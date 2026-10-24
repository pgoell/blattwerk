"""A print that misses bows, tints, line numbers or a hairline is over the limit."""

import io
import json
import re
import subprocess
import sys

import pytest
from PIL import Image
from pixels import (
    INK,
    LIMIT,
    TILE,
    as_png,
    diff,
    measures,
    over,
)
from test_pixels import (
    BLIND,
    BLUE_RED,
    COLOURS,
    LONG,
    SHIFTS,
    SHOT,
    WORDS,
    at,
    blocks,
    bowed,
    drawn,
    faults,
    fuller,
    planted,
    tinted,
)
from ui import (
    BROWSER,
    LINE,
    TEXT,
    box,
    png,
    user,
)


def test_a_block_that_prints_elsewhere_is_over_the_limit(browser, server):
    # A sentence 10 mm lower: far less of the page than a filled box.
    client = user()
    found = planted(browser, server, *(blocks("text", client, y=y) for y in (100, 110)))
    assert found["page"] > LIMIT, found


@pytest.mark.parametrize("case", COLOURS)
def test_a_wrong_colour_is_over_the_limit(browser, server, case):
    """X1"""
    found = planted(browser, server, *([block] for block in COLOURS[case]))
    assert found["ink"] > INK, found
    assert found["page"] < LIMIT and found["tile"] < TILE, found


def test_missing_bows_are_over_the_limit(browser, server):
    # The bows on the screen and none in print.
    found = planted(browser, server, bowed(), bowed(on=False))
    assert found["ink"] > INK, found


def test_missing_line_numbers_are_over_the_limit(browser, server):
    # The numbers on the screen and none in print.
    numbered = [at("text", {**TEXT, "text": LONG, "lines": 1}, y=20, h=120, w=100, x=30)]
    plain = [at("text", {**TEXT, "text": LONG}, y=20, h=120, w=100, x=30)]
    found = planted(browser, server, numbered, plain)
    assert found["ink"] > INK, found


def test_the_answer_key_prints_line_numbers(browser, server):
    # A gap on the page too: the answer key shows its word on the screen and in print alike.
    client = user()
    gapped = {"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt laut"}]}
    gap = at(
        "text",
        {**TEXT, "text": "Der Hund bellt laut", "rich": [gapped], "gapWidth": 12, "lines": 1},
        x=150,
        y=20,
        w=40,
        h=60,
    )
    assert not faults(browser, server, client, [*fuller("line numbers", client), gap], solved=True)


def test_bows_under_the_wrong_syllables_are_over_a_limit(browser, server):
    # The same word with the same number of bows: on the screen each break lies a letter or two
    # further on than in print, which splits it as "Mar-me-la-den-glä-ser".
    word = {**TEXT, "text": "Marmeladengläser", "size": 40, "syllables": True}
    wrong = {**word, "breaks": {"marmeladengläser": [4, 7, 9, 12, 14]}}
    found = planted(browser, server, [at("text", wrong)], [at("text", word)])
    assert found["tile"] > TILE or found["ink"] > INK, found


def test_missing_tints_are_over_the_limit(browser, server):
    # The colours on the screen and none in print.
    found = planted(browser, server, tinted(), tinted(on=False))
    assert found["ink"] > INK, found


def test_swapped_tints_are_over_a_limit(browser, server):
    # One large word in the pair, and the pair the other way round: print has red first.
    word = {**TEXT, "text": "Marmelade", "size": 40}
    swapped = {**word, "tints": list(reversed(BLUE_RED))}
    found = planted(
        browser, server, [at("text", {**word, "tints": BLUE_RED})], [at("text", swapped)]
    )
    assert found["ink"] > INK, found


def test_a_missing_hairline_is_over_the_limit(browser, server):
    """X2"""
    hairline = at("shape", {**LINE, "strokeWidth": 0.3}, y=160, h=10)
    found = planted(browser, server, [at("text", WORDS), hairline], [at("text", WORDS)])
    assert found["ink"] > INK, found
    assert found["page"] < LIMIT, found


@BLIND
@pytest.mark.parametrize("case", SHIFTS)
def test_a_shift_of_half_a_millimetre_is_over_the_limit(browser, server, case):
    """X3"""
    found = planted(browser, server, *([SHIFTS[case](y)] for y in (60, 60.5)))
    assert found["tile"] > TILE, found
    assert found["page"] < LIMIT, found


def test_grid_and_guide_lines_are_no_difference(browser, server):
    client = user()
    page = {"blocks": blocks("text", client), "grid": 5, "guides": {"x": [50], "y": [80]}}
    assert not faults(browser, server, client, page)


def test_diff_counts_the_pixels_that_differ():
    red, white = png(), png(b"\xff\xff\xff")
    assert diff(red, red)[0] == 0
    assert diff(red, white)[0] == 1
    # Less than the tolerance apart is the same: an edge that is smoothed another way.
    assert diff(png(b"\xff\xff\xff"), png(b"\xd0\xd0\xd0"))[0] == 0
    # A page cut to half its height differs by the half that is gone; a row of rounding does not.
    page = Image.new("RGB", (200, 300), "white")
    assert diff(as_png(page), as_png(page.crop((0, 0, 200, 150))))[0] == 0.5
    assert diff(as_png(page), as_png(page.crop((0, 0, 200, 299))))[0] == 0
    marked = Image.open(io.BytesIO(diff(red, white)[1]))
    assert marked.size == (3, 2) and marked.convert("RGB").getpixel((0, 0)) == (255, 0, 0)


def test_a_measure_over_its_limit_names_its_tile_and_its_number():
    box, line = (40, 40, 80, 80), (40, 150, 80, 151)
    page = drawn((box, "#222222"), (line, "#222222"))
    assert over(page, page) == []
    # A paler box moves no pixel past the tolerance, and lacks a fifth of the ink.
    (found,) = over(page, drawn((box, "#555555"), (line, "#222222")))
    assert re.fullmatch(r"ink 0\.2\d+, limit [\d.]+ around \d5, \d5 mm: red .*", found), found
    # A line that is gone is all the ink of its tiles, and little of the page.
    found = measures(page, drawn((box, "#222222")))[0]
    assert found["ink"][0] == 1 and found["page"][0] < LIMIT
    assert re.fullmatch(
        r" around \d5, 1[45]5 mm: red .* on the screen, 0\.0 in print", found["ink"][1]
    )
    # A box 2 mm lower: the tiles its edges lie in.
    found = measures(page, drawn(((40, 42, 80, 82), "#222222"), (line, "#222222")))[0]
    assert found["tile"][0] > 0.1 > found["page"][0]


def test_shot_writes_the_diff_and_prints_the_share(tmp_path):
    pages = tmp_path / "pages.json"
    pages.write_text(json.dumps([[box("a", "text", TEXT)]]))
    out = tmp_path / "out"
    run = subprocess.run(
        [sys.executable, str(SHOT), str(pages), str(out)], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    assert {p.name for p in out.iterdir()} == {"screen.png", "pdf.png", "diff.png"}
    # The browser it starts is the one whose limits it reads.
    assert f"In {BROWSER}:" in run.stdout
    found = re.search(
        r"([\d.]+) % of the pixels differ, within the limit of ([\d.]+) %", run.stdout
    )
    assert found and float(found[1]) < LIMIT * 100 and float(found[2]) == LIMIT * 100
    for name, limit in ("tile", TILE), ("ink", INK):
        told = re.search(rf"{name} ([\d.]+), within the limit of ([\d.]+)", run.stdout)
        assert told and float(told[1]) < limit == float(told[2])
