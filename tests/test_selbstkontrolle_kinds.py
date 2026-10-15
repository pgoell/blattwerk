"""Rule 13 for the Selbstkontrolle: every maths block with results feeds it. The list of a linked
block must hold exactly what that block's own answer key writes in red, a check that does not go
through the Selbstkontrolle's model.
"""

import pytest
from playwright.sync_api import expect
from test_selbstkontrolle import SK
from test_suchsel_print import key_print
from ui import box, maths, sheet, user

WALL = {
    "base": 3,
    "count": 4,
    "columns": 4,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
DREI = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 7}
STRAHL = {
    "start": 0,
    "end": 20,
    "minor": 1,
    "major": 5,
    "labels": "major",
    "size": 12,
    "cut": False,
    "tasks": "random",
    "boxes": 3,
    "arrows": 0,
    "jumps": False,
    "seed": 7,
}
FELD = {
    "look": "tafel",
    "from": 1,
    "show": "random",
    "hide": 6,
    "tint": "none",
    "times": 2,
    "line": 1,
    "color": 1,
    "cut": False,
    "fill": "count",
    "dots": 0,
    "seed": 7,
}
UHR = {
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
    "times": [195, 600, 315, 135],
    "seed": 3,
}
GAP = {"ops": ["+"], "max": 20, "count": 3, "seed": 7, "format": "gap", "gaps": ["a"]}
WRITTEN = {"ops": ["+"], "max": 999, "count": 2, "seed": 7, "format": "written"}
COMPARE = {"ops": ["+"], "max": 20, "count": 3, "seed": 7, "format": "compare"}
# Where each block's key writes its answers.
ANSWERS = {
    "maths": ".maths u",
    "zahlenmauer": "text.answer",
    "rechendreieck": "text.answer",
    "zahlenstrahl": "text.answer",
    "hunderterfeld": "text.answer",
    "uhr": "text.answer",
}


def texts(locator):
    return sorted(" ".join(t.split()) for t in locator.all_text_contents())


@pytest.mark.parametrize(
    "kind, props, h",
    [
        ("zahlenmauer", WALL, 40),
        ("rechendreieck", DREI, 40),
        ("zahlenstrahl", STRAHL, 30),
        ("hunderterfeld", FELD, 100),
        ("uhr", UHR, 58.5),
    ],
)
def test_the_list_holds_what_the_blocks_own_key_writes(browser, server, kind, props, h):
    """Each kind but Rechnen: the mixed list equals the red answers of the linked block's key."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", kind, props, z=1, w=180, h=h, y=15),
            box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60, y=200),
        ],
    )["id"]
    paper = key_print(browser, server, mine)
    answers = texts(paper.locator(f".block:has(.{kind}) {ANSWERS[kind]}"))
    assert answers
    expect(paper.locator("ul.mixed li")).to_have_count(len(answers))
    assert texts(paper.locator("ul.mixed li")) == answers
    paper.context.close()


@pytest.mark.parametrize("limits", [GAP, WRITTEN, COMPARE], ids=["gap", "written", "compare"])
def test_rechnen_in_each_format_feeds_the_list(browser, server, limits):
    """Rechnen with gaps, written and compared: the list equals what its key writes in."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", "maths", maths(client, **limits), z=1, w=180, h=60, y=15),
            box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60, y=200),
        ],
    )["id"]
    paper = key_print(browser, server, mine)
    if limits is WRITTEN:
        # A written task's key is its squared paper; its result is the exercise's result.
        stored = client.get(f"/api/sheets/{mine}").json()["doc"]["pages"][0]["blocks"][0]
        answers = sorted(str(e["result"]) for e in stored["props"]["exercises"])
    elif limits is COMPARE:
        answers = texts(paper.locator(".maths .ring"))
    else:
        answers = texts(paper.locator(ANSWERS["maths"]))
    assert answers
    assert texts(paper.locator("ul.mixed li")) == answers
    paper.context.close()


def test_a_zahlenmauer_gets_a_letter_box_per_wall_clear_of_its_stones(browser, server):
    """Lösungswort: one box per wall beside its top stone, touching no stone; the key writes the
    letter of its wall in it."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", "zahlenmauer", WALL, z=1, w=180, h=40, y=15),
            box(
                "s",
                "selbstkontrolle",
                {**SK, "form": "word", "word": "ABCD", "links": ["m"]},
                z=2,
                w=180,
                h=60,
                y=200,
            ),
        ],
    )["id"]
    paper = key_print(browser, server, mine)
    letters = paper.locator(".zahlenmauer .letter")
    expect(letters).to_have_count(4)
    stones = [s.bounding_box() for s in paper.locator(".zahlenmauer .stone rect").all()]
    for one in letters.all():
        r = one.locator("rect").bounding_box()
        for s in stones:
            apart = (
                r["x"] >= s["x"] + s["width"]
                or s["x"] >= r["x"] + r["width"]
                or r["y"] >= s["y"] + s["height"]
                or s["y"] >= r["y"] + r["height"]
            )
            assert apart, (r, s)
    assert [t.strip() for t in letters.all_text_contents()] == ["A", "B", "C", "D"]
    paper.context.close()


def test_an_uhr_that_asks_to_draw_gives_no_result(browser, server):
    """An Uhr with task "draw" has nothing to write in: the list is empty."""
    client = user()
    mine = sheet(
        client,
        [
            box("m", "uhr", {**UHR, "task": "draw"}, z=1, w=180, h=58.5, y=15),
            box("s", "selbstkontrolle", {**SK, "links": ["m"]}, z=2, w=180, h=60, y=200),
        ],
    )["id"]
    paper = key_print(browser, server, mine)
    expect(paper.locator("div.selbstkontrolle")).to_have_count(1)
    assert paper.locator("ul.mixed li").count() == 0
    paper.context.close()
